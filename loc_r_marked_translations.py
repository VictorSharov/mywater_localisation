#!/usr/bin/env python3
"""Extract and apply AI translations for the strings.ndjson translation backlog.

This owns the workflow for translating keys that still need a target value. The
needs-translation signal is the corpus `unverified` marker plus an empty target
(the iOS `|R|` source marker is retired): a key is "backlog" for <lang> when its
translation is

  - unverified : present but flagged by Lokalise as needing review (source moved
                 or a prior translation is fuzzy) — the cross-platform redo signal;
  - missing    : the language is absent from the key entirely;
  - empty       : the language is present but blank "".

Usage:
    python3 loc_r_marked_translations.py extract <lang>
    python3 loc_r_marked_translations.py extract <lang> --batch-size 50 --output-dir /tmp/loc_r_de --platform ios
    python3 loc_r_marked_translations.py apply <lang> /tmp/loc_r_de_001.json --dry-run
    python3 loc_r_marked_translations.py apply <lang> /tmp/loc_r_de_001.json

Scope:
  - strings.ndjson only; en is source-of-truth, ru is a style/meaning reference.
  - apply replaces a target value only for keys currently in the backlog for
    <lang> (unverified / missing / empty). Filled values are flagged `unverified`
    in the corpus — an AI translation needs human / Lokalise review before it
    counts as verified (the guarantee the corpus `unverified` marker provides).
  - non-plural values are strings; plural values are {form: text} CLDR maps.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loc_corpus import (  # noqa: E402
    DEFAULT_CORPUS,
    PLURAL_CATEGORIES,
    display_key,
    flat_source,
    flat_text,
    has_platform,
    index_by_key_name,
    is_plural,
    read_records,
    set_translation,
    translation,
    unknown_lang_message,
    unverified_langs,
    write_records,
)

MISSING_PREFIX = "<MISSING IN "
FORMAT_RE = re.compile(
    r"(?<!%)%(?!%)(?:\d+\$)?[-+#0 ]*(?:\d+|\*)?(?:\.(?:\d+|\*))?"
    r"(?:hh|h|ll|l|L|z|t|j)?[@diuoxXfFeEgGcCsSpa]"
)
# Lokalise universal placeholder ([%s], [%1$s], [%.2f], [%]) and the iOS
# .stringsdict substitution variable (%1$#@new_drinks@). Both must be peeled off
# BEFORE FORMAT_RE runs, or it would match the `%s` *inside* `[%s]` and the
# `%1$#@` head of a stringsdict var, collapsing universal and bare forms together.
UNIVERSAL_RE = re.compile(r"\[%[^\]]*\]")
STRINGSDICT_RE = re.compile(r"%\d*\$?#@\w+@")
FORBIDDEN_SPACE_RE = re.compile(
    r"[\u00a0\u1680\u180e\u2000-\u200b\u2028\u2029\u202f\u205f\u3000\ufeff]"
)
PLATFORM_CHOICES = ("ios", "android", "other", "web")


def backlog_status(record: dict, lang: str) -> str | None:
    """unverified / missing / empty, or None when the target value is verified."""
    flat = flat_text(record, lang)
    if flat is None:
        return "missing"
    if flat == "":
        return "empty"
    if lang in unverified_langs(record):
        return "unverified"
    return None


def placeholder_signature(value: str) -> list[str]:
    """Multiset of placeholders in `value`, position-normalized so a target may
    reorder indexed placeholders (`[%1$s] [%2$s]` ↔ `[%2$s] [%1$s]`).

    A universal `[%s]` and a bare `%s` are kept DISTINCT: dropping the brackets
    changes the signature so the round-trip check catches it. The brackets are
    what make Lokalise convert per platform (`[%s]`→iOS `%@`/Android `%s`); a
    bare `%s` pushed via the keys API is stored literally and mis-exports.
    """
    tokens: list[str] = []
    for match in UNIVERSAL_RE.finditer(value):
        # [%1$s] -> [%s]: strip the positional index, keep the universal bracket.
        tokens.append(re.sub(r"^\[%\d+\$", "[%", match.group(0)))
    remainder = STRINGSDICT_RE.sub("", UNIVERSAL_RE.sub("", value))
    for match in FORMAT_RE.finditer(remainder):
        tokens.append(re.sub(r"^%\d+\$", "%", match.group(0)))
    return sorted(tokens)


def json_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def backlog_records(records: list[dict], lang: str, platform: str | None) -> list[dict]:
    out = []
    for record in records:
        if platform and not has_platform(record, platform):
            continue
        if backlog_status(record, lang) is not None:
            out.append(record)
    return out


def write_batch(path: Path, lang: str, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(f"# strings.ndjson translation backlog batch - target={lang}\n")
        handle.write("# Agent workflow: docs/LOCALIZATION.md, translation backlog flow\n")
        handle.write('# Return a strict JSON object {"key":"translated value"}; do not edit files directly.\n')
        handle.write("# Plural keys: return {\"key\":{\"one\":\"...\",\"other\":\"...\"}} with the source's CLDR forms.\n")
        handle.write("# Translate the en_source only; ru_reference is a style/meaning anchor.\n\n")
        for index, record in enumerate(records, start=1):
            status = backlog_status(record, lang)
            handle.write(f"--- entry {index:04d} ---\n")
            handle.write(f'key: "{display_key(record)}"\n')
            handle.write(f"platforms: {','.join(record.get('platforms') or []) or '<none>'}\n")
            if is_plural(record):
                handle.write("plural: true\n")
            handle.write(f"backlog_status: {status}\n")
            context = record.get("context")
            if context:
                handle.write(f"context:\n{context}\n")
            if is_plural(record):
                handle.write(f"en_source: {json_string(str(translation(record, 'en')))}\n")
                ru_value = translation(record, "ru")
                handle.write(f"ru_reference: {json_string(str(ru_value)) if ru_value is not None else '<MISSING IN ru>'}\n")
                cur = translation(record, lang)
                handle.write(f"{lang}_current: {json_string(str(cur)) if cur is not None else f'<MISSING IN {lang}>'}\n\n")
            else:
                handle.write(f"en_source: {json_string(flat_source(translation(record, 'en')))}\n")
                ru_flat = flat_text(record, "ru")
                handle.write(f"ru_reference: {json_string(ru_flat) if ru_flat is not None else '<MISSING IN ru>'}\n")
                cur = flat_text(record, lang)
                handle.write(f"{lang}_current: {json_string(cur) if cur is not None else f'<MISSING IN {lang}>'}\n\n")


def extract(args: argparse.Namespace) -> int:
    if args.lang == "en":
        print("error: target language cannot be en", file=sys.stderr)
        return 2
    records = read_records(args.corpus)
    message = unknown_lang_message(records, args.lang)
    if message:
        print(f"error: {message}", file=sys.stderr)
        return 2
    entries = backlog_records(records, args.lang, args.platform)

    if args.batch_size is not None and args.batch_size <= 0:
        print("error: --batch-size must be a positive integer", file=sys.stderr)
        return 2

    if args.batch_size:
        output_dir = args.output_dir or Path("/tmp")
        output_dir.mkdir(parents=True, exist_ok=True)
        written = 0
        for offset in range(0, len(entries), args.batch_size):
            chunk = entries[offset : offset + args.batch_size]
            path = output_dir / f"loc_r_{args.lang}_{written + 1:03d}.md"
            write_batch(path, args.lang, chunk)
            print(f"wrote {path} ({len(chunk)} entries)")
            written += 1
        print(f"total backlog entries: {len(entries)} ({format_status_counts(entries, args.lang)}), batches: {written}")
        return 0

    output = args.output or Path("/tmp") / f"loc_r_{args.lang}.md"
    write_batch(output, args.lang, entries)
    print(f"wrote {output} ({len(entries)} backlog entries: {format_status_counts(entries, args.lang)})")
    return 0


def format_status_counts(records: list[dict], lang: str) -> str:
    counts = {"unverified": 0, "missing": 0, "empty": 0}
    for record in records:
        status = backlog_status(record, lang)
        if status in counts:
            counts[status] += 1
    return ", ".join(f"{key}={counts[key]}" for key in ("unverified", "missing", "empty"))


def load_translation_json(path: Path) -> dict[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a JSON object {{key: value}}")
    out: dict[str, object] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            raise ValueError(f"{path} keys must be strings")
        if not (isinstance(value, str) or isinstance(value, dict)):
            raise ValueError(f"{path}[{key!r}] must be a string or a plural-forms object")
        out[key] = value
    return out


def validate_translations(translations: dict[str, object], index: dict[str, dict], lang: str) -> list[str]:
    errors: list[str] = []
    if not translations:
        errors.append("translation JSON is empty")
        return errors

    for key, value in translations.items():
        record = index.get(key)
        if record is None:
            errors.append(f"{key}: key not found in corpus")
            continue
        if backlog_status(record, lang) is None:
            errors.append(f"{key}: {lang} already has a verified value (not in backlog)")
            continue

        if is_plural(record):
            if not isinstance(value, dict):
                errors.append(f"{key}: plural key needs a {{form: text}} object, got a string")
                continue
            unknown = [form for form in value if form not in PLURAL_CATEGORIES]
            if unknown:
                errors.append(f"{key}: unknown plural forms {unknown}; allowed {list(PLURAL_CATEGORIES)}")
            if "other" not in value:
                errors.append(f"{key}: plural value must include the 'other' form")
            check_value = flat_source(value)
        else:
            if not isinstance(value, str):
                errors.append(f"{key}: non-plural key needs a string value")
                continue
            check_value = value

        if check_value == "":
            errors.append(f"{key}: target value is empty")
        if check_value.startswith(MISSING_PREFIX):
            errors.append(f"{key}: target value still contains a missing sentinel")
        if FORBIDDEN_SPACE_RE.search(check_value):
            errors.append(f"{key}: target value contains a forbidden non-standard space character")

        source_sig = placeholder_signature(flat_source(translation(record, "en")))
        target_sig = placeholder_signature(check_value)
        if source_sig != target_sig:
            errors.append(f"{key}: placeholder mismatch; en={source_sig or '[]'} target={target_sig or '[]'}")
    return errors


def apply(args: argparse.Namespace) -> int:
    if args.lang == "en":
        print("error: target language cannot be en", file=sys.stderr)
        return 2
    try:
        translations = load_translation_json(args.translations_json)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    records = read_records(args.corpus)
    message = unknown_lang_message(records, args.lang)
    if message:
        print(f"error: {message}", file=sys.stderr)
        return 2
    index = index_by_key_name(records)
    errors = validate_translations(translations, index, args.lang)
    if errors:
        print("error: translation JSON failed validation:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    applied = 0
    for key, value in translations.items():
        set_translation(index[key], args.lang, value)
        applied += 1

    mode = "dry-run" if args.dry_run else "applied"
    if not args.dry_run and applied:
        write_records(args.corpus, records)
    print(f"{mode} {args.corpus}: applied={applied}, total={len(translations)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="write an AI translation batch for one language")
    extract_parser.add_argument("lang", help="target language code, e.g. de, fr, pt_BR")
    extract_parser.add_argument("--output", type=Path, help="single output markdown path")
    extract_parser.add_argument("--batch-size", type=int, help="split output into batches of N entries")
    extract_parser.add_argument("--output-dir", type=Path, help="directory for split batch output")
    extract_parser.add_argument("--platform", choices=PLATFORM_CHOICES, help="scope to one platform (default: all)")
    extract_parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS, help="corpus path")
    extract_parser.set_defaults(func=extract)

    apply_parser = subparsers.add_parser("apply", help="validate and apply a JSON translation map")
    apply_parser.add_argument("lang", help="target language code, e.g. de, fr, pt_BR")
    apply_parser.add_argument("translations_json", type=Path, help="JSON object {key: translated value}")
    apply_parser.add_argument("--dry-run", action="store_true", help="validate and report counts without writing")
    apply_parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS, help="corpus path")
    apply_parser.set_defaults(func=apply)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
