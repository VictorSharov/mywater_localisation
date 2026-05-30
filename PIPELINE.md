<!--
doc-role: canonical
doc-owner: PIPELINE.md (mywater_localisation repo)
doc-scope: corpus mechanics — the full bodies of CLAUDE.md's [CR-CORPUS-*] / [CR-KEY-NAME] rules (serialization, concurrency & worktree safety, review state, dirty / dirty_meta push, source-change flow, key names) + the parallel-translation-pass procedure. Pipeline diagram → CLAUDE.md § Pipeline; linguistic canon → TRANSLATION_STYLE.md; export settings → EXPORT.md.
-->

# Pipeline & corpus mechanics

Owner doc for the corpus machinery. `CLAUDE.md § Critical rules` states each
`[CR-*]` rule tersely and links here for the full mechanics, recovery procedures and
rationale — the `[CR-*]` IDs are the shared anchors (so a cross-repo link to
`CLAUDE.md § [CR-...]` lands on the contract statement, and this doc carries the depth).

- Pipeline overview / diagram — `CLAUDE.md § Pipeline`.
- Linguistic style / brand voice / placeholders canon — [`TRANSLATION_STYLE.md`](TRANSLATION_STYLE.md).
- Lokalise → platform export settings — `EXPORT.md`.

**Read this before any task that *writes* the corpus** — apply scripts, translation
fan-in, metadata edits, an `en` source change.

## [CR-CORPUS-OWNER] One serializer

`loc_corpus.py` owns corpus read/write. Never hand-edit `strings.ndjson` formatting or
re-serialize it another way — go through `loc_corpus.write_records` (or an apply script).
A round-trip read→write must be byte-identical (deterministic diff). Field order, sorted
`t`, sorted `unverified`, lean omission, compact separators are part of the contract.

## [CR-CORPUS-CONCURRENCY] Whole-file, unsynchronized writes — fan out generation, serialize applies

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

## [CR-CORPUS-WORKTREE] Worktree safety & recovery — never destroy uncommitted corpus edits

The working tree is shared state. Because parallel agents emit per-language artifacts
(`/tmp/loc_<lang>.json`) and apply them as **uncommitted edits** to `strings.ndjson` in
the *same working tree* ([CR-CORPUS-CONCURRENCY], § Parallel translation passes), the
working-tree contents of `strings.ndjson` are someone else's in-flight work — not your
private scratchpad. Destructive git operations on the corpus are therefore equivalent to
a clobbering apply and produce the same silent loss of translations as the
concurrent-write race in [CR-CORPUS-CONCURRENCY]: `git checkout strings.ndjson`,
`git restore strings.ndjson`, `git reset --hard`, `git stash push -- strings.ndjson`
followed by drop, `git clean -fd` — all wipe uncommitted edits and emit *no error*.
Reflog tracks commits, not working-tree edits; `git fsck --lost-found` tracks
orphaned blobs in the objects DB, but uncommitted modifications never enter it.
So once those edits are gone they are **unrecoverable through git** — only the
per-language `/tmp/loc_<lang>.json` artifacts (if the originating agent saved
them) and the local pre-write snapshots in `.loc_backup/` (rotated, last
`loc_corpus.SNAPSHOT_RETAIN` writes; gitignored) can restore the prior state.
Recovery: `cp .loc_backup/strings.ndjson.<ts> strings.ndjson`. Snapshots are
written automatically by `loc_corpus.write_records` before every mutation of
the live corpus; tests against `--corpus /tmp/test.ndjson` stay snapshot-free.

- **Always assume `strings.ndjson` may carry someone else's pending work.** Run
  `git diff --stat strings.ndjson` before any operation that could overwrite it,
  and treat a non-empty diff as a hold signal — confirm with the operator before
  proceeding. A clean diff is the only safe precondition for a `git checkout` /
  `git restore` / `git reset` on the corpus.
- **Test apply scripts against a copy via `--corpus`, never against the live corpus
  followed by a revert.** Every apply script (`loc_apply_lang.py`,
  `loc_audit_apply.py`, etc.) accepts `--corpus <path>` specifically so dev /
  debugging runs leave the working tree untouched. Recipe:
  ```
  cp strings.ndjson /tmp/test_corpus.ndjson
  python3 loc_apply_lang.py <lang> /tmp/test.json --corpus /tmp/test_corpus.ndjson
  diff strings.ndjson /tmp/test_corpus.ndjson    # inspect freely; live corpus untouched
  ```
  Pattern to avoid: applying to the live corpus and then `git checkout strings.ndjson`
  to "undo" — that revert also wipes any uncommitted parallel-agent work that was
  sitting in the working tree before the test apply.

## [CR-CORPUS-UNVERIFIED] Review state — edited ⇒ unverified; untranslated ⇒ empty + unverified

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

## [CR-CORPUS-DIRTY] Push iff locally edited — `dirty`, not `unverified`

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

## [CR-CORPUS-META] Key metadata is corpus-owned too — `dirty_meta`

The corpus is the source of truth not only for translation values but for three key-level
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

## [CR-CORPUS-SOURCE-CHANGE] An `en` source edit obsoletes that key's translations; re-author `ru` in the same edit

