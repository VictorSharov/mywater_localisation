"""Shared read/write/lookup primitives for the glossary.ndjson corpus.

This is a library, NOT a CLI — the glossary sibling of loc_corpus.py, and the
single owner of glossary.ndjson serialization so every producer/consumer
round-trips byte-stable (CLAUDE.md [CR-CORPUS-OWNER], applied to the glossary).
Never hand-edit glossary.ndjson formatting or re-serialize it another way — go
through write_records (or a future apply script). A round-trip read -> write must
be byte-identical (deterministic diff), exactly like the string corpus.

WHAT THE GLOSSARY IS. A git-tracked, source-of-truth list of MyWater
terminology — brand / product names, recurring UI labels, hydration-domain
concepts, beverage names, measurement units, and banned ("avoid") jargon — with
one agreed rendering per language. It exists so a term ("daily goal", "streak",
the brand "My Water") is translated the *same* way everywhere, across iOS /
Android / server and across 21 languages, instead of drifting per string. It is
the terminology analog of strings.ndjson: authored / reviewed as a clean git
diff here, then pushed into the Lokalise **glossary** (a different Lokalise
surface than translation keys — see GLOSSARY.md for the field mapping and the
CSV / API export). Translators and the audit sub-agent read it for consistency.

Record shape (full schema + rationale: GLOSSARY.md):

    {"term":"daily goal","description":"The user's target water volume for the day.",
     "tags":["domain","ui"],"t":{"de":"Tagesziel","ru":"дневная норма"}}

  - term          en headword (the source term). Required, non-empty. The Lokalise
                  glossary term itself is the en form, so there is NO t["en"].
  - term_id       Lokalise glossary-term id, stamped back after an API push.
                  Absent until pushed (the CSV path upserts by `term`, not id).
  - description   en translator-facing definition / usage note (-> Lokalise glossary
                  `description`). Recommended on every term.
  - case_sensitive / translatable / forbidden   the three Lokalise glossary flags.
                  Stored ONLY when non-default (case_sensitive/forbidden when True,
                  translatable when False) so the common term stays a lean line; an
                  absent flag reads as its default (False / True / False). A term
                  can NOT be both translatable:false and forbidden:true (Lokalise
                  rejects it) — validate_records flags the combo.
  - tags          up to 3 category tags (Lokalise max). Controlled vocab TAG_VOCAB
                  (proposed; adjust at fill time). Omitted when empty.
  - t             {lang: translation} for the 20 non-en project languages (ru + 19).
                  Sorted by language; empty / absent = not yet translated (the
                  glossary has no "present-but-blank" state — unlike the string
                  corpus there is no release gate, so absence is the only missing
                  marker). ru is authored first as the co-source (GLOSSARY.md §
                  Fill workflow), mirroring the corpus en/ru discipline.
  - t_notes       optional {lang: note} per-language translator note
                  (-> Lokalise `<iso>_description`). Rare; omitted when empty.

Unlike the string corpus there is NO `unverified` / `dirty` review or push state:
the glossary is small reference data pushed wholesale (a full CSV re-upload), not
gated by a release. See GLOSSARY.md § Why no review state.

Plurals / placeholders do NOT apply — glossary entries are lexical headwords, not
runtime strings, so there is no CLDR map and no [%s] contract here.

Sibling import works because the scripts run as files from this directory.
Consumers that may run from another CWD add
`sys.path.insert(0, str(Path(__file__).resolve().parent))` defensively.
"""

from __future__ import annotations

import csv
import io
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
# The glossary lives next to the string corpus at the shared repo root.
DEFAULT_GLOSSARY = SCRIPT_DIR / "glossary.ndjson"
# The string corpus' meta sidecar — read for the project language set so the
# glossary auto-tracks the corpus' languages instead of drifting from a hardcode.
CORPUS_META = SCRIPT_DIR / "strings.meta.json"
# Pre-write snapshot dir — reused from loc_corpus (gitignored, [CR-CORPUS-WORKTREE]);
# glossary snapshots are namespaced `glossary.ndjson.<ts>` so they rotate
# independently of the string-corpus `strings.ndjson.*` snapshots.
SNAPSHOT_DIR = SCRIPT_DIR / ".loc_backup"
SNAPSHOT_RETAIN = 20

