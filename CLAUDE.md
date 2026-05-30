<!--
doc-role: canonical
doc-owner: CLAUDE.md (mywater_localisation repo) — the agent contract
doc-scope: agent contract + navigation — bootstrap, task / reverse routing, critical rules (terse [CR-*] anchors), corpus workflow, self-translation discipline, verification. Detailed corpus mechanics → PIPELINE.md; linguistic canon → TRANSLATION_STYLE.md; export settings → EXPORT.md.
-->

# mywater_localisation — agent instructions (`AGENTS.md` / `CLAUDE.md`)

Cross-platform localization **source-of-truth corpus + tooling** for MyWater
(iOS / Android / server). Setup, the full script table, and human commands are in
[`README.md`](README.md); the detailed corpus mechanics are in
[`PIPELINE.md`](PIPELINE.md); the linguistic canon is in
[`TRANSLATION_STYLE.md`](TRANSLATION_STYLE.md). This file is the agent contract.

Ты коллаборатор, не исполнитель. Не заявляй об успехе без проверки.

**Project knowledge belongs in the repo, not in private agent memory.** Several
developers work here, and an agent's private / session memory is per-developer —
it is never shared, so another contributor's agent does not see it. Keep all
durable project knowledge (pipeline state, Lokalise export settings, placeholder /
translation conventions, gotchas, decisions) in the tracked docs — this file,
[`README.md`](README.md), [`PIPELINE.md`](PIPELINE.md),
[`TRANSLATION_STYLE.md`](TRANSLATION_STYLE.md) — or the relevant script docstring,
and review it as a git diff. Reserve private memory for personal working
preferences only; never let correctness-relevant project knowledge live only in memory.

**Scratch stays out of the working tree.** Probes, debug dumps, one-off analysis
output and any other throwaway files go in `/tmp` (the tooling already does this —
`/tmp/loc_<lang>.json`, `/tmp/loc_merge_*.txt`), never the repo root. Clean up
anything you create. The working tree must stay clean so a corpus edit reads as a
reviewable `git diff` and untracked junk never masks a real change — the whole
pipeline is diff-review based. Don't lean on `.gitignore` to hide scratch (a broad
ignore pattern would also hide real files).

## Bootstrap — read order

1. **This file** — § Critical rules + § Task router (always); the rest by need.
2. **The owner doc for your task** — pick the row in § Task router below.
3. **[`PIPELINE.md`](PIPELINE.md)** before any task that *writes* the corpus (apply /
   fan-in / metadata / `en` source change). **[`TRANSLATION_STYLE.md`](TRANSLATION_STYLE.md)**
   before translating or editing any user-facing text.

Before any action that could touch the corpus, run `git diff --stat strings.ndjson` —
a non-empty diff is someone else's in-flight work and must be preserved ([CR-CORPUS-WORKTREE]).

## Task router (forward — "doing X → read first")

| Task | Read first | Tools (token-free unless noted) |
|---|---|---|
| Translate a language / fill the backlog | `TRANSLATION_STYLE.md` + § Self-translation discipline + `PIPELINE.md § Parallel translation passes` | `loc_r_marked_translations.py`, `loc_apply_lang.py`, `make apply` |
| Audit existing translations | `loc_audit_prompt.md` (+ `loc_audit_lang_calibration/<lang>.md` for ar/hi/vi/id/ms) | `loc_audit_extract.py`, `loc_audit_apply.py` |
| Add a new key | § Adding a new key (every platform) — reuse-search first | `loc_corpus_import.py` (operator `--apply`) |
| Edit key metadata (platforms / description / filenames) | [CR-CORPUS-META] → [`PIPELINE.md`](PIPELINE.md) | `loc_apply_meta.py` |
| Change an `en` source value | [CR-CORPUS-SOURCE-CHANGE] → [`PIPELINE.md`](PIPELINE.md) | `loc_apply_lang.py` |
| Write / apply the corpus, parallel passes, recovery | § Critical rules + [`PIPELINE.md`](PIPELINE.md) | apply scripts, `make apply` / `make diff` |
| Linguistic style / brand voice / register / placeholders | `TRANSLATION_STYLE.md` | `make lint` |
| Push edits to Lokalise | [CR-MAKE] / [CR-ACCESS] — operator-run | `make push` / `make push-dry` |
| Export Lokalise → platforms | `EXPORT.md` — operator-run | `make export` / `make export-dry` |
| Lint / verify an edit | § Verification | `make lint` |