When you change a key's `en` value in a way that changes meaning, every existing
target translation now renders the *old* English and is stale. Do not leave stale
targets silently. In the same edit:
  - **Re-author `ru` immediately.** `ru` is the co-source kept in parity with `en`
    (the team is ru-native; `ru` is the audit anchor), not an ordinary target. Write a
    real translation of the new wording via `set_translation` / `loc_apply_lang`; it
    stays `unverified` until human review (it is a target, not the source). This
    `ru`-now step is the one carve-out to `CLAUDE.md § Self-translation discipline`.
  - **Blank every other target** you are not re-authoring right now by setting it to
    `""` (empty is a valid Lokalise value — present-but-blank). An emptied target is
    `dirty` (the importer pushes it, so Lokalise shows the string as untranslated) and
    `unverified`; that empty-+-`unverified` **target** state is the canonical
    cross-platform "needs (re)translation" marker ([CR-CORPUS-UNVERIFIED]) — carried by
    the target, never by the source — and the release gate blocks on it. Re-author one
    of these other languages only when the operator explicitly asks (`CLAUDE.md § Self-translation discipline`).
The `en` source itself stays verified: **never** mark `en` `unverified` or blank it;
its `dirty:[en]` flag already means "source changed, push pending". Net: an `en` change
can never ship old wording under new English — `ru` is always freshly re-authored, and
every other target is either re-authored (`unverified`) or blanked (untranslated). A
meaning-preserving `en` fix (typo, casing, punctuation) does not obsolete the
translations and does not require blanking or re-authoring `ru`.

## [CR-KEY-NAME] Keys are valid-everywhere identifiers

A key name must match the Android-strict grammar `[A-Za-z][A-Za-z0-9_]*` — lead with an
ASCII letter; letters, digits, underscore only; no space / `.` / `%` / `-` / leading
digit. Android resource names are the strict floor (they become `R.string` fields); iOS
`.strings` / R.swift and server JSON are laxer. A violating name is **silently sanitized
per platform** — by Lokalise on Android export (space → `_`, leading `[0-9%]` stripped,
`.` kept) and by R.swift on iOS *independently* — so one `key_id` ends up with a
different effective name per platform (drift) and the corpus `key` stops matching the
shipped resource name. Namespace with `_`, not `.` (`apphud_offer_trial_extend`, not
`apphud.offer.trial_extend`): a dotted name can never be an `R.string` field (only
`getIdentifier(name)` by string) and survives Android export only by luck. Renaming an
existing key to the canonical form is Lokalise-side — `lokalise_helper.py rename-keys
--map-file <{key_id,new_name}[]>` (sets one global `key_name`, `key_id` preserved), then
regenerate; the corpus has no rename op and apply scripts are replace-only
([CR-CORPUS-OWNER]).

## Parallel translation passes (fan-out / fan-in)

A multi-language translation pass parallelizes safely as fan-out / fan-in — never as
concurrent corpus writes ([CR-CORPUS-CONCURRENCY]):

1. **Fan-out — parallel, read-only.** One agent per language. Each reads the corpus
   (directly, or via `loc_merge_languages.py <lang>`, which writes a read-only
   side-by-side `/tmp/loc_merge_*.txt` whose path is keyed by the language set, so
   parallel runs never collide) and emits **its own** artifact: a `{key: value}` JSON
   for that language — the input `loc_apply_lang` expects — e.g. `/tmp/loc_<lang>.json`.
   No agent touches `strings.ndjson`. Translate per-key with per-key reasoning and the
   linguistic discipline (`CLAUDE.md § Self-translation discipline`); fan-out parallelizes the
   *languages*, it does not license batch fan-out without per-key reasoning.
2. **Fan-in — sequential, single writer.** Apply the artifacts one at a time —
   `loc_apply_lang.py <lang> /tmp/loc_<lang>.json` per language (or `make apply
   LANGS="…"`, which loops them in one process), **never two at once**. Each run is
   sub-second, touches only its `t[lang]`, and flags that language `unverified`
   ([CR-CORPUS-UNVERIFIED]); disjoint languages + a deterministic writer make the order
   free and the cumulative `git diff` clean.
   - **"Single writer" is a serialization guarantee, not a per-agent diff check.** The
     only safe enforcement is that **one** process runs every apply in sequence — so the
     parallel fan-out agents (step 1) should **emit their `/tmp/loc_<lang>.json` and
     stop**, and let the operator drain them with a single `make apply LANGS="…"` run. A
     fan-out agent applying its own language autonomously is safe **only if it is
     demonstrably the sole writer at that instant**, which a clean `git diff --stat
     strings.ndjson` does **not** establish: that check guards [CR-CORPUS-WORKTREE]
     (don't bury someone's already-unsaved edits) but is **not a lock** — it cannot stop
     another agent's `read→mutate→write` from interleaving with yours *during* the apply,
     and two agents that both observe a clean diff and both apply will still lose-update
     ([CR-CORPUS-CONCURRENCY]). When unsure: emit and defer.
3. **Review & push.** `make diff`, then the token-holding operator runs `make push`
   ([CR-ACCESS], [CR-MAKE]).

Never: let an agent write the corpus directly (race + [CR-CORPUS-OWNER]); run two
applies concurrently; regenerate (`loc_corpus_ndjson.py`) mid-pass — it overwrites
the corpus from Lokalise and discards every un-imported edit; or run a destructive
git operation on `strings.ndjson` (`git checkout` / `git restore` / `git reset --hard` /
`git stash` + drop / `git clean`) — uncommitted edits in the working tree are
someone else's in-flight fan-in and a revert wipes them silently and unrecoverably
([CR-CORPUS-WORKTREE]). For dev / debugging always run apply scripts against a
copy via `--corpus /tmp/test_corpus.ndjson`, not against the live corpus.
