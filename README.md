<!--
doc-role: canonical
doc-owner: README.md (mywater_localisation repo) — human entrypoint
doc-scope: human setup + script table + common commands + consuming the corpus. Agent contract → CLAUDE.md; corpus mechanics → PIPELINE.md; Lokalise→platform export settings → EXPORT.md; linguistic canon → TRANSLATION_STYLE.md.
-->

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
strings.ndjson + Lokalise ──(loc_export.py --apply)──▶ iOS .strings / Android .xml / server JSON
```

- **Lokalise** is the long-term source of truth for verified translations.
- **`strings.ndjson`** is a regenerable, git-tracked snapshot of the whole project
  (all keys, all platforms, all languages) that AI sessions read. Consumers only
  pull / read it — the Lokalise token never touches a consumer session.
- Edits (audits, fresh translations, new source strings, and key metadata —
  **platforms** and **description**) are written back into the corpus, reviewed as
  a clean `git diff`, then imported into Lokalise. The Lokalise → platform export
  back out is scripted by **`loc_export.py`**, which downloads each platform's
  bundle (with the validated settings baked in) straight into its repo.

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
`loc_apply_meta`, `loc_merge_languages`, `loc_r_marked_translations`,
`loc_placeholder_lint`, `loc_qa`) are **stdlib-only** and need no token — they only
read / write `strings.ndjson`. Only
the corpus generator, the importer, the QA-issues fetch, and the unused-key
tagging touch Lokalise.

## Scripts

| Script | What it does | Token? |
|---|---|---|
| `loc_corpus.py` | shared read/write/lookup lib + the single owner of corpus serialization (not a CLI) | — |
| `loc_corpus_ndjson.py` | regenerate `strings.ndjson` (+ `strings.meta.json`) from Lokalise | yes |
| `loc_corpus_import.py` | push corpus edits into Lokalise (dry-run default, `--apply`) | yes (`--apply`) |
| `loc_export.py` | download Lokalise exports into each platform repo (iOS/Android/server) with the validated per-platform settings baked in; dry-run default, `--apply`, post-download sanity checks | yes (`--apply`) |
| `loc_qa_issues_fetch.py` | fetch Lokalise QA-flagged translations (`spelling_and_grammar` default; `--issue` for others) to `qa_issues.ndjson` for AI validation | yes |
| `loc_audit_extract.py` | extract en+ru+`<lang>` audit batches from the corpus (opt. `--platform`) | — |
| `loc_audit_apply.py` | apply validated audit findings into the corpus | — |
| `loc_apply_lang.py` | apply a `{key:value}` map into the corpus (replace-only) | — |
| `loc_apply_meta.py` | edit key metadata in the corpus — platforms (add/remove/set) + description (replace-only); flags `dirty_meta` for the importer | — |
| `loc_merge_languages.py` | side-by-side language view for cross-check review | — |
| `loc_r_marked_translations.py` | translation backlog (`unverified`/missing/empty): extract → JSON → apply | — |
| `loc_placeholder_lint.py` | lint placeholders vs the Lokalise universal contract; pre-flight inside `loc_corpus_import` | — |
| `loc_qa.py` | lint value hygiene (em-dash, invisible spaces, Cyrillic in `en` source, `()` balance, edge/double whitespace, cross-language URL parity); 2nd pre-flight inside `loc_corpus_import` | — |
| `loc_unused_keys.py` | report-only unused-key scan over **iOS + Android** repos; feeds Lokalise tags | yes (tag `--apply`) |
| `lokalise_helper.py` | Lokalise API v2 CLI (list/get/tags/update/create; mutations dry-run by default) | yes (`--apply`) |
| `loc_audit_prompt.md` + `loc_audit_lang_calibration/` | sub-agent audit prompt + per-language calibration | — |
| `loc_glossary.py` | glossary read/write/lookup lib + single owner of `glossary.ndjson` serialization (not a CLI); renders the Lokalise glossary CSV/API export — see [`GLOSSARY.md`](GLOSSARY.md) | — |

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

# Edit key metadata (platforms / description) in the corpus (no token):
python3 loc_apply_meta.py --key onboarding.title --add-platform android
python3 loc_apply_meta.py --key text2_3F --description "Surface: main screen ..."

# Review + import edits into Lokalise (translations AND metadata):
git diff -- strings.ndjson
.venv-lokalise/bin/python loc_corpus_import.py --lang de            # dry-run
.venv-lokalise/bin/python loc_corpus_import.py --lang de --apply    # push translations
.venv-lokalise/bin/python loc_corpus_import.py --apply              # push everything dirty (langs + metadata)
.venv-lokalise/bin/python loc_corpus_import.py --key fullPromoText --apply  # one key: all langs + its metadata

# Unused-key candidates (iOS + Android both required):
.venv-lokalise/bin/python loc_unused_keys.py        # --repo-root <ios>, --android-repo <android>

# Export Lokalise -> each platform repo (replaces the manual Lokalise UI download):
python3 loc_export.py                                  # dry-run plan, all platforms (no token)
.venv-lokalise/bin/python loc_export.py --apply        # download iOS + Android + server into their repos
.venv-lokalise/bin/python loc_export.py ios --apply    # one platform
.venv-lokalise/bin/python loc_export.py --to /tmp/exp --apply   # write to /tmp instead of the repos (test)
```

## Consuming the corpus from another repo

Attach this repo to an iOS / Android / server session via
`permissions.additionalDirectories` and read `strings.ndjson`. Search the flat
`en` field (`rg` / `jq`) before creating a new key — if a matching key already
exists on another platform, add the missing platform to that key in the corpus
(`python3 loc_apply_meta.py --key … --add-platform …`, token-free) and let the
operator push it with `loc_corpus_import --apply`, instead of creating a duplicate.

## Export from Lokalise

The Lokalise → platform export — the validated per-platform download settings (iOS
`.strings`/`.stringsdict`, Android XML, server JSON) — lives in **[`EXPORT.md`](EXPORT.md)**:
the spec `loc_export.py` implements, doubling as the manual-UI fallback. Operator-run via
`make export` / `make export-dry` ([CR-MAKE] / [CR-ACCESS]); dry-run prints the plan token-free.

## Glossary

`glossary.ndjson` is a git-tracked **terminology** glossary (brand / product
names, recurring UI labels, domain nouns, beverage names, units, banned jargon),
one agreed rendering per language — the terminology analog of `strings.ndjson`,
pushed into the Lokalise glossary (a separate surface from translation keys). Its
serializer **`loc_glossary.py`** owns the format; the record schema, the Lokalise
CSV/API mapping, the category taxonomy and the two-pass fill workflow are in
**[`GLOSSARY.md`](GLOSSARY.md)**. The file starts empty — filling is a separate step.

## Conventions

Linguistic / translation-quality rules (brand voice, register, calque
discipline, punctuation, translator-context comments) are canonical in this repo:
[`TRANSLATION_STYLE.md`](TRANSLATION_STYLE.md); `loc_audit_prompt.md`
operationalizes them for the audit sub-agent. The cross-platform "not yet
human-verified" / "needs translation" markers are the corpus `unverified` field plus
an empty (`""`) target ([CR-CORPUS-UNVERIFIED]); apply scripts mark an edited language
`unverified` so AI/edited translations stay flagged for human / Lokalise review.
Agent-facing rules: `CLAUDE.md`.
