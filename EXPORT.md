<!--
doc-role: canonical
doc-owner: EXPORT.md (mywater_localisation repo)
doc-scope: Lokalise → platform export — validated per-platform download settings (iOS .strings/.stringsdict, Android XML, server JSON) that loc_export.py implements; doubles as the manual-UI fallback. Pipeline / corpus mechanics → CLAUDE.md + PIPELINE.md; linguistic canon → TRANSLATION_STYLE.md.
-->

# Lokalise → platform export

The corpus → Lokalise **import** is built (`loc_corpus_import.py`); the Lokalise →
platform **export** is built too — **`loc_export.py`** drives the download API with
the validated per-platform settings below baked in, downloading each bundle straight
into its repo (replacing the error-prone manual Lokalise-UI download). It is
operator-run (`--apply` needs the token; dry-run prints the resolved plan token-free)
and leaves an unstaged `git diff` in each platform repo to review before committing.
Platforms are independent and optional: a platform whose repo isn't checked out on
this machine (localization dir absent) is **skipped**, not fatal, so a missing
iOS/Android/server repo never blocks the others. Each run prints a summary of what
was exported / skipped / failed and exits non-zero only on a real failure, not a skip.
**The per-platform tables below are the spec `loc_export.py` implements** — keep them
and the script's profiles in sync, and they double as the manual-UI fallback. What
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

## Common to all platforms

- **`unverified` / untranslated strings are pre-verification, not release-ready.**
  They are the `PIPELINE.md § [CR-CORPUS-UNVERIFIED]` "not yet human-verified" /
  "needs translation" markers; an export carrying them is a pre-verification
  snapshot (fine for layout / QA, not release). No download toggle removes them —
  clear `unverified` in Lokalise before a release export.

## iOS — Apple Strings  *(finalized; validated against a real export, 2026-05-27; `Include description` flipped on→off 2026-05-27 — re-confirm comment-free on next download)*

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
- **`unverified` / untranslated strings** (release gate, see § Common to all
  platforms) carried in an iOS export render as the English base, not blank, under
  "Replace with base language" — fine for layout / QA, not release.
- **"N unassigned keys → Localizable.strings"** is cosmetic — unassigned keys
  correctly default to the flat `Localizable.strings`.
- **Routing a key to a non-default file** (e.g. an Info.plist key →
  `InfoPlist.strings`): the `ios` filename slot decides `InfoPlist.strings` vs the
  default `Localizable.strings`. The corpus owns this routing (field `filenames`,
  CLAUDE.md [CR-CORPUS-META]) — set it with
  `python3 loc_apply_meta.py --key <name> --set-filename InfoPlist.strings` (flags
  `dirty_meta`), then `python3 loc_corpus_import.py --apply`; a regenerate reads it
  back. A direct Lokalise-side change still works —
  `python3 lokalise_helper.py set-filename --key <name> --to InfoPlist.strings`
  (dry-run → `--apply`) or the Lokalise UI — and the next regenerate captures it into
  the corpus. The push is a full per-platform replace, so regenerate before the first
  routing push so any pre-existing slot is captured first.

Sanity-check a download (run in the unzipped export folder):

```bash
find . -type f | grep -oE '[^/]+$' | sort | uniq -c   # 21 each: InfoPlist.strings, Localizable.strings, Localizable.stringsdict
find . -path '*/Localization/*' -type f                # empty -> no dead nested path
grep -rl '\[%' .                                        # empty -> placeholders converted to native
grep -rl '= "";' .                                      # empty -> no blank values (base-language fill)
grep -rln '/\*' .                                       # empty -> no description comments (Include description=off)
```

## Android — XML  *(settings finalized 2026-05-27; validated against a real export, 2026-05-28)*

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
  goes straight to production `res/`, so translator descriptions stay out of the
  shipped bundle; translator-context lives in the corpus, not the platform files.

Gotchas:
- **The export never produces `values/`** — the `values-en/`→`values/` rename
  above is the one manual step every Android download needs.
- **`formatted="false"` / multi-`%s`.** A string with multiple non-positional
  `%s` (e.g. `logDrinkSiri` = `Log %s of %s`) needs `formatted="false"` or aapt
  fails ("Multiple substitutions specified in non-positional format"). Build the
  app after import to catch it; if Lokalise drops the attribute, switch the source
  to positional args (`%1$s` / `%2$s`).
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

## server — JSON  *(format locked; validated against a real export, 2026-05-28)*

Lokalise platform: **`web`** (Lokalise has no "server" platform). Target file:
`resources/locale/<lang>.json` as a **flat** `{ "<key>": "<value>" }` map —
verified against the live runtime (`mywater_server
src/Service/LocalizationService.php`, `is_scalar` branch). The runtime still
tolerates the legacy `{translation, notes}` object, but the current export is
flat without `notes`.

**Status (2026-05): migrated and exportable.** All 82 server keys carry the
`web` platform in the corpus and are pushed to Lokalise; `resources/locale/*.json`
is generated by this export. Server `notes` were dropped — translator context
lives in the corpus `context` field (→ Lokalise `description`).

Locked export settings (Lokalise "Download" for the `web` JSON target):
- **Format:** **JSON (.json)** — flat `{key: "value"}`. (Not "Structured JSON",
  which wraps every value in a `{translation: …}` object.)
- **Include all platform keys:** **off** — export only `web`-assigned keys (the
  82 server keys), so iOS/Android keys stay out.
- **Languages:** **20** — every project language except `ar`. `ar` is
  intentionally excluded: the server ships no `ar.json`, `ar` requests fall back
  to `en` (`mywater_server AL-I18N-ARABIC-UNTESTED`).
- **File structure:** **one file per language** (`locale/%LANG_ISO%.json`).
  `es` is exported as `es_ES.json` via a per-platform filename mapping on the
  `web` target (the corpus language code stays `es`; iOS/Android exports are
  unaffected); `pt_BR` / `zh_CN` already match. Do not rename server files.
- **Include description:** **off** (no `notes` on the server).
- **Empty translations:** **Replace with base language** — untranslated keys
  export the English value, never an empty `""` (an empty string would clobber
  the English fallback in `LocalizationService::loadMergedPack` and surface as
  blank text).
- **Placeholder format:** **Printf**. Server strings have no placeholders today;
  if one is ever introduced it is printf (PHP `sprintf`), never i18next `{{…}}` /
  ICU `{…}`.
- **Convert all `[%]` to `%%`:** **off** — server strings are not run through
  `sprintf`, so a literal `%` must stay `%` (this is an iOS-only printf escape).
- **Indentation:** 4 spaces.
- **Add new line at EOF:** **on** — the committed `resources/locale/*.json` end
  with a trailing newline; without this every file diffs by one line and trips a
  final-newline lint.
- **Release bar (server):** a production release needs every key translated in all 20 exported locales (`ar` excluded — falls back to `en`); the general `unverified` / pre-release rule is in § Common to all platforms.