# Project languages (Lokalise ISO codes — pt_BR / zh_CN, NOT iOS pt-BR / zh-Hans).
# Read live from strings.meta.json so adding a project language flows through to the
# glossary; DEFAULT_LANGUAGES is the fallback when the meta sidecar is unreadable.
DEFAULT_LANGUAGES = (
    "ar", "da", "de", "en", "es", "fr", "hi", "id", "it", "ja", "ko",
    "ms", "nb", "nl", "pl", "pt_BR", "ru", "sv", "tr", "vi", "zh_CN",
)
SOURCE_LANG = "en"        # the term headword is the en form — never a t[] entry
CO_SOURCE_LANG = "ru"     # authored first as the co-source (the team is ru-native)

# Proposed category tags (Lokalise allows up to 3 per term, case-sensitive).
# PROPOSAL — adjust at fill time; validate_records only WARNs on an off-vocab tag.
# Drawn from TRANSLATION_STYLE.md § Lexicon / § Brand voice:
TAG_VOCAB = (
    "brand",     # brand & product names — "My Water", "My Water Premium"
    "ui",        # recurring UI / control labels — Save, Goal, Reminder, Streak, Award
    "domain",    # hydration-domain concepts — water, drink, hydration, intake, habit
    "beverage",  # beverage names — Water, Coffee, Tea, Juice, ...
    "unit",      # measurement units — ml, l, fl oz, cup, kg, lb
    "legal",     # terms appearing in legal / Terms / Privacy text (Register: formal)
)

# Canonical top-level field order — `t` last (diff stability), scalars first.
_CANONICAL_ORDER = (
    "term", "term_id", "description",
    "case_sensitive", "translatable", "forbidden",
    "tags", "t_notes", "t",
)

# --------------------------------------------------------------------------- #
# Lokalise glossary CSV column headers.
#
# VERIFIED against a real Lokalise export (operator downloaded Glossary > More >
# Download CSV, 2026-05). The header row is ALL LOWERCASE:
#   term;description;casesensitive;translatable;forbidden;tags;<iso>;<iso>_description;...
# The earlier docs-guess of a capitalized `Forbidden` was WRONG — it is `forbidden`.
# CSV is semicolon-separated, UTF-8, with a header row. Per-language columns are the
# bare project ISO code (translation) and `<iso>_description` (the per-language note);
# the export also carries an `en` column we leave empty (the term headword IS the en
# form). Lokalise maps columns by header NAME, so our alphabetical language order
# imports fine. See GLOSSARY.md § Lokalise mapping.
# --------------------------------------------------------------------------- #
CSV_FIXED_HEADERS = ("term", "description", "casesensitive", "translatable", "forbidden", "tags")
CSV_DELIMITER = ";"


# --------------------------------------------------------------------------- #
# Project language set — read from the string corpus' meta sidecar.
# --------------------------------------------------------------------------- #
def project_languages() -> list[str]:
    """The project's Lokalise language codes, read from strings.meta.json so the
    glossary tracks the same set as the string corpus. Falls back to
    DEFAULT_LANGUAGES if the meta sidecar is missing / unreadable."""
    try:
        meta = json.loads(CORPUS_META.read_text(encoding="utf-8"))
        langs = meta.get("languages")
        if isinstance(langs, list) and langs:
            return [lang for lang in langs if isinstance(lang, str)]
    except (OSError, ValueError):
        pass
    return list(DEFAULT_LANGUAGES)


def translation_langs() -> list[str]:
    """The languages a glossary term carries in `t`: every project language except
    the en source (the term headword IS the en form). 20 languages — ru + 19."""
    return sorted(lang for lang in project_languages() if lang != SOURCE_LANG)


