"""Shared read/write/lookup primitives for the strings.ndjson corpus.

This is a library, NOT a CLI. It is the single owner of the NDJSON corpus
serialization so every producer/consumer round-trips byte-stable:

  - loc_corpus_ndjson.py  (Lokalise -> ndjson generator) writes via write_records
  - loc_audit_extract.py / loc_merge_languages.py        (read-only views)
  - loc_audit_apply.py / loc_apply_lang.py /
    loc_r_marked_translations.py                          (edit translations in ndjson)
  - loc_corpus_import.py  (ndjson -> Lokalise importer)   reads via read_records

Why one owner: the corpus is the cross-platform source of truth that gets
imported into Lokalise, then exported to iOS / Android / server. If two scripts
serialized it differently, every edit would churn the whole 1.7MB file and git
diffs would be unreadable. Keeping the writer here guarantees a deterministic
diff: keys sorted by key_id, languages inside `t` sorted, lean fields omitted,
compact separators — identical to a fresh generator run.

Record shape (see loc_corpus_ndjson.py docstring for the canonical spec):

    {"key_id":123,"key":"select_country","platforms":["ios","android"],
     "en":"Select your country","context":"Signup screen",
     "unverified":["ru"],"t":{"en":"Select your country","ru":"Выберите страну"}}

Plural keys keep nested CLDR forms per language in `t`; flat `en` is the
`other` form. A key may also carry an optional per-platform export-file routing
map `"filenames":{"ios":"InfoPlist.strings"}` — present only for keys routed to a
non-default file (an absent map exports to the default `Localizable.*` bundle).
An optional `"dirty":["en","ru"]` lists languages whose value was edited locally
and not yet pushed to Lokalise (see set_translation), and an optional
`"dirty_meta":["filenames","platforms"]` lists key-level fields (not languages)
edited locally and not yet pushed (see set_platforms / set_context / set_filename).
Both are local-only — the generator never emits them, so a regenerate clears
them, and a successful push clears exactly the pushed languages / fields.

Sibling import works because the scripts run as files from this directory.
Consumers that may run from another CWD add
`sys.path.insert(0, str(Path(__file__).resolve().parent))` defensively.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
# The corpus and its meta sidecar live next to the scripts (shared repo root).
DEFAULT_CORPUS = SCRIPT_DIR / "strings.ndjson"
# CLDR plural categories in canonical order, mirrored from loc_corpus_ndjson.py
# so plural maps render and serialize predictably across producers.
PLURAL_CATEGORIES = ("zero", "one", "two", "few", "many", "other")
# Source language: its translations are never flagged "unverified" (it is the
# dev source, not a target). Mirrors meta.source_lang; en in this project.
SOURCE_LANG = "en"
# Lokalise key platforms, in the canonical order set_platforms emits for a
# deterministic diff (matches the order the generator reads back from Lokalise).
PLATFORM_ORDER = ("ios", "android", "web", "other")
# Key-level (not per-language) fields the corpus owns and pushes to Lokalise; the
# values of a record's `dirty_meta` set are drawn from here. `context` is the
# corpus field name — loc_corpus_import maps it to the Lokalise `description`
# field on push (see that script and loc_corpus_ndjson's fold). `filenames` is the
# per-platform export-file routing map (e.g. iOS InfoPlist.strings vs the default
# Localizable.strings) — pushed as the Lokalise `filenames` object (set_filename).
META_FIELDS = ("platforms", "context", "filenames")


# --------------------------------------------------------------------------- #
# Read / write — the single owner of corpus serialization.
# --------------------------------------------------------------------------- #
def read_records(path: Path | str = DEFAULT_CORPUS) -> list[dict[str, Any]]:
    """Parse the NDJSON corpus into a list of record dicts (one per line).

    Blank lines are skipped. Field insertion order from the file is preserved
    (json.loads keeps object order), so a value-only edit re-serializes with the
    same field order the generator produced.
    """
    path = Path(path)
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid NDJSON line: {error}") from error
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: NDJSON line is not an object")
            records.append(record)
    return records


def write_records(path: Path | str, records: Iterable[dict[str, Any]]) -> None:
    """Write records as deterministic NDJSON (matches the generator's output).

    Records are sorted by key_id (None last), each `t` map is sorted by language,
    the flat `en` mirror is re-synced from `t['en']`, and empty `unverified` /
    `dirty` lang lists are dropped — so a regenerated or hand-edited corpus diffs
    cleanly.

    Rewrites the whole file from `records` (open("w"), no lock, no atomic rename),
    so it is NOT concurrency-safe: concurrent writers lose updates or interleave into
    a broken line. Callers serialize corpus writes — parallel translation passes fan
    out generation but apply one language at a time (CLAUDE.md [CR-CORPUS-CONCURRENCY]).
    """
    path = Path(path)
    prepared = [_normalized(record) for record in records]
    prepared.sort(key=lambda record: (record.get("key_id") is None, record.get("key_id")))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in prepared:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def _normalized(record: dict[str, Any]) -> dict[str, Any]:
    """In-place canonicalize a record's sub-collections (sort `t`, sort/prune the
    `unverified` and `dirty` lang lists, re-sync flat `en`). Top-level field order
    is left untouched."""
    translations = record.get("t")
    if isinstance(translations, dict):
        record["t"] = dict(sorted(translations.items()))
        if "en" in record["t"]:
            record["en"] = flat_source(record["t"]["en"])
    # `unverified` (review state) and `dirty` (per-language local-edit / push-
    # pending, set by set_translation) are sorted+deduped lang lists; `dirty_meta`
    # is the same shape but holds key-level field names ('context','platforms',
    # set by set_platforms / set_context) rather than languages. None is emitted by
    # the generator; an empty one is dropped so a cleared flag never churns the diff.
    for field in ("unverified", "dirty", "dirty_meta"):
        value = record.get(field)
        if isinstance(value, list):
            deduped = sorted(set(value))
            if deduped:
                record[field] = deduped
            else:
                record.pop(field, None)
    # `filenames` (per-platform export-file routing, a key-level META field) is
    # canonicalized to PLATFORM_ORDER with empty slots dropped, so the diff is
    # deterministic; an all-empty map drops the field (the key then exports to the
    # default Localizable.* bundle).
    fnames = record.get("filenames")
    if isinstance(fnames, dict):
        ordered = {p: fnames[p] for p in PLATFORM_ORDER if isinstance(fnames.get(p), str) and fnames[p]}
        ordered.update({p: fnames[p] for p in sorted(fnames) if p not in PLATFORM_ORDER and isinstance(fnames.get(p), str) and fnames[p]})
        if ordered:
            record["filenames"] = ordered
        else:
            record.pop("filenames", None)
    return record


# --------------------------------------------------------------------------- #
# Field accessors — keep callers from poking record dict keys directly.
# --------------------------------------------------------------------------- #
def is_plural(record: dict[str, Any]) -> bool:
    return bool(record.get("plural"))


def is_archived(record: dict[str, Any]) -> bool:
    return bool(record.get("archived"))


def platforms(record: dict[str, Any]) -> list[str]:
    return list(record.get("platforms") or [])


def has_platform(record: dict[str, Any], platform: str) -> bool:
    """True when the key targets `platform`. A key with no platforms recorded is
    treated as belonging to all (do not hide it from a platform-scoped view)."""
    plats = platforms(record)
    return not plats or platform in plats


def filenames(record: dict[str, Any]) -> dict[str, str]:
    """The key's per-platform export-file routing map (corpus field `filenames`):
    {platform: filename} for any platform routed to a non-default file (e.g.
    {"ios":"InfoPlist.strings"}). An absent / empty map means the key exports to the
    default `Localizable.*` bundle on every platform. Only non-empty slots are kept."""
    fnames = record.get("filenames")
    if not isinstance(fnames, dict):
        return {}
    return {platform: value for platform, value in fnames.items() if isinstance(value, str) and value}


def unverified_langs(record: dict[str, Any]) -> set[str]:
    return set(record.get("unverified") or [])


def dirty_langs(record: dict[str, Any]) -> set[str]:
    """Languages edited locally and not yet pushed to Lokalise — the push-pending
    set loc_corpus_import keys off. Cleared per-language on a successful push and
    wholesale on a regenerate. Includes SOURCE_LANG when the source value was
    edited (which pushes as verified)."""
    return set(record.get("dirty") or [])


def meta_dirty(record: dict[str, Any]) -> set[str]:
    """Key-level fields edited locally and not yet pushed — the metadata analog of
    dirty_langs. Values are corpus field names from META_FIELDS ('platforms',
    'context', 'filenames'); loc_corpus_import pushes them via the keys endpoint
    (update_key), clearing each on a successful push. Local-only: a regenerate never
    emits it."""
    return set(record.get("dirty_meta") or [])


def key_names(record: dict[str, Any]) -> list[str]:
    """All key-name strings for a record. `key` is a string when every platform
    shares one name (the common case), or a {platform: name} map when they
    differ — return every distinct name so name-based lookup hits either form."""
    key = record.get("key")
    if isinstance(key, str):
        return [key]
    if isinstance(key, dict):
        return sorted({value for value in key.values() if isinstance(value, str) and value})
    return []


def display_key(record: dict[str, Any]) -> str:
    """A single human-readable key label for batch output."""
    key = record.get("key")
    if isinstance(key, str):
        return key
    if isinstance(key, dict):
        return ", ".join(f"{platform}={value}" for platform, value in sorted(key.items()))
    return "<unknown>"


def translation(record: dict[str, Any], lang: str) -> Any:
    """Raw `t[lang]` value: a string for non-plural keys, a {form: text} dict for
    plural keys, or None when the language is absent. An empty string "" means a
    present-but-missing translation (Lokalise has the language, value is blank)."""
    return (record.get("t") or {}).get(lang)


def flat_text(record: dict[str, Any], lang: str) -> str | None:
    """`t[lang]` flattened to a plain string (plural -> `other` form). None when
    the language is absent; "" when present-but-empty."""
    value = translation(record, lang)
    if value is None:
        return None
    return flat_source(value)


def flat_source(value: Any) -> str:
    """A translation value as a plain string. A plural value collapses to its
    `other` form (or the first available form). Mirrors the generator."""
    if isinstance(value, dict):
        if "other" in value:
            return value["other"]
        return next(iter(value.values()), "")
    return value or ""


# --------------------------------------------------------------------------- #
# Indexing — name -> record for apply/lookup workflows.
# --------------------------------------------------------------------------- #
def index_by_key_name(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Map every key-name string to its record. First record wins on a duplicate
    name (corpus key names are unique in practice); use collect_duplicate_names
    when a caller needs to surface collisions."""
    index: dict[str, dict[str, Any]] = {}
    for record in records:
        for name in key_names(record):
            index.setdefault(name, record)
    return index


