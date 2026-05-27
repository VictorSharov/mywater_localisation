# mywater_localisation

Cross-platform localization **source-of-truth corpus + tooling** for MyWater
(iOS / Android / server). One place where an AI agent or a translator can see
**every** Lokalise key across **every** platform and language — so they never
recreate a key that already exists elsewhere, and can QA translations without
the per-platform blind spots that the native `.strings` / `.xml` files had.

## Pipeline

```
Lokalise ──(loc_corpus_ndjson.py)──▶ strings.ndjson  ◀── AI agents / translators read (dedup, audit)
   ▲                                       │
   │                                   apply scripts write edits INTO the corpus (stdlib, no token)
   └──(loc_corpus_import.py --apply)───────┘   one documented import step
strings.ndjson + Lokalise ──export──▶ iOS .strings / Android .xml / server JSON
```

- **Lokalise** is the long-term source of truth for verified translations.
- **`strings.ndjson`** is a regenerable, git-tracked snapshot of the whole project
  (all keys, all platforms, all languages) that AI sessions read. Consumers only
  pull / read it — the Lokalise token never touches a consumer session.
- Edits (audits, fresh translations, new source strings) are written back into the
  corpus, reviewed as a clean `git diff`, then imported into Lokalise. From
  Lokalise each platform exports its native format.

## Setup

System Python is PEP 668 externally-managed, so the Lokalise-facing scripts run
under a venv:

```bash
python3 -m venv .venv-lokalise
.venv-lokalise/bin/pip install -r requirements.txt
export LOKALISE_API_TOKEN=...        # never pass as a CLI arg
export LOKALISE_PROJECT_ID=...
```

The audit / translation / apply scripts (`loc_audit_*`, `loc_apply_lang`,
`loc_merge_languages`, `loc_r_marked_translations`, `loc_placeholder_lint`,
`loc_qa`) are **stdlib-only** and need no token — they only read / write
`strings.ndjson`. Only
the corpus generator, the importer, the QA-issues fetch, and the unused-key
tagging touch Lokalise.

## Scripts

| Script | What it does | Token? |
|---|---|---|
| `loc_corpus.py` | shared read/write/lookup lib + the single owner of corpus serialization (not a CLI) | — |
| `loc_corpus_ndjson.py` | regenerate `strings.ndjson` (+ `strings.meta.json`) from Lokalise | yes |
| `loc_corpus_import.py` | push corpus edits into Lokalise (dry-run default, `--apply`) | yes (`--apply`) |
| `loc_qa_issues_fetch.py` | fetch Lokalise QA-flagged translations (`spelling_and_grammar` default; `--issue` for others) to `qa_issues.ndjson` for AI validation | yes |
| `loc_audit_extract.py` | extract en+ru+`<lang>` audit batches from the corpus (opt. `--platform`) | — |
| `loc_audit_apply.py` | apply validated audit findings into the corpus | — |
| `loc_apply_lang.py` | apply a `{key:value}` map into the corpus (replace-only) | — |
| `loc_merge_languages.py` | side-by-side language view for cross-check review | — |
| `loc_r_marked_translations.py` | translation backlog (`unverified`/missing/empty): extract → JSON → apply | — |
| `loc_placeholder_lint.py` | lint placeholders vs the Lokalise universal contract; pre-flight inside `loc_corpus_import` | — |
| `loc_qa.py` | lint value hygiene (em-dash, invisible spaces, `()` balance, edge/double whitespace, cross-language URL parity); 2nd pre-flight inside `loc_corpus_import` | — |
| `loc_unused_keys.py` | report-only unused-key scan over **iOS + Android** repos; feeds Lokalise tags | yes (tag `--apply`) |
| `lokalise_helper.py` | Lokalise API v2 CLI (list/get/tags/update/create; mutations dry-run by default) | yes (`--apply`) |
| `loc_audit_prompt.md` + `loc_audit_lang_calibration/` | sub-agent audit prompt + per-language calibration | — |

Exact flags live in each script's `--help` / docstring (the canonical owner).

## Common commands

