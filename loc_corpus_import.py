#!/usr/bin/env python3
"""Import strings.ndjson edits into Lokalise — the inverse of loc_corpus_ndjson.py.

Pipeline: agents/translators edit translations in the corpus (via the loc_*
apply scripts or by hand), git review shows a clean diff, then this script pushes
those edits into Lokalise. From Lokalise the translations export to iOS / Android
/ server in each platform's native format.

    python3 loc_corpus_import.py                          # dry-run, unverified langs only
    python3 loc_corpus_import.py --lang ru --lang de      # dry-run, only ru + de
    python3 loc_corpus_import.py --lang ru --apply        # push ru to Lokalise
    python3 loc_corpus_import.py --key fullPromoText --apply   # push one key, all its langs

What gets pushed:
  - which keys: every key by default; `--key NAME` (repeatable) restricts the
    push to the named key(s) — e.g. to ship a placeholder fix to just those keys
    without a subset corpus. A requested name with no corpus match is reported on
    stderr, not silently dropped (so you never claim a push that did not happen).
  - which languages, per key:
    - default: the languages in the key's `unverified` set — the ones an apply
      script just edited (apply marks edited languages unverified) or that
      Lokalise already flagged for review — PLUS the source language when the key
      carries `source_dirty` (a local source edit has no `unverified` flag, so it
      would otherwise never be pushed; the source goes as verified). Avoids
      clobbering verified Lokalise translations with a stale snapshot: a language
      is pushed only when it was locally edited.
    - `--lang X` (repeatable): exactly these languages instead, for every in-scope
      key that has a value for them.
    - `--key` without `--lang`: ALL of each named key's languages. A committed
      edit (e.g. a placeholder fix) carries no `unverified` marker, so the default
      scope would push nothing — naming the key means "push this key".

Keys with no key_id are created (key_name + platforms + translations). Existing
keys have each translation edited through the per-translation endpoint
(update_translation by translation_id) — NOT the keys endpoint: a key-update's
`translations` array only sets values at create time and is silently ignored on
an existing key (verified: a changed `translation` left the stored value and its
modified_at untouched), which made earlier imports report success while writing
nothing. Plural values are sent as a CLDR-forms object (`{"one":…,"other":…}`) —
what the API accepts; the JSON-string form is only what it returns. Pushed target
translations are marked unverified so a human / Lokalise reviewer still signs off
(pass --mark-verified to override) — the same two-signal guarantee the corpus
`unverified` flag carries; the source language is always pushed verified (it is
the source of truth, not a translation under review).

Mutating is dry-run by default; pass --apply to perform the requests. Credentials
come from the env (LOKALISE_API_TOKEN / LOKALISE_PROJECT_ID), never CLI args.
Per [CR-ACCESS], the --apply path runs on the operator's machine with the token;
the dry-run plan is what an agent can produce without credentials.

After --apply the script re-reads the pushed keys and compares each stored value
to what was sent, warning loudly and exiting non-zero on any mismatch (--no-verify
skips it). Lokalise can return OK without a value landing as sent — the keys
endpoint ignoring translation edits (above) is one cause; equivalent-form
normalization may be another. Without this check the script would print success
for translations Lokalise never actually changed.
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
    SOURCE_LANG,
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
from loc_placeholder_lint import format_findings, lint_record  # noqa: E402
from loc_qa import format_findings as qa_format_findings, lint_record as qa_lint_record  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import strings.ndjson translations into Lokalise.")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS, help=f"Corpus path. Default: {DEFAULT_CORPUS}.")
    parser.add_argument("--lang", action="append", help="Language iso to import. Repeatable. Default: each key's unverified languages.")
    parser.add_argument("--key", action="append", help="Key name to import. Repeatable. Restricts the push to these key(s); without --lang, all of each named key's languages are pushed.")
    parser.add_argument("--mark-verified", action="store_true", help="Push target translations as verified (default: unverified, needs review). The source language is always pushed verified regardless.")
    parser.add_argument("--project-id", default=os.environ.get("LOKALISE_PROJECT_ID"), help="Lokalise project id. Defaults to LOKALISE_PROJECT_ID.")
    parser.add_argument("--branch", default=os.environ.get("LOKALISE_BRANCH"), help="Optional Lokalise branch.")
    parser.add_argument("--base-url", default=os.environ.get("LOKALISE_API_BASE", DEFAULT_BASE_URL), help=f"API base URL. Defaults to {DEFAULT_BASE_URL}.")
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("LOKALISE_TIMEOUT", "30")), help="HTTP timeout in seconds.")
    parser.add_argument("--apply", action="store_true", help="Execute the requests. Without this, prints a dry-run plan.")
    parser.add_argument("--no-lint", action="store_true", help="Skip the pre-flight lint gates (loc_placeholder_lint + loc_qa value hygiene).")
    parser.add_argument("--no-verify", action="store_true", help="Skip the post-apply verification (re-read pushed keys, compare stored vs sent).")
    return parser


def langs_for(record: dict[str, Any], requested: list[str] | None, *, all_langs_default: bool = False) -> list[str]:
    """Languages to push for this key: the requested set (where a value exists);
    else every available language when the key was explicitly named
    (all_langs_default); else the key's edited set — its `unverified` languages
    PLUS the source language when `source_dirty` is set. The source carries no
    `unverified` flag (it is never a review target), so a local source edit would
    otherwise never be pushed; `source_dirty` is the corpus signal that it was
    edited (see loc_corpus.set_translation)."""
    available = set((record.get("t") or {}).keys())
    if requested:
        return [lang for lang in requested if lang in available]
    if all_langs_default:
        return sorted(available)
    langs = unverified_langs(record) & available
    if record.get("source_dirty") and SOURCE_LANG in available:
        langs = langs | {SOURCE_LANG}
    return sorted(langs)


def translation_payload(record: dict[str, Any], lang: str, mark_verified: bool) -> dict[str, Any]:
    # Plural translations are sent as a CLDR-forms OBJECT, not a JSON string: the
    # Lokalise keys API (create AND update) wants `{"one":…,"other":…}` for a
    # plural key — the json-string form is only what the API *returns*, never what
    # it accepts (a string yields a 400 "nested error"). Non-plural values are the
    # plain string. So the corpus value goes through as-is either way.
    #
    # The source language is always pushed verified (never is_unverified): it is
    # the dev source of truth, not a translation awaiting review — the push side
    # of the corpus invariant that SOURCE_LANG is never in `unverified`.
    # `--mark-verified` governs the TARGET languages only.
    value = translation(record, lang)
    is_unverified = lang != SOURCE_LANG and not mark_verified
    return {"language_iso": lang, "translation": value, "is_unverified": is_unverified}


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
    requested_keys = set(args.key) if args.key else None
    matched_keys: set[str] = set()
    updates: list[dict[str, Any]] = []
    creates: list[dict[str, Any]] = []
    touched_langs: set[str] = set()
    pushed: list[tuple[dict[str, Any], list[str]]] = []

    for record in records:
        if record.get("archived"):
            continue
        if requested_keys is not None:
            names = [name for name in key_names(record) if name in requested_keys]
            if not names:
                continue
            matched_keys.update(names)
        langs = langs_for(record, args.lang, all_langs_default=requested_keys is not None)
        if not langs:
            continue
        touched_langs.update(langs)
        pushed.append((record, langs))
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

    if requested_keys is not None:
        missing = sorted(requested_keys - matched_keys)
        if missing:
            print(f"warning: {len(missing)} requested key(s) not found in corpus: {', '.join(missing)}", file=sys.stderr)

    if args.lang:
        scope = ",".join(args.lang)
    elif requested_keys is not None:
        scope = "all-langs-per-key"
    else:
        scope = "edited-per-key"  # unverified targets + source_dirty source
    key_scope = f"  keys: {len(matched_keys)}/{len(requested_keys)} named matched" if requested_keys is not None else ""
    print(f"corpus: {corpus_path}  scope: {scope}{key_scope}  languages touched: {','.join(sorted(touched_langs)) or '<none>'}")
    print(f"plan: update {len(updates)} existing key(s), create {len(creates)} new key(s)")

    # Placeholder pre-flight: the keys API stores translations literally (no
    # universal-placeholder auto-conversion — that only happens on file upload),
    # so a bare %@/%s or a lone % would mis-export. Gate the push on what is in
    # scope; --no-lint overrides. Canonical rules: TRANSLATION_STYLE.md § Placeholders.
    lint_findings = [finding for record, langs in pushed for finding in lint_record(record, set(langs))]
    if lint_findings:
        errors = [f for f in lint_findings if f.severity == "error"]
        print(f"\nplaceholder lint: {len(errors)} error(s), {len(lint_findings) - len(errors)} warning(s) in push scope")
        print(format_findings(lint_findings))
        if errors and not args.no_lint:
            print("\nrefusing: fix the placeholder error(s) above, or pass --no-lint to override.", file=sys.stderr)
            return 1

    # Value-hygiene pre-flight (loc_qa): em-dash / invisible spaces are absolute
    # bans that also mis-export (the keys API stores them literally). Gate the
    # push on errors in scope; --no-lint overrides (same knob as the placeholder
    # gate). Canonical rules: TRANSLATION_STYLE.md § Punctuation.
    qa_findings = [finding for record, langs in pushed for finding in qa_lint_record(record, set(langs))]
    if qa_findings:
        qa_errors = [f for f in qa_findings if f.severity == "error"]
        print(f"\nvalue-hygiene lint: {len(qa_errors)} error(s), {len(qa_findings) - len(qa_errors)} warning(s) in push scope")
        print(qa_format_findings(qa_findings))
        if qa_errors and not args.no_lint:
            print("\nrefusing: fix the value-hygiene error(s) above, or pass --no-lint to override.", file=sys.stderr)
            return 1

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

    # key_id -> {lang: value-we-sent}, used by the post-write verification below.
    sent_by_key: dict[int, dict[str, Any]] = {}
    try:
        config = LokaliseConfig(
            api_token=require_token(),
            project_id=require_project_id(args.project_id),
            branch=args.branch,
            base_url=args.base_url,
            timeout_seconds=args.timeout,
        )
        client = LokaliseClient(config)
        # Existing translations are edited via the translation endpoint, not the
        # keys endpoint (which only sets translations at create time and silently
        # ignores them on update). That needs each translation's id, so batch-read
        # the keys once and map language -> translation_id.
        tid_by_key = fetch_translation_ids(client, [int(item["key_id"]) for item in updates])
        for item in updates:
            key_id = int(item["key_id"])
            lang_to_tid = tid_by_key.get(key_id, {})
            for payload in item["translations"]:
                tid = lang_to_tid.get(payload["language_iso"])
                if tid is None:
                    print(f"warning: no translation in Lokalise for key_id={key_id} lang={payload['language_iso']}; skipped", file=sys.stderr)
                    continue
                client.update_translation(tid, {"translation": payload["translation"], "is_unverified": payload["is_unverified"]})
            print(f"updated key_id={key_id} ({item['key']})")
            sent_by_key[key_id] = {t["language_iso"]: t["translation"] for t in item["translations"]}
        for start in range(0, len(creates), 500):
            chunk = creates[start : start + 500]
            result = client.create_keys(chunk, use_automations=None)
            print(f"created {len(chunk)} key(s)")
            record_created_sent(result, chunk, sent_by_key)
    except LokaliseError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.no_verify:
        print("import complete (post-write verification skipped via --no-verify)")
        return 0

    mismatches = verify_pushed(client, sent_by_key)
    if mismatches:
        print(f"\nWARNING: {len(mismatches)} translation(s) did NOT land as sent — Lokalise stored a different value.", file=sys.stderr)
        print("Lokalise accepted the request but the value differs on re-read. Check the per-language diff below;", file=sys.stderr)
        print("if it is an equivalent-form normalization, the corpus may need to match Lokalise's canonical form.", file=sys.stderr)
        for m in mismatches:
            print(f"  key_id={m['key_id']} ({m['key']}) [{m['lang']}]: sent {m['sent']!r} -> stored {m['stored']!r}", file=sys.stderr)
        print("\nimport applied, but NOT every value landed as sent (see above).")
        return 1

    print("import complete (all pushed values verified in Lokalise)")
    return 0


def fetch_translation_ids(client: LokaliseClient, key_ids: list[int]) -> dict[int, dict[str, Any]]:
    """key_id -> {language_iso: translation_id} for the given keys, in one batched
    read. Needed because translation edits go through the per-translation endpoint,
    which is addressed by translation_id rather than language."""
    if not key_ids:
        return {}
    out: dict[int, dict[str, Any]] = {}
    for key in client.list_keys(filter_key_ids=key_ids, include_translations=True):
        key_id = key.get("key_id")
        if key_id is None:
            continue
        langs: dict[str, Any] = {}
        for t in key.get("translations") or []:
            lang = t.get("language_iso") if isinstance(t, dict) else getattr(t, "language_iso", None)
            tid = t.get("translation_id") if isinstance(t, dict) else getattr(t, "translation_id", None)
            if lang is not None and tid is not None:
                langs[lang] = int(tid)
        out[int(key_id)] = langs
    return out


def verify_pushed(client: LokaliseClient, sent_by_key: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    """Re-read the pushed keys and report any (key, lang) whose stored value
    differs from what was sent. Catches the keys-API placeholder canonicalization
    that silently no-ops a format change ([%s] == sequential [%1$s][%2$s], % == %%)."""
    if not sent_by_key:
        return []
    fetched = client.list_keys(filter_key_ids=list(sent_by_key), include_translations=True)
    by_id = {int(key["key_id"]): key for key in fetched if key.get("key_id") is not None}
    mismatches: list[dict[str, Any]] = []
    for key_id, lang_values in sent_by_key.items():
        key = by_id.get(int(key_id))
        if key is None:
            for lang, sent in lang_values.items():
                mismatches.append({"key_id": key_id, "key": str(key_id), "lang": lang, "sent": sent, "stored": "<key not found on re-fetch>"})
            continue
        stored = stored_by_lang(key)
        display = key_display(key)
        for lang, sent in lang_values.items():
            got = stored.get(lang, "<missing>")
            if not value_matches(sent, got):
                mismatches.append({"key_id": key_id, "key": display, "lang": lang, "sent": sent, "stored": got})
    return mismatches


def record_created_sent(result: dict[str, Any], chunk: list[dict[str, Any]], sent_by_key: dict[int, dict[str, Any]]) -> None:
    """Map freshly created keys (by name) to their new key_id so verify_pushed can
    re-read them, since create payloads carry no key_id of their own."""
    name_to_id: dict[str, int] = {}
    for key in result.get("keys") or []:
        key_id = key.get("key_id")
        if key_id is None:
            continue
        for name in names_of(key.get("key_name")):
            name_to_id[name] = int(key_id)
    for payload in chunk:
        key_id = next((name_to_id[name] for name in names_of(payload.get("key_name")) if name in name_to_id), None)
        if key_id is None:
            continue
        sent_by_key[key_id] = {t["language_iso"]: t["translation"] for t in payload.get("translations", [])}


def stored_by_lang(key: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for t in key.get("translations") or []:
        lang = t.get("language_iso") if isinstance(t, dict) else getattr(t, "language_iso", None)
        value = t.get("translation") if isinstance(t, dict) else getattr(t, "translation", None)
        if lang is not None:
            out[lang] = value
    return out


def value_matches(sent: Any, stored: Any) -> bool:
    """Exact compare of sent vs stored. Plural values are sent as a CLDR-forms
    dict but returned by the API as a JSON string — parse and compare the forms we
    sent (Lokalise may add empty CLDR categories we never set)."""
    if isinstance(sent, dict):
        parsed = stored
        if isinstance(stored, str):
            try:
                parsed = json.loads(stored)
            except (ValueError, TypeError):
                return False
        if not isinstance(parsed, dict):
            return False
        return all(parsed.get(form) == text for form, text in sent.items())
    return sent == stored


def key_display(key: dict[str, Any]) -> str:
    name = key.get("key_name")
    if isinstance(name, str):
        return name
    if isinstance(name, dict):
        for platform in ("ios", "android", "web", "other"):
            if isinstance(name.get(platform), str) and name[platform]:
                return name[platform]
        values = [value for value in name.values() if isinstance(value, str)]
        return values[0] if values else "<key>"
    return "<key>"


def names_of(name: Any) -> list[str]:
    if isinstance(name, str):
        return [name]
    if isinstance(name, dict):
        return [value for value in name.values() if isinstance(value, str)]
    return []


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