## Reverse routing (changed X → also update Y)

| Changed | Update / re-verify |
|---|---|
| `loc_corpus.py` (the serializer) | Round-trip byte-identical test against a copy ([CR-CORPUS-OWNER], § Verification) |
| A rule in `TRANSLATION_STYLE.md § Brand voice` / discipline | Mirror its **operational** form into `loc_audit_prompt.md` — the sub-agent reads it verbatim with no doc access, so this duplication is intentional — and add a dated `§ Calibration changelog` entry |
| An export setting (Lokalise download) | `EXPORT.md` table + the matching profile in `loc_export.py` (keep in sync) |
| A `[CR-*]` rule's mechanics in `PIPELINE.md` | Keep the terse statement in § Critical rules in sync (same `[CR-*]` anchor) |

## Pipeline

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

Each rule below is the **contract statement** carrying its `[CR-*]` anchor (cross-repo
links resolve here). For the corpus-data rules, the full mechanics, recovery procedures
and rationale live in [`PIPELINE.md`](PIPELINE.md) under the same `[CR-*]` heading — keep
the two in sync.

- **[CR-CORPUS-OWNER] One serializer.** `loc_corpus.py` owns corpus read/write. Never
  hand-edit `strings.ndjson` formatting or re-serialize it another way — go through
  `loc_corpus.write_records` (or an apply script). A round-trip read→write must be
  byte-identical (deterministic diff). → mechanics & field-order contract:
  `PIPELINE.md § [CR-CORPUS-OWNER]`.
- **[CR-CORPUS-CONCURRENCY] Corpus writes are whole-file and unsynchronized — fan out
  generation, serialize applies.** Reads are safe for any number of readers, but two
  apply processes racing on the same corpus lose-update silently (the slower write
  clobbers the faster — no error, clean diff, translations just gone). Translation
  *reasoning* fans out across agents freely; the **apply** step (`loc_apply_lang` /
  `loc_audit_apply`) runs **one at a time**. → mechanics:
  `PIPELINE.md § [CR-CORPUS-CONCURRENCY]`.
