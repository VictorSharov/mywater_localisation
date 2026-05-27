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
  edited target language `unverified`. This is the corpus end of one
  cross-platform "AI/edited translation not yet human-verified" marker, and this
  rule is its **canonical owner** — the three consuming repos thin-link here
  instead of re-explaining it:
    - corpus `strings.ndjson` — the `unverified` field (this repo);
    - iOS `.strings` — the `|R|` prefix on a fresh `en.lproj` source
      (`mywater_ios docs/LOCALIZATION.md`);
    - server `resources/locale/*.json` — the `|R|` tag at the start of an
      entry's `notes` (`mywater_server resources/locale/CLAUDE.md`).
  All three mean the same thing and clear the same way: do **not** clear
  `unverified` / strip `|R|` for AI-produced translations — that is a separate
  operator-/Lokalise-gated action. Filling, correcting, or re-translating keeps
  the marker set. The **source** language is the exception: it is never
  `unverified` (dev source of truth, not a review target) — it is pushed
  verified.
- **[CR-CORPUS-DIRTY] Push iff locally edited — `dirty`, not `unverified`.**
  `unverified` is *review state* and does **not** drive the push: pushing is not
  verifying, so a pushed translation stays `unverified` (and `|R|`) until a human
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
mechanics (iOS `.strings` / `|R|` / `R.swift`, server `notes`) stay in those platform
docs; this canon owns *style and meaning* only.

## Verification

- `python3 -m py_compile <changed>.py` for any touched script.
- After a `loc_corpus.py` change: round-trip the corpus and assert byte-identical
  (`read_records` → `write_records` → `diff`).
- After an apply: `git diff -- strings.ndjson` should touch only the edited keys.
- After editing values: `python3 loc_placeholder_lint.py` (token-free) — no new
  placeholder errors ([CR-PLACEHOLDER]). It also runs as a pre-flight in
  `loc_corpus_import`; `--no-lint` overrides.
- After editing values: `python3 loc_qa.py` (token-free) — value hygiene:
  em-dash U+2014 ban + invisible/zero-width spaces (ERROR), `()` balance + edge/
  double whitespace + cross-language URL parity (WARN). Lints `t` values only,
  never `context`. 2nd pre-flight in
  `loc_corpus_import` (shares `--no-lint`). Enforces the em-dash ban of
  `TRANSLATION_STYLE.md § Punctuation`; the linguistic layer (calque / register /
  drift) stays with the audit sub-agent, not this gate.
- `loc_corpus_import.py` / `lokalise_helper.py` dry-run is the agent-runnable
  evidence; `--apply` is operator-run ([CR-ACCESS]).
- Report what ran and what was deferred to the operator; never report `--apply`
  success you did not observe.
