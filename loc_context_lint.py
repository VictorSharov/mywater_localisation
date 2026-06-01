#!/usr/bin/env python3
"""Deterministic, token-free pre-audit of the translator `context` field.

Read-only companion to the LLM context audit (loc_context_audit_prompt.md). It
runs the checks a machine does *better* than a model — exact symbol existence and
exact string length — and emits ground-truth grounding signals (the real
call-sites of each key) so the LLM phase audits from facts instead of
re-deriving (and hallucinating) them.

iOS is the primary platform (the corpus is iOS-led; Android mirrors it). Android
is indexed only as a fallback: a citation counts as alive if it exists on *either*
platform, and a key counts as grounded if it is referenced on *either*. So a
genuinely Android-only string still resolves, and an iOS symbol that is simply
absent everywhere is a true dead citation.

It NEVER writes the corpus. Per key it reports:

  - usage_sites          iOS call-sites where the key is actually referenced
                         (R.string.localizable.<key> / NSLocalizedString("<key>" /
                         a "<key>" literal). The ground-truth iOS surface.
  - android_sites        Android call-sites (R.string.<key> / Strings.<key> /
                         @string/<key>) — the fallback surface for iOS-orphans.
  - referenced           "ios" | "android" | "both" | "none". "none" => plural /
                         InfoPlist / dynamic / server-only / genuinely orphan.
  - dead_citations       code symbols / *.swift filenames the context cites that
                         exist on NEITHER platform — a near-certain faithfulness
                         defect, caught here for free.
  - cap_violations       a "<=N chars" constraint whose longest shipped
                         translation exceeds N by MORE than the soft tolerance
                         (house style allows +5). A material overflow means the
                         cap is wrong or already broken.
  - placeholder_unexplained   t.en carries [%...] but the context never mentions it.
  - register_inconsistent     some family members carry `Register:` and others
                         don't (a consistency signal across passes).
  - family               key family (variant/number suffix stripped) for grouping.

EXISTENCE IS NECESSARY, NOT SUFFICIENT. A *live* citation can still name the wrong
surface (the string may not actually be rendered at the cited symbol — e.g. `year`
citing `BeveragesStatPeriod`, which uses the Calendar.year component, not the
localized string). That residue is the LLM's job. A *dead* citation, though, is
unambiguous and is the highest-precision signal this tool produces.

Outputs (analysis artifacts — written to /tmp, never the repo tree):
  - <out>.txt    human-readable report (default /tmp/context_lint.txt)
  - <out>.json   per-key machine-readable signals for the LLM audit phase
                 (default /tmp/context_lint.json)

Usage:
    python3 loc_context_lint.py                       # full scan, default outputs
    python3 loc_context_lint.py --key year --key or   # scan a subset (debug)
    python3 loc_context_lint.py --out /tmp/clint      # custom output prefix
    python3 loc_context_lint.py --no-android          # iOS-only (faster, noisier)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loc_corpus import DEFAULT_CORPUS, read_records  # noqa: E402

IOS_ROOT = Path(os.environ.get("MYWATER_IOS_REPO", "/Users/me/git/mywater_ios"))
ANDROID_ROOT = Path(os.environ.get("MYWATER_ANDROID_REPO", "/Users/me/git/mywater_android"))

# Directories never worth indexing (build output / deps / generated).
SKIP_DIRS = {".git", ".build", "DerivedData", "Pods", "Carthage", "build", "fastlane", "node_modules"}

# House style: "<=N chars" is a SOFT cap — a target may exceed it by a few chars
# (Dynamic Type / autoshrink / wrapping). Only a material overflow is a signal.
CAP_SOFT_TOLERANCE = 5

IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
SWIFT_FILE_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*\.swift)\b")
# `Type.member` chains — capture the leading (app- or SDK-) type token.
DOTTED_TYPE_RE = re.compile(r"\b([A-Z][A-Za-z0-9_]+)\.[A-Za-z_]")
# Bare multi-hump CamelCase tokens (app types like DefaultAwards, BeveragesStatPeriod).
CAMEL_RE = re.compile(r"\b([A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+){1,})\b")
# "<=N chars" / "~N characters" / "within N chars" style caps.
CAP_RE = re.compile(r"(\d+)\s*(?:char|character)s?", re.IGNORECASE)
REGISTER_RE = re.compile(r"(?mi)^\s*Register:")

R_STRING_RE = re.compile(r"R\.string\.localizable\.([A-Za-z_][A-Za-z0-9_]*)")
NSLOCAL_RE = re.compile(r'NSLocalizedString\(\s*"([^"]+)"')

# Android references: R.string.<key>, Strings.<key> (generated accessor), @string/<key>.
ANDROID_R_RE = re.compile(r"\bR\.string\.([A-Za-z_][A-Za-z0-9_]*)")
ANDROID_STRINGS_RE = re.compile(r"\bStrings\.([A-Za-z_][A-Za-z0-9_]*)")
ANDROID_XMLREF_RE = re.compile(r"@string/([A-Za-z_][A-Za-z0-9_]*)")
ANDROID_XMLDEF_RE = re.compile(r'<(?:string|plurals)\s+name="([^"]+)"')

# SDK/type tokens that are legitimately citable even if they never appear verbatim
# in app source — never flag these as "dead". Conservative: precision over recall.
SDK_ALLOW = {
    "Calendar", "Date", "DateFormatter", "DateComponents", "Locale", "TimeZone",
    "String", "Array", "Dictionary", "Set", "Int", "Double", "Float", "Bool",
    "URL", "URLSession", "Data", "Notification", "NotificationCenter",
    "UIView", "UILabel", "UIButton", "UIImage", "UIColor", "UIFont",
    "UINavigationBar", "UITableView", "UICollectionView", "UIViewController",
    "Text", "View", "Image", "Color", "Font", "Button", "VStack", "HStack",
    "Info", "InfoPlist", "Localizable", "AppDelegate", "SceneDelegate",
    "HealthKit", "HKQuantity", "WidgetKit", "AppIntent", "Siri", "SiriKit",
    # Added 2026-05-31 (Tier A adjudication, loc_audit_status.md § Context-audit):
    # mechanism / namespace tokens that are ALWAYS cited as a code reference, never
    # as the localized-string surface — so a context naming them is not a mismatch.
    "UIApplication", "UIAccessibility", "HKQuantityTypeIdentifier", "StoreKit",
    "A11y",  # app accessibility-identifier namespace (A11y.Settings.… — an id, not a surface)
}

# *.swift "filenames" the context legitimately cites that are NOT real files —
# the R.swift code-gen LIBRARY (contexts say "R.swift exposes it as foo()"), which
# SWIFT_FILE_RE would otherwise read as a dead file citation. (2026-05-31, as above.)
SWIFT_FILE_ALLOW = {"R.swift"}

# Words that look CamelCase-ish but are English prose / brand, not code symbols.
PROSE_ALLOW = {
    "VoiceOver", "AppStore", "MyWater", "HealthKit", "FaceID", "TouchID",
    "WeekDay", "WeekDays", "WatchOS", "WidgetKit",
    "LoremIpsum", "JavaScript", "TypeScript", "AppHud", "RudderStack",
    # repo doc references (e.g. "see TRANSLATION_STYLE.md") — never code symbols.
    "TRANSLATION_STYLE", "PIPELINE", "GLOSSARY", "EXPORT", "README",
    "CLAUDE", "AGENTS",
}


def iter_source_files(root: Path, suffixes: tuple[str, ...]) -> "list[Path]":
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(suffixes):
                out.append(Path(dirpath) / name)
    return out


class IOSIndex:
    """One-pass index of the iOS sources: identifier universe, swift filenames,
    directory (module) names, and the precise localized-string call-sites per key."""

    def __init__(self, root: Path):
        self.root = root
        self.identifiers: set[str] = set()
        self.filenames: set[str] = set()
        self.dir_names: set[str] = set()
        self.call_sites: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
        self._file_texts: dict[str, str] = {}
        self._alive_memo: dict[str, bool] = {}
        self._build()

    def alive(self, sym: str) -> bool:
        """True if `sym` is a real symbol here: an exact identifier / dir / filename
        stem, OR a CamelCase prefix of some identifier (SubscriptionWoman ->
        SubscriptionWomanViewController). Prefix — not substring — so a typo like
        `SpecialPrie` (no identifier STARTS with it, though it sits inside
        `SpecialPrice`) is still correctly dead. Memoized."""
        hit = self._alive_memo.get(sym)
        if hit is not None:
            return hit
        ok = (sym in self.identifiers or sym in self.dir_names
              or sym in self.filenames or f"{sym}.swift" in self.filenames
              or any(i.startswith(sym) for i in self.identifiers))
        self._alive_memo[sym] = ok
        return ok

    def _build(self) -> None:
        for path in iter_source_files(self.root, (".swift",)):
            self.filenames.add(path.name)
            self.dir_names.update(p.name for p in path.relative_to(self.root).parents if p.name)
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            rel = str(path.relative_to(self.root))
            self._file_texts[rel] = text
            self.identifiers.update(IDENT_RE.findall(text))
            for lineno, line in enumerate(text.splitlines(), 1):
                for m in R_STRING_RE.finditer(line):
                    self.call_sites[m.group(1)].append((rel, lineno, "R.string"))
                for m in NSLOCAL_RE.finditer(line):
                    self.call_sites[m.group(1)].append((rel, lineno, "NSLocalizedString"))

    def literal_sites(self, key: str, limit: int = 5) -> "list[tuple[str, int, str]]":
        """Best-effort fallback: files containing the bare "<key>" string literal.
        Used for keys with no precise call-site (sound ids, A11y ids, etc.)."""
        needle = f'"{key}"'
        hits: list[tuple[str, int, str]] = []
        for rel, text in self._file_texts.items():
            if needle in text:
                for lineno, line in enumerate(text.splitlines(), 1):
                    if needle in line:
                        hits.append((rel, lineno, "literal"))
                        if len(hits) >= limit:
                            return hits
        return hits


class AndroidIndex:
    """Fallback index of the Android sources: identifier universe (Kotlin),
    declared string-resource names (XML), and per-key reference call-sites."""

    def __init__(self, root: Path):
        self.root = root
        self.identifiers: set[str] = set()
        self.filenames: set[str] = set()
        self.dir_names: set[str] = set()
        self.string_names: set[str] = set()
        self.call_sites: dict[str, list[tuple[str, int, str]]] = defaultdict(list)
        self._alive_memo: dict[str, bool] = {}
        self._build()

    def alive(self, sym: str) -> bool:
        """Android analog of IOSIndex.alive (identifier / dir / string-name / prefix)."""
        hit = self._alive_memo.get(sym)
        if hit is not None:
            return hit
        ok = (sym in self.identifiers or sym in self.dir_names
              or sym in self.string_names
              or any(i.startswith(sym) for i in self.identifiers))
        self._alive_memo[sym] = ok
        return ok

    def _build(self) -> None:
        for path in iter_source_files(self.root, (".kt", ".kts", ".xml", ".java")):
            self.filenames.add(path.name)
            self.dir_names.update(p.name for p in path.relative_to(self.root).parents if p.name)
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            rel = str(path.relative_to(self.root))
            is_xml = path.suffix == ".xml"
            if not is_xml:
                self.identifiers.update(IDENT_RE.findall(text))
            for lineno, line in enumerate(text.splitlines(), 1):
                if is_xml:
                    for m in ANDROID_XMLDEF_RE.finditer(line):
                        self.string_names.add(m.group(1))
                    for m in ANDROID_XMLREF_RE.finditer(line):
                        self.call_sites[m.group(1)].append((rel, lineno, "@string"))
                else:
                    for m in ANDROID_R_RE.finditer(line):
                        self.call_sites[m.group(1)].append((rel, lineno, "R.string"))
                    for m in ANDROID_STRINGS_RE.finditer(line):
                        self.call_sites[m.group(1)].append((rel, lineno, "Strings"))


def family_of(key: str) -> str:
    """Group siblings: strip a trailing variant/number suffix.
    text1_2M -> text1 ; ach_descr4 -> ach_descr ; notification1_1 -> notification1."""
    fam = re.sub(r"_?\d+[MF]?$", "", key)
    return fam or key


def extract_cited_symbols(context: str) -> "list[tuple[str, str]]":
    """(symbol, kind) pairs the context cites that look like code, deduped."""
    found: dict[str, str] = {}
    for m in SWIFT_FILE_RE.finditer(context):
        if m.group(1) in SWIFT_FILE_ALLOW:
            continue
        found.setdefault(m.group(1), "file")
    for m in DOTTED_TYPE_RE.finditer(context):
        tok = m.group(1)
        if tok not in SDK_ALLOW and tok not in PROSE_ALLOW:
            found.setdefault(tok, "type")
    for m in CAMEL_RE.finditer(context):
        tok = m.group(1)
        if tok.endswith(".swift"):
            continue
        if tok in SDK_ALLOW or tok in PROSE_ALLOW:
            continue
        found.setdefault(tok, "camel")
    return [(s, k) for s, k in found.items()]


def longest_translation(t: dict) -> tuple[int, str]:
    """(max char length across all non-empty translations, the lang code)."""
    best = (0, "")
    for lang, val in (t or {}).items():
        if isinstance(val, str):
            if len(val) > best[0]:
                best = (len(val), lang)
        elif isinstance(val, dict):  # plural forms
            for form_val in val.values():
                if isinstance(form_val, str) and len(form_val) > best[0]:
                    best = (len(form_val), f"{lang}.plural")
    return best


def lint_record(rec: dict, ios: IOSIndex, andr: "AndroidIndex | None") -> dict:
    key = rec.get("key", "")
    context = rec.get("context", "") or ""
    t = rec.get("t", {}) or {}
    en = t.get("en", "")
    en_str = en if isinstance(en, str) else json.dumps(en, ensure_ascii=False)

    # Ground-truth iOS call-sites (precise first, literal fallback).
    sites = ios.call_sites.get(key, [])
    if not sites:
        sites = ios.literal_sites(key)
    site_strs = [f"{p}:{ln} ({kind})" for p, ln, kind in sites[:8]]

    # Android fallback call-sites.
    android_strs: list[str] = []
    android_defined = False
    if andr is not None:
        asites = andr.call_sites.get(key, [])
        android_strs = [f"{p}:{ln} ({kind})" for p, ln, kind in asites[:6]]
        android_defined = key in andr.string_names

    if sites and android_strs:
        referenced = "both"
    elif sites:
        referenced = "ios"
    elif android_strs or android_defined:
        referenced = "android"
    else:
        referenced = "none"

    # Citation analysis. A cited code token is "alive" if it exists ANYWHERE on
    # either platform — as an identifier, a filename, or a directory/module name.
    #   dead             — alive nowhere. Truly nonexistent (typo / stale). High precision.
    #   surface_mismatch — alive (a real module/screen) BUT absent from THIS key's
    #                      real call-site paths. The string is rendered elsewhere
    #                      than the context claims (e.g. month/year citing the
    #                      stat-period module while rendered in the weight picker).
    #                      Only computed when the key has >=1 precise R.string site
    #                      (literal/generated-only sites carry no module path).
    site_paths = [p for p, _, kind in sites if kind in ("R.string", "NSLocalizedString")]
    site_blob = " ".join(site_paths)
    have_precise = bool(site_paths)
    dead = []
    surface_mismatch = []
    for sym, kind in extract_cited_symbols(context):
        if kind == "file":  # *.swift filenames are iOS-only by nature
            alive = sym in ios.filenames
        else:
            alive = ios.alive(sym) or (andr is not None and andr.alive(sym))
        if not alive:
            dead.append({"symbol": sym, "kind": kind})
        elif kind != "file" and have_precise and sym not in site_blob:
            # Real module/type, but not on any of this key's actual call-site paths.
            surface_mismatch.append({"symbol": sym, "kind": kind})

    # Length caps vs longest shipped translation (material overflow only).
    caps = [int(n) for n in CAP_RE.findall(context)]
    cap_violations = []
    if caps:
        cap_n = min(caps)
        long_len, long_lang = longest_translation(t)
        margin = long_len - cap_n
        if margin > CAP_SOFT_TOLERANCE:
            cap_violations.append({"cap": cap_n, "longest": long_len, "lang": long_lang, "margin": margin})

    has_ph = isinstance(en, str) and "[%" in en
    ph_unexplained = bool(
        has_ph and not re.search(r"(?i)placeholder|\[%|%@|%d|%s|%i", context)
    )

    return {
        "key": key,
        "family": family_of(key),
        "platforms": rec.get("platforms", []),
        "en": en_str[:120],
        "context_len": len(context),
        "usage_sites": site_strs,
        "android_sites": android_strs,
        "referenced": referenced,
        "dead_citations": dead,
        "surface_mismatch": surface_mismatch,
        "cap_violations": cap_violations,
        "placeholder_unexplained": ph_unexplained,
        "has_register": bool(REGISTER_RE.search(context)),
    }


def family_register_inconsistency(results: "list[dict]") -> "dict[str, dict]":
    """Per family: if some members carry Register: and others don't, the missing
    ones are flagged (consistency signal). Returns key -> {family, with, without}."""
    by_fam: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_fam[r["family"]].append(r)
    flagged: dict[str, dict] = {}
    for fam, members in by_fam.items():
        if len(members) < 2:
            continue
        have = [m["key"] for m in members if m["has_register"]]
        lack = [m["key"] for m in members if not m["has_register"]]
        if have and lack:
            for k in lack:
                flagged[k] = {"family": fam, "with_register": len(have), "without_register": len(lack)}
    return flagged


def shared_boilerplate(records: "list[dict]") -> "list[dict]":
    """Context lines (Surface:/Constraints:) repeated verbatim across >=3 keys of a
    family — a single claim to verify once and propagate (or a copy-pasted lie)."""
    by_fam_line: dict[tuple[str, str], list[str]] = defaultdict(list)
    for rec in records:
        fam = family_of(rec.get("key", ""))
        for line in (rec.get("context", "") or "").splitlines():
            line = line.strip()
            if line.startswith(("Surface:", "Constraints:")) and len(line) > 25:
                by_fam_line[(fam, line)].append(rec.get("key", ""))
    out = []
    for (fam, line), keys in by_fam_line.items():
        if len(keys) >= 3:
            out.append({"family": fam, "line": line, "count": len(keys), "keys": keys})
    out.sort(key=lambda d: -d["count"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--key", action="append", default=[], help="Limit to these keys (repeatable, debug).")
    ap.add_argument("--out", default="/tmp/context_lint", help="Output prefix (.txt + .json).")
    ap.add_argument("--no-android", action="store_true", help="Skip the Android fallback index (faster, more dead-citation false positives).")
    args = ap.parse_args()

    if not IOS_ROOT.exists():
        print(f"error: iOS repo not found at {IOS_ROOT}", file=sys.stderr)
        return 2

    records = read_records(args.corpus)
    if args.key:
        wanted = set(args.key)
        records = [r for r in records if r.get("key") in wanted]

    print(f"[context-lint] indexing iOS sources at {IOS_ROOT} …", file=sys.stderr)
    ios = IOSIndex(IOS_ROOT)
    print(f"[context-lint] iOS: {len(ios.filenames)} swift files, "
          f"{len(ios.identifiers)} identifiers, "
          f"{len(ios.call_sites)} keys with precise call-sites", file=sys.stderr)

    andr = None
    if not args.no_android and ANDROID_ROOT.exists():
        print(f"[context-lint] indexing Android sources at {ANDROID_ROOT} …", file=sys.stderr)
        andr = AndroidIndex(ANDROID_ROOT)
        print(f"[context-lint] Android: {len(andr.identifiers)} identifiers, "
              f"{len(andr.string_names)} declared strings, "
              f"{len(andr.call_sites)} keys with refs", file=sys.stderr)
    elif not args.no_android:
        print(f"[context-lint] WARN: Android repo not found at {ANDROID_ROOT}; "
              f"dead-citation precision reduced", file=sys.stderr)

    results = [lint_record(r, ios, andr) for r in records]
    reg_flags = family_register_inconsistency(results)
    boilerplate = shared_boilerplate(records)
    for r in results:
        r["register_inconsistent"] = reg_flags.get(r["key"])

    dead = [r for r in results if r["dead_citations"]]
    mismatch = [r for r in results if r["surface_mismatch"]]
    caps = [r for r in results if r["cap_violations"]]
    orphan = [r for r in results if r["referenced"] == "none"]
    android_only = [r for r in results if r["referenced"] == "android"]
    ph = [r for r in results if r["placeholder_unexplained"]]
    reg = [r for r in results if r["register_inconsistent"]]

    json_path = Path(f"{args.out}.json")
    json_path.write_text(json.dumps(
        {"records": results, "shared_boilerplate": boilerplate}, ensure_ascii=False, indent=2
    ), encoding="utf-8")

    lines: list[str] = []
    def w(s=""): lines.append(s)
    w("# Context-field deterministic pre-audit")
    w(f"corpus: {args.corpus}")
    w(f"records scanned: {len(results)}   android fallback: {'on' if andr else 'off'}")
    w("")
    w("## Summary (deterministic signals)")
    w(f"  dead citations (cited symbol exists nowhere)        : {len(dead)} key(s)")
    w(f"  surface mismatch (cited module not in real sites)   : {len(mismatch)} key(s)")
    w(f"  length-cap violations (longest tr > cap + {CAP_SOFT_TOLERANCE}) : {len(caps)} key(s)")
    w(f"  orphan: not referenced on iOS OR Android           : {len(orphan)} key(s)")
    w(f"  android-only (iOS-orphan, grounded via Android)     : {len(android_only)} key(s)")
    w(f"  placeholder present but unexplained                 : {len(ph)} key(s)")
    w(f"  Register inconsistent within family                 : {len(reg)} key(s)")
    w(f"  shared family boilerplate lines (>=3 keys)          : {len(boilerplate)} group(s)")
    w("")
    w("## DEAD CITATIONS (cited symbol exists on neither platform — typo/stale)")
    for r in dead:
        syms = ", ".join(f"{d['symbol']}({d['kind']})" for d in r["dead_citations"])
        w(f"  {r['key']:28s} cites missing: {syms}")
    w("")
    w("## SURFACE MISMATCH (cited module is real but NOT a real call-site of this key)")
    for r in mismatch:
        syms = ", ".join(d["symbol"] for d in r["surface_mismatch"])
        site0 = (r["usage_sites"][0] if r["usage_sites"] else "?")
        w(f"  {r['key']:28s} cites {syms}; real site: {site0}")
    w("")
    w("## LENGTH-CAP VIOLATIONS (material; soft tolerance applied)")
    for r in sorted(caps, key=lambda x: -x["cap_violations"][0]["margin"]):
        cv = r["cap_violations"][0]
        w(f"  {r['key']:28s} cap<= {cv['cap']:>3} but {cv['lang']} is {cv['longest']} (+{cv['margin']})")
    w("")
    w("## SHARED FAMILY BOILERPLATE (verify once, propagate / suspect copy-paste)")
    for b in boilerplate[:40]:
        w(f"  [{b['count']:>3}x] {b['family']:18s} {b['line'][:88]}")
    w("")
    w("## ORPHANS (plural / InfoPlist / dynamic / server-only / genuinely dead)")
    w("  " + ", ".join(r["key"] for r in orphan[:100]))
    if len(orphan) > 100:
        w(f"  … +{len(orphan) - 100} more (see JSON)")

    txt_path = Path(f"{args.out}.txt")
    txt_path.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines[:15]))
    print(f"\n[context-lint] full report: {txt_path}")
    print(f"[context-lint] per-key JSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