```bash
# Regenerate the corpus from Lokalise (token holder; commit + push the result):
.venv-lokalise/bin/python loc_corpus_ndjson.py

# Fetch Lokalise QA warnings (spelling/grammar by default) for AI validation (token holder):
.venv-lokalise/bin/python loc_qa_issues_fetch.py
.venv-lokalise/bin/python loc_qa_issues_fetch.py --issue spelling_and_grammar --issue placeholders

# Audit a language (reads the corpus; no token):
python3 loc_audit_extract.py de 1 200 /tmp/loc_audit_de_001.txt
#   → run the Opus 4.7 sub-agent with loc_audit_prompt.md → validated findings
python3 loc_audit_apply.py de /tmp/validated_de.md      # writes t[de] into the corpus

# Translate the backlog (unverified / missing / empty) for a language:
python3 loc_r_marked_translations.py extract de --batch-size 50 --output-dir /tmp/loc_r_de
python3 loc_r_marked_translations.py apply de /tmp/loc_r_de_001.json --dry-run
python3 loc_r_marked_translations.py apply de /tmp/loc_r_de_001.json

# Review + import edits into Lokalise:
git diff -- strings.ndjson
.venv-lokalise/bin/python loc_corpus_import.py --lang de            # dry-run
.venv-lokalise/bin/python loc_corpus_import.py --lang de --apply    # push
.venv-lokalise/bin/python loc_corpus_import.py --key fullPromoText --apply  # one key, all its langs

# Unused-key candidates (iOS + Android both required):
.venv-lokalise/bin/python loc_unused_keys.py        # --repo-root <ios>, --android-repo <android>
```

## Consuming the corpus from another repo

Attach this repo to an iOS / Android / server session via
`permissions.additionalDirectories` and read `strings.ndjson`. Search the flat
`en` field (`rg` / `jq`) before creating a new key — if a matching key already
exists on another platform, add the missing platform in Lokalise instead of a
duplicate.

## Export from Lokalise

The corpus → Lokalise **import** is built (`loc_corpus_import.py`); the Lokalise →
platform **export** is operator-run from the Lokalise UI (this repo writes no platform files). What
each platform's bundle must end up as:

| Platform | File format | Placeholder format | Plural | Path (expected) |
|---|---|---|---|---|
| iOS | `.strings` + `.stringsdict` | iOS (`[%s]`→`%@`, `[%i]`→`%li`) | `.stringsdict` | `<lang>.lproj/Localizable.strings` |
| Android | XML | printf (`[%s]`→`%s`, `[%i]`→`%d`) | `<plurals>` | `values-<lang>/strings.xml` |
| server (`web`) | JSON `{translation, notes}` | none today (printf if ever, not i18next) | none today | `resources/locale/<lang>.json` |

- **Placeholder conversion is automatic on export** from the universal form
  ([CR-PLACEHOLDER] / `TRANSLATION_STYLE.md § Placeholders`) — the export just
  needs the right per-bundle *placeholder format* selected (not "raw"). Lokalise
  lets you override the default; pin it explicitly per bundle.
- **Plurals** reach each platform's native plural mechanism only if the key is a
  Lokalise plural (`is_plural`); a flat key carrying `%#@var@` does **not** (a
  broken stringsdict import — see `TRANSLATION_STYLE.md § Placeholders`).
- **Language codes** differ from the corpus (`pt_BR` / `zh_CN` → iOS `pt-BR` /
  `zh-Hans`); the download config owns that mapping (the trap `loc_corpus.py`
  guards against).

### iOS — Apple Strings  *(finalized; validated against a real export, 2026-05-27; `Include description` flipped on→off 2026-05-27 — re-confirm comment-free on next download)*

Lokalise → **Download**, file format **Apple Strings**. Set exactly:

| Setting | Value |
|---|---|
| File structure | **Multiple files per language (use assigned filenames)**, directory prefix `%LANG_ISO%.lproj` |
| Languages / Data | All |
| Empty translations | **Replace with base language** |
| Plural format | Default plural format |
| Placeholder format | **iOS** |
| Convert all `[%]` to `%%` | on |
| Sort keys by | Key name A-Z |
| Indentation | 2 spaces |
| Include description | off |
| Include comments | off |
| Replace line breaks with `\n` | on |
| Add new line at EOF | on |
| Don't use directory prefix | off |
| Disable referencing | off |
| Include all platform keys | off |
| Include other Project strings | off |

