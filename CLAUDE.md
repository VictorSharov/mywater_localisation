# mywater_localisation — agent instructions (`AGENTS.md` / `CLAUDE.md`)

Cross-platform localization **source-of-truth corpus + tooling** for MyWater
(iOS / Android / server). Setup, the full script table, and human commands are in
[`README.md`](README.md); this file is the agent contract.

Ты коллаборатор, не исполнитель. Не заявляй об успехе без проверки.

**Project knowledge belongs in the repo, not in private agent memory.** Several
developers work here, and an agent's private / session memory is per-developer —
it is never shared, so another contributor's agent does not see it. Keep all
durable project knowledge (pipeline state, Lokalise export settings, placeholder /
translation conventions, gotchas, decisions) in the tracked docs — this file,
[`README.md`](README.md), [`TRANSLATION_STYLE.md`](TRANSLATION_STYLE.md) — or the
relevant script docstring, and review it as a git diff. Reserve private memory for
personal working preferences only; never let correctness-relevant project
knowledge live only in memory.

**Scratch stays out of the working tree.** Probes, debug dumps, one-off analysis
output and any other throwaway files go in `/tmp` (the tooling already does this —
`/tmp/loc_<lang>.json`, `/tmp/loc_merge_*.txt`), never the repo root. Clean up
anything you create. The working tree must stay clean so a corpus edit reads as a
reviewable `git diff` and untracked junk never masks a real change — the whole
pipeline is diff-review based. Don't lean on `.gitignore` to hide scratch (a broad
ignore pattern would also hide real files).

## Pipeline (read this first)

```
Lokalise ─(loc_corpus_ndjson.py)→ strings.ndjson ←─ agents read for dedup / audit
   ▲                                   │ apply scripts write edits INTO the corpus
   └─(loc_corpus_import.py --apply)─────┘
strings.ndjson + Lokalise ─(loc_export.py --apply)→ iOS .strings / Android .xml / server JSON
```

- `strings.ndjson` is a regenerable snapshot of **every** key, platform and
  language. It exists so an agent can decide "reuse an existing key (add the
  missing platform) vs create a new one" and audit translations without the
  per-platform blind spot the native files had.
- This repo's own tree never holds platform files. Edits land in the corpus, are
  reviewed as a `git diff`, imported into Lokalise; the Lokalise→platform export is
  then scripted by `loc_export.py`, which downloads each platform's bundle straight
  into *its* repo (iOS / Android / server) with the validated export settings baked
  in — the corpus repo still contains only `strings.ndjson`, not the native files.

## Critical rules

- **[CR-CORPUS-OWNER] One serializer.** `loc_corpus.py` owns corpus read/write.
  Never hand-edit `strings.ndjson` formatting or re-serialize it another way —
  go through `loc_corpus.write_records` (or an apply script). A round-trip
  read→write must be byte-identical (deterministic diff). Field order, sorted
  `t`, sorted `unverified`, lean omission, compact separators are part of the
  contract.
- **[CR-CORPUS-CONCURRENCY] Corpus writes are whole-file and unsynchronized — fan out generation, serialize applies.**
  `write_records` rewrites the *entire* `strings.ndjson` from an in-memory snapshot
  (`open("w")`, buffered, no lock, no atomic rename) and every apply script is
  read-all → mutate → write-all ([CR-CORPUS-OWNER]). So two apply processes on the
  same corpus race: the slower one's write silently clobbers the faster one's edits
  (lost update — no error, clean diff, translations just gone), and interleaved buffer
  flushes can emit a broken NDJSON line. Reads are safe for any number of readers.
  Therefore the **translation reasoning** (read corpus → emit a per-language
  `{key:value}` JSON) fans out across agents freely, but the **apply** step
  (`loc_apply_lang` / `loc_audit_apply`, which write the corpus) runs **one at a time**.
  Each language is a disjoint `t[lang]` and the writer is deterministic, so sequential
  applies compose into one clean diff in any order. Recipe: § Parallel translation passes.
