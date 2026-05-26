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
`other` form.

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
    the flat `en` mirror is re-synced from `t['en']`, and empty `unverified` lists
    are dropped — so a regenerated or hand-edited corpus diffs cleanly.
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
    """In-place canonicalize a record's sub-collections (sort `t`, sort/prune
    `unverified`, re-sync flat `en`). Top-level field order is left untouched."""
    translations = record.get("t")
    if isinstance(translations, dict):
        record["t"] = dict(sorted(translations.items()))
        if "en" in record["t"]:
            record["en"] = flat_source(record["t"]["en"])
    unverified = record.get("unverified")
    if isinstance(unverified, list):
        deduped = sorted(set(unverified))
        if deduped:
            record["unverified"] = deduped
        else:
            record.pop("unverified", None)
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


def unverified_langs(record: dict[str, Any]) -> set[str]:
    return set(record.get("unverified") or [])


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
# enforced in one place (the ndjson analog of the iOS `|R|` marker).
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

    When `mark_unverified` is True (default) and `lang` is not the source
    language, the language is added to `unverified` — an edited or fresh
    translation needs human / Lokalise review before it counts as verified, the
    same two-signal guarantee the iOS `|R|` marker carried. The flat `en` mirror
    is re-synced when the source language is edited.
    """
    translations = record.setdefault("t", {})
    if is_plural(record) and isinstance(value, dict):
        value = {category: value[category] for category in PLURAL_CATEGORIES if category in value}
    translations[lang] = value
    if lang == SOURCE_LANG:
        record["en"] = flat_source(value)
    elif mark_unverified:
        marked = set(record.get("unverified") or [])
        marked.add(lang)
        record["unverified"] = sorted(marked)
