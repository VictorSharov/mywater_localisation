"""Shared Lokalise glossary API helpers.

The source-of-truth glossary lives in `glossary.ndjson` and is serialized only by
`loc_glossary.py`. This module is deliberately just conversion / API plumbing for
the two CLI edges:

* `loc_glossary_import.py` pushes local records to Lokalise glossary terms;
* `loc_glossary_ndjson.py` regenerates local records from Lokalise.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from loc_glossary import (
    is_case_sensitive,
    is_forbidden,
    is_translatable,
    note,
    tags,
    term,
    translations,
)
from lokalise_helper import DEFAULT_BASE_URL, LokaliseClient, LokaliseConfig, LokaliseError


def require_token() -> str:
    token = os.environ.get("LOKALISE_API_TOKEN")
    if not token:
        raise LokaliseError("LOKALISE_API_TOKEN is required; pass secrets via env, not CLI args.")
    return token


def require_project_id(project_id: str | None) -> str:
    if not project_id:
        raise LokaliseError("project id is required via --project-id or LOKALISE_PROJECT_ID.")
    return project_id


def config_from_args(args: Any) -> LokaliseConfig:
    return LokaliseConfig(
        api_token=require_token(),
        project_id=require_project_id(args.project_id),
        branch=args.branch,
        base_url=args.base_url,
        timeout_seconds=args.timeout,
    )


def add_lokalise_api_args(parser: Any) -> None:
    parser.add_argument("--project-id", default=os.environ.get("LOKALISE_PROJECT_ID"), help="Lokalise project id. Defaults to LOKALISE_PROJECT_ID.")
    parser.add_argument("--branch", default=os.environ.get("LOKALISE_BRANCH"), help="Optional Lokalise branch. Defaults to LOKALISE_BRANCH.")
    parser.add_argument("--base-url", default=os.environ.get("LOKALISE_API_BASE", DEFAULT_BASE_URL), help=f"API base URL. Defaults to {DEFAULT_BASE_URL}.")
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("LOKALISE_TIMEOUT", "30")), help="HTTP timeout in seconds.")


def language_maps(client: LokaliseClient) -> tuple[dict[str, int], dict[int, str]]:
    iso_to_id: dict[str, int] = {}
    id_to_iso: dict[int, str] = {}
    for language in client.list_project_languages():
        iso = language.get("lang_iso")
        lang_id = language.get("lang_id")
        if isinstance(iso, str) and lang_id is not None:
            lang_id_int = int(lang_id)
            iso_to_id[iso] = lang_id_int
            id_to_iso[lang_id_int] = iso
    return iso_to_id, id_to_iso


def used_translation_langs(records: list[dict[str, Any]]) -> set[str]:
    langs: set[str] = set()
    for record in records:
        langs.update(translations(record))
    return langs


def api_term_id(api_term: dict[str, Any]) -> int | None:
    value = api_term.get("id") or api_term.get("term_id")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def api_term_name(api_term: dict[str, Any]) -> str:
    value = api_term.get("term")
    return value if isinstance(value, str) else ""


def api_term_to_record(api_term: dict[str, Any], id_to_iso: dict[int, str]) -> dict[str, Any]:
    record: dict[str, Any] = {}
    term_id = api_term_id(api_term)
    if term_id is not None:
        record["term_id"] = term_id
    name = api_term_name(api_term)
    if name:
        record["term"] = name
    description = api_term.get("description")
    if isinstance(description, str) and description.strip():
        record["description"] = description.strip()
    if _as_bool(api_term.get("caseSensitive"), default=False):
        record["case_sensitive"] = True
    if not _as_bool(api_term.get("translatable"), default=True):
        record["translatable"] = False
    if _as_bool(api_term.get("forbidden"), default=False):
        record["forbidden"] = True

    raw_tags = api_term.get("tags")
    if isinstance(raw_tags, list):
        clean_tags = [tag for tag in raw_tags if isinstance(tag, str) and tag]
        if clean_tags:
            record["tags"] = clean_tags

    t: dict[str, str] = {}
    t_notes: dict[str, str] = {}
    raw_translations = api_term.get("translations")
    if isinstance(raw_translations, list):
        for item in raw_translations:
            if not isinstance(item, dict):
                continue
            lang_id = _translation_lang_id(item)
            if lang_id is None:
                continue
            iso = id_to_iso.get(lang_id)
            if not iso:
                continue
            text = item.get("translation")
            if isinstance(text, str) and text:
                t[iso] = text
            note_text = item.get("description")
            if isinstance(note_text, str) and note_text.strip():
                t_notes[iso] = note_text.strip()
    if t_notes:
        record["t_notes"] = t_notes
    if t:
        record["t"] = t
    return record


def payload_matches_remote(payload: dict[str, Any], remote: dict[str, Any], id_to_iso: dict[int, str]) -> list[str]:
    """Compare the values we send to the values stored by Lokalise.

    This intentionally compares only local payload languages. If Lokalise has extra
    translations for languages absent from `glossary.ndjson`, the API push leaves
    them untouched rather than deleting them silently.
    """
    mismatches: list[str] = []
    scalar_checks = (
        ("term", "term"),
        ("description", "description"),
        ("caseSensitive", "caseSensitive"),
        ("translatable", "translatable"),
        ("forbidden", "forbidden"),
    )
    for payload_key, remote_key in scalar_checks:
        if payload.get(payload_key) != _remote_scalar(remote, remote_key):
            mismatches.append(f"{payload_key}: sent {payload.get(payload_key)!r}, stored {_remote_scalar(remote, remote_key)!r}")
    if sorted(payload.get("tags") or []) != sorted(remote.get("tags") or []):
        mismatches.append(f"tags: sent {payload.get('tags') or []!r}, stored {remote.get('tags') or []!r}")

    remote_translations = _remote_translations_by_iso(remote, id_to_iso)
    for item in payload.get("translations") or []:
        if not isinstance(item, dict):
            continue
        lang_id = _translation_lang_id(item)
        iso = id_to_iso.get(lang_id) if lang_id is not None else None
        if not iso:
            continue
        stored = remote_translations.get(iso, {})
        if item.get("translation") != stored.get("translation"):
            mismatches.append(
                f"translations[{iso}]: sent {item.get('translation')!r}, stored {stored.get('translation')!r}"
            )
        expected_note = item.get("description") or ""
        stored_note = stored.get("description") or ""
        if expected_note != stored_note:
            mismatches.append(f"translations[{iso}].description: sent {expected_note!r}, stored {stored_note!r}")
    return mismatches


def local_record_matches_remote(record: dict[str, Any], remote: dict[str, Any], iso_to_id: dict[str, int], id_to_iso: dict[int, str]) -> list[str]:
    payload = {
        "term": term(record),
        "description": record.get("description") or "",
        "caseSensitive": is_case_sensitive(record),
        "translatable": is_translatable(record),
        "forbidden": is_forbidden(record),
        "tags": tags(record),
        "translations": [
            _translation_payload(lang, text, iso_to_id[lang], note(record, lang))
            for lang, text in sorted(translations(record).items())
            if lang in iso_to_id
        ],
    }
    return payload_matches_remote(payload, remote, id_to_iso)


def glossary_path_display(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _translation_payload(lang: str, text: str, lang_id: int, note_text: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {"langId": lang_id, "translation": text}
    if note_text:
        payload["description"] = note_text
    return payload


def _remote_scalar(remote: dict[str, Any], key: str) -> Any:
    if key in ("caseSensitive", "forbidden"):
        return _as_bool(remote.get(key), default=False)
    if key == "translatable":
        return _as_bool(remote.get(key), default=True)
    value = remote.get(key)
    if key == "description" and value is None:
        return ""
    return value


def _remote_translations_by_iso(remote: dict[str, Any], id_to_iso: dict[int, str]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    raw = remote.get("translations")
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        lang_id = _translation_lang_id(item)
        if lang_id is None:
            continue
        iso = id_to_iso.get(lang_id)
        if not iso:
            continue
        text = item.get("translation")
        description = item.get("description")
        out[iso] = {
            "translation": text if isinstance(text, str) else "",
            "description": description if isinstance(description, str) else "",
        }
    return out


def _translation_lang_id(item: dict[str, Any]) -> int | None:
    for key in ("langId", "lang_id", "languageId", "language_id"):
        value = item.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
    return None


def _as_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("yes", "true", "1"):
            return True
        if lowered in ("no", "false", "0"):
            return False
    return bool(value)
