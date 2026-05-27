#!/usr/bin/env python3
"""Lint placeholders in strings.ndjson against the Lokalise universal contract.

Why this exists: edits land in the corpus and are pushed to Lokalise through the
**keys API** (`loc_corpus_import.py`), which — unlike a file upload — does NOT
auto-convert platform-specific placeholders to the universal format. So a bare
`%@` / `%s` / `%d` is stored literally and mis-exports (iOS keeps `%s` instead of
`%@`; a lone `%` is undefined under iOS R.swift `String(format:)`). This linter is
the pre-flight that keeps non-universal placeholders out of the corpus.

The contract (canonical: TRANSLATION_STYLE.md § Placeholders):
  - String/int/float args use Lokalise universal placeholders: `[%s]`, `[%1$s]`,
    `[%i]`, `[%.1f]`, `[%2$i]`. Lokalise converts these per platform on export.
  - A literal percent sign is the universal `[%]`; Lokalise escapes it per platform
    on export (`→ %%` for printf/iOS when the string has another placeholder, `→ %`
    standalone). A bare `%%` is the iOS printf escape; the keys-API stores it
    literally (no conversion), so it survives unconverted and leaks `%%` to
    consumers that don't run a formatter (Android plain getString, server). It is
    flagged (`literal-percent-escape`): ERROR on any non-ios platform where it
    leaks, WARN for an ios-only key where `String(format:)` still renders it. The
    canonical literal percent is `[%]` ([CR-PLACEHOLDER]).
  - iOS `.stringsdict` substitution variables (`%1$#@new_drinks@`) have no
    universal form. They are the outer NSStringLocalizedFormatKey of a correctly-
    modeled stringsdict key whose plural forms live in a sibling `::var` companion
    key (e.g. `appleHealthResyncDoneExported` + `appleHealthResyncDoneExported::new_drinks`).
    When that companion exists the key is fine — no finding. Only an ORPHANED
    outer key (no `::var` companion) would mis-export and is flagged. Raw
    specifiers sharing such a value (e.g. the `%2$d` in `Uploaded %1$#@new_drinks@
    of %2$d`) are legitimate iOS placeholders, not bare-placeholder errors.

Findings (per value):
  ERROR  bare-placeholder  a `%s`/`%@`/`%d`/… not wrapped in `[ ]` (non-stringsdict value)
  ERROR  lone-percent      a literal `%` that is not `%%` and not `[%]` (runtime only)
  ERR/WARN literal-percent-escape  a bare `%%` instead of the universal `[%]` — ERROR on a
                                non-ios platform (leaks `%%` to non-printf consumers), WARN ios-only
  WARN   stringsdict       an iOS `%#@var@` outer key with NO `::var` companion (orphaned)
Findings (cross-language, per key — all langs fill the same runtime args):
  ERROR  placeholder-count     a translation's placeholder set (type × count) ≠ the source's
  ERR/WARN placeholder-indexing ≥2 placeholders not consistently indexed `[%1$s]` across langs
                                (ERROR if it mixes bare/indexed; WARN if uniformly bare)

    python3 loc_placeholder_lint.py                 # lint whole corpus
    python3 loc_placeholder_lint.py --lang ru de    # only these languages
    python3 loc_placeholder_lint.py --strict        # warnings fail too

Exit code is non-zero when any ERROR is found (any finding under --strict), so it
can gate CI or an import. Stdlib-only, token-free — it only reads the corpus.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loc_corpus import (  # noqa: E402
    DEFAULT_CORPUS,
    SOURCE_LANG,
    display_key,
    is_archived,
    key_names,
    platforms,
    read_records,
)

# Platforms whose strings are run through printf / iOS `String(format:)` at
# runtime, where a lone `%` is undefined. App Store metadata / server copy
# (`other`) is not formatted, so a literal `%` (e.g. "70%") is valid there.
RUNTIME_PLATFORMS = {"ios", "android"}

# Lokalise universal placeholder: [%s] [%1$s] [%.2f] [%s:name] and literal [%].
UNIVERSAL_RE = re.compile(r"\[%[^\]]*\]")
# iOS .stringsdict substitution variable: %#@var@, %1$#@new_drinks@.
STRINGSDICT_RE = re.compile(r"%\d*\$?#@\w+@")
# A bare printf / iOS placeholder (what must instead be wrapped as universal):
# %@ %d %i %s %ld %lld %.1f %1$@ %2$d %02d. Deliberately conservative — the C
# space/`+`/`-` flags are excluded so a literal "50% off" / "% tu" in prose is NOT
# mistaken for a `% o`-style spec; such a stray `%` falls through to lone-percent.
# `%%` is removed before this runs, so it never matches a literal-percent escape.
BARE_RE = re.compile(
    r"%(?:\d+\$)?0*\d*(?:\.\d+)?(?:hh|h|ll|l|L|z|t|j)?[@diouxXeEfFgGcCsS]"
)


class Finding(NamedTuple):
    key: str
    lang: str
    severity: str  # "error" | "warn"
    code: str
    token: str
    snippet: str


def _snippet(value: str, limit: int = 70) -> str:
    return value if len(value) <= limit else value[:limit] + "…"


def lint_value(value: str) -> list[tuple[str, str, str]]:
    """(severity, code, token) findings for one translation string.

    A value containing an iOS `.stringsdict` substitution (`%#@var@`) is an iOS
    NSStringLocalizedFormatKey format string — inherently iOS-native, since that
    syntax has no universal form and only iOS has stringsdict. Its sibling
    specifiers (e.g. `%2$d`) are therefore legitimate raw iOS placeholders, NOT
    corpus-contract violations, so bare-placeholder is suppressed for such a value.
    Whether the substitution is actually valid depends on a `::var` plural
    companion existing — decided at the record level (companion-aware)."""
    findings: list[tuple[str, str, str]] = []
    is_stringsdict = bool(STRINGSDICT_RE.search(value))
    for match in STRINGSDICT_RE.finditer(value):
        findings.append(("warn", "stringsdict", match.group(0)))
    # Peel off what is allowed before scanning the remainder.
    remainder = STRINGSDICT_RE.sub("", UNIVERSAL_RE.sub("", value))
    # A bare `%%` is the iOS printf escape. The keys-API stores it literally (no
    # universal conversion), so it survives unconverted and leaks `%%` to consumers
    # that don't run a formatter (Android plain getString, server); the canonical
    # literal percent is universal `[%]` ([CR-PLACEHOLDER]). Flag it, then strip it
    # so it doesn't also trip bare-placeholder / lone-percent. Per-platform severity
    # (ERROR where it leaks vs WARN ios-only) is decided in lint_record.
    if "%%" in remainder:
        findings.append(("warn", "literal-percent-escape", "%%"))
    remainder = remainder.replace("%%", "")
    for match in BARE_RE.finditer(remainder):
        if not is_stringsdict:  # raw specifiers are legitimate in an iOS stringsdict string
            findings.append(("error", "bare-placeholder", match.group(0)))
    remainder = BARE_RE.sub("", remainder)  # strip regardless, so a stripped %2$d ≠ lone-percent
    if "%" in remainder:
        findings.append(("error", "lone-percent", "%"))
    return findings


def _value_strings(value: Any) -> Iterable[str]:
    """Plain strings to lint: a flat value, or each form of a plural value."""
    if isinstance(value, dict):
        return [form for form in value.values() if isinstance(form, str)]
    if isinstance(value, str):
        return [value]
    return []


def _ptype(token: str) -> str:
    """Conversion letter of a universal token: `[%1$.2f]` -> `f`."""
    return re.sub(r"[\[\]%\d$.\-+# ]", "", token) or "?"


def _is_indexed(token: str) -> bool:
    """True for a positional token `[%1$s]`, False for a bare `[%s]`."""
    return bool(re.match(r"\[%\d+\$", token))


def _type_multiset(tokens: list[str]) -> tuple[tuple[str, int], ...]:
    """The placeholder set ignoring index: `[%1$s][%2$s]` -> ((s,2),)."""
    return tuple(sorted(Counter(_ptype(t) for t in tokens).items()))


def _fmt_ms(multiset: tuple[tuple[str, int], ...]) -> str:
    return ", ".join(f"%{t}×{c}" for t, c in multiset) or "none"


def consistency_findings(record: dict[str, Any]) -> list[Finding]:
    """Cross-language placeholder consistency for ONE key (flat values only).

    All language values of a key fill the SAME runtime args, so they must agree:
      - `placeholder-count` (ERROR): a non-empty translation's placeholder set
        (type × count) differs from the source's — a dropped / added / retyped
        arg, which crashes or renders wrong.
      - `placeholder-indexing`: a key with ≥2 placeholders must be INDEXED
        (`[%1$s]` / `[%2$s]`) in every language so a translation can reorder them.
        Mixing bare `[%s]` and indexed `[%1$s]` across languages ⇒ ERROR (the
        bare ones can't reorder and are fragile); uniformly bare ⇒ WARN (convention).
    """
    values = {
        lang: value
        for lang, value in (record.get("t") or {}).items()
        if isinstance(value, str) and value.strip()
    }
    tokens = {lang: UNIVERSAL_RE.findall(value) for lang, value in values.items()}
    if not any(tokens.values()):
        return []  # no placeholders anywhere → nothing to reconcile

    key = display_key(record)
    findings: list[Finding] = []

    # Reference set: the source language if present, else the most common set.
    if SOURCE_LANG in tokens:
        ref = _type_multiset(tokens[SOURCE_LANG])
    else:
        counts = Counter(_type_multiset(tk) for tk in tokens.values() if tk)
        ref = counts.most_common(1)[0][0] if counts else ()
    for lang, tk in tokens.items():
        got = _type_multiset(tk)
        if got != ref:
            findings.append(Finding(key, lang, "error", "placeholder-count",
                                    _fmt_ms(got), f"has {_fmt_ms(got)}, {SOURCE_LANG} has {_fmt_ms(ref)}"))

    if max((len(tk) for tk in tokens.values()), default=0) >= 2:
        multi = {lang: tk for lang, tk in tokens.items() if len(tk) >= 2}
        indexed = {lang for lang, tk in multi.items() if any(_is_indexed(t) for t in tk)}
        bare = {lang for lang, tk in multi.items() if not any(_is_indexed(t) for t in tk)}
        if indexed and bare:
            for lang in sorted(bare):
                findings.append(Finding(key, lang, "error", "placeholder-indexing",
                                        "[%s]", "mixes bare [%s] with indexed [%1$s] across languages — index all"))
        elif bare and not indexed:
            anchor = SOURCE_LANG if SOURCE_LANG in bare else sorted(bare)[0]
            findings.append(Finding(key, anchor, "warn", "placeholder-indexing",
                                    "[%s]", "≥2 placeholders should be indexed [%1$s]/[%2$s] so translations can reorder"))
    return findings


def lint_record(
    record: dict[str, Any],
    langs: set[str] | None = None,
    companion_bases: set[str] | None = None,
) -> list[Finding]:
    """Findings for one record's translation values (limit to `langs` if given).

    Context / notes are intentionally NOT linted — they describe placeholders in
    prose (e.g. "the %@ is the unit") and are never exported. `lone-percent` is
    only reported for runtime platforms (ios/android), where the value is run
    through `String(format:)` and a lone `%` is undefined; for non-formatted
    metadata / server copy (`other`) a literal `%` like "70%" is valid.

    `companion_bases` is the set of base names that own a `::var` plural companion
    key. When this record's name is in it, the record is a correctly-modeled
    stringsdict outer key (its plural forms live in the companion) — the
    stringsdict notice is suppressed; only an orphaned outer key (no companion)
    is flagged."""
    if is_archived(record):
        return []
    key = display_key(record)
    plats = platforms(record)
    # No platforms recorded ⇒ treat as runtime (be safe and flag a lone %).
    runtime = not plats or bool(RUNTIME_PLATFORMS.intersection(plats))
    has_companion = bool(companion_bases and set(key_names(record)) & companion_bases)
    # A stored `%%` provably leaks on any consumer that doesn't run a formatter
    # (Android plain getString, server/`other`); only an ios-only key is safe
    # (R.swift always formats). No platforms recorded ⇒ be safe and treat as leaking.
    percent_leaks = (not plats) or bool(set(plats) - {"ios"})
    findings: list[Finding] = []
    for lang, value in (record.get("t") or {}).items():
        if langs is not None and lang not in langs:
            continue
        for text in _value_strings(value):
            for severity, code, token in lint_value(text):
                if code == "lone-percent" and not runtime:
                    continue
                if code == "stringsdict" and has_companion:
                    continue  # correctly modeled — plural forms live in the `::var` companion
                if code == "literal-percent-escape":
                    severity = "error" if percent_leaks else "warn"
                findings.append(Finding(key, lang, severity, code, token, _snippet(text)))
    # Cross-language consistency is computed over ALL languages of the key, then
    # filtered to scope so the import gate only blocks on a language being pushed.
    for finding in consistency_findings(record):
        if langs is None or finding.lang in langs:
            findings.append(finding)
    return findings


def lint_records(
    records: Iterable[dict[str, Any]], langs: set[str] | None = None
) -> list[Finding]:
    """Lint every (non-archived) record's translation values. Limit to `langs`
    when given."""
    records = list(records)
    # Base names owning a `::var` companion ⇒ correctly-modeled iOS stringsdict
    # keys whose plural forms live in the companion. Computed once over the whole
    # corpus so a stringsdict outer key is only flagged when truly orphaned.
    companion_bases = {
        name.split("::", 1)[0]
        for record in records
        for name in key_names(record)
        if "::" in name
    }
    findings: list[Finding] = []
    for record in records:
        findings.extend(lint_record(record, langs, companion_bases))
    return findings


def has_errors(findings: Iterable[Finding], strict: bool = False) -> bool:
    return any(strict or f.severity == "error" for f in findings)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lint corpus placeholders against the Lokalise universal contract.")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS, help=f"Corpus path. Default: {DEFAULT_CORPUS}.")
    parser.add_argument("--lang", action="append", help="Limit to these language isos. Repeatable.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings (stringsdict) as failures too.")
    return parser


def format_findings(findings: list[Finding]) -> str:
    lines = []
    for f in sorted(findings, key=lambda f: (f.severity != "error", f.code, f.key, f.lang)):
        mark = "ERROR" if f.severity == "error" else "warn "
        lines.append(f"  {mark} [{f.code}] {f.key} ({f.lang}): {f.token!r}  in {f.snippet!r}")
    return "\n".join(lines)


def main() -> int:
    args = build_parser().parse_args()
    if not args.corpus.exists():
        print(f"error: corpus not found: {args.corpus}", file=sys.stderr)
        return 2
    records = read_records(args.corpus)
    langs = set(args.lang) if args.lang else None
    findings = lint_records(records, langs)
    errors = [f for f in findings if f.severity == "error"]
    warns = [f for f in findings if f.severity == "warn"]
    if findings:
        print(format_findings(findings))
    print(f"\n{len(errors)} error(s), {len(warns)} warning(s) over {len(records)} keys.")
    return 1 if has_errors(findings, strict=args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