def target_langs() -> list[str]:
    """The 19 ordinary targets — translation_langs minus the ru co-source. ru is
    authored in the first fill pass alongside the en term; these fill in pass 2."""
    return sorted(lang for lang in translation_langs() if lang != CO_SOURCE_LANG)


# --------------------------------------------------------------------------- #
# Read / write — the single owner of glossary serialization.
# --------------------------------------------------------------------------- #
def read_records(path: Path | str = DEFAULT_GLOSSARY) -> list[dict[str, Any]]:
    """Parse the NDJSON glossary into a list of term-record dicts (one per line).
    Blank lines are skipped. An empty file (the initial state) yields []."""
    path = Path(path)
    if not path.exists():
        return []
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


def _snapshot_before_write(path: Path) -> None:
    """Copy the live glossary to `.loc_backup/glossary.ndjson.<ts>` before a write
    overwrites it, then rotate to the most recent SNAPSHOT_RETAIN. No-op for a
    non-DEFAULT_GLOSSARY path (tests with --glossary /tmp/x.ndjson stay
    snapshot-free) or a not-yet-existing file. Mirrors loc_corpus."""
    try:
        if path.resolve() != DEFAULT_GLOSSARY.resolve():
            return
    except FileNotFoundError:
        return
    if not path.exists():
        return
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    shutil.copy2(path, SNAPSHOT_DIR / f"glossary.ndjson.{ts}")
    snapshots = sorted(SNAPSHOT_DIR.glob("glossary.ndjson.*"))
    for stale in snapshots[:-SNAPSHOT_RETAIN]:
        try:
            stale.unlink()
        except OSError:
            pass


def write_records(path: Path | str, records: Iterable[dict[str, Any]]) -> None:
    """Write term records as deterministic NDJSON (the glossary's only writer).

    Records are normalized (canonical field order, lean default-omission, `t` and
    `t_notes` sorted by language) and sorted by headword (case-insensitive, then
    case-sensitive tiebreak) so a re-serialize diffs cleanly. Rewrites the whole
    file from `records` (open("w"), no lock) — not concurrency-safe; serialize
    writes ([CR-CORPUS-CONCURRENCY]). An empty `records` writes an empty file.
    """
    path = Path(path)
    _snapshot_before_write(path)
    prepared = [_normalized(record) for record in records]
    prepared.sort(key=lambda record: (str(record.get("term", "")).casefold(), str(record.get("term", ""))))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in prepared:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def _normalized(record: dict[str, Any]) -> dict[str, Any]:
    """Return a canonicalized copy: fields in _CANONICAL_ORDER with `t` last,
    default-valued flags dropped, empty collections dropped, `t` / `t_notes`
    sorted by language and stripped of empty translations. Unknown fields are
    preserved (placed before `t`, sorted) so nothing is silently lost. Idempotent.
    """
    src = dict(record)
    out: dict[str, Any] = {}

    term = src.pop("term", None)
    if isinstance(term, str):
        out["term"] = term

    if "term_id" in src and src["term_id"] is not None:
        out["term_id"] = src.pop("term_id")
    else:
        src.pop("term_id", None)

    description = src.pop("description", None)
    if isinstance(description, str) and description.strip():
        out["description"] = description.strip()

    # Flags: store only when non-default (case_sensitive/forbidden True, translatable
    # False) so an ordinary term is a lean line; an absent flag reads as its default.
    if _as_bool(src.pop("case_sensitive", False)):
        out["case_sensitive"] = True
    if not _as_bool(src.pop("translatable", True)):
        out["translatable"] = False
    if _as_bool(src.pop("forbidden", False)):
        out["forbidden"] = True

    tags = src.pop("tags", None)
    if isinstance(tags, list):
        deduped = list(dict.fromkeys(tag for tag in tags if isinstance(tag, str) and tag))
        if deduped:
            out["tags"] = deduped

    notes = src.pop("t_notes", None)
    if isinstance(notes, dict):
        clean = {lang: text for lang, text in notes.items()
                 if isinstance(text, str) and text.strip()}
        if clean:
            out["t_notes"] = {lang: clean[lang] for lang in sorted(clean)}

    translations = src.pop("t", None)
    # Any leftover (unknown) fields go before `t`, sorted, so they round-trip.
    for key in sorted(src):
        out[key] = src[key]

    if isinstance(translations, dict):
        clean_t = {lang: text for lang, text in translations.items()
                   if isinstance(text, str) and text != ""}
        out["t"] = {lang: clean_t[lang] for lang in sorted(clean_t)}

    return out


