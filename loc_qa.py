#!/usr/bin/env python3
"""Lint value hygiene in strings.ndjson — the checks placeholder-lint does not do.

Why this exists: `loc_placeholder_lint.py` owns the placeholder contract and
`loc_r_marked_translations.placeholder_signature` owns source↔target placeholder
parity. This script owns the remaining *character-level* hygiene of a translation
value — the cheap, deterministic, near-zero-false-positive checks that a generic
QA tool (Lokalise, translate-toolkit) either cannot express (an absolute em-dash
ban, regardless of source) or drowns in cross-language noise. It runs token-free
over the corpus and gates the same import the placeholder lint gates.

Scope: only user-facing translation values in `t` (every language incl. `en`, and
every CLDR form of a plural). The `context` field is NOT linted — it is source
prose where, e.g., an em-dash is the correct Russian punctuation (canonical:
TRANSLATION_STYLE.md § Punctuation reserves the em-dash ban for user-facing values
only). Linting it would flag ~1100 legitimate doc-prose dashes.

Findings (per value):
  ERROR  em-dash          a long dash `—` (U+2014) in a user-facing value. Banned
                          outright (TRANSLATION_STYLE.md § Punctuation); en-dash
                          `–` (U+2013) and hyphen `-` are NOT flagged. Absolute,
                          not relational — flagged even in the `en` source.
  ERROR  invisible-space  a non-standard / zero-width space (NBSP, ZWSP, BOM, …)
                          that looks like a normal space but breaks comparison and
                          export. Same set rejected on apply by
                          loc_r_marked_translations.
  WARN   paren-balance    unbalanced round brackets `()` after emoticons are
                          peeled off (`;)` / `:(` are not bugs). Catches a stray
                          `)` from a botched sentence split. `[ ]` of `[%s]`
                          placeholders are ignored — only `()` is balanced.
  WARN   edge-whitespace  leading or trailing whitespace on a value. WARN, not
                          ERROR: a trailing space is occasionally intentional for
                          runtime concatenation.

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
from pathlib import Path
from typing import Any, Iterable, NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loc_corpus import (  # noqa: E402
    DEFAULT_CORPUS,
    display_key,
    is_archived,
    read_records,
)

# Long dash U+2014. en-dash U+2013 and hyphen-minus U+002D are deliberately NOT
# here — only the em-dash is banned (TRANSLATION_STYLE.md § Punctuation).
EM_DASH = "—"

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

    return findings


def _value_strings(value: Any) -> Iterable[str]:
    """Plain strings to lint: a flat value, or each form of a plural value."""
    if isinstance(value, dict):
        return [form for form in value.values() if isinstance(form, str)]
    if isinstance(value, str):
        return [value]
    return []


def lint_record(record: dict[str, Any], langs: set[str] | None = None) -> list[Finding]:
    """Findings for one record's translation values (limit to `langs` if given).

    Every language is linted, including the `en` source — the em-dash /
    invisible-space bans are absolute (a defect in the source is still a defect),
    unlike the placeholder-consistency checks that treat `en` as the reference.
    The `context` field is never linted (source prose, see module docstring)."""
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
    parser = argparse.ArgumentParser(description="Lint corpus value hygiene (em-dash, invisible spaces, bracket balance, edge whitespace).")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS, help=f"Corpus path. Default: {DEFAULT_CORPUS}.")
    parser.add_argument("--lang", action="append", help="Limit to these language isos. Repeatable.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings (paren-balance, edge-whitespace) as failures too.")
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
