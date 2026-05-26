#!/usr/bin/env python3
"""Merge a set of languages into one review file for AI phrase cross-check.

Reads strings.ndjson (the cross-platform corpus). `en` + `ru` are always
included automatically (en = source-of-truth anchor, ru = full-parity audit
anchor). Any extra language codes are appended in the given order so a review
sub-agent can read the whole set side-by-side per key instead of opening many
files.

    python3 loc_merge_languages.py de fr ja
    python3 loc_merge_languages.py zh_CN
    python3 loc_merge_languages.py                # en + ru only
    python3 loc_merge_languages.py de --platform ios

Keys are iterated in corpus order (sorted by key_id). A language missing a key
shows `<MISSING IN {lang}>` (expected for the Lokalise backlog, not a bug). A
trailing section lists keys with no en source (data-quality signal) and the
unverified-by-language tally.

Output: deterministic `/tmp/loc_merge_<en_ru_extra>.txt` so the review agent
reads a predictable path.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loc_corpus import (  # noqa: E402
    DEFAULT_CORPUS,
    display_key,
    flat_text,
    has_platform,
    is_plural,
    read_records,
    translation,
    unknown_lang_message,
    unverified_langs,
)

PLATFORM_CHOICES = ("ios", "android", "other", "web")


def usage() -> None:
    print("usage:", file=sys.stderr)
    print("  loc_merge_languages.py [<lang> ...] [--platform ios|android|other|web]   (en + ru auto-included)", file=sys.stderr)
    print("  example: loc_merge_languages.py de fr ja", file=sys.stderr)


def resolve_languages(extra: list[str]) -> list[str]:
    """en, ru first (auto), then requested extras in order, deduped."""
    ordered = ["en", "ru"]
    for lang in extra:
        if lang not in ordered:
            ordered.append(lang)
    return ordered


def value_repr(record: dict, lang: str) -> str:
    if is_plural(record):
        forms = translation(record, lang)
        return repr(forms) if forms is not None else f"<MISSING IN {lang}>"
    flat = flat_text(record, lang)
    return repr(flat) if flat is not None else f"<MISSING IN {lang}>"


def main() -> int:
    argv = sys.argv[1:]
    if any(arg in ("-h", "--help") for arg in argv):
        usage()
        return 0

    platform: str | None = None
    if "--platform" in argv:
        index = argv.index("--platform")
        try:
            platform = argv[index + 1]
        except IndexError:
            usage()
            return 2
        if platform not in PLATFORM_CHOICES:
            print(f"error: --platform must be one of {PLATFORM_CHOICES}", file=sys.stderr)
            return 2
        del argv[index : index + 2]

    languages = resolve_languages(argv)

    records = read_records(DEFAULT_CORPUS)
    for lang in languages:
        message = unknown_lang_message(records, lang)
        if message:
            print(f"error: {message}", file=sys.stderr)
            return 2
    if platform:
        records = [record for record in records if has_platform(record, platform)]

    totals = {lang: sum(1 for record in records if flat_text(record, lang) is not None) for lang in languages}
    no_en = [display_key(record) for record in records if flat_text(record, "en") is None]

    out_name = "loc_merge_" + "_".join(languages) + (f"_{platform}" if platform else "") + ".txt"
    out_path = Path("/tmp") / out_name

    with out_path.open("w", encoding="utf-8") as handle:
        scope = f" (platform={platform})" if platform else ""
        handle.write(f"# Localization merge for review — languages: {', '.join(languages)}{scope}\n")
        handle.write(f"# Key order: corpus order (sorted by key_id), {len(records)} keys\n")
        for lang in languages:
            handle.write(f"# {lang} present: {totals[lang]}\n")
        handle.write("# <MISSING IN {lang}> = key has no translation for that language (Lokalise backlog, expected)\n")
        handle.write("# unverified (if present) = languages Lokalise flags as needing review\n")
        handle.write("# context (if present) is translator context per docs/LOCALIZATION.md\n\n")

        for index, record in enumerate(records, 1):
            handle.write(f"--- entry {index:04d} ---\n")
            handle.write(f'key: "{display_key(record)}"\n')
            handle.write(f"platforms: {','.join(record.get('platforms') or []) or '<none>'}\n")
            if is_plural(record):
                handle.write("plural: true\n")
            marked = unverified_langs(record)
            if marked:
                handle.write(f"unverified: {','.join(sorted(marked))}\n")
            context = record.get("context")
            if context:
                handle.write(f"context:\n{context}\n")
            for lang in languages:
                handle.write(f"{lang} : {value_repr(record, lang)}\n")
            handle.write("\n")

        if no_en:
            handle.write(f"# Keys with no en source ({len(no_en)} — data-quality signal):\n")
            for key in no_en:
                handle.write(f"#   {key}\n")
        else:
            handle.write("# Every key has an en source.\n")

    summary = ", ".join(f"{lang}: {totals[lang]}" for lang in languages)
    print(f"wrote {out_path} ({len(records)} entries)")
    print(f"present per language — {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
