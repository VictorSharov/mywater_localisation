#!/usr/bin/env python3
"""Apply a flat {key: value} translation map to one language in strings.ndjson.

    python3 loc_apply_lang.py <lang> <translations.json> [--corpus strings.ndjson]

`<translations.json>` is a JSON object mapping existing key -> new value, e.g.

    { "allow": "अनुमति दें", "week": "हफ़्ता" }

Only keys that already exist in the corpus are replaced (by exact name). Keys not
found are reported and the process exits non-zero — an unmatched key means an
upstream transcription error, not a new string to append. New keys are never
added here (add them to the corpus directly so every platform sees them).

Apply / unmatched-reporting is NOT reimplemented: this is a thin JSON input
adapter over loc_audit_apply.apply_changes(), the canonical owner of the corpus
replace invariant. Consequence: each applied language is flagged `unverified` in
the corpus (a fresh map still needs human / Lokalise review). Plural keys cannot
be expressed by a flat string value and are reported as skipped.

Not concurrency-safe: this rewrites the whole corpus (read-all -> mutate -> write-all),
so a parallel translation pass must run the apply step one language at a time — fan out
the per-language JSON generation, serialize the applies (CLAUDE.md
[CR-CORPUS-CONCURRENCY], § Parallel translation passes).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loc_audit_apply import apply_changes  # noqa: E402
from loc_corpus import (  # noqa: E402
    DEFAULT_CORPUS,
    read_records,
    unknown_lang_message,
    write_records,
)


def main() -> int:
    argv = sys.argv[1:]
    corpus_path = DEFAULT_CORPUS
    if "--corpus" in argv:
        index = argv.index("--corpus")
        try:
            corpus_path = Path(argv[index + 1])
        except IndexError:
            print("usage: loc_apply_lang.py <lang> <translations.json> [--corpus strings.ndjson]", file=sys.stderr)
            return 2
        del argv[index : index + 2]

    if len(argv) != 2:
        print("usage: loc_apply_lang.py <lang> <translations.json> [--corpus strings.ndjson]", file=sys.stderr)
        return 2

    lang = argv[0]
    json_path = Path(argv[1])
    if not json_path.exists():
        print(f"error: translations file not found: {json_path}", file=sys.stderr)
        return 2
    if not corpus_path.exists():
        print(f"error: corpus not found: {corpus_path}", file=sys.stderr)
        return 2

    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {json_path}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(raw, dict):
        print(f"error: {json_path} must be a JSON object {{key: value}}", file=sys.stderr)
        return 2

    changes: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(value, str):
            print(f"error: value for key {key!r} is not a string", file=sys.stderr)
            return 2
        changes[key] = value

    if not changes:
        print(f"no entries in {json_path}")
        return 0

    records = read_records(corpus_path)
    message = unknown_lang_message(records, lang)
    if message:
        print(f"error: {message}", file=sys.stderr)
        return 2
    replaced, unmatched, plural_skipped = apply_changes(records, changes, lang)
    if replaced:
        write_records(corpus_path, records)
    print(
        f"applied to {corpus_path}: replaced={replaced}, total={len(changes)}, "
        f"unmatched={len(unmatched)}, plural_skipped={len(plural_skipped)}"
    )

    if plural_skipped:
        print(
            f"\nPLURAL KEYS SKIPPED ({len(plural_skipped)}): a flat map cannot express "
            f"CLDR plural forms — edit the corpus `t` directly for these:",
            file=sys.stderr,
        )
        for key in sorted(plural_skipped):
            print(f"  - {key}", file=sys.stderr)

    if unmatched:
        print(
            f"\nUNMATCHED KEYS (NOT APPLIED) for lang={lang} — {len(unmatched)} key(s) "
            f"not found in {corpus_path.name}:",
            file=sys.stderr,
        )
        for key in sorted(unmatched):
            print(f"  - {key}", file=sys.stderr)
        print(
            "Unmatched = upstream key transcription error or stale corpus. "
            "Hand-correct the JSON key against the corpus and re-run. Matched "
            "replacements above were still written.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
