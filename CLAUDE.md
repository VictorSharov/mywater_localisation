# mywater_localisation — agent instructions (`AGENTS.md` / `CLAUDE.md`)

Cross-platform localization **source-of-truth corpus + tooling** for MyWater
(iOS / Android / server). Setup, the full script table, and human commands are in
[`README.md`](README.md); this file is the agent contract.

Ты коллаборатор, не исполнитель. Не заявляй об успехе без проверки.

## Pipeline (read this first)

```
Lokalise ─(loc_corpus_ndjson.py)→ strings.ndjson ←─ agents read for dedup / audit
   ▲                                   │ apply scripts write edits INTO the corpus
   └─(loc_corpus_import.py --apply)─────┘
strings.ndjson + Lokalise ─export→ iOS .strings / Android .xml / server JSON
```

- `strings.ndjson` is a regenerable snapshot of **every** key, platform and
  language. It exists so an agent can decide "reuse an existing key (add the
  missing platform) vs create a new one" and audit translations without the
  per-platform blind spot the native files had.
- This repo never writes platform files. Edits land in the corpus, are reviewed
  as a `git diff`, imported into Lokalise, then Lokalise exports to each platform.

## Critical rules

- **[CR-CORPUS-OWNER] One serializer.** `loc_corpus.py` owns corpus read/write.
  Never hand-edit `strings.ndjson` formatting or re-serialize it another way —
  go through `loc_corpus.write_records` (or an apply script). A round-trip
  read→write must be byte-identical (deterministic diff). Field order, sorted
  `t`, sorted `unverified`, lean omission, compact separators are part of the
  contract.
- **[CR-CORPUS-UNVERIFIED] Edited ⇒ unverified.** `set_translation` flags an
  edited target language `unverified` (the corpus analog of the iOS `|R|`
  marker's "AI/edited translation not yet human-verified" signal). Do **not**
  clear `unverified` for AI-produced translations — that is a separate
  operator-/Lokalise-gated action. Filling, correcting, or re-translating keeps
  the language `unverified`.
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
  key already used on Android can be reused for iOS by adding the platform in
  Lokalise — not a duplicate.
- **Apply scripts are stdlib-only and token-free** (`loc_audit_apply`,
  `loc_apply_lang`, `loc_r_marked_translations apply`). They mutate
  `strings.ndjson` in place; replace-only (an unknown key is reported, not
  appended). Plural keys are CLDR-forms maps in `t`; flat-string apply paths skip
  them.
- **New source strings** are added to the corpus directly (visible to every
  platform) and created in Lokalise by `loc_corpus_import` (records without a
  `key_id` → create). Do not add new keys via the audit-findings path.

## Self-translation discipline

Same scoped rule as iOS: do **not** self-translate as a side effect of unrelated
work. When the operator explicitly asks for a translation pass (or the task *is*
translation), translate per-key with per-key reasoning, keep the language
`unverified`, and follow the linguistic discipline. Batch fan-out without per-key
reasoning is an anti-pattern (caught by the audit as `awkward` / `calque` /
`semantic-drift`).

## Canonical linguistic rules live in iOS docs

Brand voice, register (T-/V-form), RU→EN reverse-calque, punctuation, em-dash and
the per-language calibration are canonical in:

- `mywater_ios docs/LOCALIZATION.md § Translation discipline` (cross-repo);
- `loc_audit_prompt.md` (this repo) + `loc_audit_lang_calibration/<lang>.md`.

Do not fork these rules here — reference them.

## Verification

- `python3 -m py_compile <changed>.py` for any touched script.
- After a `loc_corpus.py` change: round-trip the corpus and assert byte-identical
  (`read_records` → `write_records` → `diff`).
- After an apply: `git diff -- strings.ndjson` should touch only the edited keys.
- `loc_corpus_import.py` / `lokalise_helper.py` dry-run is the agent-runnable
  evidence; `--apply` is operator-run ([CR-ACCESS]).
- Report what ran and what was deferred to the operator; never report `--apply`
  success you did not observe.
