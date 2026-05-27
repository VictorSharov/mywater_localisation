#!/usr/bin/env python3
"""CLI for Lokalise API v2 key operations, built on the official SDK.

Lives in the shared localisation repo. Requires the `python-lokalise-api`
package (pinned in `requirements.txt`). The system Python is PEP 668
externally-managed, so install into a venv:

    python3 -m venv .venv-lokalise
    .venv-lokalise/bin/pip install -r requirements.txt
    .venv-lokalise/bin/python lokalise_helper.py ...

Credentials:
    export LOKALISE_API_TOKEN=...
    export LOKALISE_PROJECT_ID=...
    export LOKALISE_BRANCH=...          # optional

Examples:
    python3 lokalise_helper.py list-keys --filter-tag ai-added --limit 50
    python3 lokalise_helper.py get-key --key-name onboarding.title
    python3 lokalise_helper.py add-tags --key-name onboarding.title --tag needs-review --apply
    python3 lokalise_helper.py remove-tags --key-id 123456 --tag stale
    python3 lokalise_helper.py update-key --key-name onboarding.title --payload-file /tmp/key_patch.json --apply
    python3 lokalise_helper.py create-keys --keys-file /tmp/lokalise_keys.json --apply
    python3 lokalise_helper.py delete-keys --key-name zz_loctest_plural --apply   # DESTRUCTIVE

Mutating commands are dry-run by default; pass --apply to perform the request.

Key-name resolution and bulk tag writes are batched: a `--keys-file` of N
names costs a few cursor-paginated list calls plus chunked bulk updates, not
one request per key. `add-tags --skip-missing` is reserved for generated local
scan files that can include platform-local resources absent from Lokalise.

When adding `unused-localization`, the helper also checks the Android repo at
`/Users/viktor/git/mywater_android` (or `--android-repo`) and adds
`android_only` instead for keys that are still used by Android.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

try:
    import lokalise
    from lokalise import errors as lok_errors
except ImportError:  # keep argparse / --help usable without the dependency
    lokalise = None
    lok_errors = None

try:
    import requests.exceptions as _requests_exceptions
except ImportError:
    _requests_exceptions = None


DEFAULT_BASE_URL = "https://api.lokalise.com/api2"
DEFAULT_ANDROID_REPO = Path("/Users/viktor/git/mywater_android")
MAX_KEYS_LIMIT = 500
UNUSED_LOCALIZATION_TAG = "unused-localization"
ANDROID_ONLY_TAG = "android_only"
INSTALL_HINT = (
    "python-lokalise-api is not installed. Create a venv and "
    "`pip install -r requirements.txt` (see README.md in this repo)."
)
ANDROID_SOURCE_SUFFIXES = {
    ".java",
    ".kt",
    ".kts",
    ".xml",
}
ANDROID_EXCLUDED_DIR_NAMES = {
    ".git",
    ".gradle",
    ".idea",
    "build",
}
ANDROID_VALUE_RESOURCE_TAGS = {
    "array",
    "plurals",
    "string",
    "string-array",
}
ANDROID_RESOURCE_REFERENCE_RE = re.compile(
    r"@(?:[A-Za-z0-9_.]+:)?(?:array|plurals|string)/([A-Za-z0-9_.]+)"
)
ANDROID_R_STRING_RE = re.compile(r"\bR\s*\.\s*string\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)\b")
ANDROID_STRING_CLASS_IMPORT_RE = re.compile(
    r"^\s*import\s+[A-Za-z0-9_.]+\.R\.string(?:\s+as\s+([A-Za-z_][A-Za-z0-9_]*))?\s*$",
    re.M,
)
ANDROID_STRING_STATIC_IMPORT_RE = re.compile(
    r"^\s*import\s+[A-Za-z0-9_.]+\.R\.string\.([A-Za-z_][A-Za-z0-9_]*)\s*$",
    re.M,
)
ANDROID_DYNAMIC_STRING_RE = re.compile(
    r"\b(?:defaultName|name|stringName)\s*=\s*\"((?:\\.|[^\"\\])*)\""
    r"|\b(?:getStringIdentifier|getString)\(\s*\"((?:\\.|[^\"\\])*)\"\s*\)"
    r"|\bgetIdentifier\(\s*\"((?:\\.|[^\"\\])*)\"\s*,\s*\"string\"\s*,",
    re.M,
)


class LokaliseError(RuntimeError):
    """Raised when Lokalise API returns an error or the CLI input is unsafe."""


class LokaliseKeyNotFoundError(LokaliseError):
    """Raised when an exact key-name lookup has no Lokalise match."""


@dataclass(frozen=True)
class LokaliseConfig:
    api_token: str
    project_id: str
    branch: str | None
    base_url: str
    timeout_seconds: float


@dataclass(frozen=True)
class KeyRef:
    key_id: int
    key_name: str | None = None


@dataclass(frozen=True)
class AddTagsPlan:
    ref: KeyRef
    tags: list[str]
    android_key_name: str | None = None
    android_usage: str | None = None


@dataclass(frozen=True)
class AndroidUsageScan:
    repo_root: Path
    defined_keys: set[str]
    used_keys: set[str]
    usage_by_key: dict[str, list[str]]

    def usage_for(self, key_name: str | None) -> list[str]:
        if not key_name:
            return []
        return self.usage_by_key.get(key_name, [])


class LokaliseClient:
    def __init__(self, config: LokaliseConfig) -> None:
        if lokalise is None or lok_errors is None:
            raise LokaliseError(INSTALL_HINT)
        self.config = config

        kwargs: dict[str, Any] = {
            "connect_timeout": config.timeout_seconds,
            "read_timeout": config.timeout_seconds,
        }
        if config.base_url and config.base_url != DEFAULT_BASE_URL:
            kwargs["api_host"] = config.base_url
        self._sdk = lokalise.Client(config.api_token, **kwargs)

        retryable: list[type[BaseException]] = [TimeoutError, OSError]
        for name in ("TooManyRequests", "ServerError", "BadGateway", "ServiceUnavailable", "GatewayTimeout"):
            exc = getattr(lok_errors, name, None)
            if isinstance(exc, type):
                retryable.append(exc)
        if _requests_exceptions is not None:
            retryable.append(_requests_exceptions.Timeout)
            retryable.append(_requests_exceptions.ConnectionError)
        self._retryable: tuple[type[BaseException], ...] = tuple(retryable)

        self._key_cache: dict[int, dict[str, Any]] = {}
        self._name_index: dict[str, list[dict[str, Any]]] | None = None

    @property
    def project_path(self) -> str:
        if not self.config.branch:
            return self.config.project_id
        return f"{self.config.project_id}:{self.config.branch}"

    def _call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        last_error: BaseException | None = None
        for attempt in range(4):
            try:
                return func(*args, **kwargs)
            except self._retryable as error:
                last_error = error
                retry_after = None
                headers = getattr(error, "headers", None)
                if headers:
                    retry_after = _retry_after_seconds(_header(dict(headers), "Retry-After"))
                time.sleep(retry_after if retry_after is not None else min(2**attempt, 8))
            except lok_errors.ClientError as error:  # type: ignore[union-attr]
                raise LokaliseError(f"Lokalise API error: {error}") from error
        raise LokaliseError(f"Lokalise API request failed after retries: {last_error}")

    def list_keys(
        self,
        *,
        filter_keys: list[str] | None = None,
        filter_key_ids: list[int] | None = None,
        filter_tags: list[str] | None = None,
        filter_platforms: list[str] | None = None,
        include_translations: bool = False,
        include_comments: bool = False,
        filter_archived: str = "exclude",
        limit: int = MAX_KEYS_LIMIT,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "limit": min(max(limit, 1), MAX_KEYS_LIMIT),
            "pagination": "cursor",
            "disable_references": 1,
            "include_translations": 1 if include_translations else 0,
            "include_comments": 1 if include_comments else 0,
            "filter_archived": filter_archived,
        }
        if filter_keys:
            params["filter_keys"] = _csv(filter_keys)
        if filter_key_ids:
            params["filter_key_ids"] = _csv([str(key_id) for key_id in filter_key_ids])
        if filter_tags:
            params["filter_tags"] = _csv(filter_tags)
        if filter_platforms:
            params["filter_platforms"] = _csv(filter_platforms)

        out: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            page_params = dict(params)
            if cursor:
                page_params["cursor"] = cursor
            collection = self._call(self._sdk.keys, self.project_path, page_params)
            for model in collection.items:
                record = _key_to_dict(model)
                out.append(record)
                key_id = record.get("key_id")
                if key_id is not None:
                    self._key_cache[int(key_id)] = record
            if collection.has_next_cursor():
                cursor = collection.next_cursor
            else:
                return out

    def prime_name_index(self) -> None:
        if self._name_index is not None:
            return
        index: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in self.list_keys(filter_archived="include"):
            key_name = record.get("key_name")
            if isinstance(key_name, str):
                names: list[str] = [key_name]
            elif isinstance(key_name, dict):
                names = [value for value in key_name.values() if isinstance(value, str)]
            else:
                names = []
            for name in set(names):
                index[name].append(record)
        self._name_index = index

    def retrieve_key(self, key_id: int) -> dict[str, Any]:
        cached = self._key_cache.get(int(key_id))
        if cached is not None:
            return cached
        model = self._call(self._sdk.key, self.project_path, key_id, {"disable_references": 1})
        record = _key_to_dict(model)
        resolved_id = record.get("key_id")
        self._key_cache[int(resolved_id if resolved_id is not None else key_id)] = record
        return record

    def update_key(self, key_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        model = self._call(self._sdk.update_key, self.project_path, key_id, payload)
        record = _key_to_dict(model)
        resolved_id = record.get("key_id")
        self._key_cache[int(resolved_id if resolved_id is not None else key_id)] = record
        return record

    def bulk_update_keys(self, items: list[dict[str, Any]]) -> None:
        for start in range(0, len(items), MAX_KEYS_LIMIT):
            chunk = items[start : start + MAX_KEYS_LIMIT]
            self._call(self._sdk.update_keys, self.project_path, chunk)

    def create_keys(self, keys: list[dict[str, Any]], *, use_automations: bool | None) -> dict[str, Any]:
        params: dict[str, Any] = {"keys": keys}
        if use_automations is not None:
            params["use_automations"] = use_automations
        collection = self._call(self._sdk.create_keys, self.project_path, params)
        return {"keys": [_key_to_dict(model) for model in collection.items]}

    def delete_keys(self, key_ids: list[int]) -> dict[str, Any]:
        """Bulk-delete keys, chunked to the API max. DESTRUCTIVE and irreversible —
        callers must gate this behind --apply (there is no undo in Lokalise)."""
        deleted = 0
        for start in range(0, len(key_ids), MAX_KEYS_LIMIT):
            chunk = [int(key_id) for key_id in key_ids[start : start + MAX_KEYS_LIMIT]]
            self._call(self._sdk.delete_keys, self.project_path, chunk)
            for key_id in chunk:
                self._key_cache.pop(key_id, None)
            deleted += len(chunk)
        return {"deleted": deleted}


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        preflight_args(args)
        config = config_from_args(args)
        client = LokaliseClient(config)
        return args.func(client, args)
    except LokaliseError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Repo-local Lokalise API v2 helper for key lookup, tags, and small key updates."
    )
    parser.add_argument("--project-id", default=os.environ.get("LOKALISE_PROJECT_ID"), help="Lokalise project id. Defaults to LOKALISE_PROJECT_ID.")
    parser.add_argument("--branch", default=os.environ.get("LOKALISE_BRANCH"), help="Optional Lokalise branch name. Defaults to LOKALISE_BRANCH.")
    parser.add_argument("--base-url", default=os.environ.get("LOKALISE_API_BASE", DEFAULT_BASE_URL), help=f"API base URL. Defaults to {DEFAULT_BASE_URL}.")
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("LOKALISE_TIMEOUT", "30")), help="HTTP timeout in seconds.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-keys", help="List keys with optional Lokalise filters.")
    add_filter_args(list_parser)
    list_parser.add_argument("--include-translations", action="store_true", help="Include translations in API response.")
    list_parser.add_argument("--include-comments", action="store_true", help="Include key comments in API response.")
    list_parser.add_argument("--limit", type=int, default=MAX_KEYS_LIMIT, help="Page size, clamped to Lokalise max 500.")
    list_parser.add_argument("--json", action="store_true", help="Print raw keys JSON.")
    list_parser.set_defaults(func=cmd_list_keys)

    get_parser = subparsers.add_parser("get-key", help="Retrieve one key by key id or exact key name.")
    add_key_ref_args(get_parser, require_one=True)
    get_parser.add_argument("--json", action="store_true", help="Print raw key JSON.")
    get_parser.set_defaults(func=cmd_get_key)

    add_tags_parser = subparsers.add_parser("add-tags", help="Add tags to keys using Lokalise merge_tags.")
    add_mutation_key_args(add_tags_parser)
    add_tags_parser.add_argument("--tag", action="append", required=True, help="Tag to add. Repeatable.")
    add_tags_parser.add_argument(
        "--skip-missing",
        action="store_true",
        help=(
            "Skip key names that are not present in Lokalise. Intended for generated "
            "local scan files that may include platform-local resources; ambiguous "
            "matches still fail."
        ),
    )
    add_tags_parser.add_argument(
        "--android-repo",
        type=Path,
        default=Path(os.environ.get("MYWATER_ANDROID_REPO", str(DEFAULT_ANDROID_REPO))),
        help=(
            "Android repo used to protect unused-localization tagging. "
            f"Required when adding {UNUSED_LOCALIZATION_TAG}. Defaults to {DEFAULT_ANDROID_REPO} "
            "or MYWATER_ANDROID_REPO."
        ),
    )
    add_tags_parser.add_argument("--apply", action="store_true", help="Execute the update. Without this, prints a dry-run plan.")
    add_tags_parser.set_defaults(func=cmd_add_tags)

    remove_tags_parser = subparsers.add_parser("remove-tags", help="Remove tags from keys by replacing the key tags list.")
    add_mutation_key_args(remove_tags_parser)
    remove_tags_parser.add_argument("--tag", action="append", required=True, help="Tag to remove. Repeatable.")
    remove_tags_parser.add_argument("--apply", action="store_true", help="Execute the update. Without this, prints a dry-run plan.")
    remove_tags_parser.set_defaults(func=cmd_remove_tags)

    set_tags_parser = subparsers.add_parser("set-tags", help="Replace key tags with the provided tags.")
    add_mutation_key_args(set_tags_parser)
    set_tags_parser.add_argument("--tag", action="append", required=True, help="Final tag. Repeatable.")
    set_tags_parser.add_argument("--apply", action="store_true", help="Execute the update. Without this, prints a dry-run plan.")
    set_tags_parser.set_defaults(func=cmd_set_tags)

    update_parser = subparsers.add_parser("update-key", help="Patch one key with a Lokalise update-key JSON payload.")
    add_key_ref_args(update_parser, require_one=True)
    payload_group = update_parser.add_mutually_exclusive_group(required=True)
    payload_group.add_argument("--payload-json", help="Inline JSON object for the update-key body.")
    payload_group.add_argument("--payload-file", type=Path, help="Path to a JSON object for the update-key body.")
    update_parser.add_argument("--apply", action="store_true", help="Execute the update. Without this, prints a dry-run plan.")
    update_parser.set_defaults(func=cmd_update_key)

    create_parser = subparsers.add_parser("create-keys", help="Create keys from JSON using Lokalise create-keys endpoint.")
    create_parser.add_argument("--keys-file", type=Path, required=True, help="JSON file containing an array of key payloads or {'keys': [...]} object.")
    automations_group = create_parser.add_mutually_exclusive_group()
    automations_group.add_argument("--use-automations", action="store_true", help="Ask Lokalise to run automations for created key translations.")
    automations_group.add_argument("--no-automations", action="store_true", help="Ask Lokalise not to run automations.")
    create_parser.add_argument("--apply", action="store_true", help="Execute the create. Without this, prints a dry-run plan.")
    create_parser.set_defaults(func=cmd_create_keys)

    delete_parser = subparsers.add_parser("delete-keys", help="DESTRUCTIVE: permanently delete keys by id or name (no undo).")
    add_mutation_key_args(delete_parser)
    delete_parser.add_argument("--apply", action="store_true", help="Execute the deletion. Without this, prints a dry-run plan.")
    delete_parser.set_defaults(func=cmd_delete_keys)

    return parser


def add_filter_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--filter-key", action="append", help="Filter by key name. Repeatable.")
    parser.add_argument("--filter-key-id", action="append", type=int, help="Filter by key id. Repeatable.")
    parser.add_argument("--filter-tag", action="append", help="Filter by tag. Repeatable.")
    parser.add_argument("--filter-platform", action="append", choices=("ios", "android", "web", "other"), help="Filter by platform. Repeatable.")
    parser.add_argument("--archived", choices=("exclude", "include", "only"), default="exclude", help="Archived filter. Default: exclude.")


def add_key_ref_args(parser: argparse.ArgumentParser, *, require_one: bool) -> None:
    group = parser.add_mutually_exclusive_group(required=require_one)
    group.add_argument("--key-id", type=int, help="Lokalise numeric key id.")
    group.add_argument("--key-name", help="Exact key name.")


def add_mutation_key_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--key-id", action="append", type=int, help="Lokalise numeric key id. Repeatable.")
    parser.add_argument("--key-name", action="append", help="Exact key name. Repeatable.")
    parser.add_argument("--keys-file", type=Path, help="Line-delimited key ids or names. Empty lines and # comments are ignored.")
    parser.add_argument("--keys-file-kind", choices=("name", "id"), default="name", help="How to interpret --keys-file lines. Default: name.")


def config_from_args(args: argparse.Namespace) -> LokaliseConfig:
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


def preflight_args(args: argparse.Namespace) -> None:
    if requires_android_usage_check(args):
        validate_android_repo(args.android_repo)


def requires_android_usage_check(args: argparse.Namespace) -> bool:
    return args.command == "add-tags" and UNUSED_LOCALIZATION_TAG in set(args.tag or [])


def validate_android_repo(path: Path) -> None:
    resolved = path.expanduser()
    if not resolved.exists():
        raise LokaliseError(f"Android repo is required: {resolved} does not exist.")
    if not resolved.is_dir():
        raise LokaliseError(f"Android repo is required: {resolved} is not a directory.")
    if not (resolved / ".git").exists() or not (resolved / "settings.gradle.kts").exists():
        raise LokaliseError(
            f"Android repo is required: {resolved} does not look like mywater_android."
        )


def cmd_list_keys(client: LokaliseClient, args: argparse.Namespace) -> int:
    keys = client.list_keys(
        filter_keys=args.filter_key,
        filter_key_ids=args.filter_key_id,
        filter_tags=args.filter_tag,
        filter_platforms=args.filter_platform,
        include_translations=args.include_translations,
        include_comments=args.include_comments,
        filter_archived=args.archived,
        limit=args.limit,
    )
    if args.json:
        print(json.dumps({"keys": keys}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print_key_table(keys)
    return 0


def cmd_get_key(client: LokaliseClient, args: argparse.Namespace) -> int:
    key = resolve_single_key(client, key_id=args.key_id, key_name=args.key_name)
    if args.json:
        print(json.dumps(key, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print_key_details(key)
    return 0


def cmd_add_tags(client: LokaliseClient, args: argparse.Namespace) -> int:
    refs = resolve_key_refs(client, args)
    tags = sorted(set(args.tag))
    plans = build_add_tags_plans(client, args, refs, tags)
    if not args.apply:
        print("DRY RUN: would add tags. Pass --apply to execute.")
        print_add_tags_plans(plans)
        return 0

    client.bulk_update_keys([{"key_id": plan.ref.key_id, "tags": plan.tags, "merge_tags": True} for plan in plans])
    for plan in plans:
        print(f"updated key_id={plan.ref.key_id}: added tags {','.join(plan.tags)}")
    return 0


def build_add_tags_plans(
    client: LokaliseClient,
    args: argparse.Namespace,
    refs: list[KeyRef],
    tags: list[str],
) -> list[AddTagsPlan]:
    if not requires_android_usage_check(args):
        return [AddTagsPlan(ref=ref, tags=tags) for ref in refs]

    android_usage = collect_android_usage(args.android_repo)
    plans: list[AddTagsPlan] = []
    for ref in refs:
        key = client.retrieve_key(ref.key_id)
        display_ref = KeyRef(key_id=ref.key_id, key_name=ref.key_name or summarize_key_name(key))
        android_key_name = android_lokalise_key_name(key)
        usage = android_usage.usage_for(android_key_name)
        if usage:
            android_tags = sorted((set(tags) - {UNUSED_LOCALIZATION_TAG}) | {ANDROID_ONLY_TAG})
            plans.append(
                AddTagsPlan(
                    ref=display_ref,
                    tags=android_tags,
                    android_key_name=android_key_name,
                    android_usage=usage[0],
                )
            )
        else:
            plans.append(AddTagsPlan(ref=display_ref, tags=tags))
    return plans


def cmd_remove_tags(client: LokaliseClient, args: argparse.Namespace) -> int:
    refs = resolve_key_refs(client, args)
    remove_tags = set(args.tag)
    plans: list[tuple[KeyRef, list[str], list[str]]] = []
    for ref in refs:
        key = client.retrieve_key(ref.key_id)
        current_tags = sorted(set(key.get("tags") or []))
        next_tags = [tag for tag in current_tags if tag not in remove_tags]
        plans.append((KeyRef(ref.key_id, ref.key_name or summarize_key_name(key)), current_tags, next_tags))

    if not args.apply:
        print("DRY RUN: would remove tags. Pass --apply to execute.")
        print_tag_plans(plans)
        return 0

    client.bulk_update_keys(
        [{"key_id": ref.key_id, "tags": next_tags} for ref, current_tags, next_tags in plans if current_tags != next_tags]
    )
    for ref, current_tags, next_tags in plans:
        if current_tags == next_tags:
            print(f"skipped key_id={ref.key_id}: none of requested tags were present")
            continue
        print(f"updated key_id={ref.key_id}: {','.join(current_tags)} -> {','.join(next_tags)}")
    return 0


def cmd_set_tags(client: LokaliseClient, args: argparse.Namespace) -> int:
    refs = resolve_key_refs(client, args)
    next_tags = sorted(set(args.tag))
    plans: list[tuple[KeyRef, list[str], list[str]]] = []
    for ref in refs:
        key = client.retrieve_key(ref.key_id)
        current_tags = sorted(set(key.get("tags") or []))
        plans.append((KeyRef(ref.key_id, ref.key_name or summarize_key_name(key)), current_tags, next_tags))

    if not args.apply:
        print("DRY RUN: would replace tags. Pass --apply to execute.")
        print_tag_plans(plans)
        return 0

    client.bulk_update_keys(
        [{"key_id": ref.key_id, "tags": final_tags} for ref, current_tags, final_tags in plans if current_tags != final_tags]
    )
    for ref, current_tags, final_tags in plans:
        if current_tags == final_tags:
            print(f"skipped key_id={ref.key_id}: tags already match")
            continue
        print(f"updated key_id={ref.key_id}: {','.join(current_tags)} -> {','.join(final_tags)}")
    return 0


def cmd_update_key(client: LokaliseClient, args: argparse.Namespace) -> int:
    key = resolve_single_key(client, key_id=args.key_id, key_name=args.key_name)
    payload = read_json_payload(args.payload_json, args.payload_file)
    if not isinstance(payload, dict):
        raise LokaliseError("update payload must be a JSON object.")
    if not args.apply:
        print("DRY RUN: would update key. Pass --apply to execute.")
        print(json.dumps({"key_id": key["key_id"], "key_name": summarize_key_name(key), "payload": payload}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    updated = client.update_key(int(key["key_id"]), payload)
    print(json.dumps(updated, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def cmd_create_keys(client: LokaliseClient, args: argparse.Namespace) -> int:
    payload = read_json_file(args.keys_file)
    if isinstance(payload, dict):
        keys = payload.get("keys")
    else:
        keys = payload
    if not isinstance(keys, list) or any(not isinstance(item, dict) for item in keys):
        raise LokaliseError("--keys-file must contain an array of key objects or an object with a keys array.")
    use_automations = True if args.use_automations else False if args.no_automations else None

    if not args.apply:
        print("DRY RUN: would create keys. Pass --apply to execute.")
        print(json.dumps({"keys": keys, "use_automations": use_automations}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    if len(keys) > 500:
        raise LokaliseError("create-keys received more than 500 keys; split the file into chunks up to 500.")
    result = client.create_keys(keys, use_automations=use_automations)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def cmd_delete_keys(client: LokaliseClient, args: argparse.Namespace) -> int:
    refs = resolve_key_refs(client, args)
    if not args.apply:
        print(f"DRY RUN: would PERMANENTLY delete {len(refs)} key(s) — irreversible. Pass --apply to execute.")
        for ref in refs:
            print(f"  delete key_id={ref.key_id} key_name={ref.key_name or '<unknown>'}")
        return 0

    client.delete_keys([ref.key_id for ref in refs])
    for ref in refs:
        print(f"deleted key_id={ref.key_id} key_name={ref.key_name or '<unknown>'}")
    print(f"deleted {len(refs)} key(s)")
    return 0


def resolve_key_refs(client: LokaliseClient, args: argparse.Namespace) -> list[KeyRef]:
    key_ids = list(args.key_id or [])
    key_names = list(args.key_name or [])

    if args.keys_file:
        for item in read_keys_file(args.keys_file):
            if args.keys_file_kind == "id":
                try:
                    key_ids.append(int(item))
                except ValueError as error:
                    raise LokaliseError(f"invalid key id in {args.keys_file}: {item!r}") from error
            else:
                key_names.append(item)

    if not key_ids and not key_names:
        raise LokaliseError("provide at least one --key-id, --key-name, or --keys-file entry.")

    refs: list[KeyRef] = []
    seen_ids: set[int] = set()
    skipped_names: list[str] = []
    for key_id in key_ids:
        if key_id not in seen_ids:
            refs.append(KeyRef(key_id=key_id))
            seen_ids.add(key_id)

    if key_names:
        client.prime_name_index()
    for key_name in key_names:
        try:
            key = resolve_key_by_name(client, key_name)
        except LokaliseKeyNotFoundError:
            if getattr(args, "skip_missing", False):
                skipped_names.append(key_name)
                continue
            raise
        key_id = int(key["key_id"])
        if key_id not in seen_ids:
            refs.append(KeyRef(key_id=key_id, key_name=summarize_key_name(key)))
            seen_ids.add(key_id)

    if skipped_names:
        print_skipped_missing_key_names(skipped_names)

    return refs


def resolve_single_key(client: LokaliseClient, *, key_id: int | None, key_name: str | None) -> dict[str, Any]:
    if key_id is not None:
        return client.retrieve_key(key_id)
    if key_name is not None:
        return resolve_key_by_name(client, key_name)
    raise LokaliseError("provide --key-id or --key-name.")


def resolve_key_by_name(client: LokaliseClient, key_name: str) -> dict[str, Any]:
    if client._name_index is not None:
        candidates = client._name_index.get(key_name, [])
    else:
        candidates = client.list_keys(filter_keys=[key_name], filter_archived="include")

    exact: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for key in candidates:
        if not key_name_matches(key, key_name):
            continue
        key_id = key.get("key_id")
        if key_id is None or int(key_id) in seen_ids:
            continue
        seen_ids.add(int(key_id))
        exact.append(key)

    if len(exact) == 1:
        return exact[0]
    if not exact:
        raise LokaliseKeyNotFoundError(f"no exact Lokalise key found for key name {key_name!r}.")
    ids = ", ".join(str(key.get("key_id")) for key in exact)
    raise LokaliseError(f"multiple Lokalise keys matched {key_name!r}; use --key-id. Matches: {ids}")


def print_skipped_missing_key_names(key_names: list[str]) -> None:
    unique_names = list(dict.fromkeys(key_names))
    preview_limit = 20
    preview = ", ".join(repr(name) for name in unique_names[:preview_limit])
    if len(unique_names) > preview_limit:
        preview += f", ... (+{len(unique_names) - preview_limit} more)"
    print(
        f"warning: skipped {len(unique_names)} key name(s) not present in Lokalise: {preview}",
        file=sys.stderr,
    )


def key_name_matches(key: dict[str, Any], expected: str) -> bool:
    key_name = key.get("key_name")
    if isinstance(key_name, str):
        return key_name == expected
    if isinstance(key_name, dict):
        return any(value == expected for value in key_name.values())
    return False


def summarize_key_name(key: dict[str, Any]) -> str:
    key_name = key.get("key_name")
    if isinstance(key_name, str):
        return key_name
    if isinstance(key_name, dict):
        return ", ".join(f"{platform}={value}" for platform, value in sorted(key_name.items()))
    return "<unknown>"


def android_lokalise_key_name(key: dict[str, Any]) -> str | None:
    platforms = key.get("platforms")
    if isinstance(platforms, list) and platforms and "android" not in platforms:
        return None

    key_name = key.get("key_name")
    if isinstance(key_name, dict):
        android_key = key_name.get("android")
        if isinstance(android_key, str) and android_key:
            return android_key
        return None
    if isinstance(key_name, str) and key_name:
        return key_name
    return None


def collect_android_usage(android_repo: Path) -> AndroidUsageScan:
    validate_android_repo(android_repo)
    repo_root = android_repo.expanduser().resolve()
    defined_keys = collect_android_defined_keys(repo_root)
    if not defined_keys:
        raise LokaliseError(f"no Android string resources found under {repo_root}")

    field_to_keys = build_android_r_field_index(defined_keys)
    usage_by_key: dict[str, list[str]] = defaultdict(list)
    for path in iter_android_source_files(repo_root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as error:
            raise LokaliseError(f"failed to read Android source file {path}: {error}") from error

        rel_path = path.relative_to(repo_root).as_posix()
        if path.suffix == ".xml":
            scan_android_xml_references(text, rel_path, defined_keys, usage_by_key)
        if path.suffix in {".java", ".kt", ".kts"}:
            scan_android_code_references(text, rel_path, defined_keys, field_to_keys, usage_by_key)

    return AndroidUsageScan(
        repo_root=repo_root,
        defined_keys=defined_keys,
        used_keys=set(usage_by_key),
        usage_by_key={key: sorted(values) for key, values in usage_by_key.items()},
    )


def collect_android_defined_keys(repo_root: Path) -> set[str]:
    keys: set[str] = set()
    for path in iter_android_source_files(repo_root):
        if path.suffix != ".xml" or not is_android_values_file(repo_root, path):
            continue
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as error:
            raise LokaliseError(f"failed to parse Android resource XML {path}: {error}") from error
        for element in root.iter():
            tag = xml_tag_name(element.tag)
            if tag == "item" and element.attrib.get("type") in ANDROID_VALUE_RESOURCE_TAGS:
                name = element.attrib.get("name")
            elif tag in ANDROID_VALUE_RESOURCE_TAGS:
                name = element.attrib.get("name")
            else:
                name = None
            if name:
                keys.add(name)
    return keys


def iter_android_source_files(repo_root: Path) -> list[Path]:
    out: list[Path] = []
    for path in repo_root.rglob("*"):
        try:
            rel_parts = path.relative_to(repo_root).parts
        except ValueError:
            continue
        if any(part in ANDROID_EXCLUDED_DIR_NAMES for part in rel_parts):
            continue
        if path.is_file() and path.suffix in ANDROID_SOURCE_SUFFIXES:
            out.append(path)
    return sorted(out)


def is_android_values_file(repo_root: Path, path: Path) -> bool:
    parts = path.relative_to(repo_root).parts
    return any(index > 0 and parts[index - 1] == "res" and part.startswith("values") for index, part in enumerate(parts))


def scan_android_xml_references(
    text: str,
    rel_path: str,
    defined_keys: set[str],
    usage_by_key: dict[str, list[str]],
) -> None:
    for match in ANDROID_RESOURCE_REFERENCE_RE.finditer(text):
        add_android_direct_usage(match.group(1), f"{rel_path}:@resource", defined_keys, usage_by_key)


def scan_android_code_references(
    text: str,
    rel_path: str,
    defined_keys: set[str],
    field_to_keys: dict[str, set[str]],
    usage_by_key: dict[str, list[str]],
) -> None:
    for match in ANDROID_STRING_STATIC_IMPORT_RE.finditer(text):
        add_android_r_field_usage(match.group(1), f"{rel_path}:import", defined_keys, field_to_keys, usage_by_key)

    for match in ANDROID_R_STRING_RE.finditer(text):
        add_android_r_field_usage(match.group(1), f"{rel_path}:R.string", defined_keys, field_to_keys, usage_by_key)

    aliases = {
        match.group(1) if match.group(1) else "string"
        for match in ANDROID_STRING_CLASS_IMPORT_RE.finditer(text)
    }
    for alias in aliases:
        alias_re = re.compile(rf"\b{re.escape(alias)}\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)\b")
        for match in alias_re.finditer(text):
            add_android_r_field_usage(match.group(1), f"{rel_path}:{alias}", defined_keys, field_to_keys, usage_by_key)

    for match in ANDROID_DYNAMIC_STRING_RE.finditer(text):
        for value in match.groups():
            if value:
                add_android_direct_usage(unescape_android_string(value), f"{rel_path}:dynamic-string", defined_keys, usage_by_key)


def add_android_direct_usage(
    key_name: str,
    source: str,
    defined_keys: set[str],
    usage_by_key: dict[str, list[str]],
) -> None:
    if key_name not in defined_keys:
        return
    if source not in usage_by_key[key_name]:
        usage_by_key[key_name].append(source)


def add_android_r_field_usage(
    field_name: str,
    source: str,
    defined_keys: set[str],
    field_to_keys: dict[str, set[str]],
    usage_by_key: dict[str, list[str]],
) -> None:
    if field_name in defined_keys:
        add_android_direct_usage(field_name, source, defined_keys, usage_by_key)
        return
    for key_name in field_to_keys.get(field_name, ()):
        add_android_direct_usage(key_name, source, defined_keys, usage_by_key)


def build_android_r_field_index(defined_keys: set[str]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = defaultdict(set)
    for key_name in defined_keys:
        index[android_r_field_name(key_name)].add(key_name)
    return index


def android_r_field_name(key_name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", key_name)


def unescape_android_string(value: str) -> str:
    try:
        return bytes(value, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return value.replace('\\"', '"').replace("\\\\", "\\")


def xml_tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def print_key_table(keys: list[dict[str, Any]]) -> None:
    print(f"keys: {len(keys)}")
    if not keys:
        return
    print("key_id\tplatforms\ttags\tkey_name")
    for key in keys:
        platforms = ",".join(key.get("platforms") or [])
        tags = ",".join(key.get("tags") or [])
        print(f"{key.get('key_id')}\t{platforms}\t{tags}\t{summarize_key_name(key)}")


def print_key_details(key: dict[str, Any]) -> None:
    details = {
        "key_id": key.get("key_id"),
        "key_name": key.get("key_name"),
        "platforms": key.get("platforms"),
        "filenames": key.get("filenames"),
        "tags": key.get("tags"),
        "description": key.get("description"),
        "is_archived": key.get("is_archived"),
        "is_hidden": key.get("is_hidden"),
        "is_plural": key.get("is_plural"),
    }
    print(json.dumps(details, ensure_ascii=False, indent=2, sort_keys=True))


def print_tag_plans(plans: list[tuple[KeyRef, list[str], list[str]]]) -> None:
    for ref, current_tags, next_tags in plans:
        print(
            f"  key_id={ref.key_id} key_name={ref.key_name or '<unknown>'} "
            f"tags={','.join(current_tags)} -> {','.join(next_tags)}"
        )


def print_add_tags_plans(plans: list[AddTagsPlan]) -> None:
    android_only_count = sum(1 for plan in plans if plan.android_key_name)
    if android_only_count:
        print(f"Android usage check: {android_only_count} key(s) will receive {ANDROID_ONLY_TAG} instead of {UNUSED_LOCALIZATION_TAG}.")
    for plan in plans:
        message = (
            f"  key_id={plan.ref.key_id} key_name={plan.ref.key_name or '<unknown>'} "
            f"add_tags={','.join(plan.tags)}"
        )
        if plan.android_key_name:
            message += f" android_key={plan.android_key_name}"
        if plan.android_usage:
            message += f" android_usage={plan.android_usage}"
        print(message)


def read_keys_file(path: Path) -> list[str]:
    out: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            value = line.strip()
            if not value or value.startswith("#"):
                continue
            out.append(value)
    return out


def read_json_payload(inline_json: str | None, file_path: Path | None) -> Any:
    if inline_json is not None:
        try:
            return json.loads(inline_json)
        except json.JSONDecodeError as error:
            raise LokaliseError(f"invalid --payload-json: {error}") from error
    if file_path is not None:
        return read_json_file(file_path)
    raise LokaliseError("provide --payload-json or --payload-file.")


def read_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise LokaliseError(f"invalid JSON in {path}: {error}") from error


def _key_to_dict(model: Any) -> dict[str, Any]:
    return {
        "key_id": getattr(model, "key_id", None),
        "key_name": getattr(model, "key_name", None),
        "platforms": getattr(model, "platforms", None),
        "filenames": getattr(model, "filenames", None),
        "tags": getattr(model, "tags", None),
        "description": getattr(model, "description", None),
        "context": getattr(model, "context", None),
        "char_limit": getattr(model, "char_limit", None),
        "is_archived": getattr(model, "is_archived", None),
        "is_hidden": getattr(model, "is_hidden", None),
        "is_plural": getattr(model, "is_plural", None),
        "translations": getattr(model, "translations", None),
    }


def _csv(values: list[str] | None) -> str | None:
    if not values:
        return None
    return ",".join(values)


def _header(headers: dict[str, str], name: str) -> str | None:
    lowered = name.lower()
    for key, value in headers.items():
        if key.lower() == lowered and value:
            return value
    return None


def _retry_after_seconds(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return max(0, int(value))
    except ValueError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