def collect_duplicate_names(records: Iterable[dict[str, Any]]) -> dict[str, int]:
    """Key names that appear on more than one record (diagnostic only)."""
    counts: dict[str, int] = {}
    for record in records:
        for name in key_names(record):
            counts[name] = counts.get(name, 0) + 1
    return {name: count for name, count in counts.items() if count > 1}


# --------------------------------------------------------------------------- #
# Language validation — guard against the iOS `.lproj` vs Lokalise code trap.
# The corpus `t` map uses Lokalise ISO codes (pt_BR, zh_CN); the iOS world uses
# hyphenated `.lproj` names (pt-BR, zh-Hans). A CLI fed the wrong form would
# treat every key as "missing this language" and silently mis-run (empty audit
# batch, or the whole corpus mis-classified as translation backlog).
# --------------------------------------------------------------------------- #
def known_langs(records: Iterable[dict[str, Any]]) -> set[str]:
    """Every language code present in any record's `t` map — the valid target
    set for this corpus (includes the source language `en`)."""
    langs: set[str] = set()
    for record in records:
        translations = record.get("t")
        if isinstance(translations, dict):
            langs.update(translations.keys())
    return langs


def unknown_lang_message(records: Iterable[dict[str, Any]], lang: str) -> str | None:
    """Error string if `lang` is not a corpus language, else None. Suggests the
    hyphen/underscore sibling so the pt-BR vs pt_BR slip is obvious."""
    known = known_langs(records)
    if lang in known:
        return None
    sibling = lang.replace("-", "_") if "-" in lang else lang.replace("_", "-")
    hint = f" (did you mean {sibling!r}?)" if sibling in known else ""
    return (
        f"unknown language {lang!r}{hint}; corpus uses Lokalise codes: "
        f"{', '.join(sorted(known))}"
    )


