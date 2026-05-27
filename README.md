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
`loc_merge_languages`, `loc_r_marked_translations`, `loc_placeholder_lint`) are
**stdlib-only** and need no token — they only read / write `strings.ndjson`. Only
the corpus generator, the importer, and the unused-key tagging touch Lokalise.

## Scripts

| Script | What it does | Token? |
|---|---|---|
| `loc_corpus.py` | shared read/write/lookup lib + the single owner of corpus serialization (not a CLI) | — |
| `loc_corpus_ndjson.py` | regenerate `strings.ndjson` (+ `strings.meta.json`) from Lokalise | yes |
| `loc_corpus_import.py` | push corpus edits into Lokalise (dry-run default, `--apply`) | yes (`--apply`) |
| `loc_audit_extract.py` | extract en+ru+`<lang>` audit batches from the corpus (opt. `--platform`) | — |
| `loc_audit_apply.py` | apply validated audit findings into the corpus | — |
| `loc_apply_lang.py` | apply a `{key:value}` map into the corpus (replace-only) | — |
| `loc_merge_languages.py` | side-by-side language view for cross-check review | — |
| `loc_r_marked_translations.py` | translation backlog (`unverified`/missing/empty): extract → JSON → apply | — |
| `loc_placeholder_lint.py` | lint placeholders vs the Lokalise universal contract; pre-flight inside `loc_corpus_import` | — |
| `loc_unused_keys.py` | report-only unused-key scan over **iOS + Android** repos; feeds Lokalise tags | yes (tag `--apply`) |
| `lokalise_helper.py` | Lokalise API v2 CLI (list/get/tags/update/create; mutations dry-run by default) | yes (`--apply`) |
| `loc_audit_prompt.md` + `loc_audit_lang_calibration/` | sub-agent audit prompt + per-language calibration | — |

Exact flags live in each script's `--help` / docstring (the canonical owner).

## Common commands

```bash
# Regenerate the corpus from Lokalise (token holder; commit + push the result):
.venv-lokalise/bin/python loc_corpus_ndjson.py

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

# Unused-key candidates (iOS + Android both required):
.venv-lokalise/bin/python loc_unused_keys.py        # --repo-root <ios>, --android-repo <android>
```

## Consuming the corpus from another repo

Attach this repo to an iOS / Android / server session via
`permissions.additionalDirectories` and read `strings.ndjson`. Search the flat
`en` field (`rg` / `jq`) before creating a new key — if a matching key already
exists on another platform, add the missing platform in Lokalise instead of a
duplicate.

## Export from Lokalise (to be finalized)

The corpus → Lokalise **import** is built (`loc_corpus_import.py`); the Lokalise →
platform **export** is still operator-run and not yet captured as a reproducible
config. What the final export must pin down per platform so placeholders / plurals
land correctly:

| Platform | File format | Placeholder format | Plural | Path (expected) |
|---|---|---|---|---|
| iOS | `.strings` + `.stringsdict` | iOS (`[%s]`→`%@`, `[%i]`→`%li`) | `.stringsdict` | `<lang>.lproj/Localizable.strings` |
| Android | XML | printf (`[%s]`→`%s`, `[%i]`→`%d`) | `<plurals>` | `values-<lang>/strings.xml` |
| server | JSON (i18next / ICU) | `{{…}}` / `{…}` | ICU / i18next | `resources/locale/<lang>.json` |

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
- **TODO (final export script):** capture the exact Lokalise download settings
  (format ids, placeholder-format, plural-format, filename templates, directory
  prefix, branch) here so the export is reproducible.

## Conventions

Linguistic / translation-quality rules (brand voice, register, calque
discipline, punctuation, translator-context comments) are canonical in this repo:
[`TRANSLATION_STYLE.md`](TRANSLATION_STYLE.md); `loc_audit_prompt.md`
operationalizes them for the audit sub-agent. The `|R|` marker that iOS `.strings` use for an
unverified source maps to the corpus `unverified` field; apply scripts mark an
edited language `unverified` so AI/edited translations stay flagged for human /
Lokalise review. Agent-facing rules: `CLAUDE.md`.