Non-obvious choices:
- **Multiple files, never "One file per language."** The bundle needs
  `InfoPlist.strings` (permission prompts `NS*UsageDescription`,
  `CFBundleDisplayName`) split from `Localizable.strings`; one-file emits no
  `InfoPlist.strings`, so localized Info.plist values break. Plurals land in
  `Localizable.stringsdict` automatically.
- **Empty translations = Replace with base language.** The iOS app is R.swift: a
  *missing* key falls back to the English source, but an *empty* value renders
  blank, and `.stringsdict` plurals / forced-language (`preferredLanguages`) /
  dynamic-key lookups show the raw key on a miss — base-language is the only
  uniformly safe option ("export as empty" → blank UI; "don't export" → breaks
  plurals).
- **iOS placeholder + Convert `[%]`→`%%`.** Converts universal `[%s]`→`%@` etc.;
  the `[%]`→`%%` toggle is what ships the canonical literal-percent `[%]`
  ([CR-PLACEHOLDER]) as `%%` — without it a standalone `[%]` de-escapes to a bare
  `%`, undefined under iOS `String(format:)`. Keep it **on** for the iOS bundle.
- **Include description = off.** The durable home of translator-context is the
  corpus (`strings.ndjson` `context`) + the Lokalise Description field; the
  `en.lproj` `/* … */` is only the authoring input Lokalise imports from, and this
  export overwrites `en.lproj`, so the comment would not survive in the committed
  files anyway. Re-shipping it into the exported `.strings` + the app bundle is a
  redundant, drift-prone copy that nothing reads at runtime (R.swift / Foundation
  ignore comments). Off matches Android and the iOS rule that context must not fan
  out into non-en `.lproj` (`mywater_ios docs/LOCALIZATION.md § Comment encoding`).
  Flipping on→off strips the comment from every exported `.strings` — a large
  one-time diff.

Gotchas:
- **Dead nested path `<lang>.lproj/Localization/<lang>.lproj/Localizable.strings`.**
  Keys can carry a Lokalise filename with a `.lproj/` path (stamped when an iOS
  `.strings` file is uploaded / synced via the Git integration); the directory
  prefix then doubles it and those keys drop out of the usable bundle. Fix:
  `python3 lokalise_helper.py normalize-filenames` (dry-run → `--apply`), or clear
  the filename in the Lokalise UI, then re-download. **Before normalizing, confirm
  the manual download is the canonical Lokalise→iOS path:** that `.lproj/` filename
  is *correct* for a Git-integration write-back that uses no directory prefix, so
  clearing it fixes the manual download but could relocate where the integration
  writes those keys. The repo already shipping them flat indicates flat is the
  target — but verify the integration isn't relying on the path before clearing.
- **`|R|` in values** is the [CR-CORPUS-UNVERIFIED] "not human-verified" marker; an
  export carrying `|R|` is a pre-verification snapshot (fine for layout / QA, not
  release). Clear `|R|` / unverified in Lokalise before a release export — no
  download toggle removes it.
- **"N unassigned keys → Localizable.strings"** is cosmetic — unassigned keys
  correctly default to the flat `Localizable.strings`.

Sanity-check a download (run in the unzipped export folder):

```bash
find . -type f | grep -oE '[^/]+$' | sort | uniq -c   # 21 each: InfoPlist.strings, Localizable.strings, Localizable.stringsdict
find . -path '*/Localization/*' -type f                # empty -> no dead nested path
grep -rl '\[%' .                                        # empty -> placeholders converted to native
grep -rl '= "";' .                                      # empty -> no blank values (base-language fill)
grep -rln '/\*' .                                       # empty -> no description comments (Include description=off)
```

### Android — XML  *(settings finalized 2026-05-27; not yet validated against a real export)*

