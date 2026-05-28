#!/usr/bin/env python3
"""Lint value hygiene in strings.ndjson — the checks placeholder-lint does not do.

Why this exists: `loc_placeholder_lint.py` owns the placeholder contract and
`loc_r_marked_translations.placeholder_signature` owns source↔target placeholder
parity. This script owns the remaining *character-level* hygiene of a translation
value — the cheap, deterministic, near-zero-false-positive checks that a generic
QA tool (Lokalise, translate-toolkit) either cannot express (an absolute em-dash
ban, regardless of source) or drowns in cross-language noise. One cheap
cross-language check (URL parity) rides along, analogous to
loc_placeholder_lint's consistency pass. It runs token-free over the corpus and
gates the same import the placeholder lint gates.

Scope: user-facing translation values in `t` (every language incl. `en`, and every
CLDR form of a plural), plus three structural checks on the translator `context`
field. The `context` field carries source prose where an em-dash is the correct
Russian punctuation (canonical: TRANSLATION_STYLE.md § Punctuation reserves the
em-dash ban for user-facing values only); the value-side checks therefore stay
off it, and the context-side checks added here are limited to defects that cannot
be a legitimate authoring choice — a long Cyrillic block (context is author-side
prose in English; short inline examples like `"млн" in ru` stay legal), an
empty optional field (the canon mandates omission, never `Constraints:\\n`), and
an off-vocabulary Type (silently splits the audit's Type-equality sibling bucket).

Findings (per value):
  ERROR  em-dash          a long dash `—` (U+2014) in a user-facing value. Banned
                          outright (TRANSLATION_STYLE.md § Punctuation); en-dash
                          `–` (U+2013) and hyphen `-` are NOT flagged. Absolute,
                          not relational — flagged even in the `en` source.
  ERROR  invisible-space  a non-standard / zero-width space (NBSP, ZWSP, BOM, …)
                          that looks like a normal space but breaks comparison and
                          export. Same set rejected on apply by
                          loc_r_marked_translations.
  ERROR  cyrillic-in-source  Cyrillic letters in the `en` SOURCE value. Russian is
                          the only Cyrillic-script language in this corpus, so
                          Cyrillic in `en` means a translation was mis-filed into the
                          source column (e.g. an AI agent left a Russian string in
                          `en`). Source-only — target values are not script-checked.
  WARN   paren-balance    unbalanced round brackets `()` after emoticons are
                          peeled off (`;)` / `:(` are not bugs). Catches a stray
                          `)` from a botched sentence split. `[ ]` of `[%s]`
                          placeholders are ignored — only `()` is balanced.
  WARN   edge-whitespace  leading or trailing whitespace on a value. WARN, not
                          ERROR: a trailing space is occasionally intentional for
                          runtime concatenation.
  WARN   double-space     two or more consecutive ASCII spaces inside a value
                          (Lokalise `double_space`). WARN — cosmetic, never breaks
                          export; non-standard spaces are the `invisible-space`
                          ERROR above, this is only the plain U+0020 run.

Findings (cross-language, per key — relational, like loc_placeholder_lint):
  WARN   url-mismatch     a language's set of URLs differs from the `en` source's
                          (Lokalise `different_urls` / `different_number_of_urls`).
                          WARN, not ERROR: a legitimately localized link (e.g. a
                          `/en/` vs `/de/` path) is rare but possible, so it surfaces
                          without blocking the import gate.

Findings (per `context` field — author-side, lang reported as `(context)`):
  ERROR  context-empty-field   a `Constraints:` / `Placeholders:` / `Register:` /
                          `Tone:` field is present but its body is whitespace-only
                          (canon mandates omission of unused optional fields —
                          TRANSLATION_STYLE.md § Translator context § Формат).
                          `Placeholders:` is treated as multi-line: an indented
                          `[%…]` continuation line counts as content.
  ERROR  context-cyrillic-block  a multi-word Cyrillic phrase (≥2 Cyrillic words
                          running together, ≥10 letters total) in the context.
                          A single inline word ("Зарегистрируйся", "Какао") stays
                          legal as a translation example; a Russian phrase
                          ("никогда не появляется") is the bug (canon: context
                          lives only in source language — TRANSLATION_STYLE.md
                          § Translator context).
  WARN   context-type-vocab    the `Type:` value is not in the closed Type vocabulary
                          (TRANSLATION_STYLE.md § Translator context § Обязательные
                          поля). Subtype qualifier `paragraph (xxx)` is allowed —
                          only the base must match. Synonyms silently split the
                          audit's Type-equality sibling bucket (loc_audit_prompt.md
                          § rule #4 / #9).

Exit code is non-zero when any ERROR is found (any finding under --strict), so it
can gate CI or an import (it is a second pre-flight in loc_corpus_import alongside
loc_placeholder_lint). Stdlib-only, token-free — it only reads the corpus.

    python3 loc_qa.py                 # lint whole corpus
    python3 loc_qa.py --lang ru de    # only these languages
    python3 loc_qa.py --strict        # warnings fail too
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
    read_records,
)

# Long dash U+2014. en-dash U+2013 and hyphen-minus U+002D are deliberately NOT
# here — only the em-dash is banned (TRANSLATION_STYLE.md § Punctuation).
EM_DASH = "—"

# Cyrillic letters (main block U+0400–U+04FF + Supplement U+0500–U+052F). Russian is
# the only Cyrillic-script language in this corpus, so Cyrillic in the `en` SOURCE
# value is never legitimate — it means a translation was mis-filed into the source
# column (e.g. an AI agent left the Russian string in `en`; the photoPickerUnavailable
# class of bug). Flagged ERROR on the source language only; targets are not
# script-checked here (Cyrillic is correct in `ru`).
CYRILLIC_RE = re.compile("[Ѐ-ӿԀ-ԯ]+")

# Non-standard / invisible spaces: NBSP, ogham, Mongolian vowel sep, the
# U+2000–U+200B en/em/thin/hair/zero-width run, line/paragraph separators, narrow
# & medium-math NBSP, ideographic space, BOM/ZWNBSP. Mirrors the set
# loc_r_marked_translations rejects on apply (kept in sync deliberately).
INVISIBLE_SPACE_RE = re.compile(
    r"[  ᠎ -​    　﻿]"
)
# Readable names for the few that actually occur, else U+XXXX in the finding.
_SPACE_NAMES = {
    " ": "NBSP", " ": "NARROW-NBSP", "​": "ZWSP",
    "﻿": "BOM", " ": "LINE-SEP", " ": "PARA-SEP",
    "　": "IDEOGRAPHIC-SPACE", " ": "MATH-SPACE",
}
# Text emoticons whose trailing paren is NOT a bracket: :) ;) :-( =) etc. Peeled
# off before the paren-balance count so a friendly `;)` is not a false positive.
EMOTICON_RE = re.compile(r"[:;=]['\-^]?[()]")
# Two or more consecutive plain ASCII spaces inside a value (Lokalise
# `double_space`). Non-standard / zero-width spaces are the invisible-space ERROR
# (INVISIBLE_SPACE_RE); this is only the U+0020 run.
DOUBLE_SPACE_RE = re.compile(r" {2,}")
# A URL whose presence must match across all languages of a key (Lokalise
# `different_urls`). Trailing sentence punctuation is stripped on capture so a
# sentence-final link compares equal across languages.
URL_RE = re.compile(r"https?://[^\s\"<>]+")

# Closed Type vocabulary from TRANSLATION_STYLE.md § Translator context § Обязательные
# поля. The audit buckets keys by Type equality for sibling-consistency checks
# (loc_audit_prompt.md § rule #4 / #9) — a synonym ("section header / row title"
# vs "section header") silently splits the bucket. Subtype qualifiers in parens
# (`paragraph (educational)`, `section header (eyebrow)`) are allowed; the closed
# membership is on the base. Extend only through a PR to TRANSLATION_STYLE.md.
CLOSED_TYPE_VOCAB = frozenset({
    # Buttons & controls
    "button label", "badge", "toggle", "picker option", "segmented option",
    # Headers & titles
    "screen title", "section header", "card title", "feature row title",
    "popup title", "alert title", "confirmation alert title", "tab title",
    # Settings
    "settings row title", "settings row value", "settings row label", "option label",
    # Body text — `paragraph` carries optional `(subtype)` and is matched on the base
    "paragraph",
    # Messaging
    "notification title", "notification body", "alert message", "error message",
    "success message", "status message", "warning message", "motivational text",
    "tip", "tip headline",
    # Domain
    "beverage name", "unit abbreviation", "container name", "character name",
    "achievement title", "achievement description",
    # Widget / system
    "widget gallery title", "widget gallery description", "permission prompt",
    "home screen quick action label", "screenshot caption", "App Store title",
    "App Store keywords", "accessibility label", "accessibility hint",
    # Siri / voice
    "AppIntent title", "AppIntent description", "AppIntent dialog",
    "AppIntent prompt", "AppIntent parameter label", "Siri snippet",
    # Onboarding / forms
    "tutorial step", "form field label", "placeholder",
    # Generic fallback
    "label",
})

# Optional fields in the translator-context block that the canon mandates omitting
# when unused (TRANSLATION_STYLE.md § Translator context § Формат "Пустые поля
# пропускать полностью"). A present-but-empty body is the bug to flag.
OPTIONAL_CONTEXT_FIELDS = ("Constraints", "Placeholders", "Register", "Tone")
# All recognised field names — used to bound a field's body when extracting it.
ALL_CONTEXT_FIELDS = ("Surface", "Type", "Context") + OPTIONAL_CONTEXT_FIELDS

# A Cyrillic "phrase" — two or more Cyrillic words running together with at least
# this many letters total — is what we want to catch (a Russian sentence left
# where English prose belongs). A single long Cyrillic word ("Зарегистрируйся",
# 15 letters) is a legitimate inline example and stays under the bar because the
# word-count threshold is 2+.
CYRILLIC_PHRASE_MIN_LETTERS = 10
CYRILLIC_PHRASE_MIN_WORDS = 2
# A run of one or more Cyrillic words separated only by ASCII spaces — this
# matches a "phrase" candidate; word count and letter count are measured on it.
CYRILLIC_PHRASE_RE = re.compile(r"[Ѐ-ӿԀ-ԯ]+(?:[ \t]+[Ѐ-ӿԀ-ԯ]+)+")

# Field-body extractor: captures everything from after `Field:` up to (but not
# including) the next known field on its own line, or end-of-context. `re.DOTALL`
# so the body can span lines (Placeholders is multi-line).
_FIELD_BODY_RE_CACHE: dict[str, re.Pattern[str]] = {}


def _field_body_re(field: str) -> re.Pattern[str]:
    if field not in _FIELD_BODY_RE_CACHE:
        boundary = "|".join(ALL_CONTEXT_FIELDS)
        _FIELD_BODY_RE_CACHE[field] = re.compile(
            rf"^{field}:(.*?)(?=^(?:{boundary}):|\Z)",
            re.MULTILINE | re.DOTALL,
        )
    return _FIELD_BODY_RE_CACHE[field]


def _type_base(type_value: str) -> str:
    """Drop a trailing `(subtype)` qualifier and trailing punctuation/whitespace —
    `paragraph (educational)` → `paragraph`; `motivational text.` → `motivational
    text` — so the closed-vocab check is on the base only."""
    base = re.sub(r"\s*\([^)]*\)\s*$", "", type_value).strip()
    return base.rstrip(".").strip()


_QUOTE_CHARS = frozenset('"«“‘„»”’\'`')


def _has_cyrillic_phrase(text: str) -> bool:
    """True iff `text` contains an UNQUOTED Cyrillic phrase: two or more Cyrillic
    words separated by spaces, totalling at least CYRILLIC_PHRASE_MIN_LETTERS
    letters, and NOT immediately preceded by a quotation mark. Quoted phrases
    ("от Алекса смайл", "Лайки друзей") are inline translation examples and stay
    legal; an unquoted phrase ("никогда не появляется", "Live Activity появляется
    на момент активного напоминания") is the bug."""
    for match in CYRILLIC_PHRASE_RE.finditer(text):
        run = match.group(0)
        words = run.split()
        if len(words) < CYRILLIC_PHRASE_MIN_WORDS or sum(len(w) for w in words) < CYRILLIC_PHRASE_MIN_LETTERS:
            continue
        # Skip when the run is inline-quoted — the canonical way to embed a
        # target-language example in English context prose.
        start = match.start()
        if start > 0 and text[start - 1] in _QUOTE_CHARS:
            continue
        return True
    return False


def lint_context(context: str | None) -> list[tuple[str, str, str]]:
    """(severity, code, token) findings for one key's translator-context block.
    Empty / missing context yields nothing — context-coverage is a separate
    concern (CLAUDE.md § Adding a new key), not a hygiene defect."""
    if not context:
        return []
    findings: list[tuple[str, str, str]] = []

    type_match = _field_body_re("Type").search(context)
    if type_match:
        base = _type_base(type_match.group(1))
        if base and base not in CLOSED_TYPE_VOCAB:
            findings.append(("warn", "context-type-vocab", base))

    for field in OPTIONAL_CONTEXT_FIELDS:
        m = _field_body_re(field).search(context)
        if not m:
            continue
        body = m.group(1)
        if body.strip():
            continue
        # Placeholders is multi-line: an indented `[%…]` continuation counts as
        # content. The body extractor captured everything up to the next field,
        # so if `.strip()` was empty there were no indented continuation lines.
        findings.append(("error", "context-empty-field", field))

    if _has_cyrillic_phrase(context):
        findings.append(("error", "context-cyrillic-block", "Cyrillic phrase (multi-word)"))

    return findings


class Finding(NamedTuple):
    key: str
    lang: str
    severity: str  # "error" | "warn"
    code: str
    token: str
    snippet: str


def _snippet(value: str, limit: int = 70) -> str:
    return value if len(value) <= limit else value[:limit] + "…"


def _space_name(char: str) -> str:
    return _SPACE_NAMES.get(char, f"U+{ord(char):04X}")


def lint_value(value: str) -> list[tuple[str, str, str]]:
    """(severity, code, token) findings for one translation string."""
    findings: list[tuple[str, str, str]] = []

    if EM_DASH in value:
        findings.append(("error", "em-dash", EM_DASH))

    seen: set[str] = set()
    for match in INVISIBLE_SPACE_RE.finditer(value):
        char = match.group(0)
        if char not in seen:
            seen.add(char)
            findings.append(("error", "invisible-space", _space_name(char)))

    # Round-bracket balance, ignoring `[%s]`-style placeholders (square brackets)
    # and text emoticons. A stray `)` from a botched sentence split shows up here.
    without_emoticons = EMOTICON_RE.sub("", value)
    opens = without_emoticons.count("(")
    closes = without_emoticons.count(")")
    if opens != closes:
        findings.append(("warn", "paren-balance", f"({opens}/{closes})"))

    if value != value.strip() and value.strip():
        side = "leading" if value[:1].isspace() else "trailing"
        findings.append(("warn", "edge-whitespace", side))

    runs = [match.group(0) for match in DOUBLE_SPACE_RE.finditer(value)]
    if runs:
        findings.append(("warn", "double-space", f"{max(len(run) for run in runs)} spaces"))

    return findings


def _value_strings(value: Any) -> Iterable[str]:
    """Plain strings to lint: a flat value, or each form of a plural value."""
    if isinstance(value, dict):
        return [form for form in value.values() if isinstance(form, str)]
    if isinstance(value, str):
        return [value]
    return []


def _urls(value: str) -> tuple[str, ...]:
    """Sorted URLs in a value, trailing sentence punctuation stripped so a
    sentence-final link (`… see https://x.com.`) compares equal across languages."""
    return tuple(sorted(match.group(0).rstrip(".,;:!?)]}'\"") for match in URL_RE.finditer(value)))


def url_findings(record: dict[str, Any]) -> list[Finding]:
    """Cross-language URL parity for ONE key (flat values only).

    A URL in the source must survive verbatim into every translated language; a
    dropped, added, or mangled link is a real defect (Lokalise's `different_urls`
    / `different_number_of_urls`). WARN, not ERROR: a legitimately localized link
    is rare but possible, so this surfaces the mismatch without blocking the
    import gate. Mirrors loc_placeholder_lint.consistency_findings — `en`-referenced
    (most-common set as fallback when the key has no source value), plurals skipped."""
    values = {
        lang: value
        for lang, value in (record.get("t") or {}).items()
        if isinstance(value, str) and value.strip()
    }
    urls = {lang: _urls(value) for lang, value in values.items()}
    if not any(urls.values()):
        return []  # no URLs anywhere → nothing to reconcile

    if SOURCE_LANG in urls:
        ref = urls[SOURCE_LANG]
    else:
        counts = Counter(urls.values())
        ref = counts.most_common(1)[0][0] if counts else ()

    key = display_key(record)
    findings: list[Finding] = []
    for lang, got in urls.items():
        if got != ref:
            findings.append(Finding(
                key, lang, "warn", "url-mismatch",
                ", ".join(got) or "none",
                f"has {', '.join(got) or 'none'}, {SOURCE_LANG} has {', '.join(ref) or 'none'}",
            ))
    return findings


def lint_record(record: dict[str, Any], langs: set[str] | None = None) -> list[Finding]:
    """Findings for one record's translation values (limit to `langs` if given).

    The per-value checks (em-dash, invisible-space, double-space, …) are absolute:
    every language including the `en` source is linted, since a defect in the
    source is still a defect. Two checks are language-aware: cyrillic-in-source
    fires only on the `en` value (CYRILLIC_RE), and the cross-language url-mismatch
    check treats `en` as the reference (see url_findings), like
    loc_placeholder_lint's consistency pass. The `context` field is never linted
    (source prose, see module docstring)."""
    if is_archived(record):
        return []
    key = display_key(record)
    findings: list[Finding] = []
    for lang, value in (record.get("t") or {}).items():
        if langs is not None and lang not in langs:
            continue
        for text in _value_strings(value):
            for severity, code, token in lint_value(text):
                findings.append(Finding(key, lang, severity, code, token, _snippet(text)))
            # Source-only: Cyrillic in the `en` value means a translation was
            # mis-filed into the source column (see CYRILLIC_RE). Targets are not
            # script-checked — Cyrillic is correct in `ru`.
            if lang == SOURCE_LANG:
                match = CYRILLIC_RE.search(text)
                if match:
                    findings.append(Finding(
                        key, lang, "error", "cyrillic-in-source",
                        _snippet(match.group(0), 30), _snippet(text),
                    ))
    # Cross-language URL parity is computed over ALL languages of the key (`en` is
    # the reference), then filtered to scope so the import gate only reports on a
    # language being pushed — mirrors loc_placeholder_lint.consistency_findings.
    for finding in url_findings(record):
        if langs is None or finding.lang in langs:
            findings.append(finding)

    # Translator-context checks are reported under the pseudo-lang `(context)` so
    # they coexist with per-value findings under the same Finding shape. They are
    # author-side hygiene (Type vocab, empty optional fields, Russian-where-English-
    # belongs) and are not filtered by --lang (a context defect is language-
    # independent — it affects every downstream translator equally).
    snippet = _snippet((record.get("context") or "").replace("\n", " ⏎ "))
    for severity, code, token in lint_context(record.get("context")):
        findings.append(Finding(key, "(context)", severity, code, token, snippet))
    return findings


def lint_records(
    records: Iterable[dict[str, Any]], langs: set[str] | None = None
) -> list[Finding]:
    """Lint every (non-archived) record's translation values. Limit to `langs`
    when given."""
    findings: list[Finding] = []
    for record in records:
        findings.extend(lint_record(record, langs))
    return findings


def has_errors(findings: Iterable[Finding], strict: bool = False) -> bool:
    return any(strict or f.severity == "error" for f in findings)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lint corpus value hygiene (em-dash, invisible spaces, Cyrillic-in-source, bracket balance, edge/double whitespace, URL parity).")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS, help=f"Corpus path. Default: {DEFAULT_CORPUS}.")
    parser.add_argument("--lang", action="append", help="Limit to these language isos. Repeatable.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings (paren-balance, edge-whitespace, double-space, url-mismatch) as failures too.")
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