- **[CR-CORPUS-UNVERIFIED] Edited ⇒ unverified; untranslated ⇒ empty + unverified.**
  `set_translation` flags an edited target language `unverified`. This field is the
  **canonical, cross-platform owner** of the localization review state; the consuming
  repos thin-link here instead of re-explaining it. It carries two related signals:
    - **"AI/edited, not yet human-verified"** — a target holds a value but `unverified`
      is set. Corpus: the `unverified` field (this repo); Lokalise: the translation's
      *unverified* review state, which iOS / Android / server read back from there.
    - **"needs (re)translation"** — a target is **empty (`""`) and `unverified`**. An
      empty-but-present target is the cross-platform "untranslated" marker, and the
      release gate blocks on it.
  Both clear the same way: do **not** clear `unverified` for an AI-produced translation —
  that is a separate operator-/Lokalise-gated action (a human verifies it in Lokalise).
  Filling, correcting, or re-translating keeps `unverified` set. The **source** language
  (`en`) is the exception: it is never `unverified`, and never empty for a live key — it
  is the dev source of truth, not a review target, and is always pushed **verified**.
  - **Retired — the `|R|` source marker.** The old `|R|` prefix (iOS `en.lproj` value,
    server `notes` tag) is no longer the marker: it tagged the *source*, which is always
    verified anyway — a mismatch. The signal now lives only on the **targets** (empty +
    `unverified`), never on `en`. The `|R|` validation lints (iOS `localization_lint.py`,
    server doc-sync Check 39) and the dead iOS runtime strip have been removed.
- **[CR-CORPUS-DIRTY] Push iff locally edited — `dirty`, not `unverified`.**
  `unverified` is *review state* and does **not** drive the push: pushing is not
  verifying, so a pushed translation stays `unverified` until a human
  reviews it in Lokalise. The push signal is a separate `dirty` set — on a value
  change `set_translation` adds the language (source **or** target) to `dirty`,
  and `loc_corpus_import`'s default scope pushes exactly the `dirty` languages
  (source as **verified**, targets as **unverified**). A successful `--apply`
  clears the pushed languages from `dirty` (the importer writes the corpus back
  through `loc_corpus.write_records`), so re-running is a no-op rather than a
  re-push, and a verified Lokalise translation is never clobbered by a stale
  snapshot of a language nobody edited. A regenerate rebuilds from Lokalise and
  never emits `dirty`, so it self-clears. Net: a local edit (fixing the `en`
  wording, or a target translation) propagates on the next plain
  `loc_corpus_import --apply`, then drains — not silently dropped, not endlessly
  re-sent.
