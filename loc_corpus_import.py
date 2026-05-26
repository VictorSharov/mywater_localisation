#!/usr/bin/env python3
"""Import strings.ndjson edits into Lokalise — the inverse of loc_corpus_ndjson.py.

Pipeline: agents/translators edit translations in the corpus (via the loc_*
apply scripts or by hand), git review shows a clean diff, then this script pushes
those edits into Lokalise. From Lokalise the translations export to iOS / Android
/ server in each platform's native format.

    python3 loc_corpus_import.py                         # dry-run, unverified langs only
    python3 loc_corpus_import.py --lang ru --lang de     # dry-run, only ru + de
    python3 loc_corpus_import.py --lang ru --apply        # push ru to Lokalise

What gets pushed, per key:
  - default: only the languages listed in the key's `unverified` set — i.e. the
    ones an apply script just edited (apply marks edited languages unverified) or
    that Lokalise already flagged for review. This avoids clobbering verified
    Lokalise translations with a stale snapshot.
  - `--lang X` (repeatable): push exactly these languages instead, for every key
    that has a value for them.

Existing keys (key_id present) are updated; keys with no key_id are created
(key_name + platforms + translations). Plural values are serialized as the CLDR
forms JSON string Lokalise expects. Pushed translations are marked unverified so
a human / Lokalise reviewer still signs off (pass --mark-verified to override) —
the same two-signal guarantee the corpus `unverified` flag carries.

Mutating is dry-run by default; pass --apply to perform the requests. Credentials
come from the env (LOKALISE_API_TOKEN / LOKALISE_PROJECT_ID), never CLI args.
Per [CR-ACCESS], the --apply path runs on the operator's machine with the token;
the dry-run plan is what an agent can produce without credentials.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loc_corpus import (  # noqa: E402
    DEFAULT_CORPUS,
    display_key,
    is_plural,
    key_names,
    read_records,
    translation,
    unverified_langs,
)
from lokalise_helper import (  # noqa: E402
    DEFAULT_BASE_URL,
    LokaliseClient,
    LokaliseConfig,
    LokaliseError,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import strings.ndjson translations into Lokalise.")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS, help=f"Corpus path. Default: {DEFAULT_CORPUS}.")
    parser.add_argument("--lang", action="append", help="Language iso to import. Repeatable. Default: each key's unverified languages.")
    parser.add_argument("--mark-verified", action="store_true", help="Push translations as verified (default: unverified, needs review).")
    parser.add_argument("--project-id", default=os.environ.get("LOKALISE_PROJECT_ID"), help="Lokalise project id. Defaults to LOKALISE_PROJECT_ID.")
    parser.add_argument("--branch", default=os.environ.get("LOKALISE_BRANCH"), help="Optional Lokalise branch.")
    parser.add_argument("--base-url", default=os.environ.get("LOKALISE_API_BASE", DEFAULT_BASE_URL), help=f"API base URL. Defaults to {DEFAULT_BASE_URL}.")
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("LOKALISE_TIMEOUT", "30")), help="HTTP timeout in seconds.")
    parser.add_argument("--apply", action="store_true", help="Execute the requests. Without this, prints a dry-run plan.")
    return parser


def langs_for(record: dict[str, Any], requested: list[str] | None) -> list[str]:
    """Languages to push for this key: the requested set (where a value exists),
    else the key's unverified set."""
    available = set((record.get("t") or {}).keys())
    if requested:
        return [lang for lang in requested if lang in available]
    return sorted(unverified_langs(record) & available)


def translation_payload(record: dict[str, Any], lang: str, mark_verified: bool) -> dict[str, Any]:
    value = translation(record, lang)
    serialized = json.dumps(value, ensure_ascii=False) if is_plural(record) and isinstance(value, dict) else value
    return {"language_iso": lang, "translation": serialized, "is_unverified": not mark_verified}


def create_key_name(record: dict[str, Any]) -> Any:
    """Lokalise create-keys accepts a string name or a per-platform map. Preserve
    whichever the corpus carries."""
    key = record.get("key")
    if isinstance(key, (str, dict)):
        return key
    names = key_names(record)
    return names[0] if names else None


def main() -> int:
    args = build_parser().parse_args()
    corpus_path = args.corpus
    if not corpus_path.exists():
        print(f"error: corpus not found: {corpus_path}", file=sys.stderr)
        return 2

    records = read_records(corpus_path)
    updates: list[dict[str, Any]] = []
    creates: list[dict[str, Any]] = []
    touched_langs: set[str] = set()

    for record in records:
        if record.get("archived"):
            continue
        langs = langs_for(record, args.lang)
        if not langs:
            continue
        touched_langs.update(langs)
        translations = [translation_payload(record, lang, args.mark_verified) for lang in langs]
        key_id = record.get("key_id")
        if key_id is not None:
            updates.append({"key_id": int(key_id), "key": display_key(record), "translations": translations})
        else:
            name = create_key_name(record)
            if name is None:
                print(f"warning: skipping key with no name and no key_id: {record!r}", file=sys.stderr)
                continue
            payload: dict[str, Any] = {"key_name": name, "platforms": record.get("platforms") or ["ios"], "translations": translations}
            if is_plural(record):
                payload["is_plural"] = True
            creates.append(payload)

    scope = ",".join(args.lang) if args.lang else "unverified-per-key"
    print(f"corpus: {corpus_path}  scope: {scope}  languages touched: {','.join(sorted(touched_langs)) or '<none>'}")
    print(f"plan: update {len(updates)} existing key(s), create {len(creates)} new key(s)")

    if not args.apply:
        print("\nDRY RUN: pass --apply to push to Lokalise. Sample of what would be sent:")
        for item in updates[:3]:
            langs = ",".join(t["language_iso"] for t in item["translations"])
            print(f"  update key_id={item['key_id']} ({item['key']}): langs {langs}")
        for item in creates[:3]:
            langs = ",".join(t["language_iso"] for t in item["translations"])
            print(f"  create key_name={item['key_name']}: langs {langs}")
        if not updates and not creates:
            print("  (nothing to import — no edited/unverified translations in scope)")
        return 0

    try:
        config = LokaliseConfig(
            api_token=require_token(),
            project_id=require_project_id(args.project_id),
            branch=args.branch,
            base_url=args.base_url,
            timeout_seconds=args.timeout,
        )
        client = LokaliseClient(config)
        for item in updates:
            client.update_key(item["key_id"], {"translations": item["translations"]})
            print(f"updated key_id={item['key_id']} ({item['key']})")
        for start in range(0, len(creates), 500):
            chunk = creates[start : start + 500]
            client.create_keys(chunk, use_automations=None)
            print(f"created {len(chunk)} key(s)")
    except LokaliseError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print("import complete")
    return 0


def require_token() -> str:
    token = os.environ.get("LOKALISE_API_TOKEN")
    if not token:
        raise LokaliseError("LOKALISE_API_TOKEN is required; pass secrets via env, not CLI args.")
    return token


def require_project_id(project_id: str | None) -> str:
    if not project_id:
        raise LokaliseError("project id is required via --project-id or LOKALISE_PROJECT_ID.")
    return project_id


if __name__ == "__main__":
    raise SystemExit(main())
