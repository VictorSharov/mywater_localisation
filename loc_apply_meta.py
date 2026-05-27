#!/usr/bin/env python3
"""Edit key-level metadata (platforms, description) in strings.ndjson.

    # add a platform to an existing key (reuse it on a new platform)
    python3 loc_apply_meta.py --key onboarding.title --add-platform android
    # drop a platform
    python3 loc_apply_meta.py --key legacy.banner --remove-platform ios
    # replace the whole platform set
    python3 loc_apply_meta.py --key promo.cta --set-platforms ios,android
    # change the translator description (the Lokalise `description` field)
    python3 loc_apply_meta.py --key text2_3F --description "Surface: main screen ..."
    python3 loc_apply_meta.py --key text2_3F --description-file note.txt
    python3 loc_apply_meta.py --key text2_3F --clear-description

This is the metadata sibling of loc_apply_lang.py: stdlib-only, token-free, and it
mutates the corpus IN PLACE through loc_corpus's setters (never hand-edits the
NDJSON — [CR-CORPUS-OWNER]). It is replace-only: every --key must already exist in
the corpus; an unknown key is reported and the run exits non-zero (a metadata edit
is never a new key — add new keys per CLAUDE.md § Adding a new key).

The corpus is the source of truth for these fields. Each edited field is flagged
in the record's `dirty_meta` set, and the next `loc_corpus_import.py --apply`
pushes it to Lokalise via the keys endpoint (platforms = full-array replace, so
add/remove propagates as the resulting set; the corpus `context` field is pushed
to the Lokalise `description` field), then clears `dirty_meta` so a re-run is a
no-op. Review `git diff -- strings.ndjson` before importing.

Platforms are validated against Lokalise's set (ios/android/web/other) and a key is
never left with zero platforms. --set-platforms cannot be combined with
--add-platform / --remove-platform (replace vs. modify are different intents).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loc_corpus import (  # noqa: E402
    DEFAULT_CORPUS,
    PLATFORM_ORDER,
    display_key,
    index_by_key_name,
    platforms,
    read_records,
    set_context,
    set_platforms,
    write_records,
)

VALID_PLATFORMS = set(PLATFORM_ORDER)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Edit key platforms / description in strings.ndjson.")
    parser.add_argument("--key", action="append", required=True, help="Key name to edit. Repeatable; the same ops apply to each.")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS, help=f"Corpus path. Default: {DEFAULT_CORPUS}.")
    parser.add_argument("--add-platform", action="append", default=[], metavar="P", help="Platform to add (ios/android/web/other). Repeatable.")
    parser.add_argument("--remove-platform", action="append", default=[], metavar="P", help="Platform to remove. Repeatable.")
    parser.add_argument("--set-platforms", metavar="P,P", help="Replace the platform set with this comma-separated list.")
    desc = parser.add_mutually_exclusive_group()
    desc.add_argument("--description", help="Set the translator description (pushed to Lokalise `description`).")
    desc.add_argument("--description-file", type=Path, help="Read the description from this file (for multi-line notes).")
    desc.add_argument("--clear-description", action="store_true", help="Clear the description (pushes an empty Lokalise `description`).")
    return parser


def parse_platform_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def resolve_description(args: argparse.Namespace) -> str | None:
    """The new description text, or None when no description op was requested."""
    if args.clear_description:
        return ""
    if args.description is not None:
        return args.description
    if args.description_file is not None:
        if not args.description_file.exists():
            raise FileNotFoundError(f"description file not found: {args.description_file}")
        return args.description_file.read_text(encoding="utf-8")
    return None


def validate_platform_args(args: argparse.Namespace) -> str | None:
    """Error string for the platform options, or None when they are coherent."""
    if args.set_platforms is not None and (args.add_platform or args.remove_platform):
        return "--set-platforms cannot be combined with --add-platform / --remove-platform."
    requested = set(args.add_platform) | set(args.remove_platform) | set(parse_platform_list(args.set_platforms or ""))
    unknown = sorted(requested - VALID_PLATFORMS)
    if unknown:
        return f"unknown platform(s): {', '.join(unknown)}; valid: {', '.join(PLATFORM_ORDER)}"
    return None


def next_platforms(record: dict, args: argparse.Namespace) -> list[str] | None:
    """The platform list this key should end up with, or None when no platform op
    was requested. add/remove modify the current set; --set-platforms replaces it."""
    if args.set_platforms is not None:
        return parse_platform_list(args.set_platforms)
    if not args.add_platform and not args.remove_platform:
        return None
    current = platforms(record)
    result = list(current)
    for platform in args.add_platform:
        if platform not in result:
            result.append(platform)
    remove = set(args.remove_platform)
    return [platform for platform in result if platform not in remove]


def main() -> int:
    args = build_parser().parse_args()

    platform_error = validate_platform_args(args)
    if platform_error:
        print(f"error: {platform_error}", file=sys.stderr)
        return 2
    try:
        new_description = resolve_description(args)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    has_platform_op = args.set_platforms is not None or args.add_platform or args.remove_platform
    if not has_platform_op and new_description is None:
        print("error: nothing to do — pass a platform op and/or a description op.", file=sys.stderr)
        return 2

    corpus_path = args.corpus
    if not corpus_path.exists():
        print(f"error: corpus not found: {corpus_path}", file=sys.stderr)
        return 2

    records = read_records(corpus_path)
    index = index_by_key_name(records)

    requested = list(dict.fromkeys(args.key))
    missing = [name for name in requested if name not in index]
    targets = [(name, index[name]) for name in requested if name in index]

    changed_records = 0
    for name, record in targets:
        touched: list[str] = []
        if has_platform_op:
            resulting = next_platforms(record, args)
            if resulting is not None:
                if not resulting:
                    print(f"error: refusing to leave key {name!r} with zero platforms.", file=sys.stderr)
                    return 2
                if set_platforms(record, resulting):
                    touched.append(f"platforms={','.join(platforms(record))}")
        if new_description is not None:
            if set_context(record, new_description):
                shown = record.get("context") or "<cleared>"
                touched.append(f"description={shown!r}" if shown == "<cleared>" else f"description set ({len(record['context'])} chars)")
        if touched:
            changed_records += 1
            print(f"updated {display_key(record)}: {'; '.join(touched)}")
        else:
            print(f"unchanged {display_key(record)}: already matches requested metadata")

    if changed_records:
        write_records(corpus_path, records)
        print(
            f"\nwrote {changed_records} change(s) to {corpus_path.name}; review `git diff -- {corpus_path.name}`, "
            f"then push with `python3 loc_corpus_import.py --apply` (pushes the dirty_meta fields)."
        )

    if missing:
        print(
            f"\nUNMATCHED KEYS (NOT APPLIED) — {len(missing)} key(s) not found in {corpus_path.name}:",
            file=sys.stderr,
        )
        for name in missing:
            print(f"  - {name}", file=sys.stderr)
        print(
            "A metadata edit is never a new key. Hand-correct the name against the corpus, or add a "
            "new key per CLAUDE.md § Adding a new key.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