def _as_bool(value: Any) -> bool:
    """Coerce a JSON flag to bool. Accepts real bools and the "yes"/"no" CSV forms."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("yes", "true", "1")
    return bool(value)


# --------------------------------------------------------------------------- #
# Field accessors — keep callers from poking record dict keys directly.
# --------------------------------------------------------------------------- #
def term(record: dict[str, Any]) -> str:
    value = record.get("term")
    return value if isinstance(value, str) else ""


def description(record: dict[str, Any]) -> str:
    value = record.get("description")
    return value if isinstance(value, str) else ""


def is_case_sensitive(record: dict[str, Any]) -> bool:
    return _as_bool(record.get("case_sensitive", False))


def is_translatable(record: dict[str, Any]) -> bool:
    return _as_bool(record.get("translatable", True))


def is_forbidden(record: dict[str, Any]) -> bool:
    return _as_bool(record.get("forbidden", False))


def tags(record: dict[str, Any]) -> list[str]:
    value = record.get("tags")
    return [tag for tag in value if isinstance(tag, str)] if isinstance(value, list) else []


def translations(record: dict[str, Any]) -> dict[str, str]:
    value = record.get("t")
    return {lang: text for lang, text in value.items() if isinstance(text, str)} if isinstance(value, dict) else {}


def translation(record: dict[str, Any], lang: str) -> str | None:
    """`t[lang]`, or None when the language is absent (= not yet translated)."""
    return translations(record).get(lang)


def note(record: dict[str, Any], lang: str) -> str | None:
    value = record.get("t_notes")
    return value.get(lang) if isinstance(value, dict) else None


def index_by_term(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Map each headword to its record (exact, case-sensitive — Lokalise glossary
    is case-sensitive). First record wins on a duplicate; validate_records flags
    duplicates."""
    index: dict[str, dict[str, Any]] = {}
    for record in records:
        index.setdefault(term(record), record)
    return index


