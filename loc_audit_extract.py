#!/usr/bin/env python3
"""Extract a batch of en+ru[+target] key entries from the ndjson corpus for audit.

Reads strings.ndjson (the cross-platform corpus), so the audit is no longer
limited to one platform's slice — pass --platform to scope, or audit everything.

    python3 loc_audit_extract.py de 1 200 /tmp/loc_audit_de_batch_001.txt
    python3 loc_audit_extract.py fr 201 400 /tmp/loc_audit_fr_batch_002.txt --platform ios
    python3 loc_audit_extract.py en 1 200 /tmp/loc_audit_en_batch_001.txt   # en source audit

`<lang>` is the language under audit. en+ru are always shown as anchors
(en = source-of-truth, ru = full-parity reference). When <lang> is en or ru the
batch is just the en+ru pair (no duplicate column).

Indices are 1-based, inclusive, over corpus order (records sorted by key_id) —
the same record order a fresh generation produces, so batch ranges are stable.

Keys whose <lang> translation is absent are skipped from the batch (counted in
the header). They are translation backlog, not audit-of-existing scope — fill
them via loc_r_marked_translations.py. en source audit (<lang>=en) never skips.

Output format is consumed by the loc_audit_prompt.md sub-agent workflow.
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
    print("  loc_audit_extract.py <lang> <start> <end> <output_path> [--platform ios|android|other|web]", file=sys.stderr)
    print("  indices are 1-based, inclusive, over corpus order (sorted by key_id)", file=sys.stderr)
    print("  example: loc_audit_extract.py de 1 200 /tmp/loc_audit_de_batch_001.txt", file=sys.stderr)


def value_repr(record: dict, lang: str) -> str:
    """Plural keys show their {form: text} map; others show the flat string."""
    if is_plural(record):
        forms = translation(record, lang)
        return repr(forms) if forms is not None else f"<MISSING IN {lang}>"
    flat = flat_text(record, lang)
    return repr(flat) if flat is not None else f"<MISSING IN {lang}>"


def main() -> int:
    argv = sys.argv[1:]
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

    if len(argv) != 4:
        usage()
        return 2
    lang = argv[0]
    if lang.isdigit():
        usage()
        return 2
    try:
        start = int(argv[1])
        end = int(argv[2])
    except ValueError:
        usage()
        return 2
    out_path = Path(argv[3])

    records = read_records(DEFAULT_CORPUS)
    message = unknown_lang_message(records, lang)
    if message:
        print(f"error: {message}", file=sys.stderr)
        return 2
    if platform:
        records = [record for record in records if has_platform(record, platform)]

    total = len(records)
    if start < 1 or end > total or start > end:
        scope = f" (platform={platform})" if platform else ""
        print(f"error: indices out of range (corpus has {total} keys{scope}, got {start}..{end})", file=sys.stderr)
        return 2

    audit_en_source = lang == "en"
    batch = records[start - 1 : end]
    emitted = 0
    skipped = 0

    with out_path.open("w", encoding="utf-8") as handle:
        scope = f", platform={platform}" if platform else ""
        handle.write(f"# Localization audit batch (corpus keys {start}..{end}, target={lang}{scope})\n")
        handle.write(f"# corpus total: {total} keys\n")
        if audit_en_source:
            handle.write("# en source audit mode: every key in range is emitted; ru shown as reference\n")
            handle.write("# Format: each entry is `key` / `en` / `ru`\n")
        else:
            handle.write(f"# Skipped keys (missing {lang} translation) are out of audit scope — fill via loc_r_marked_translations.py\n")
            if lang == "ru":
                handle.write("# Format: each entry is `key` / `en` / `ru`\n")
            else:
                handle.write(f"# Format: each entry is `key` / `en` / `ru` / `{lang}`\n")
        handle.write("# unverified: languages Lokalise flags as needing review (the cross-platform QA signal)\n")
        handle.write("# context (if present) is translator context per docs/LOCALIZATION.md\n\n")

        for offset, record in enumerate(batch, start):
            if not audit_en_source and flat_text(record, lang) is None:
                skipped += 1
                continue
            emitted += 1
            handle.write(f"--- entry {offset:04d} ---\n")
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
            handle.write(f"en : {value_repr(record, 'en')}\n")
            handle.write(f"ru : {value_repr(record, 'ru')}\n")
            if not audit_en_source and lang not in {"en", "ru"}:
                handle.write(f"{lang} : {value_repr(record, lang)}\n")
            handle.write("\n")

    print(f"wrote {out_path}: emitted {emitted} entries (skipped {skipped} missing {lang})")
    print(f"corpus total: {total}{' (platform=' + platform + ')' if platform else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
