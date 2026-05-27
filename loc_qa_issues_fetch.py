#!/usr/bin/env python3
"""Fetch the translations Lokalise's QA checks flag, for AI-agent validation.

Lokalise's dashboard shows QA-warning counts (e.g. "Spelling/grammar errors:
1798"). Those checks run server-side (LanguageTool for spelling/grammar) and are
reachable through the API: the translations endpoint accepts `filter_qa_issues`,
so this pulls exactly the flagged translations. It queries one issue type per pass
so every row is attributed to the check that fired, regardless of whether the API
also returns per-translation `qa_issues` detail (captured when present).

Output: NDJSON, one line per flagged (key, language), sorted by (key_id, lang) so a
re-fetch diffs cleanly:

    {"key_id":123,"lang":"de","translation_id":456,
     "issues":["spelling_and_grammar"],"value":"Wilkommen"}

This is a regenerable Lokalise snapshot (like strings.ndjson) — do not hand-edit,
re-fetch instead. It is the seed for the QA-validation pipeline: a token-free
extract step joins it to strings.ndjson by key_id to build per-key batches (en + ru
+ flagged target + which check fired); a sub-agent then validates each flag (real
error vs LanguageTool false positive on brand / technical terms / placeholders) and
the confirmed fixes are applied into the corpus, kept `unverified`.

Of the QA categories, the non-linguistic ones (placeholders / whitespace / brackets
/ numbers) are already enforced deterministically and token-free by
loc_placeholder_lint.py + loc_qa.py, so the default issue type is
`spelling_and_grammar` — the one that needs linguistic judgement. Pass --issue to
fetch others (e.g. to reconcile what Lokalise flags against the local linters).

Needs the Lokalise token (operator-run, like loc_corpus_ndjson.py):

    python3 -m venv .venv-lokalise
    .venv-lokalise/bin/pip install -r requirements.txt
    export LOKALISE_API_TOKEN=...
    export LOKALISE_PROJECT_ID=...
    .venv-lokalise/bin/python loc_qa_issues_fetch.py
    .venv-lokalise/bin/python loc_qa_issues_fetch.py --issue spelling_and_grammar --issue placeholders
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# Run as a file; keep sibling imports working regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lokalise_helper import (  # noqa: E402
    DEFAULT_BASE_URL,
    QA_ISSUE_TYPES,
    LokaliseClient,
    LokaliseConfig,
    LokaliseError,
)

DEFAULT_ISSUE = "spelling_and_grammar"
DEFAULT_OUT = str(Path(__file__).resolve().parent / "qa_issues.ndjson")


def main() -> int:
    args = build_parser().parse_args()
    try:
        issues = chosen_issues(args.issue)
        config = config_from_env(args)
        client = LokaliseClient(config)
        rows = collect_rows(client, issues, args.limit)
        out_path = Path(args.out)
        write_rows(out_path, rows)
        print_summary(rows, issues, out_path)
        return 0
    except LokaliseError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch Lokalise QA-flagged translations to an NDJSON snapshot for AI validation."
    )
    parser.add_argument("--out", default=DEFAULT_OUT, help=f"Output NDJSON path. Default: {DEFAULT_OUT}.")
    parser.add_argument(
        "--issue",
        action="append",
        choices=QA_ISSUE_TYPES,
        help=f"QA issue type to fetch. Repeatable. Default: {DEFAULT_ISSUE}.",
    )
    parser.add_argument("--project-id", default=os.environ.get("LOKALISE_PROJECT_ID"), help="Lokalise project id. Defaults to LOKALISE_PROJECT_ID.")
    parser.add_argument("--branch", default=os.environ.get("LOKALISE_BRANCH"), help="Optional Lokalise branch. Defaults to LOKALISE_BRANCH.")
    parser.add_argument("--base-url", default=os.environ.get("LOKALISE_API_BASE", DEFAULT_BASE_URL), help=f"API base URL. Defaults to {DEFAULT_BASE_URL}.")
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("LOKALISE_TIMEOUT", "30")), help="HTTP timeout in seconds.")
    parser.add_argument("--limit", type=int, default=500, help="Page size, clamped to Lokalise max 500.")
    return parser


def chosen_issues(issues: list[str] | None) -> list[str]:
    """Apply the default and de-dup while preserving order. argparse `choices`
    already rejects unknown values."""
    selected = issues or [DEFAULT_ISSUE]
    seen: set[str] = set()
    out: list[str] = []
    for issue in selected:
        if issue not in seen:
            seen.add(issue)
            out.append(issue)
    return out


def config_from_env(args: argparse.Namespace) -> LokaliseConfig:
    api_token = os.environ.get("LOKALISE_API_TOKEN")
    if not api_token:
        raise LokaliseError("LOKALISE_API_TOKEN is required; pass secrets via env, not CLI args.")
    if not args.project_id:
        raise LokaliseError("project id is required via --project-id or LOKALISE_PROJECT_ID.")
    return LokaliseConfig(
        api_token=api_token,
        project_id=args.project_id,
        branch=args.branch,
        base_url=args.base_url,
        timeout_seconds=args.timeout,
    )


def collect_rows(client: LokaliseClient, issues: list[str], limit: int) -> list[dict[str, Any]]:
    """One server-side pass per issue type, merged by (key_id, lang) so a translation
    flagged by several checks becomes a single row with a sorted `issues` list."""
    merged: dict[tuple[int, str], dict[str, Any]] = {}
    for issue in issues:
        for translation in client.list_translations(filter_qa_issues=[issue], limit=limit):
            key_id = translation.get("key_id")
            lang = translation.get("language_iso")
            if key_id is None or not lang:
                continue
            entry = merged.setdefault(
                (int(key_id), lang),
                {
                    "key_id": int(key_id),
                    "lang": lang,
                    "translation_id": translation.get("translation_id"),
                    "issues": set(),
                    "value": translation.get("translation"),
                    "qa": translation.get("qa_issues"),
                },
            )
            entry["issues"].add(issue)
            if entry.get("qa") is None and translation.get("qa_issues") is not None:
                entry["qa"] = translation.get("qa_issues")

    rows: list[dict[str, Any]] = []
    for entry in merged.values():
        # Fixed field order (not sort_keys) for a readable, deterministic line.
        row: dict[str, Any] = {
            "key_id": entry["key_id"],
            "lang": entry["lang"],
            "translation_id": entry["translation_id"],
            "issues": sorted(entry["issues"]),
            "value": entry["value"],
        }
        if entry.get("qa") is not None:
            row["qa"] = entry["qa"]
        rows.append(row)
    rows.sort(key=lambda row: (row["key_id"], row["lang"]))
    return rows


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def print_summary(rows: list[dict[str, Any]], issues: list[str], out_path: Path) -> None:
    by_issue: Counter[str] = Counter()
    by_lang: Counter[str] = Counter()
    with_detail = 0
    for row in rows:
        for issue in row["issues"]:
            by_issue[issue] += 1
        by_lang[row["lang"]] += 1
        if "qa" in row:
            with_detail += 1
    print(f"wrote {len(rows)} flagged translations -> {out_path}", file=sys.stderr)
    print(f"  issues queried: {', '.join(issues)}", file=sys.stderr)
    for issue in issues:
        print(f"    {issue}: {by_issue.get(issue, 0)}", file=sys.stderr)
    by_lang_str = ", ".join(f"{lang}={count}" for lang, count in sorted(by_lang.items(), key=lambda item: (-item[1], item[0])))
    print(f"  by language: {by_lang_str or '(none)'}", file=sys.stderr)
    print(f"  rows with API qa_issues detail: {with_detail}/{len(rows)}", file=sys.stderr)
    if rows and with_detail == 0:
        print(
            "  note: no per-translation qa_issues detail in the response — attribution "
            "comes from the per-issue filter passes (still correct).",
            file=sys.stderr,
        )


if __name__ == "__main__":
    raise SystemExit(main())