- **[CR-CORPUS-WORKTREE] The working tree is shared state — never destroy uncommitted
  corpus edits.** Uncommitted `strings.ndjson` may be another agent's in-flight fan-in;
  destructive git ops (`git checkout` / `git restore` / `git reset --hard` /
  `git stash` + drop / `git clean`) wipe it silently and **unrecoverably** (reflog / fsck
  don't track working-tree edits). Run `git diff --stat strings.ndjson` first; test
  applies against a `--corpus` copy, never the live corpus + revert. → recovery & recipes:
  `PIPELINE.md § [CR-CORPUS-WORKTREE]`.
- **[CR-CORPUS-UNVERIFIED] Edited ⇒ unverified; untranslated ⇒ empty + unverified.**
  Canonical cross-platform owner of review state. A target with a value but `unverified`
  = AI/edited-not-yet-human-verified; empty (`""`) + `unverified` = needs (re)translation
  (release gate blocks). Do **not** clear `unverified` for an AI-produced translation —
  that is operator-/Lokalise-gated. The `en` source is never `unverified` and never empty.
  → mechanics + retired `|R|` marker: `PIPELINE.md § [CR-CORPUS-UNVERIFIED]`.
- **[CR-CORPUS-DIRTY] Push iff locally edited — `dirty`, not `unverified`.** A value
  change adds the language (source or target) to `dirty`; `loc_corpus_import` pushes
  exactly the `dirty` set (source verified, targets unverified) and a successful `--apply`
  drains it (re-run is a no-op). Pushing is not verifying — pushed targets stay
  `unverified`. → mechanics: `PIPELINE.md § [CR-CORPUS-DIRTY]`.
- **[CR-CORPUS-META] Key metadata is corpus-owned too — `dirty_meta`.** `platforms`, the
  translator description (corpus `context` → Lokalise `description`), and export routing
  (`filenames`) are edited via `loc_apply_meta.py` (never hand-edit), tracked in
  `dirty_meta`, and pushed via the keys endpoint as full replaces. Metadata has **no**
  review state. → mechanics: `PIPELINE.md § [CR-CORPUS-META]`.
- **[CR-CORPUS-SOURCE-CHANGE] An `en` meaning change obsoletes that key's translations;
  re-author `ru` in the same edit.** Re-author `ru` immediately (co-source kept in parity
  with `en`), and blank every other target to `""` (→ `dirty` + `unverified` =
  untranslated). `en` stays verified — never blank or `unverified` it. A meaning-preserving
  fix (typo / casing / punctuation) does not obsolete and needs no blanking. → mechanics:
  `PIPELINE.md § [CR-CORPUS-SOURCE-CHANGE]`.
- **[CR-PLACEHOLDER] Universal placeholders.** Corpus values store **Lokalise universal
  placeholders** (`[%s]` / `[%i]` / `[%.1f]` / `[%1$s]`), never bare `%@` / `%d` / `%s` —
  Lokalise converts universal → platform on export, but the keys-API import
  (`loc_corpus_import`) stores a bare placeholder literally and it mis-exports. Literal
  percent is the universal `[%]`; do **not** store a bare `%%` or a lone `%` in a runtime
  value. iOS `.stringsdict` `%#@var@` has no universal form → such a key must be a Lokalise
  plural. → canonical detail: `TRANSLATION_STYLE.md § Placeholders`; enforced by
  `loc_placeholder_lint.py` (also a pre-flight in `loc_corpus_import`).
- **[CR-KEY-NAME] Keys are valid-everywhere identifiers.** Match `[A-Za-z][A-Za-z0-9_]*` —
  ASCII letter lead; letters, digits, underscore only; no space / `.` / `%` / `-` /
  leading digit. Namespace with `_`, not `.`. A violating name is silently sanitized per
  platform → per-platform drift. Renaming is Lokalise-side
  (`lokalise_helper.py rename-keys`), then regenerate. → mechanics:
  `PIPELINE.md § [CR-KEY-NAME]`.
- **[CR-SECRETS] Token discipline.** `LOKALISE_API_TOKEN` only via env, never as
  a CLI arg, and never printed to chat / logs / docs. Mutating commands
  (`loc_corpus_import`, `lokalise_helper`, unused tagging) are **dry-run by
  default**; `--apply` mutates Lokalise.
- **[CR-ACCESS] No silent API claims.** An agent without the token cannot run
  `--apply` against Lokalise — produce the dry-run plan and stop; the operator
  runs `--apply`. Do not claim a push happened without evidence.
- **[CR-MAKE] Drive the pipeline through `make`, not raw scripts.** The `Makefile` is
  the operator entrypoint — it bakes in the validated flags, dry-run defaults and
  confirmation gates (e.g. `make pull` guards the destructive corpus overwrite), so
  routing through it keeps everyone on the guarded path. Therefore:
  - **Hand the operator a `make` target, never the raw script.** For the token-gated
    steps you cannot run yourself: `make push` (not `loc_corpus_import.py --apply`),
    `make push-dry`, `make pull`, `make export` / `make export-dry`. Pairs with
    [CR-ACCESS] — you produce the plan, the operator runs `make push`.
  - **For your own token-free runs, prefer the `make` target where one exists** —
    `make lint` (placeholder + qa in one), `make diff`, `make apply LANGS="<lang>"`
    (the serialized single-writer fan-in, `PIPELINE.md § Parallel translation passes`).
  - **No target ⇒ run the script directly** — extract / audit / metadata / merge
    (`loc_r_marked_translations.py` extract, `loc_audit_*`, `loc_apply_meta.py`,
    `loc_merge_languages.py`, `lokalise_helper.py`) have no wrapper; use them as
    documented (a mutating `--apply` is still operator-run, [CR-ACCESS]). `make help`
    is the registry of what's wrapped.
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
  appended). Plural keys are CLDR-forms maps in `t`: the audit findings-table path
  (`loc_audit_apply`) can't express CLDR in one cell so it skips them, but
  `loc_apply_lang` applies a plural key whose JSON value is a `{cldr_form: text}`
  map (a thin adapter over the same `apply_changes`, identical replace invariant) —
  not a hand-edit of `t`. `loc_apply_meta` edits key metadata (platforms / description) rather than
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
   the per-platform export (`loc_export.py --apply`, EXPORT.md)
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

