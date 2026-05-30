#!/usr/bin/env python3
"""Apply a {key: value} translation map to one language in strings.ndjson.

    python3 loc_apply_lang.py <lang> <translations.json> [--corpus strings.ndjson]

`<translations.json>` is a JSON object mapping existing key -> new value:

    - Non-plural key — value is a string:
        { "allow": "अनुमति दें", "week": "हफ़्ता" }

    - Plural key — value is a CLDR-forms map. Author every form your language
      needs (en one/other; ru one/few/many/other; ar zero/one/two/few/many/other):
        { "appleHealthResyncDoneExported":
            { "one":   "Caricata [%1$i] nuova bevanda su [%2$i]",
              "other": "Caricate [%1$i] nuove bevande su [%2$i]" } }

Only keys that already exist in the corpus are replaced (by exact name). Keys not
found are reported and the process exits non-zero — an unmatched key means an
upstream transcription error, not a new string to append. New keys are never
added here (add them to the corpus directly so every platform sees them).

Shape mismatches exit non-zero and are reported:
  - dict value passed for a non-plural corpus key — malformed input;
  - string value passed for a plural corpus key — author the CLDR-forms map.
Unknown CLDR form names in a plural value (typos like "oher") are rejected at
parse time before any corpus write.

Apply / unmatched-reporting is NOT reimplemented: this is a thin JSON input
adapter over loc_audit_apply.apply_changes(), the canonical owner of the corpus
replace invariant. Consequence: each applied language is flagged `unverified` in
the corpus (a fresh map still needs human / Lokalise review).

Not concurrency-safe: this rewrites the whole corpus (read-all -> mutate -> write-all),
so a parallel translation pass must run the apply step one language at a time — fan out
the per-language JSON generation, serialize the applies (CLAUDE.md
[CR-CORPUS-CONCURRENCY], PIPELINE.md § Parallel translation passes).

For dev / debugging runs use `--corpus /tmp/test_corpus.ndjson` (copy the live
corpus first) so the working-tree `strings.ndjson` is never touched. Do NOT apply
to the live corpus and then `git checkout strings.ndjson` to "undo" — that revert
also wipes any uncommitted parallel-agent edits sitting in the working tree
([CR-CORPUS-WORKTREE]).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loc_audit_apply import apply_changes  # noqa: E402
from loc_corpus import (  # noqa: E402
    DEFAULT_CORPUS,
    PLURAL_CATEGORIES,
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

    changes: dict[str, str | dict[str, str]] = {}
    for key, value in raw.items():
        if isinstance(value, str):
            changes[key] = value
            continue
        if isinstance(value, dict):
            unknown = [form for form in value if form not in PLURAL_CATEGORIES]
            if unknown:
                print(
                    f"error: plural value for key {key!r} has unknown CLDR form(s): "
                    f"{sorted(unknown)} (allowed: {list(PLURAL_CATEGORIES)})",
                    file=sys.stderr,
                )
                return 2
            non_string = [form for form, text in value.items() if not isinstance(text, str)]
            if non_string:
                print(
                    f"error: plural value for key {key!r} has non-string form(s): "
                    f"{sorted(non_string)}",
                    file=sys.stderr,
                )
                return 2
            changes[key] = value
            continue
        print(
            f"error: value for key {key!r} must be a string or a CLDR-forms dict "
            f"(got {type(value).__name__})",
            file=sys.stderr,
        )
        return 2

    if not changes:
        print(f"no entries in {json_path}")
        return 0

    records = read_records(corpus_path)
    message = unknown_lang_message(records, lang)
    if message:
        print(f"error: {message}", file=sys.stderr)
        return 2
    replaced, unmatched, plural_skipped, type_mismatched = apply_changes(records, changes, lang)
    if replaced:
        write_records(corpus_path, records)
    print(
        f"applied to {corpus_path}: replaced={replaced}, total={len(changes)}, "
        f"unmatched={len(unmatched)}, plural_skipped={len(plural_skipped)}, "
        f"type_mismatched={len(type_mismatched)}"
    )

    if plural_skipped:
        print(
            f"\nPLURAL KEYS SKIPPED ({len(plural_skipped)}): a flat string cannot express "
            f"CLDR plural forms — provide a {{form: text}} dict over "
            f"{list(PLURAL_CATEGORIES)} for these:",
            file=sys.stderr,
        )
        for key in sorted(plural_skipped):
            print(f"  - {key}", file=sys.stderr)

    if type_mismatched:
        print(
            f"\nTYPE MISMATCHED ({len(type_mismatched)}): a plural-forms dict was passed "
            f"for a non-plural corpus key — provide a plain string instead:",
            file=sys.stderr,
        )
        for key in sorted(type_mismatched):
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
    if plural_skipped or type_mismatched:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
