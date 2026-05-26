#!/usr/bin/env python3
"""Generate a machine-readable NDJSON corpus of ALL Lokalise keys for AI-agent use.

Purpose: one file an AI agent reads to (1) avoid creating duplicate keys —
it sees keys from every platform, not just the local slice — and (2) QA
translations across every language at once.

One line per key, e.g.:
    {"key_id":123,"key":"select_country","platforms":["ios","android"],
     "en":"Select your country","context":"Signup screen",
     "unverified":["ru"],"t":{"en":"Select your country","ru":"Выберите страну"}}

Top-level `en` is a flat source string for quick dedup search (grep / jq) — it is
always a string. Plural keys keep nested CLDR forms per language in `t`; their
flat `en` is the `other` form:
    {"key_id":456,"key":"days_left","platforms":["ios"],"plural":true,
     "en":"%d days","t":{"en":{"one":"%d day","other":"%d days"}}}

`unverified` lists languages whose translation Lokalise flags unverified / fuzzy
(needs review) — the primary cross-platform QA signal. Missing translations are
NOT listed here; they show as "" inside `t` (missing, not unverified).

A sibling `strings.meta.json` records generated_at, source_lang and the
language / platform sets + counts — so a consumer can spot a stale corpus and
orient without scanning the whole file.

Lean by design: false/empty fields (`plural`, `archived`, `context`,
`char_limit`, `unverified`) are omitted. Keys are sorted by key_id and languages
within `t` are sorted, so a regenerated corpus diffs cleanly (only the meta
timestamp churns).

Lokalise is the source of truth; this file is a regenerable cache — do not
hand-edit, regenerate instead. Stale cache reintroduces duplicate keys, so
re-run whenever keys change.

Output defaults next to this script (the shared localisation repo) so iOS /
Android / server sessions read one file (attach it via
permissions.additionalDirectories). The token holder regenerates, then commits +
pushes; consumers only pull / read — the Lokalise token never touches a consumer
session.

Runs under a local venv (needs the python-lokalise-api SDK; see requirements.txt):

    python3 -m venv .venv-lokalise
    .venv-lokalise/bin/pip install -r requirements.txt
    export LOKALISE_API_TOKEN=...
    export LOKALISE_PROJECT_ID=...
    .venv-lokalise/bin/python loc_corpus_ndjson.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Run as a file; keep sibling imports working regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from loc_corpus import (  # noqa: E402
    DEFAULT_CORPUS,
    PLURAL_CATEGORIES,
    flat_source,
    write_records,
)
from lokalise_helper import (  # noqa: E402
    DEFAULT_BASE_URL,
    LokaliseClient,
    LokaliseConfig,
    LokaliseError,
)

# The generator lives inside the shared localisation repo, so the corpus and its
# meta sidecar default to sitting next to this script. Override with --out.
DEFAULT_OUT = str(DEFAULT_CORPUS)


def main() -> int:
    args = build_parser().parse_args()
    try:
        config = config_from_env(args)
        client = LokaliseClient(config)
        keys = client.list_keys(
            include_translations=True,
            filter_archived=args.archived,
            limit=500,
        )
        records = [key_record(key) for key in keys]
        out_path = Path(args.out)
        write_records(out_path, records)
        meta = build_meta(records, args.source_lang)
        meta_path = out_path.with_name(out_path.stem + ".meta.json")
        write_json(meta_path, meta)
        print(
            f"wrote {meta['key_count']} keys, {len(meta['languages'])} languages -> {out_path}",
            file=sys.stderr,
        )
        print(
            f"meta -> {meta_path} (archived={args.archived}, unverified_keys={meta['unverified_key_count']})",
            file=sys.stderr,
        )
        return 0
    except LokaliseError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export all Lokalise keys to one NDJSON corpus for AI agents.")
    parser.add_argument("--out", default=DEFAULT_OUT, help=f"Output NDJSON path. Default: {DEFAULT_OUT}.")
    parser.add_argument("--project-id", default=os.environ.get("LOKALISE_PROJECT_ID"), help="Lokalise project id. Defaults to LOKALISE_PROJECT_ID.")
    parser.add_argument("--branch", default=os.environ.get("LOKALISE_BRANCH"), help="Optional Lokalise branch. Defaults to LOKALISE_BRANCH.")
    parser.add_argument("--base-url", default=os.environ.get("LOKALISE_API_BASE", DEFAULT_BASE_URL), help=f"API base URL. Defaults to {DEFAULT_BASE_URL}.")
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("LOKALISE_TIMEOUT", "30")), help="HTTP timeout in seconds.")
    parser.add_argument("--source-lang", default=os.environ.get("LOKALISE_SOURCE_LANG", "en"), help="Source language iso recorded in the meta sidecar. Default: en.")
    parser.add_argument(
        "--archived",
        choices=("exclude", "include", "only"),
        default="include",
        help="Archived filter. Default: include — the agent should see archived keys so it never reuses a dead one.",
    )
    return parser


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


def key_record(key: dict[str, Any]) -> dict[str, Any]:
    translations = translations_map(key)
    record: dict[str, Any] = {
        "key_id": key.get("key_id"),
        "key": collapse_key_name(key.get("key_name")),
        "platforms": list(key.get("platforms") or []),
        # Flat source string for quick dedup search (grep / jq). Always a string,
        # even for plural keys (their `other` form) — full per-form data is in `t`.
        "en": flat_source(translations.get("en")),
    }
    if key.get("is_plural"):
        record["plural"] = True
    context = (key.get("context") or key.get("description") or "").strip()
    if context:
        record["context"] = context
    char_limit = key.get("char_limit") or 0
    if char_limit:
        record["char_limit"] = char_limit
    if key.get("is_archived"):
        record["archived"] = True
    unverified = unverified_langs(key)
    if unverified:
        record["unverified"] = unverified
    record["t"] = translations
    return record


def unverified_langs(key: dict[str, Any]) -> list[str]:
    """Languages whose translation Lokalise flags as needing review. `is_unverified`
    is the current flag; `is_fuzzy` is its legacy alias (same state). Empty / missing
    translations are skipped — they already show as "" in `t` (missing, not unverified)."""
    out: list[str] = []
    for translation in key.get("translations") or []:
        iso = translation.get("language_iso")
        if not iso:
            continue
        if not (translation.get("is_unverified") or translation.get("is_fuzzy")):
            continue
        if not translation.get("translation"):
            continue
        out.append(iso)
    return sorted(out)


def collapse_key_name(key_name: Any) -> Any:
    """Lokalise key_name is per-platform. Collapse to a string when all platforms
    share one name (the common case → grep-friendly); keep the per-platform map
    only when they genuinely differ (lossless)."""
    if isinstance(key_name, str):
        return key_name
    if isinstance(key_name, dict):
        names = {platform: value for platform, value in key_name.items() if isinstance(value, str) and value}
        distinct = set(names.values())
        if len(distinct) == 1:
            return next(iter(distinct))
        return names
    return None


def translations_map(key: dict[str, Any]) -> dict[str, Any]:
    is_plural = bool(key.get("is_plural"))
    out: dict[str, Any] = {}
    for translation in key.get("translations") or []:
        iso = translation.get("language_iso")
        if not iso:
            continue
        value = translation.get("translation")
        out[iso] = plural_value(value) if is_plural else (value or "")
    return dict(sorted(out.items()))


def plural_value(raw: Any) -> dict[str, Any]:
    """Lokalise serializes a plural translation as a JSON object string of CLDR
    forms. Parse it; fall back to {'other': raw} when it is plain/empty."""
    forms: dict[str, Any]
    if isinstance(raw, dict):
        forms = raw
    elif isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {"other": raw}
        forms = parsed if isinstance(parsed, dict) else {"other": raw}
    else:
        return {"other": raw or ""}
    return {category: forms[category] for category in PLURAL_CATEGORIES if category in forms}


def build_meta(records: list[dict[str, Any]], source_lang: str) -> dict[str, Any]:
    languages: set[str] = set()
    platforms: set[str] = set()
    archived = 0
    plural = 0
    unverified_keys = 0
    for record in records:
        languages.update((record.get("t") or {}).keys())
        platforms.update(record.get("platforms") or [])
        if record.get("archived"):
            archived += 1
        if record.get("plural"):
            plural += 1
        if record.get("unverified"):
            unverified_keys += 1
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_lang": source_lang,
        "languages": sorted(languages),
        "platforms": sorted(platforms),
        "key_count": len(records),
        "archived_count": archived,
        "plural_count": plural,
        "unverified_key_count": unverified_keys,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
