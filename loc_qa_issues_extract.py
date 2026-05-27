#!/usr/bin/env python3
"""Build per-language validation batches from the Lokalise QA-flag snapshot.

Token-free join step of the QA-validation pipeline: reads qa_issues.ndjson (the
flagged (key, lang) snapshot from loc_qa_issues_fetch.py) and strings.ndjson (the
corpus), joins by key_id, and emits one batch per language containing only the
flagged keys — en (source) + ru (full-parity reference) + the flagged target
value + which QA check fired + translator context. A sub-agent then judges each
flag (real error vs LanguageTool false positive), and confirmed fixes go back
into the corpus via loc_apply_lang.py (replace-only, stays `unverified`).

    python3 loc_qa_issues_extract.py de /tmp/qa_de.txt
    python3 loc_qa_issues_extract.py --all --out-dir /tmp/qa_batches
    python3 loc_qa_issues_extract.py pt_BR /tmp/qa_pt.txt --platform ios

Split by LANGUAGE on purpose: LanguageTool's false-positive patterns are
language-specific and each language has its own calibration
(loc_audit_lang_calibration/<lang>.md), so one batch == one linguistic context.
The output format mirrors loc_audit_extract.py so the loc_audit_prompt.md
sub-agent workflow consumes it directly.

Stdlib-only and token-free (operates on the local snapshots, produces a git
diff). Re-fetch qa_issues.ndjson / regenerate strings.ndjson upstream — never
hand-edit either; this script only reads them.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Run as a file; keep sibling imports working regardless of CWD.
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

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_QA = SCRIPT_DIR / "qa_issues.ndjson"
PLATFORM_CHOICES = ("ios", "android", "other", "web")
ANCHOR_LANGS = ("en", "ru")  # always shown; no duplicate column when target is one of these


def main() -> int:
    args = build_parser().parse_args()
    try:
        qa_path = Path(args.qa)
        corpus_path = Path(args.corpus)
        for label, path in (("qa-issues", qa_path), ("corpus", corpus_path)):
            if not path.exists():
                print(f"error: {label} file not found: {path}", file=sys.stderr)
                return 2

        rows_by_lang = group_by_lang(load_qa_rows(qa_path))
        records = read_records(corpus_path)
        corpus_index = index_by_key_id(records)

        if args.all:
            if args.lang or args.out:
                print("error: do not combine --all with positional <lang> <out>", file=sys.stderr)
                return 2
            if not args.out_dir:
                print("error: --all requires --out-dir", file=sys.stderr)
                return 2
            return run_all(rows_by_lang, records, corpus_index, Path(args.out_dir), args.platform)

        if not args.lang or not args.out:
            print(
                "usage: loc_qa_issues_extract.py <lang> <out> [--platform ios|android|other|web]\n"
                "       loc_qa_issues_extract.py --all --out-dir DIR",
                file=sys.stderr,
            )
            return 2
        return run_single(args.lang, Path(args.out), rows_by_lang, records, corpus_index, args.platform)
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Join the QA-flag snapshot to the corpus into per-language validation batches."
    )
    parser.add_argument("lang", nargs="?", help="Language to extract flagged entries for (single-language mode).")
    parser.add_argument("out", nargs="?", help="Output batch path (single-language mode).")
    parser.add_argument("--all", action="store_true", help="Write one batch per flagged language into --out-dir.")
    parser.add_argument("--out-dir", help="Output directory for --all mode.")
    parser.add_argument("--platform", choices=PLATFORM_CHOICES, help="Scope to keys targeting this platform.")
    parser.add_argument("--qa", default=str(DEFAULT_QA), help=f"QA-issues NDJSON. Default: {DEFAULT_QA}.")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS), help=f"Corpus NDJSON. Default: {DEFAULT_CORPUS}.")
    return parser


def load_qa_rows(path: Path) -> list[dict[str, Any]]:
    """Parse the QA-flag snapshot (NDJSON, one flagged (key, lang) per line)."""
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid NDJSON line: {error}") from error
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: NDJSON line is not an object")
            rows.append(row)
    return rows


def group_by_lang(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Bucket flagged rows by language, each bucket sorted by key_id for a stable batch."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        lang = row.get("lang")
        if lang:
            grouped[lang].append(row)
    for bucket in grouped.values():
        bucket.sort(key=lambda row: (row.get("key_id") is None, row.get("key_id")))
    return grouped


def index_by_key_id(records: list[dict[str, Any]]) -> dict[Any, dict[str, Any]]:
    index: dict[Any, dict[str, Any]] = {}
    for record in records:
        key_id = record.get("key_id")
        if key_id is not None:
            index.setdefault(key_id, record)
    return index


def value_repr(record: dict[str, Any], lang: str) -> str:
    """Plural keys show their {form: text} map; others the flat string. Mirrors loc_audit_extract."""
    if is_plural(record):
        forms = translation(record, lang)
        return repr(forms) if forms is not None else f"<MISSING IN {lang}>"
    flat = flat_text(record, lang)
    return repr(flat) if flat is not None else f"<MISSING IN {lang}>"


def render_entry(number: int, record: dict[str, Any], lang: str, qa_row: dict[str, Any]) -> str:
    is_anchor = lang in ANCHOR_LANGS
    lines = [f"--- entry {number:04d} ---"]
    lines.append(f'key: "{display_key(record)}"')
    lines.append(f"platforms: {','.join(record.get('platforms') or []) or '<none>'}")
    if is_plural(record):
        lines.append("plural: true")
    lines.append(f"qa: {','.join(qa_row.get('issues') or []) or '<none>'}")
    marked = unverified_langs(record)
    if marked:
        lines.append(f"unverified: {','.join(sorted(marked))}")
    context = record.get("context")
    if context:
        lines.append(f"context:\n{context}")
    lines.append(f"en : {value_repr(record, 'en')}")
    lines.append(f"ru : {value_repr(record, 'ru')}")
    if not is_anchor:
        lines.append(f"{lang} : {value_repr(record, lang)}")

    # Surface corpus/Lokalise drift: the flag was raised on the Lokalise value, but
    # the corpus is the edit surface — if they differ the corpus is stale for this lang.
    flagged = qa_row.get("value")
    corpus_flat = flat_text(record, lang)
    if not is_plural(record) and isinstance(flagged, str) and corpus_flat is not None and flagged != corpus_flat:
        lines.append(f"flagged_value: {flagged!r}  # corpus drifted from Lokalise — regenerate before editing")

    detail = qa_row.get("qa")
    if detail is not None:
        lines.append(f"qa_detail: {json.dumps(detail, ensure_ascii=False)}")
    return "\n".join(lines)


def batch_text(lang: str, rows: list[dict[str, Any]], corpus_index: dict[Any, dict[str, Any]], platform: str | None) -> tuple[str, dict[str, int]]:
    blocks: list[str] = []
    stats = {"emitted": 0, "no_key": 0, "off_platform": 0}
    for qa_row in rows:
        record = corpus_index.get(qa_row.get("key_id"))
        if record is None:
            stats["no_key"] += 1
            continue
        if platform and not has_platform(record, platform):
            stats["off_platform"] += 1
            continue
        stats["emitted"] += 1
        blocks.append(render_entry(stats["emitted"], record, lang, qa_row))

    scope = f", platform={platform}" if platform else ""
    header = [
        f"# QA validation batch — language={lang}{scope}",
        "# Source: qa_issues.ndjson (Lokalise LanguageTool flags) joined to strings.ndjson by key_id.",
        "# Task per entry: decide REAL error vs LanguageTool FALSE POSITIVE; if real, give the corrected value.",
        "#   Frequent false positives on UI strings: brand (MyWater), placeholders [%s]/[%i],",
        "#   informal register (du / ты), fragments without final punctuation, loanwords/transliteration.",
        "# en = source of truth · ru = full-parity reference · <lang> = the flagged value to judge.",
        "# qa: which QA check(s) fired. unverified: langs Lokalise flags for review. context: translator context.",
        "# flagged_value appears only on corpus/Lokalise drift (corpus stale for this lang — regenerate first).",
        "# Confirmed fixes -> {key: value} JSON -> loc_apply_lang.py <lang> fixes.json (stays unverified).",
        f"# flagged entries: {stats['emitted']}  "
        f"(skipped: {stats['no_key']} key_id not in corpus, {stats['off_platform']} off-platform)",
        "",
    ]
    body = "\n\n".join(blocks)
    text = "\n".join(header) + (body + "\n" if body else "")
    return text, stats


def run_single(
    lang: str,
    out_path: Path,
    rows_by_lang: dict[str, list[dict[str, Any]]],
    records: list[dict[str, Any]],
    corpus_index: dict[Any, dict[str, Any]],
    platform: str | None,
) -> int:
    message = unknown_lang_message(records, lang)
    if message:
        print(f"error: {message}", file=sys.stderr)
        return 2
    rows = rows_by_lang.get(lang, [])
    text, stats = batch_text(lang, rows, corpus_index, platform)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(
        f"wrote {out_path}: {stats['emitted']} flagged {lang} entries "
        f"(skipped {stats['no_key']} not in corpus, {stats['off_platform']} off-platform)"
    )
    if not rows:
        print(f"note: no {lang} flags in the QA snapshot", file=sys.stderr)
    return 0


def run_all(
    rows_by_lang: dict[str, list[dict[str, Any]]],
    records: list[dict[str, Any]],
    corpus_index: dict[Any, dict[str, Any]],
    out_dir: Path,
    platform: str | None,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: list[tuple[str, int]] = []
    for lang in sorted(rows_by_lang):
        message = unknown_lang_message(records, lang)
        if message:
            print(f"skip {lang}: {message}", file=sys.stderr)
            continue
        text, stats = batch_text(lang, rows_by_lang[lang], corpus_index, platform)
        out_path = out_dir / f"qa_{lang}.txt"
        out_path.write_text(text, encoding="utf-8")
        summary.append((lang, stats["emitted"]))

    print(f"wrote {len(summary)} per-language batches -> {out_dir}", file=sys.stderr)
    for lang, emitted in sorted(summary, key=lambda item: (-item[1], item[0])):
        print(f"  qa_{lang}.txt: {emitted}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