Lokalise → **Download**, file format **Android Resources (.xml)**. Set exactly:

| Setting | Value |
|---|---|
| File structure | **One file per language**, bundle structure `values-%LANG_ISO%/strings.xml` |
| Languages / Data | All |
| Empty translations | **Replace with base language** |
| Plural format | Default plural format |
| Placeholder format | **Printf** |
| Convert all `[%]` to `%%` | on |
| Sort keys by | Key name A-Z |
| Indentation | 2 spaces |
| Include description | off |
| Include comments | off |
| Replace line breaks with `\n` | on |
| Don't use directory prefix | off |
| Disable referencing | off |
| Include all platform keys | **off** |
| Include other Project strings | off |

**Per-language download codes** — must match the app's existing res dirs
(`mywater_android modules/resources/lib-strings/src/main/res/`). Set on the
Download page → expand **Languages** → click the language code. Lokalise
auto-inserts the `-r` region prefix, but two need a manual override and the base
language needs a manual rename:

| Lokalise language | Download code | Android dir |
|---|---|---|
| English (base) | `en` | **`values/`** — rename `values-en/`→`values/` on download (Lokalise can't emit an un-prefixed dir) |
| Indonesian | **`in`** (override, not `id`) | `values-in/` |
| Spanish (Spain) | **`es-rES`** (override, not `es`) | `values-es-rES/` |
| Chinese Simplified | `zh-rCN` (auto `-r`) | `values-zh-rCN/` |
| Portuguese (Brazil) | `pt-rBR` (auto `-r`) | `values-pt-rBR/` |
| 16 others | `ar da de fr hi it ja ko ms nb nl pl ru sv tr vi` | `values-<code>/` (1:1) |

Non-obvious choices:
- **One file per language** (not "Multiple") — Android has no `InfoPlist.strings`
  analogue; every key → one `strings.xml` per `values-*` dir.
- **English base = manual `values-en/`→`values/` rename.** `%LANG_ISO%` always
  prefixes and Lokalise has no toggle to drop the suffix for the base language,
  so the export yields `values-en/`. Rename it to the un-qualified `values/` —
  the required default fallback: any device locale not among the 20, and every
  referenced `R.string.*`, resolves to `values/`; a miss there is a
  `Resources$NotFoundException`. Never delete / empty `values/`.
- **Per-language overrides match the app's res dirs.** Lokalise auto-converts the
  region form (`zh_CN`→`zh-rCN`, `pt_BR`→`pt-rBR`), but `id`→`in` (Android's
  legacy ISO-639 code for Indonesian) and `es`→`es-rES` (the app region-qualifies
  Spanish) must be set by hand. The other 16 map 1:1.
- **Empty translations = Replace with base language.** A *missing* key falls back
  to `values/`, but an *empty* `<string>` renders blank and an incomplete
  `<plurals>` (missing a required CLDR quantity for the locale) throws at format
  time — base-language fill is uniformly safe and makes each locale file
  self-contained (RU is ~94.6%; its gaps fill with English). Same rationale as iOS.
- **Printf placeholder + Convert `[%]`→`%%` = on.** Converts universal `[%s]`→`%s`,
  `[%i]`→`%d`; the toggle ships the canonical literal-percent `[%]`
  ([CR-PLACEHOLDER]) as `%%` (e.g. `50%% off!`) — `getString(id, args…)` /
  `String.format` is printf and aapt requires `%%` for a literal percent in a
  formatted string. Keep **on**. See [`TRANSLATION_STYLE.md`](TRANSLATION_STYLE.md) § Placeholders.
- **Include all platform keys = off** — export only Android-assigned keys; keeps
  iOS-/server-only keys (and any non-Android placeholder form) out of
  `strings.xml`. Requires the Android platform assignment in Lokalise to be correct.
- **Include description / comments = off** (same as iOS) — Android `strings.xml`
  goes straight to production `res/`, so notes / `|R|` stay out of the shipped
  bundle; translator-context lives in the corpus, not the platform files.

Gotchas:
- **The export never produces `values/`** — the `values-en/`→`values/` rename
  above is the one manual step every Android download needs.
- **`formatted="false"` / multi-`%s`.** A string with multiple non-positional
  `%s` (e.g. `logDrinkSiri` = `Log %s of %s`) needs `formatted="false"` or aapt
  fails ("Multiple substitutions specified in non-positional format"). Build the
  app after import to catch it; if Lokalise drops the attribute, switch the source
  to positional args (`%1$s` / `%2$s`).
- **`|R|` in values** is the [CR-CORPUS-UNVERIFIED] "not human-verified" marker; an
  export carrying `|R|` is a pre-verification snapshot (fine for layout / QA, not
  release). No download toggle removes it — clear `|R|` / unverified in Lokalise
  before a release export.
- **Region-only dirs match only that region.** `values-es-rES` serves
  Spanish (Spain) only — Spanish (Mexico) etc. fall back to `values/` (English);
  `values-zh-rCN` / `values-pt-rBR` are Simplified-China / Brazil only. Deliberate
  here, but a coverage trade-off to know.

Sanity-check a download (run in the unzipped export folder, after the rename):

```bash
find . -type d -name 'values-*' | sort                 # 20 dirs; incl values-in, values-es-rES, values-zh-rCN, values-pt-rBR
ls -d values 2>/dev/null || echo 'MISSING default values/ — rename values-en/'
grep -rl '\[%' .                                        # empty -> placeholders converted to native
grep -rln '%@\|%#@' .                                   # empty -> no iOS-only forms leaked
grep -rl '<plurals' . | head                            # plurals present as native <plurals>
```

### server — JSON  *(format locked; export settings TODO until `web` keys are migrated)*

Lokalise platform: **`web`** (Lokalise has no "server" platform). Target file:
`resources/locale/<lang>.json` in the server's bespoke shape
`{ "<key>": { "translation": "…", "notes": "…" } }` — verified against the live
runtime (`mywater_server src/Service/LocalizationService.php`, which reads only
`translation` and also tolerates a flat `{key: "value"}`).

**Status (2026-05): not yet exportable.** Server runtime keys are not in the
corpus/Lokalise yet — no key carries the `web` platform and `strings.meta.json`
platforms are `[android, ios, other]`. Migrating the existing
`resources/locale/*.json` keys into Lokalise under `web` is a separate task;
finalize the download settings after that pass.

Locked decisions:
- **Format:** keep `{translation, notes}`. A flat Lokalise JSON would also run
  (the runtime accepts a flat scalar), but the server keeps `notes` for
  translator context, so the export needs a structured-JSON template (or a
  post-export converter) that emits `{translation, notes}` — not a flat dump.
- **Placeholder format:** server strings have **no placeholders** today; if one
  is ever introduced it is **printf** (PHP `sprintf`), never i18next `{{…}}` /
  ICU `{…}`. Pin the export to printf, not "raw".
- **Languages:** 20. `ar` is intentionally **excluded** — the server ships no
  `ar.json`, `ar` requests fall back to `en` (`mywater_server`
  `AL-I18N-ARABIC-UNTESTED`). Corpus codes are not the server filenames: map on
  download `es → es_ES.json`; the other 19 (incl. `pt_BR`, `zh_CN`) are 1:1
  `<code>.json`. Server filenames use `_` (underscore) and are a runtime
  contract — do not rename.
- **`|R|` / unverified:** dev-only. A pre-release export may carry untranslated
  en-only keys for layout / QA, but a **production** server release requires
  every key translated in all 20 locales and `|R|` cleared (same release gate as
  iOS / Android above).

## Conventions

Linguistic / translation-quality rules (brand voice, register, calque
discipline, punctuation, translator-context comments) are canonical in this repo:
[`TRANSLATION_STYLE.md`](TRANSLATION_STYLE.md); `loc_audit_prompt.md`
operationalizes them for the audit sub-agent. The `|R|` marker that iOS `.strings` use for an
unverified source maps to the corpus `unverified` field; apply scripts mark an
edited language `unverified` so AI/edited translations stay flagged for human /
Lokalise review. Agent-facing rules: `CLAUDE.md`.