- **[CR-CORPUS-META] Key metadata is corpus-owned too — `dirty_meta`.** The corpus
  is the source of truth not only for translation values but for three key-level
  fields: `platforms`, the translator description (corpus field `context`), and
  per-platform export-file routing (`filenames`). Edit them through
  `loc_apply_meta.py` (token-free) or `loc_corpus.set_platforms` / `set_context` /
  `set_filename` — never hand-edit ([CR-CORPUS-OWNER]). A change adds the field to a
  key-level `dirty_meta` set (the metadata analog of `dirty`), and
  `loc_corpus_import` pushes those fields via the **keys endpoint** (`update_key`),
  separate from the per-translation endpoint: `platforms` as a full-array replace
  (so add/remove a platform = the resulting set), corpus `context` → the Lokalise
  **`description`** field (this project's translator-notes field), and `filenames` →
  the Lokalise **`filenames`** object as a full per-platform replace (the iOS slot
  decides `InfoPlist.strings` vs the default `Localizable.strings`; an unset slot
  exports to the default bundle — so the corpus map is authoritative). A successful
  `--apply` clears the pushed fields from `dirty_meta` (re-run is a no-op); a
  regenerate never emits it (self-clears) and reads `description` + `filenames` back
  first so a pushed value round-trips. Metadata has **no** review state — unlike a
  translation it is never `unverified`. Naming a key (`--key`) re-pushes its
  platforms + any existing description + any existing filenames regardless of
  `dirty_meta`; to *clear* a description / routing use `loc_apply_meta
  --clear-description` / `--clear-filename` (the dirty path pushes an empty value).
  Because the push is a full replace, run `loc_corpus_import` against a freshly
  regenerated corpus the first time, so any pre-existing Lokalise `filenames` slot
  is captured before it could be overwritten with an empty.
- **[CR-CORPUS-SOURCE-CHANGE] An `en` source edit obsoletes that key's translations; re-author `ru` in the same edit.**
  When you change a key's `en` value in a way that changes meaning, every existing
  target translation now renders the *old* English and is stale. Do not leave stale
  targets silently. In the same edit:
    - **Re-author `ru` immediately.** `ru` is the co-source kept in parity with `en`
      (the team is ru-native; `ru` is the audit anchor), not an ordinary target. Write a
      real translation of the new wording via `set_translation` / `loc_apply_lang`; it
      stays `unverified` until human review (it is a target, not the source). This
      `ru`-now step is the one carve-out to § Self-translation discipline.
    - **Blank every other target** you are not re-authoring right now by setting it to
      `""` (empty is a valid Lokalise value — present-but-blank). An emptied target is
      `dirty` (the importer pushes it, so Lokalise shows the string as untranslated) and
      `unverified`; that empty-+-`unverified` **target** state is the canonical
      cross-platform "needs (re)translation" marker ([CR-CORPUS-UNVERIFIED]) — carried by
      the target, never by the source — and the release gate blocks on it. Re-author one
      of these other languages only when the operator explicitly asks (§ Self-translation
      discipline).
  The `en` source itself stays verified: **never** mark `en` `unverified` or blank it;
  its `dirty:[en]` flag already means "source changed, push pending". Net: an `en` change
  can never ship old wording under new English — `ru` is always freshly re-authored, and
  every other target is either re-authored (`unverified`) or blanked (untranslated). A
  meaning-preserving `en` fix (typo, casing, punctuation) does not obsolete the
  translations and does not require blanking or re-authoring `ru`.
- **[CR-PLACEHOLDER] Universal placeholders.** Corpus values store **Lokalise
  universal placeholders** (`[%s]` / `[%i]` / `[%.1f]` / `[%1$s]`), never bare
  `%@` / `%d` / `%s`. Lokalise converts universal → platform on export; the
  reverse (platform → universal) happens ONLY on file upload, so the keys-API
  import (`loc_corpus_import`) stores a bare placeholder literally and it
  mis-exports. Literal percent is the universal `[%]`; Lokalise escapes it per
  platform on export (`→ %%` for printf/iOS, `→ %` standalone), and the iOS bundle
  pins "Convert all [%]→%%" on so even a standalone `[%]` is safe under R.swift
  `String(format:)`. Do **not** store a bare `%%` (an iOS-only printf escape the
  keys-API stores literally → leaks `%%` to Android/server consumers that don't
  format) or a lone `%` in a runtime value. iOS `.stringsdict` `%#@var@` has no
  universal form → such a key
  must be a Lokalise plural. Canonical: `TRANSLATION_STYLE.md § Placeholders`;
  `loc_placeholder_lint.py` enforces it (also a pre-flight in `loc_corpus_import`).
- **[CR-KEY-NAME] Keys are valid-everywhere identifiers.** A key name must match the
  Android-strict grammar `[A-Za-z][A-Za-z0-9_]*` — lead with an ASCII letter; letters,
  digits, underscore only; no space / `.` / `%` / `-` / leading digit. Android resource
  names are the strict floor (they become `R.string` fields); iOS `.strings` / R.swift and
  server JSON are laxer. A violating name is **silently sanitized per platform** — by
  Lokalise on Android export (space → `_`, leading `[0-9%]` stripped, `.` kept) and by
  R.swift on iOS *independently* — so one `key_id` ends up with a different effective name
  per platform (drift) and the corpus `key` stops matching the shipped resource name.
  Namespace with `_`, not `.` (`apphud_offer_trial_extend`, not `apphud.offer.trial_extend`):
  a dotted name can never be an `R.string` field (only `getIdentifier(name)` by string) and
  survives Android export only by luck. Renaming an existing key to the canonical form is
  Lokalise-side — `lokalise_helper.py rename-keys --map-file <{key_id,new_name}[]>` (sets one
  global `key_name`, `key_id` preserved), then regenerate; the corpus has no rename op and
  apply scripts are replace-only ([CR-CORPUS-OWNER]).
- **[CR-SECRETS] Token discipline.** `LOKALISE_API_TOKEN` only via env, never as
  a CLI arg, and never printed to chat / logs / docs. Mutating commands
  (`loc_corpus_import`, `lokalise_helper`, unused tagging) are **dry-run by
  default**; `--apply` mutates Lokalise.
- **[CR-ACCESS] No silent API claims.** An agent without the token cannot run
  `--apply` against Lokalise — produce the dry-run plan and stop; the operator
  runs `--apply`. Do not claim a push happened without evidence.
- **Import before regenerate.** `loc_corpus_ndjson.py` overwrites `strings.ndjson`
  from Lokalise. If the corpus has un-imported edits, regenerating discards them.
  Order: edit → review diff → `loc_corpus_import --apply` → (later) regenerate.

## Working on the corpus

- **Reuse / audit are corpus-wide.** Search `strings.ndjson` (flat `en` via
  `rg` / `jq`) before introducing a key. The corpus carries `platforms`, so a
  key already used on Android can be reused for iOS by adding the platform to its
  record (`loc_apply_meta --key … --add-platform ios`) and pushing
  ([CR-CORPUS-META]) — not a duplicate.
- **Apply scripts are stdlib-only and token-free** (`loc_audit_apply`,
  `loc_apply_lang`, `loc_apply_meta`, `loc_r_marked_translations apply`). They
  mutate `strings.ndjson` in place; replace-only (an unknown key is reported, not
  appended). Plural keys are CLDR-forms maps in `t`; flat-string apply paths skip
  them. `loc_apply_meta` edits key metadata (platforms / description) rather than
  translation values ([CR-CORPUS-META]).
- **New source strings / new keys** — see `§ Adding a new key (every platform)`
  below for the full flow.

## Adding a new key (every platform)

Canonical cross-platform flow for introducing a new string — iOS, Android and
server all follow it; each platform doc thin-links here and adds only its own
*encoding* mechanics, not a forked copy. One principle: **a word is born in the
corpus; the platform repo carries only a throwaway, source-language-only compile
scaffold; the Lokalise export reconciles it and fans out every language.** No
platform re-implements placeholder or plural conversion — Lokalise owns that on
export ([CR-PLACEHOLDER]).

1. **Reuse-search first** (corpus-wide) — `rg` / `jq` the flat `en` in
   `strings.ndjson`. A key already on another platform is reused by adding the
   missing platform to its record (`loc_apply_meta --add-platform`, pushed via
   [CR-CORPUS-META]), never duplicated.
2. **Add the source to the corpus**, through `loc_corpus.write_records` (or a thin
   constructor) — never hand-edit the ndjson ([CR-CORPUS-OWNER]). One new record:
   `key` (a valid-everywhere identifier — [CR-KEY-NAME]), `platforms` (the consuming
   platforms), `t.en`, **and `t.ru`** — author the Russian immediately (`ru` is the
   co-source kept in parity with `en`; [CR-CORPUS-SOURCE-CHANGE]). Every other target
   stays **empty (`""`) + `unverified`** — the canonical "needs translation" state
   ([CR-CORPUS-UNVERIFIED]); it fills later via a translation pass / Lokalise. (`ru`
   is also `unverified` until human review; `en` is verified.) For a key that must
   export to a non-default file — an iOS Info.plist key (permission
   `NS*UsageDescription`, `CFBundle*`, home-screen quick-action title) — also set its
   routing with `loc_apply_meta --key <name> --set-filename InfoPlist.strings` (corpus
   field `filenames`, [CR-CORPUS-META]); without it the key exports to
   `Localizable.strings` and the localized Info.plist value never takes effect.
   - Non-plural: `t.en` is a string in **universal placeholders** (`[%s]` / `[%i]`
     / `[%.1f]` / `[%]`), never a bare `%@` / `%d` / `%s`. Author the universal form
     directly — there is no "convert from a platform string" step, so there is no
     converter to get wrong.
   - Plural: `t.en` is a CLDR-forms map (`{"one":…,"other":…}`) so the key is a
     Lokalise plural. Do **not** hand-write any platform's native plural file.
   - Review `git diff -- strings.ndjson`; `loc_placeholder_lint.py` + `loc_qa.py`
     (token-free, also pre-flights in `loc_corpus_import`) catch placeholder /
     hygiene mistakes before import.
3. **Compile scaffold — platform-specific, source-language-only, throwaway.** So
   platform code compiles and can be laid out before the round-trip, the platform
   repo adds the new key in its source-language file only; the export overwrites it
   later from the corpus. Encoding lives in each platform doc:
   - iOS — `en.lproj/Localizable.strings` line (native iOS placeholders, **no marker
     prefix** — the en source is clean); a plural adds one rule in
     `en.lproj/Localizable.stringsdict`. `mywater_ios docs/LOCALIZATION.md § Rules for AI`.
   - Android / server — wire up the encoding when those platforms adopt this flow.
   Source-language-only by design: a platform's other-language files must not be
   hand-filled — `ru` and the rest live in the corpus (`ru` translated, the others
   empty + `unverified`), and the export produces every language correctly.
4. **Round-trip — operator (token holder).** `loc_corpus_import.py --apply` creates
   the key in Lokalise (records without `key_id` → create) and stamps the new
   `key_id` back into the corpus — **commit the corpus** so a re-run updates instead
   of re-creating. Then translate / verify (audit sub-agent), and the operator runs
   the per-platform export (`loc_export.py --apply`, README § Export from Lokalise)
   and commits the platform
   bundle, which replaces the scaffold and fans out every language. A new key (a new
   typed accessor) needs the platform's own release to appear; the export only
   updates values for keys already shipped.
5. **Translator-description for the new key** lives in the corpus `context` field
   and is pushed for you: a brand-new key carries it in the create payload, and a
   later edit (`loc_apply_meta --description`) propagates via `dirty_meta`
   ([CR-CORPUS-META]) to the Lokalise `description` field. The keys-API path still
   does not ingest a platform file's `/* … */` comment — that is only the iOS
   compile scaffold. (Lokalise also has a separate `context` field this pipeline
   does not manage; translator notes live in `description`.)

Do not add new keys via the audit-findings path — `loc_audit_apply` /
`loc_apply_lang` are replace-only (an unknown key is reported, not appended).

## Self-translation discipline

Same scoped rule as iOS: do **not** self-translate target languages as a side effect
of unrelated work. When the operator explicitly asks for a translation pass (or the
task *is* translation), translate per-key with per-key reasoning, keep the language
`unverified`, and follow the linguistic discipline. Batch fan-out without per-key
reasoning is an anti-pattern (caught by the audit as `awkward` / `calque` /
`semantic-drift`).

**One carve-out — `ru`.** `ru` is a co-source, not an ordinary target: whenever you
add or change an `en` source you re-author `ru` **immediately**, even as a side effect
of unrelated work ([CR-CORPUS-SOURCE-CHANGE], § Adding a new key). The discipline above
governs the other 19 targets — they stay empty (`""` + `unverified`) until an explicit
translation pass.

## Parallel translation passes (fan-out / fan-in)

A multi-language translation pass parallelizes safely as fan-out / fan-in — never as
concurrent corpus writes ([CR-CORPUS-CONCURRENCY]):

1. **Fan-out — parallel, read-only.** One agent per language. Each reads the corpus
   (directly, or via `loc_merge_languages.py <lang>`, which writes a read-only
   side-by-side `/tmp/loc_merge_*.txt` whose path is keyed by the language set, so
   parallel runs never collide) and emits **its own** artifact: a `{key: value}` JSON
   for that language — the input `loc_apply_lang` expects — e.g. `/tmp/loc_<lang>.json`.
   No agent touches `strings.ndjson`. Translate per-key with per-key reasoning and the
   linguistic discipline (§ Self-translation discipline); fan-out parallelizes the
   *languages*, it does not license batch fan-out without per-key reasoning.
2. **Fan-in — sequential, single writer.** Apply the artifacts one at a time —
   `loc_apply_lang.py <lang> /tmp/loc_<lang>.json` per language, **never two at once**.
   Each run is sub-second, touches only its `t[lang]`, and flags that language
   `unverified` ([CR-CORPUS-UNVERIFIED]); disjoint languages + a deterministic writer
   make the order free and the cumulative `git diff` clean.
3. **Review & push.** `git diff -- strings.ndjson`, then the token-holding operator
   runs `loc_corpus_import --apply` ([CR-ACCESS]).

Never: let an agent write the corpus directly (race + [CR-CORPUS-OWNER]); run two
applies concurrently; or regenerate (`loc_corpus_ndjson.py`) mid-pass — it overwrites
the corpus from Lokalise and discards every un-imported edit.

## Canonical linguistic rules live here

Brand voice, register (T-/V-form / honorific), RU→EN reverse-calque, punctuation,
em-dash, per-language specifics and the translator-context comment discipline are
canonical **in this repo** (moved out of iOS so server / Android agents need not
read iOS docs — the rules are cross-platform and live next to the corpus + tooling):

- [`TRANSLATION_STYLE.md`](TRANSLATION_STYLE.md) — the cross-platform style /
  linguistics canon (§ Translation discipline, § Brand voice, § Translator context);
- `loc_audit_prompt.md` **operationalizes** it (flag / skip / severity) verbatim for
  the audit sub-agent; `loc_audit_lang_calibration/<lang>.md` — per-language calibration.

Consumers thin-link here, do **not** fork: iOS `mywater_ios docs/LOCALIZATION.md`,
server `mywater_server resources/locale/CLAUDE.md`. Platform-specific *encoding*
mechanics (iOS `.strings` / `R.swift`, server flat JSON) stay in those platform
docs; this canon owns *style and meaning* only.

## Verification

- `python3 -m py_compile <changed>.py` for any touched script.
- After a `loc_corpus.py` change: round-trip the corpus and assert byte-identical
  (`read_records` → `write_records` → `diff`).
- After an apply: `git diff -- strings.ndjson` should touch only the edited keys.
- After an `en` meaning change: `git diff -- strings.ndjson` shows `ru` re-authored and
  every other target blanked to `""`, all flagged `dirty` + `unverified` (except `en`,
  which is `dirty` only — never `unverified`) ([CR-CORPUS-SOURCE-CHANGE]).
- After a metadata edit (`loc_apply_meta`): `git diff -- strings.ndjson` shows the
  changed `platforms` / `context` / `filenames` plus a `dirty_meta` marker on those
  keys; a `loc_corpus_import` dry-run lists them under "push metadata on N key(s)",
  and a successful `--apply` drains `dirty_meta` (a re-run plans 0) ([CR-CORPUS-META]).
- After editing values: `python3 loc_placeholder_lint.py` (token-free) — no new
  placeholder errors ([CR-PLACEHOLDER]). It also runs as a pre-flight in
  `loc_corpus_import`; `--no-lint` overrides.
- After editing values: `python3 loc_qa.py` (token-free) — value hygiene:
  em-dash U+2014 ban + invisible/zero-width spaces + Cyrillic in the `en` source
  (ERROR), `()` balance + edge/double whitespace + cross-language URL parity
  (WARN). The Cyrillic-in-source check catches a translation mis-filed into the
  `en` column (an AI agent leaving a Russian string in `en`), since `ru` is the
  only Cyrillic-script language. Lints `t` values only,
  never `context`. 2nd pre-flight in
  `loc_corpus_import` (shares `--no-lint`). Enforces the em-dash ban of
  `TRANSLATION_STYLE.md § Punctuation`; the linguistic layer (calque / register /
  drift) stays with the audit sub-agent, not this gate.
- `loc_corpus_import.py` / `lokalise_helper.py` dry-run is the agent-runnable
  evidence; `--apply` is operator-run ([CR-ACCESS]).
- Report what ran and what was deferred to the operator; never report `--apply`
  success you did not observe.
