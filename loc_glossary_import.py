#!/usr/bin/env python3
"""Push `glossary.ndjson` into the Lokalise glossary through the API.

This is the glossary analogue of `loc_corpus_import.py`, but glossary terms are
reference data rather than release-gated strings: the push is a whole-glossary
upsert, not a dirty-marker drain. Mutating is dry-run by default; pass `--apply`
to write Lokalise.

Upsert identity:
  1. `term_id` when the local record has one and Lokalise still has that id;
  2. exact `term` match when the id is absent/stale;
  3. create when neither exists.

After a successful API push, newly resolved/created Lokalise ids are stamped back
into `glossary.ndjson` through `loc_glossary.write_records`, so re-runs update
instead of creating duplicate terms. Remote terms absent from the local glossary
are preserved; delete them explicitly in Lokalise or pull first if you intend to
reconcile remote-only terms.

Credentials come from the env (`LOKALISE_API_TOKEN` / `LOKALISE_PROJECT_ID`),
never CLI args.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import loc_glossary as glossary  # noqa: E402
from loc_glossary_api import (  # noqa: E402
    add_lokalise_api_args,
    api_term_id,
    api_term_name,
    config_from_args,
    glossary_path_display,
    language_maps,
    local_record_matches_remote,
    payload_matches_remote,
    used_translation_langs,
)
from lokalise_helper import LokaliseClient, LokaliseError  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Push glossary.ndjson into the Lokalise glossary via API.")
    parser.add_argument("--glossary", type=Path, default=glossary.DEFAULT_GLOSSARY, help=f"Glossary path. Default: {glossary.DEFAULT_GLOSSARY}.")
    add_lokalise_api_args(parser)
    parser.add_argument("--apply", action="store_true", help="Execute the API upsert. Without this, prints a dry-run plan.")
    parser.add_argument("--no-verify", action="store_true", help="Skip post-apply verification (re-read remote terms and compare stored vs sent).")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    glossary_path = args.glossary
    if not glossary_path.exists():
        print(f"error: glossary not found: {glossary_path}", file=sys.stderr)
        return 2

    records = glossary.read_records(glossary_path)
    issues = glossary.validate_records(records)
    errors = [issue for issue in issues if issue[0] == "error"]
    for level, name, message in issues:
        print(f"{level}: {name}: {message}")
    if errors:
        print(f"refusing: {len(errors)} glossary validation error(s); fix before API push.", file=sys.stderr)
        return 1

    local_langs = sorted(used_translation_langs(records))
    print(
        f"glossary: {glossary_path_display(glossary_path)}  "
        f"terms: {len(records)}  languages: {','.join(local_langs) or '<none>'}"
    )

    if not args.apply:
        print("DRY RUN: would upsert the whole local glossary via Lokalise glossary API. Pass --apply to execute.")
        for record in records[:5]:
            lang_count = len(glossary.translations(record))
            id_note = f" term_id={record.get('term_id')}" if record.get("term_id") is not None else ""
            print(f"  upsert term={glossary.term(record)!r}{id_note} translations={lang_count}")
        if len(records) > 5:
            print(f"  ... {len(records) - 5} more term(s)")
        return 0

    try:
        client = LokaliseClient(config_from_args(args))
        iso_to_id, id_to_iso = language_maps(client)
        missing_lang_ids = sorted(set(local_langs) - set(iso_to_id))
        if missing_lang_ids:
            raise LokaliseError(
                "project languages missing in Lokalise API response: "
                + ", ".join(missing_lang_ids)
                + " (cannot build glossary translation langId payloads)"
            )

        remote_terms = client.list_glossary_terms()
        plan = build_upsert_plan(records, remote_terms, iso_to_id)
        print(
            f"plan: update {len(plan['updates'])} existing term(s), "
            f"create {len(plan['creates'])} new term(s), "
            f"stamp {len(plan['stamp_ids'])} local term_id(s)"
        )

        updated_terms = client.update_glossary_terms([item["payload"] for item in plan["updates"]])
        created_terms = client.create_glossary_terms([item["payload"] for item in plan["creates"]])
        stamp_updated_ids(records, plan, updated_terms, created_terms)

        if plan["stamp_ids"] or created_terms:
            glossary.write_records(glossary_path, records)
            print(f"stamped Lokalise term ids; review `git diff -- {glossary_path.name}`")

        if args.no_verify:
            print("glossary push complete (post-write verification skipped via --no-verify)")
            return 0

        mismatches = verify_pushed(client, plan, id_to_iso)
        if mismatches:
            print(f"\nWARNING: {len(mismatches)} term(s) did NOT land as sent.", file=sys.stderr)
            for name, details in mismatches:
                print(f"  {name}:", file=sys.stderr)
                for detail in details:
                    print(f"    - {detail}", file=sys.stderr)
            return 1

        remote_after = client.list_glossary_terms()
        remote_by_id = {api_term_id(term): term for term in remote_after if api_term_id(term) is not None}
        post_stamp_mismatches: list[tuple[str, list[str]]] = []
        for record in records:
            term_id = record.get("term_id")
            remote = remote_by_id.get(int(term_id)) if term_id is not None else None
            if remote is None:
                post_stamp_mismatches.append((glossary.term(record), ["remote term not found after push"]))
                continue
            details = local_record_matches_remote(record, remote, iso_to_id, id_to_iso)
            if details:
                post_stamp_mismatches.append((glossary.term(record), details))
        if post_stamp_mismatches:
            print(f"\nWARNING: {len(post_stamp_mismatches)} local record(s) differ after id stamping.", file=sys.stderr)
            for name, details in post_stamp_mismatches:
                print(f"  {name}:", file=sys.stderr)
                for detail in details:
                    print(f"    - {detail}", file=sys.stderr)
            return 1

        print("glossary push complete (all upserted values verified in Lokalise)")
        return 0
    except LokaliseError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


def build_upsert_plan(
    records: list[dict[str, Any]],
    remote_terms: list[dict[str, Any]],
    iso_to_id: dict[str, int],
) -> dict[str, Any]:
    remote_by_id: dict[int, dict[str, Any]] = {}
    remote_by_term: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()
    for item in remote_terms:
        term_id = api_term_id(item)
        name = api_term_name(item)
        if term_id is not None:
            remote_by_id[term_id] = item
        if name:
            if name in remote_by_term:
                duplicates.add(name)
            remote_by_term[name] = item
    if duplicates:
        raise LokaliseError(
            "remote glossary has duplicate term names; refusing ambiguous upsert: "
            + ", ".join(sorted(duplicates))
        )

    updates: list[dict[str, Any]] = []
    creates: list[dict[str, Any]] = []
    stamp_ids: dict[str, int] = {}
    for record in records:
        payload = glossary.to_api_terms([record], iso_to_id)[0]
        if not payload.get("translations"):
            payload.pop("translations", None)
        name = glossary.term(record)
        local_id = _int_or_none(record.get("term_id"))
        remote = remote_by_id.get(local_id) if local_id is not None else None
        if remote is None:
            remote = remote_by_term.get(name)
        remote_id = api_term_id(remote) if remote is not None else None
        if remote_id is None:
            payload.pop("id", None)
            creates.append({"record": record, "payload": payload})
        else:
            payload["id"] = remote_id
            updates.append({"record": record, "payload": payload})
            if local_id != remote_id:
                stamp_ids[name] = remote_id
    return {"updates": updates, "creates": creates, "stamp_ids": stamp_ids}


def stamp_updated_ids(
    records: list[dict[str, Any]],
    plan: dict[str, Any],
    updated_terms: list[dict[str, Any]],
    created_terms: list[dict[str, Any]],
) -> None:
    by_name = {glossary.term(record): record for record in records}
    for name, term_id in plan["stamp_ids"].items():
        record = by_name.get(name)
        if record is not None:
            record["term_id"] = term_id
    for item in updated_terms + created_terms:
        term_id = api_term_id(item)
        name = api_term_name(item)
        if term_id is not None and name in by_name:
            by_name[name]["term_id"] = term_id


def verify_pushed(
    client: LokaliseClient,
    plan: dict[str, Any],
    id_to_iso: dict[int, str],
) -> list[tuple[str, list[str]]]:
    remote_terms = client.list_glossary_terms()
    remote_by_id = {api_term_id(item): item for item in remote_terms if api_term_id(item) is not None}
    remote_by_term = {api_term_name(item): item for item in remote_terms if api_term_name(item)}
    mismatches: list[tuple[str, list[str]]] = []
    for item in plan["updates"] + plan["creates"]:
        payload = item["payload"]
        remote = None
        if payload.get("id") is not None:
            remote = remote_by_id.get(int(payload["id"]))
        if remote is None:
            remote = remote_by_term.get(payload["term"])
        if remote is None:
            mismatches.append((payload["term"], ["remote term not found after push"]))
            continue
        details = payload_matches_remote(payload, remote, id_to_iso)
        if details:
            mismatches.append((payload["term"], details))
    return mismatches


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