# --------------------------------------------------------------------------- #
# Edit — set a translation in place. Apply scripts go through here so the
# "AI / freshly-edited translation stays unverified until human review" rule is
# enforced in one place (the corpus `unverified` marker; [CR-CORPUS-UNVERIFIED]).
# --------------------------------------------------------------------------- #
def set_translation(
    record: dict[str, Any],
    lang: str,
    value: Any,
    *,
    mark_unverified: bool = True,
) -> None:
    """Set `t[lang] = value`. For non-plural keys `value` is a string; for plural
    keys it is a {form: text} dict restricted to CLDR categories.

    Two independent markers are maintained:

    - `dirty` (push-pending): when the value actually changes, `lang` is added to
      `dirty` — the signal loc_corpus_import's default scope keys off to push a
      language. It applies to every language alike (source or target), so the rule
      is uniform: push a language iff it was locally edited. It is local-only — a
      regenerate rebuilds from Lokalise and never emits it (self-clears), and a
      successful push clears the pushed languages.
    - `unverified` (review state): when `mark_unverified` is True (default) and
      `lang` is a target (not SOURCE_LANG), the language is added to `unverified`
      — an edited/fresh translation still needs human / Lokalise review, the
      cross-platform guarantee the corpus `unverified` marker provides. SOURCE_LANG
      is never `unverified` (it is the dev source of truth, not a review target) and
      the importer always pushes it verified.

    The two are separate because pushing is not verifying: a pushed translation
    leaves `dirty` at once (it is synced) but stays `unverified` until a human
    reviews it in Lokalise. Editing the source also re-syncs the flat `en` mirror.
    """
    translations = record.setdefault("t", {})
    if is_plural(record) and isinstance(value, dict):
        value = {category: value[category] for category in PLURAL_CATEGORIES if category in value}
    previous = translations.get(lang)
    translations[lang] = value
    if lang == SOURCE_LANG:
        record["en"] = flat_source(value)
    elif mark_unverified:
        marked = set(record.get("unverified") or [])
        marked.add(lang)
        record["unverified"] = sorted(marked)
    if value != previous:
        dirty = set(record.get("dirty") or [])
        dirty.add(lang)
        record["dirty"] = sorted(dirty)


