#!/usr/bin/env python3
"""Apply a translation / field edit map into glossary.ndjson (the fan-in tool).

The glossary sibling of loc_apply_lang.py — replace-only, single-writer, routed
through loc_glossary.write_records (the one serializer, GLOSSARY.md § Serializer-
owned / [CR-CORPUS-OWNER]). Two input shapes:

    # Mode 1 — one language per file (the parallel-pass fan-in case):
    python3 loc_glossary_apply.py <lang> <edits.json> [--glossary glossary.ndjson]
        <edits.json> = {term: "translation"}      -> sets t[lang] for each term
        e.g.  { "daily goal": "Tagesziel", "Water": "Wasser" }

    # Mode 2 — a {term: {lang: translation}} map (no positional lang):
    python3 loc_glossary_apply.py --map <edits.json> [--glossary glossary.ndjson]
        <edits.json> = {term: {lang: text, ...}}  -> sets each t[lang]
        e.g.  { "гидратация": {"ru": "гидратация"}, "daily goal": {"de": "Tagesziel"} }

Only terms that ALREADY exist in the glossary are edited (matched by exact, case-
sensitive headword — the Lokalise glossary is case-sensitive). Unknown terms are
reported and the process exits non-zero — an unmatched term means an upstream
transcription error, not a new term to append (add new terms through a
write_records constructor / the create flow, GLOSSARY.md). This mirrors the
replace-only invariant of loc_apply_lang.py.

`en` is never a `t` entry (the headword IS the en form) — a `t["en"]` edit is
rejected. An empty / whitespace value is a no-op clear: write_records drops empty
`t` entries, so the language reverts to "absent = not yet translated" (the
glossary has no present-but-blank state). Unlike the string corpus there is NO
`unverified` / `dirty` review state to set — the glossary is reference data
pushed as a whole-glossary upsert (GLOSSARY.md § Why no review state).

Not concurrency-safe: write_records rewrites the whole file (read-all -> mutate ->
write-all, no lock). A parallel multi-language fill must SERIALIZE the applies —
fan out the per-language JSON generation read-only, then run this one language at
a time ([CR-CORPUS-CONCURRENCY], GLOSSARY.md § Fill workflow). For dev / smoke
runs pass `--glossary /tmp/test_glossary.ndjson` (copy the live file first) so the
working-tree glossary.ndjson is never touched; do NOT apply to the live file and
then `git checkout` to "undo" — that revert also wipes any uncommitted parallel
fill sitting in the working tree ([CR-CORPUS-WORKTREE]).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import loc_glossary  # noqa: E402
from loc_glossary import (  # noqa: E402
    DEFAULT_GLOSSARY,
    SOURCE_LANG,
    index_by_term,
    project_languages,
    read_records,
    write_records,
)

_USAGE = (
    "usage:\n"
    "  loc_glossary_apply.py <lang> <edits.json> [--glossary glossary.ndjson]\n"
    "      edits.json = {term: \"translation\"}\n"
    "  loc_glossary_apply.py --map <edits.json> [--glossary glossary.ndjson]\n"
    "      edits.json = {term: {lang: translation, ...}}"
)


def _flatten(raw: dict, lang: str | None) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Normalize either input shape into {term: {lang: text}}. Returns (edits, errors)."""
    edits: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    if lang is not None:  # Mode 1: {term: text}
        for term, value in raw.items():
            if not isinstance(value, str):
                errors.append(f"term {term!r}: value must be a string in <lang> mode (got {type(value).__name__})")
                continue
            edits.setdefault(term, {})[lang] = value
    else:                 # Mode 2: {term: {lang: text}}
        for term, value in raw.items():
            if not isinstance(value, dict):
                errors.append(f"term {term!r}: value must be an object {{lang: text}} in --map mode (got {type(value).__name__})")
                continue
            for lng, text in value.items():
                if not isinstance(text, str):
                    errors.append(f"term {term!r} lang {lng!r}: translation must be a string (got {type(text).__name__})")
                    continue
                edits.setdefault(term, {})[lng] = text
    return edits, errors


def main() -> int:
    argv = sys.argv[1:]

    glossary_path = DEFAULT_GLOSSARY
    if "--glossary" in argv:
        i = argv.index("--glossary")
        try:
            glossary_path = Path(argv[i + 1])
        except IndexError:
            print(_USAGE, file=sys.stderr)
            return 2
        del argv[i : i + 2]

    map_mode = False
    if "--map" in argv:
        map_mode = True
        argv.remove("--map")

    if map_mode:
        if len(argv) != 1:
            print(_USAGE, file=sys.stderr)
            return 2
        lang: str | None = None
        json_path = Path(argv[0])
    else:
        if len(argv) != 2:
            print(_USAGE, file=sys.stderr)
            return 2
        lang = argv[0]
        json_path = Path(argv[1])

    if not json_path.exists():
        print(f"error: edits file not found: {json_path}", file=sys.stderr)
        return 2
    if not glossary_path.exists():
        print(f"error: glossary not found: {glossary_path}", file=sys.stderr)
        return 2

    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {json_path}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(raw, dict):
        print(f"error: {json_path} must be a JSON object", file=sys.stderr)
        return 2

    edits, errors = _flatten(raw, lang)
    if errors:
        for msg in errors:
            print(f"error: {msg}", file=sys.stderr)
        return 2

    known = set(project_languages())
    bad_lang: set[str] = set()
    for langs in edits.values():
        for lng in langs:
            if lng == SOURCE_LANG:
                bad_lang.add(lng)
            elif lng not in known:
                bad_lang.add(lng)
    if bad_lang:
        if SOURCE_LANG in bad_lang:
            print(f"error: cannot set t[{SOURCE_LANG!r}] — the en form is the term headword, not a translation", file=sys.stderr)
        unknown = sorted(bad_lang - {SOURCE_LANG})
        if unknown:
            print(f"error: unknown language(s) (not project languages): {unknown}", file=sys.stderr)
        return 2

    if not edits:
        print(f"no entries in {json_path}")
        return 0

    records = read_records(glossary_path)
    index = index_by_term(records)

    replaced = 0
    touched_terms = 0
    unmatched: list[str] = []
    for term, langs in edits.items():
        record = index.get(term)
        if record is None:
            unmatched.append(term)
            continue
        t = record.get("t")
        if not isinstance(t, dict):
            t = {}
            record["t"] = t
        applied_here = 0
        for lng, text in langs.items():
            t[lng] = text  # write_records drops empties + sorts on serialize
            applied_here += 1
        if applied_here:
            touched_terms += 1
            replaced += applied_here

    if replaced:
        write_records(glossary_path, records)

    print(
        f"applied to {glossary_path}: cells={replaced}, terms={touched_terms}, "
        f"total_terms={len(edits)}, unmatched={len(unmatched)}"
    )

    if unmatched:
        print(
            f"\nUNMATCHED TERMS (NOT APPLIED) — {len(unmatched)} not found in "
            f"{glossary_path.name} (exact, case-sensitive):",
            file=sys.stderr,
        )
        for term in sorted(unmatched):
            print(f"  - {term}", file=sys.stderr)
        print(
            "Unmatched = upstream term transcription error or stale glossary. "
            "Hand-correct the JSON term against the glossary and re-run. Matched "
            "edits above were still written.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
