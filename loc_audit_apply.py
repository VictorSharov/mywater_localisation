#!/usr/bin/env python3
"""Apply validated audit findings to strings.ndjson (one target language).

Usage:
    python3 loc_audit_apply.py <lang> <validated_findings_path> [--corpus strings.ndjson]

Reads the validator's findings table (Markdown) and applies rows whose
verdict ∈ {accept, modify} to the <lang> translation of each matching key in the
corpus, then rewrites the corpus deterministically (only the touched lines diff).

Findings table format (output of the audit validator):

    | # | key | lang | severity | category | current | suggestion | rationale | verdict | applied_value |

Rules:
  - verdict ∈ {accept, modify, reject} — apply only accept/modify.
  - lang column must match <lang>; en-side findings are ignored here (en source
    edits are reviewed manually by the operator).
  - applied_value: for `accept` rows falls back to `suggestion` when empty/`—`;
    for `modify` rows the validator's `applied_value` overrides.
  - Each applied language is flagged `unverified` in the corpus — a corrected
    translation needs human / Lokalise review before it counts as verified.

Replace-only: a finding whose key is not in the corpus is reported as UNMATCHED
and the process exits non-zero (an unmatched key is an upstream transcription
error, not a new string — audit fixes only correct existing values). Plural keys
cannot be expressed in one findings cell (it holds a single flat string) and are
reported as skipped — apply those through `loc_apply_lang.py` with a `{cldr_form:
text}` map (a thin JSON adapter over this module's apply_changes, so the corpus
replace invariant is identical), not by hand-editing `t`.

New source strings are NOT appended here: add them to the corpus directly (so
every platform sees them) and let loc_corpus_import.py create them in Lokalise.

For dev / debugging runs use `--corpus /tmp/test_corpus.ndjson` (copy the live
corpus first) so the working-tree `strings.ndjson` is never touched. Do NOT apply
to the live corpus and then `git checkout strings.ndjson` to "undo" — that revert
also wipes any uncommitted parallel-agent edits sitting in the working tree
([CR-CORPUS-WORKTREE]).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loc_corpus import (  # noqa: E402
    DEFAULT_CORPUS,
    index_by_key_name,
    is_plural,
    read_records,
    set_translation,
    unknown_lang_message,
    write_records,
)


def parse_table(path: Path, target_lang: str) -> list[tuple[str, str]]:
    """Return list of (key, applied_value) for accept/modify rows matching target_lang."""
    rows: list[tuple[str, str]] = []
    header_columns: list[str] | None = None
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if header_columns is None:
                lower = [c.lower() for c in cells]
                if "key" in lower and "verdict" in lower:
                    header_columns = lower
                continue
            if all(set(c) <= set("-: ") for c in cells):
                continue
            if len(cells) != len(header_columns):
                continue
            entry = dict(zip(header_columns, cells))
            verdict = entry.get("verdict", "").lower()
            lang = entry.get("lang", "").lower()
            if verdict not in {"accept", "modify"}:
                continue
            if lang != target_lang.lower():
                continue
            key = entry.get("key", "").strip().strip('"').strip("`")
            applied = entry.get("applied_value", "").strip()
            if applied in {"—", "-", ""}:
                applied = entry.get("suggestion", "").strip()
            applied = applied.replace("\\|", "|")
            if not key or applied in {"—", "-", ""}:
                continue
            rows.append((key, applied))
    return rows


def apply_changes(
    records: list[dict],
    changes: dict[str, str | dict[str, str]],
    lang: str,
) -> tuple[int, list[str], list[str], list[str]]:
    """Set `t[lang]` for each matching key. A value is a string for a non-plural
    record or a `{cldr_form: text}` dict for a plural record. Returns
    (replaced, unmatched_keys, plural_skipped_keys, type_mismatched_keys):
    `plural_skipped` = string value passed for a plural record (findings tables
    cannot express CLDR forms); `type_mismatched` = dict value passed for a
    non-plural record (malformed input). Records are mutated in place."""
    index = index_by_key_name(records)
    replaced = 0
    unmatched: list[str] = []
    plural_skipped: list[str] = []
    type_mismatched: list[str] = []
    for key, value in changes.items():
        record = index.get(key)
        if record is None:
            unmatched.append(key)
            continue
        record_is_plural = is_plural(record)
        value_is_dict = isinstance(value, dict)
        if record_is_plural and not value_is_dict:
            plural_skipped.append(key)
            continue
        if not record_is_plural and value_is_dict:
            type_mismatched.append(key)
            continue
        set_translation(record, lang, value)
        replaced += 1
    return replaced, unmatched, plural_skipped, type_mismatched


def main() -> int:
    argv = sys.argv[1:]
    corpus_path = DEFAULT_CORPUS
    if "--corpus" in argv:
        index = argv.index("--corpus")
        try:
            corpus_path = Path(argv[index + 1])
        except IndexError:
            print("usage: loc_audit_apply.py <lang> <findings_path> [--corpus strings.ndjson]", file=sys.stderr)
            return 2
        del argv[index : index + 2]

    if len(argv) != 2:
        print("usage: loc_audit_apply.py <lang> <findings_path> [--corpus strings.ndjson]", file=sys.stderr)
        return 2
    lang = argv[0]
    findings_path = Path(argv[1])
    if not findings_path.exists():
        print(f"error: findings file not found: {findings_path}", file=sys.stderr)
        return 2
    if not corpus_path.exists():
        print(f"error: corpus not found: {corpus_path}", file=sys.stderr)
        return 2

    rows = parse_table(findings_path, lang)
    if not rows:
        print(f"no applicable rows found in {findings_path} for lang={lang}")
        return 0

    changes: dict[str, str] = {key: value for key, value in rows}
    records = read_records(corpus_path)
    message = unknown_lang_message(records, lang)
    if message:
        print(f"error: {message}", file=sys.stderr)
        return 2
    replaced, unmatched, plural_skipped, _ = apply_changes(records, changes, lang)

    if replaced:
        write_records(corpus_path, records)
    print(
        f"applied to {corpus_path}: replaced={replaced}, total={len(changes)}, "
        f"unmatched={len(unmatched)}, plural_skipped={len(plural_skipped)}"
    )

    if plural_skipped:
        print(
            f"\nPLURAL KEYS SKIPPED ({len(plural_skipped)}): a findings-table cell carries "
            f"one flat value and cannot express CLDR plural forms — apply these via "
            f"`loc_apply_lang.py <lang> <map.json>` with a {{form: text}} CLDR map.",
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
            "Unmatched = upstream key transcription error (case / whitespace / "
            "truncation) or a stale corpus. Hand-correct each finding's key against "
            "the corpus and re-run; matched replacements above were still written.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