# --------------------------------------------------------------------------- #
# Edit — key-level metadata (platforms, description). The corpus owns these and
# pushes them to Lokalise via the keys endpoint, so edits go through here to set
# the `dirty_meta` push-pending marker in one place (the key-level analog of the
# per-language `dirty` set set_translation maintains). No review state attaches:
# `unverified` is a translation concept, so metadata has no "unverified" marker.
# --------------------------------------------------------------------------- #
def _mark_meta_dirty(record: dict[str, Any], field: str) -> None:
    marked = set(record.get("dirty_meta") or [])
    marked.add(field)
    record["dirty_meta"] = sorted(marked)


def set_platforms(record: dict[str, Any], platforms_list: Iterable[str]) -> bool:
    """Set the key's platform list (its consuming platforms). The set is deduped
    and canonically ordered (PLATFORM_ORDER, unknown platforms sorted after) so the
    diff is deterministic. When the value actually changes, `platforms` is added to
    `dirty_meta` and loc_corpus_import pushes it to Lokalise (a full-array replace
    via update_key — that is how add/remove a platform propagates). Returns True iff
    the value changed. Callers validate platform names; this only canonicalizes."""
    incoming = list(dict.fromkeys(platforms_list))
    known = [platform for platform in PLATFORM_ORDER if platform in incoming]
    extra = sorted(platform for platform in incoming if platform not in PLATFORM_ORDER)
    canonical = known + extra
    previous = list(record.get("platforms") or [])
    record["platforms"] = canonical
    if canonical != previous:
        _mark_meta_dirty(record, "platforms")
        return True
    return False


def set_context(record: dict[str, Any], text: str) -> bool:
    """Set the key's translator description — the corpus `context` field, which
    loc_corpus_import pushes to the Lokalise `description` field. Stored stripped
    (the generator strips it too, so it round-trips); empty clears the field and
    pushes an empty description. When the value changes, `context` is added to
    `dirty_meta`. Returns True iff the value changed."""
    value = (text or "").strip()
    previous = record.get("context") or ""
    if value:
        record["context"] = value
    else:
        record.pop("context", None)
    if value != previous:
        _mark_meta_dirty(record, "context")
        return True
    return False


def set_filename(record: dict[str, Any], platform: str, filename: str) -> bool:
    """Set (or clear) one platform's export filename — the corpus `filenames` map,
    which loc_corpus_import pushes to the Lokalise `filenames` object so the export
    routes the key to that file (e.g. iOS `InfoPlist.strings` instead of the default
    `Localizable.strings`). A blank `filename` clears that platform's slot; clearing
    the last slot drops the field (the key returns to the default bundle). Other slots
    are preserved (merge, not replace), so routing iOS never disturbs Android. When the
    slot's value changes, `filenames` is added to `dirty_meta`; on push the full
    per-platform object is sent (a full replace — Lokalise has no per-slot update, so
    the corpus map is authoritative and a regenerate captures every slot back). Returns
    True iff the value changed. Callers validate the platform name; this only
    canonicalizes (PLATFORM_ORDER, empty slots dropped)."""
    current = {p: v for p, v in (record.get("filenames") or {}).items() if isinstance(v, str) and v}
    value = (filename or "").strip()
    previous = current.get(platform, "")
    if value:
        current[platform] = value
    else:
        current.pop(platform, None)
    ordered = {p: current[p] for p in PLATFORM_ORDER if current.get(p)}
    ordered.update({p: current[p] for p in sorted(current) if p not in PLATFORM_ORDER})
    if ordered:
        record["filenames"] = ordered
    else:
        record.pop("filenames", None)
    if value != previous:
        _mark_meta_dirty(record, "filenames")
        return True
    return False
