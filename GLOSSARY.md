<!--
doc-role: canonical
doc-owner: GLOSSARY.md (mywater_localisation repo)
doc-scope: the terminology glossary — what it is, the glossary.ndjson record schema, the Lokalise glossary export mapping (CSV + API), the category taxonomy, the do-not-translate / forbidden / case-sensitivity conventions, and the two-pass fill workflow. Serializer + accessors → loc_glossary.py (the single owner, the format's canonical home). Linguistic term choice → TRANSLATION_STYLE.md. String corpus mechanics → PIPELINE.md.
-->

# Glossary — cross-platform terminology source of truth

A git-tracked, source-of-truth list of MyWater **terminology** — brand / product
names, recurring UI labels, hydration-domain concepts, beverage names,
measurement units, and banned ("avoid") jargon — each with one agreed rendering
per language. It exists so a term ("daily goal", "streak", the brand "My Water")
is translated the **same** way in every string, on every platform (iOS / Android
/ server), across all 21 languages — instead of drifting per key. It is the
**terminology analog of `strings.ndjson`**: authored and reviewed here as a clean
`git diff`, then pushed into the **Lokalise glossary** (a separate Lokalise
surface from translation keys), where it surfaces to translators inline and
drives Lokalise's glossary QA.

> This file documents the **structure** and API round-trip. Filling / expanding
> `glossary.ndjson` follows the staged workflow in § Fill workflow.

## Pipeline placement

```
                 strings.ndjson  ── translators / audit read both for term consistency ──▶
                       ▲ (terms recur as values)
glossary.ndjson ──(loc_glossary_import.py / to_lokalise_csv)──▶ Lokalise glossary
   ▲    │  the single serializer (loc_glossary.py) owns read/write
   └────┘  edits land here, reviewed as a git diff, then pushed (API upsert / CSV upload)
```

- `glossary.ndjson` is the source of truth (like `strings.ndjson` for strings).
  It is **not** the Lokalise format — there is an explicit export step, so the
  working format stays diff-friendly and the Lokalise representation is generated.
- The Lokalise glossary is a **different surface** from translation keys: terms
  are reference data, not reviewed/release-gated strings. So the glossary is
  simpler than the string corpus — see § Why no review state.

## Record schema

One JSON object per line (NDJSON), serialized **only** by `loc_glossary.py`
(`write_records`) — never hand-edited (the glossary's [CR-CORPUS-OWNER]; § Serializer-owned).

| Field | Type | Required | Meaning |
|---|---|---|---|
| `term` | string | **yes** | The **en** headword (the source term). The Lokalise glossary term *is* the en form, so there is **no** `t["en"]`. Must be non-empty and unique. |
| `term_id` | int | no | Lokalise glossary-term id, stamped back after an **API** push. Absent until then (the CSV path upserts by `term`, not id). |
| `description` | string | recommended | en translator-facing definition / usage note → Lokalise glossary `description`. |
| `case_sensitive` | bool | no (default `false`) | Lokalise flag. Stored only when `true`. Use for acronyms / cased brand forms (see § Conventions). |
| `translatable` | bool | no (default `true`) | Lokalise flag. Stored only when `false` (do-not-translate — brand / product names). |
| `forbidden` | bool | no (default `false`) | Lokalise flag. Stored only when `true` (banned term — Lokalise QA flags it). |
| `tags` | string[] | no | Up to **3** category tags (Lokalise max). Controlled vocab — § Tag taxonomy. |
| `t` | {lang: string} | no | Per-language translation for the **20 non-en** project languages (ru + 19). Sorted by language. Absent / missing language = not yet translated. |
| `t_notes` | {lang: string} | no | Optional per-language translator note → Lokalise `<iso>_description`. Rare. |

**Lean by default — an absent field reads as its default.** `loc_glossary.write_records`
drops a flag at its default value, drops empty `tags` / `t_notes`, sorts `t` by
language, and sorts records by headword — so an ordinary term is a short line and
the diff is deterministic (`read → write` is byte-identical, the same contract as
the string corpus). Annotated examples:

```jsonc
// Ordinary domain term: lean line, ru co-source + one target, a ru-specific note.
{"term":"daily goal","description":"The user's target water volume for the day.",
 "tags":["domain","ui"],"t_notes":{"ru":"закрепляем «норма», не «дневная цель»"},
 "t":{"de":"Tagesziel","ru":"дневная норма"}}

// Brand: do-not-translate (translatable:false) + cased (case_sensitive:true).
{"term":"My Water","description":"Product/brand name.","case_sensitive":true,
 "translatable":false,"tags":["brand"],"t":{"ru":"My Water"}}

// Banned jargon: forbidden:true so Lokalise QA flags it if it appears.
{"term":"hydration metrics","description":"Avoid — clinical jargon; prefer plain language.",
 "forbidden":true,"tags":["domain"],"t":{}}
```

## Lokalise mapping

Two import paths into the Lokalise glossary; the serializer renders both.

| `glossary.ndjson` | Lokalise glossary field | CSV column | API (`create-glossary-terms`) |
|---|---|---|---|
| `term` | Term | `term` | `term` |
| `description` | General description | `description` | `description` |
| `case_sensitive` | Case-sensitive | `casesensitive` (`yes`/`no`) | `caseSensitive` (bool) |
| `translatable` | Translatable | `translatable` (`yes`/`no`) | `translatable` (bool) |
| `forbidden` | Forbidden | `forbidden` (`yes`/`no`) | `forbidden` (bool) |
| `tags` | Tags (≤3) | `tags` (comma-separated) | `tags` (array) |
| `t[<iso>]` | Translation (per language) | `<iso>` (bare ISO code) | `translations[].translation` + `langId` |
| `t_notes[<iso>]` | Translation description | `<iso>_description` | `translations[].description` |

- **CSV** — `loc_glossary.to_lokalise_csv(records)`. Semicolon-separated, UTF-8,
  header row. Keyed by **ISO code** — our `t` keys are already Lokalise ISO codes
  (`pt_BR`, `zh_CN`), so they map 1:1. This remains the manual UI fallback
  (Glossary > More > Upload CSV); no language-id lookup.
- **API** — `loc_glossary_import.py` uses
  `loc_glossary.to_api_terms(records, iso_to_lang_id)`. Keyed by numeric
  **`langId`**, so it resolves ISO → lang_id from the project languages endpoint
  (`lokalise_helper.py`). The API path is the normal scripted path:
  `make glossary-push-dry` then `make glossary-push`.
  It upserts every local term and stamps returned `term_id`s into the local file;
  remote-only terms and languages absent from local `t` are preserved rather than
  silently deleted.
- **Pull / device download** — `make glossary-pull` runs `loc_glossary_ndjson.py`
  and downloads the Lokalise glossary into local `glossary.ndjson`. It overwrites
  the local file and is confirmation-gated (`FORCE=1` skips the prompt), mirroring
  `make pull` for `strings.ndjson`.
- **CSV headers are verified** against a real Lokalise export (2026-05):
  `term;description;casesensitive;translatable;forbidden;tags;<iso>;...`.
- ⚠️ **An empty translation cell REMOVES the existing translation** on upload
  (omitting the whole column preserves it). `to_lokalise_csv` therefore defaults
  its columns to the languages **actually present** across records — never the full
  21 — so a partial (pass-1) glossary can be pushed without wiping languages you
  have not filled yet.
- **Constraint — a term can NOT be both `translatable:false` and `forbidden:true`**
  (Lokalise rejects it). `validate_records` flags the combo as an error.

## Tag taxonomy (proposed)

Lokalise allows **≤3** tags per term (case-sensitive). Proposed controlled vocab
(`loc_glossary.TAG_VOCAB`) — drawn from `TRANSLATION_STYLE.md § Lexicon` /
`§ Brand voice`. **Adjust at fill time**; `validate_records` only *warns* on an
off-vocab tag (it does not block).

| Tag | Covers |
|---|---|
| `brand` | brand & product names — "My Water", "My Water Premium" |
| `ui` | recurring UI / control labels — Save, Goal, Reminder, Streak, Award, Widget |
| `domain` | hydration-domain concepts — water, drink, hydration, intake, habit |
| `beverage` | beverage names — Water, Coffee, Tea, Juice, ... |
| `unit` | measurement units — ml, l, fl oz, cup, kg, lb |
| `legal` | terms appearing in legal / Terms / Privacy text (`Register: formal`) |

## Conventions & nuances

- **Do-not-translate — `translatable:false`.** Brand / product names that must
  stay verbatim ("My Water", "My Water Premium"). Keep a `t` entry per language
  equal to the source *only* where the script differs and a transliteration is
  intended; otherwise leave `t` empty and rely on the flag. Brand-name rendering
  and locale quotation marks (`«»` ru/fr, `„"` de, `「」` ja) are governed by
  `TRANSLATION_STYLE.md § Punctuation` — the glossary pins the **word**, the style
  doc pins the **quoting**.
- **Brand localization — `My Water` is `translatable:true` and ANCHORED ON
  `CFBundleName`.** The per-locale rendering of the brand **is** the app's
  `CFBundleName` / `CFBundleDisplayName` value (the home-screen icon name) — that is
  the source of truth we build from: da «Mit vand», de «Mein Wasser», es «Mi agua»,
  fr «Mon eau», it «La mia acqua», ko «나의 물», ru «Моя вода», zh «我的水». **ar / id /
  vi keep Latin `My Water`** (their `CFBundleDisplayName` is Latin — not drift).
  - **Current state (2026-06) — partial sweep, intentionally `пока так`.** The brand
    is localized where `ru` also localizes (and on the named drift keys
    `shareInviteFriendsText` / `shareInviteMessage` / `spotlightOpenDrinkDescription`);
    `da` was swept first. Many user-facing keys still carry Latin `My Water`
    (≈ de 15 / es 27 / fr 23 / ko 32 / it 13). Aligning them is a **pending
    per-language sweep, built from the `CFBundleName` anchor** and done with per-key
    judgment (mirror what `ru` does on each key) — **not** a blind find-replace.
  - **Intentional KEEP-Latin carve-outs** (do not localize without an explicit
    operator decision): (a) ar / id / vi; (b) **social-share + App Store** surfaces
    (`socialShareText*`, `achivmentTextShare*`, `appstore_app_*`) — Latin across *all*
    locales, an ASO / brand-recognition choice; (c) keys where **`ru` itself keeps
    Latin** (e.g. `weightPromo1`, in-app Settings navigation paths like
    `appleHealthPartialFooter`).
- **Forbidden — `forbidden:true`.** The "avoid" lexicon
  (`TRANSLATION_STYLE.md § Lexicon`: `hydration metrics`, `consumption logs`,
  `metabolic profile`, medical jargon) modeled as banned terms so Lokalise QA
  flags them. A forbidden term is usually `translatable:true` (the ban is on the
  term appearing); never combine with `translatable:false`.
  - **Lokalise `forbidden` QA fires on the *translation*, per target language**
    (verified — Lokalise docs: "this term cannot be used in **the translation** …
    checks if **the translation** contains any terms marked as forbidden"). A
    forbidden term carries its banned form **per language** in `t`, so the check
    fires in each language whose `t[<iso>]` is set. This drives three patterns:
    - **Bilingual ban** — banned in both en and ru: set `t[ru]` to the ru calque
      (e.g. `hydration metrics` → `показатели гидратации`). QA flags both sides.
    - **EN-source-only ban** — bad in en but whose ru rendering is *correct*: leave
      `t` **empty** (e.g. `application` — ru «приложение» is fine, so a `t[ru]`
      would wrongly flag every legitimate string). The entry gates the en source
      only; the audit's en-lane is the backstop.
    - **RU-only calque ban (carve-out from the en-headword rule)** — bad only in ru,
      where the en concept is *allowed* (so its en word can't be marked forbidden):
      key the entry by the **Russian token itself** (`term` = `гидратация`,
      `t.ru` = `гидратация`, `forbidden:true`). The en concept (`hydration`) stays a
      separate allowed entry. Surface-**conditional** bans (familiarity diminutives
      `водичка`/`стаканчик`; ambiguous `насыщенность` = saturation) stay in the
      audit, not here — a flat lexical flag would false-positive on the casual
      surfaces where they are acceptable.
- **`case_sensitive:true`** — acronyms and cased brand forms where only the exact
  casing should match (Lokalise matching is case-sensitive per entry; a separate
  lowercase variant needs its own entry).
- **Third-party / Apple feature names — use the vendor's OFFICIAL localization,
  never an invented one.** Some names Apple keeps verbatim in RU (`Siri`,
  `Apple Watch`, `App Store`, `Apple ID`, `iPhone`) → `translatable:false`. Others
  Apple *does* localize and we adopt that exact form: `Shortcuts` → «Быстрые
  команды»; `Live Activities` → «Эфир активности» (both from Apple's RU iPhone User
  Guide, support.apple.com/ru-ru) — the corpus's «Live-активности» is drift to
  reconcile. Apple's Health **app** is «Здоровье»; the corpus keeps `Apple Health`
  as the integration/brand name (verify app-vs-platform usage in pass-2). Never
  coin a hybrid.
- **Register / T-V is NOT a glossary field.** Glossary entries are lexical
  headwords (nouns / short labels), which carry no T-/V-form. The T-form-default /
  `formal`-in-legal register lives in `TRANSLATION_STYLE.md § Brand voice`. When a
  term's *rendering* depends on a per-language decision worth recording, put it in
  `t_notes[<iso>]` (e.g. the `water balance` casual-surface carve-out, or the
  `Apple Health` → «Здоровье» note).
- **Plurals / placeholders do NOT apply.** Terms are not runtime strings — there
  is no CLDR-forms map and no `[%s]` contract here (those are string-corpus
  concerns, `TRANSLATION_STYLE.md § Placeholders`).
- **Why no review state.** The string corpus carries `unverified` (review) and
  `dirty` (push-pending) because translations are release-gated and pushed
  incrementally ([CR-CORPUS-UNVERIFIED] / [CR-CORPUS-DIRTY]). The glossary is small
  reference data with no release gate, pushed as a whole-glossary upsert / CSV
  upload, so it needs neither: a language simply present in `t` is filled,
  absent is not.

## What belongs in the glossary

Include a term when **consistency across strings matters** and a translator could
otherwise diverge:

- **Yes** — brand / product names; named features (Premium, Awards, Reminders,
  Widgets, Siri); recurring domain nouns (water, drink, goal, streak, habit,
  intake); beverage names; unit abbreviations; banned jargon; a handful of
  ambiguous short labels whose meaning is fixed by convention.
- **No** — whole sentences / micro-copy (those live in `strings.ndjson`);
  one-off strings; anything whose translation is context-dependent rather than a
  fixed term. A glossary is dozens-to-low-hundreds of entries, not a phrasebook.

Reuse-search first (`rg`/`jq` over `glossary.ndjson` and the flat `en` of
`strings.ndjson`) so a term is not added twice or under two spellings.

## Fill workflow (the two passes)

Filling is deliberately staged, mirroring the corpus en/ru co-source discipline
([CR-CORPUS-SOURCE-CHANGE]) and the fan-out / fan-in of a translation pass
(`PIPELINE.md § Parallel translation passes`):

1. **Pass 1 — en + ru (co-source, for сверка / cross-check).** Author each term:
   `term` (en headword), `description` (en usage note), the flags, `tags`, and
   `t["ru"]` (the Russian rendering). ru is the co-source — settle the
   en↔ru terminology pair *first* and review it as a `git diff` before fanning
   out. No other target is filled yet.
2. **Pass 2 — the 19 other targets.** With the en/ru pairs locked, fill
   `t[<lang>]` for `loc_glossary.target_langs()` (ar, da, de, es, fr, hi, id, it,
   ja, ko, ms, nb, nl, pl, pt_BR, sv, tr, vi, zh_CN) — per-language, with per-key
   reasoning and the linguistic discipline (`TRANSLATION_STYLE.md`,
   `CLAUDE.md § Self-translation discipline`). Fan out read-only, then serialize
   the writes through the single owner (never two writers at once,
   [CR-CORPUS-CONCURRENCY]).
3. **Review & push.** `git diff -- glossary.ndjson`, run validation, then the
   token-holding operator pushes to Lokalise with `make glossary-push-dry` /
   `make glossary-push` ([CR-ACCESS]).

## Verification

- `python3 -m py_compile loc_glossary.py` after any change to the serializer.
- **Round-trip byte-identical** — `read_records → write_records` against a
  **copy** in `/tmp` (never the live file, [CR-CORPUS-WORKTREE]); `filecmp` must
  match (deterministic-diff contract, [CR-CORPUS-OWNER]).
- **`loc_glossary.validate_records(records)`** — errors block a push: empty /
  duplicate `term`, `translatable:false`+`forbidden:true`, >3 tags, unknown `t`
  language, `t["en"]` present. Warnings (review-worthy): off-vocab tag, missing
  `description`, `t_notes` for an untranslated language, case-only-duplicate terms.
- After a fill: `git diff -- glossary.ndjson` touches only the edited terms.
- Before a Lokalise upload: `make glossary-push-dry` validates the local glossary
  and prints the upsert plan. `make glossary-push` is operator-run and token-gated;
  after success it stamps Lokalise `term_id`s back into `glossary.ndjson` and
  verifies the stored values by re-reading the glossary API.
- Before a Lokalise download: `make glossary-pull` warns on local `glossary.ndjson`
  diff and requires typed confirmation because it overwrites the local file.
  Report what ran and what was deferred to the operator — never claim a push/pull
  you did not observe ([CR-ACCESS]).

## Serializer-owned

`loc_glossary.py` owns `glossary.ndjson` read/write — the glossary form of
[CR-CORPUS-OWNER]. **Never hand-edit the file** or re-serialize it another way;
go through `write_records` (or the planned apply tool). The same worktree-safety
rules as the string corpus apply: a non-empty `git diff --stat glossary.ndjson`
may be someone's in-flight fill — preserve it, test applies against a `--glossary`
copy in `/tmp`, and never `git checkout` / `reset` away uncommitted edits
([CR-CORPUS-WORKTREE]).

## Tooling

- **`loc_glossary_apply.py`** (token-free) — apply a `{term: translation}` (one
  language: `loc_glossary_apply.py <lang> edits.json`) or `{term: {lang:
  translation}}` (`--map`) edit map into `glossary.ndjson` through `write_records`;
  replace-only and single-writer, like `loc_apply_lang.py` (an unknown term is
  reported, not appended; an empty value clears the language). This is the fan-in
  tool for a parallel multi-language fill (§ Fill workflow pass 2): fan out the
  per-language reasoning read-only, then serialize the applies one language (or one
  `--map`) at a time ([CR-CORPUS-CONCURRENCY]). Test against a `--glossary
  /tmp/x.ndjson` copy, never the live file + revert ([CR-CORPUS-WORKTREE]).
- **`loc_glossary_import.py`** + a `make glossary-push` / `make glossary-push-dry`
  target (operator-run, token-gated) — render `to_api_terms` and upsert into the
  Lokalise glossary API; dry-run validates locally and prints a token-free plan
  ([CR-MAKE] / [CR-ACCESS]).
- **`loc_glossary_ndjson.py`** + `make glossary-pull` (operator-run, token-gated)
  — download Lokalise glossary terms into `glossary.ndjson`; confirmation-gated
  because it overwrites local edits.

## Related

- `loc_glossary.py` — the serializer + accessors + validation + CSV/API export
  (the format's canonical owner; library, not a CLI).
- `TRANSLATION_STYLE.md` — linguistic canon: which term to prefer (§ Lexicon),
  brand voice, register, locale punctuation. The glossary pins the *word*; the
  style doc pins *how* it is rendered.
- `PIPELINE.md` — string-corpus mechanics and the parallel-pass / single-writer
  discipline the fill workflow reuses.
- `CLAUDE.md` — agent contract; § Task router routes glossary work here.