# --------------------------------------------------------------------------- #
# Validation — pre-write / pre-push hygiene. Returns (level, term, message)
# tuples; level is "error" (blocks a push) or "warn" (review-worthy). Mirrors the
# loc_qa / loc_placeholder_lint role for the string corpus.
# --------------------------------------------------------------------------- #
def validate_records(records: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    issues: list[tuple[str, str, str]] = []
    known = set(project_languages())
    seen: dict[str, int] = {}
    seen_ci: dict[str, int] = {}

    for record in records:
        name = term(record)
        if not name:
            issues.append(("error", "<empty>", "term is empty (the term field cannot be empty)"))
            continue
        seen[name] = seen.get(name, 0) + 1
        seen_ci[name.casefold()] = seen_ci.get(name.casefold(), 0) + 1

        # Lokalise constraint: a term cannot be both non-translatable and forbidden.
        if not is_translatable(record) and is_forbidden(record):
            issues.append(("error", name, "translatable:false and forbidden:true — Lokalise rejects this combo"))

        tag_list = tags(record)
        if len(tag_list) > 3:
            issues.append(("error", name, f"{len(tag_list)} tags — Lokalise allows at most 3"))
        for tag in tag_list:
            if tag not in TAG_VOCAB:
                issues.append(("warn", name, f"tag {tag!r} is not in TAG_VOCAB (proposed vocab)"))

        t = record.get("t")
        if t is not None and not isinstance(t, dict):
            issues.append(("error", name, "`t` is not an object"))
        for lang in translations(record):
            if lang == SOURCE_LANG:
                issues.append(("warn", name, "t['en'] present — the en form is the `term`; drop t['en']"))
            elif lang not in known:
                issues.append(("error", name, f"unknown language {lang!r} in `t` (not a project language)"))

        note_map = record.get("t_notes") or {}
        if isinstance(note_map, dict):
            for lang in note_map:
                if lang not in translations(record):
                    issues.append(("warn", name, f"t_notes[{lang!r}] has no matching translation"))

        if not description(record):
            issues.append(("warn", name, "no description — translators benefit from a usage note"))

    for name, count in seen.items():
        if count > 1:
            issues.append(("error", name, f"duplicate term ({count}×) — terms must be unique"))
    for name_ci, count in seen_ci.items():
        if count > 1 and seen.get(name_ci, 0) != count:  # differ only by case
            issues.append(("warn", name_ci, "terms differ only by case — Lokalise allows it but confirm intent"))

    return issues


# --------------------------------------------------------------------------- #
# Export — render the glossary into the Lokalise import formats. These prove the
# schema is export-ready (the format requirement); the operator-run push CLI
# (loc_glossary_import.py, planned — GLOSSARY.md § Push) will wrap them.
# --------------------------------------------------------------------------- #
def to_lokalise_csv(records: list[dict[str, Any]], languages: list[str] | None = None,
                    include_descriptions: bool = True) -> str:
    """Render records as a Lokalise glossary CSV (semicolon-separated, UTF-8).

    `languages` defaults to the languages actually present across records — NOT the
    full project set — because an empty translation cell in a Lokalise upload
    REMOVES the existing translation. Pass an explicit list to push a fixed set.
    A `<iso>_description` column is emitted only for languages that have a note.
    Header strings come from CSV_FIXED_HEADERS — VERIFY against a Lokalise template
    before the first import (see that constant).
    """
    records = [_normalized(record) for record in records]
    if languages is None:
        present: set[str] = set()
        for record in records:
            present.update(translations(record))
        languages = sorted(present)
    desc_langs = [lang for lang in languages
                  if include_descriptions and any(note(record, lang) for record in records)]

    header = list(CSV_FIXED_HEADERS) + list(languages) + [f"{lang}_description" for lang in desc_langs]
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=CSV_DELIMITER, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    writer.writerow(header)
    for record in records:
        row = [
            term(record),
            description(record),
            "yes" if is_case_sensitive(record) else "no",
            "yes" if is_translatable(record) else "no",
            "yes" if is_forbidden(record) else "no",
            ",".join(tags(record)),
        ]
        row += [translation(record, lang) or "" for lang in languages]
        row += [note(record, lang) or "" for lang in desc_langs]
        writer.writerow(row)
    return buffer.getvalue()


def to_api_terms(records: list[dict[str, Any]], iso_to_lang_id: dict[str, int]) -> list[dict[str, Any]]:
    """Render records as create-glossary-terms API payloads (the alternative to CSV).

    Unlike the CSV path (keyed by ISO), the API keys translations by numeric
    `langId`, so the caller supplies an ISO -> lang_id map (resolve it from the
    project languages endpoint — lokalise_helper.py). A language missing from the
    map is skipped. See GLOSSARY.md § Push for which path to use.
    """
    payloads: list[dict[str, Any]] = []
    for record in records:
        translation_objs = []
        for lang, text in sorted(translations(record).items()):
            lang_id = iso_to_lang_id.get(lang)
            if lang_id is None:
                continue
            obj: dict[str, Any] = {"langId": lang_id, "translation": text}
            note_text = note(record, lang)
            if note_text:
                obj["description"] = note_text
            translation_objs.append(obj)
        payload: dict[str, Any] = {
            "term": term(record),
            "description": description(record),
            "caseSensitive": is_case_sensitive(record),
            "translatable": is_translatable(record),
            "forbidden": is_forbidden(record),
            "tags": tags(record),
            "translations": translation_objs,
        }
        if record.get("term_id") is not None:
            payload["id"] = record["term_id"]
        payloads.append(payload)
    return payloads