Safe parallelization of an explicit multi-language pass (fan-out / fan-in, single
writer) — `PIPELINE.md § Parallel translation passes`.

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
- **Before any action that could touch the corpus:** `git diff --stat strings.ndjson`
  — a non-empty diff is someone else's in-flight fan-in and must be preserved
  ([CR-CORPUS-WORKTREE]). Apply-script smoke tests run against a copy via
  `--corpus /tmp/test_corpus.ndjson`, never against the live corpus followed by a
  `git checkout` revert.
- After a `loc_corpus.py` change: round-trip the corpus and assert byte-identical
  (`read_records` → `write_records` → `diff`) **against a copy** (e.g. write the
  round-trip into `/tmp/strings.ndjson.roundtrip` and `filecmp` against the live
  file) so the live working tree is never overwritten.
- After an apply: `git diff -- strings.ndjson` should touch only the edited keys.
- After an `en` meaning change: `git diff -- strings.ndjson` shows `ru` re-authored and
  every other target blanked to `""`, all flagged `dirty` + `unverified` (except `en`,
  which is `dirty` only — never `unverified`) ([CR-CORPUS-SOURCE-CHANGE]).
- After a metadata edit (`loc_apply_meta`): `git diff -- strings.ndjson` shows the
  changed `platforms` / `context` / `filenames` plus a `dirty_meta` marker on those
  keys; a `loc_corpus_import` dry-run lists them under "push metadata on N key(s)",
  and a successful `--apply` drains `dirty_meta` (a re-run plans 0) ([CR-CORPUS-META]).
- After editing values: **`make lint`** (token-free) — runs both value gates in one
  command (also pre-flighted inside `loc_corpus_import` / `make push`; `--no-lint`
  overrides):
    - **placeholder lint** (`loc_placeholder_lint.py`) — no new placeholder errors
      ([CR-PLACEHOLDER]).
    - **qa hygiene** (`loc_qa.py`) — em-dash U+2014 ban + invisible/zero-width spaces +
      Cyrillic in the `en` source (ERROR), `()` balance + edge/double whitespace +
      cross-language URL parity (WARN). The Cyrillic-in-source check catches a
      translation mis-filed into the `en` column (an AI agent leaving a Russian string
      in `en`), since `ru` is the only Cyrillic-script language. Lints `t` values only,
      never `context`. Enforces the em-dash ban of `TRANSLATION_STYLE.md § Punctuation`;
      the linguistic layer (calque / register / drift) stays with the audit sub-agent,
      not this gate.
- `make push-dry` (corpus-import dry-run) / `lokalise_helper.py` dry-run is the
  agent-runnable evidence; `make push` / the helper's `--apply` is operator-run
  ([CR-ACCESS], [CR-MAKE]).
- Report what ran and what was deferred to the operator; never report `--apply`
  success you did not observe.
