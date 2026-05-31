# Per-language audit calibration profiles

Generated 2026-05-15 for weak-AI-signal languages: `ar`, `hi`, `vi`, `id`, `ms`. A
sixth, **`pl`** (lean, trap-focused), was added 2026-05-31 — not weak-signal but
trap-dense (4-form plural, gendered past, ru→pl Slavic calque); evidence-derived from a
2-batch Opus 4.8 pilot (see `loc_audit_changelog.md`).

For the other 13 languages of the 19-language sweep (`de`, `fr`, `es`, `it`,
`nl`, `pt_BR`, `da`, `nb`, `sv`, `tr`, `ja`, `ko`, `zh_CN`) Opus 4.8 Max
has native-grade convention knowledge; the inline T-V / honorific map and
gender table in `loc_audit_prompt.md` § Sub-agent prompt (calibrated)
suffices. (`tr` / `ja` / `ko` are the next candidates if a sweep surfaces
recurring false positives — see `loc_audit_changelog.md`.)

Language codes here are the corpus / Lokalise ISO form (underscored: `pt_BR`,
`zh_CN`) — the exact `<lang>` you pass to `loc_audit_extract.py` /
`loc_r_marked_translations.py`. They are **not** the iOS `.lproj` hyphenated form
(`pt-BR`, `zh-Hans`); the scripts reject an unknown code with a hint.

## How these are consumed

Phase 3 sub-agents (per `ai_reports/tasks/2026-05-15_localization_audit_19_langs_plan.md`)
inline the relevant profile before the main prompt block:

```
Target language: <lang>
Input: /tmp/loc_audit_<lang>_batch_<i>.txt

Calibration profile:
<full content of loc_audit_lang_calibration/<lang>.md>

<then full content of loc_audit_prompt.md § Sub-agent prompt (calibrated)>
```

## What lives in each profile

Each `<lang>.md` follows the same structure:

- `## T-V / formality system` — pronoun / register tier choice for casual UI.
- `## Gender system in grammar` — whether past-tense / adjectives inflect for user gender.
- `## Script & direction` — Latin / Devanagari / Arabic / etc. + LTR / RTL implications.
- `## Punctuation conventions` — quotation marks, decimal separator, sentence-end markers.
- `## Common EN→target calque patterns` — 3-5 concrete examples drawn from hydration / fitness UI domain.
- `## Plural rules summary` — CLDR plural categories (1 / 2 / 6) and common `.stringsdict` traps.
- `## Language-specific skip rules for audit` — false positives a non-native auditor would raise.

## When to update

- Phase 2 family pilot reveals a recurring false positive in a covered language → add to that profile's skip rules.
- Phase 3 post-group analysis flags systematic miss → update the profile's calque examples or skip rules.
- New weak-AI-signal language added to sweep → generate new profile via parallel Opus 4.7 sub-agent (template prompt in the 19-langs plan, Phase 1 § 1.4).

Do NOT update these profiles inline during a Phase 3 audit run — the prompt is
copied verbatim into the sub-agent, so mid-sweep edits cause inconsistency
between batches. Update between groups only.

## Provenance & validation — these profiles are AI-generated

These profiles were produced by an AI sub-agent (see the dates above) — the same
class of agent that produces the translations they are used to audit. Their
factual claims (beverage meanings, term mappings, register calls) are
**hypotheses, not ground truth**.

- **Do not self-validate.** Confirming a translation against these profiles, or
  confirming a profile against the corpus translations, is circular — both are AI
  artifacts, and cross-checking them launders an error into "verified."
- **Validate against a non-circular anchor:** (1) app code / data — e.g.
  `mywater_ios …/DefaultBeverageCatalog.swift` (sugar / alcohol% / icon define
  what a drink *is*); (2) external human authority — dictionaries, language
  councils, real product usage.
- **Worked example (2026-05-31).** The `Soda` lines in `ms.md` / `vi.md`
  originally sanctioned bare "Soda" for a *sweet* soft drink. External
  dictionaries show Malay / Vietnamese "soda" leans to soda **water**, and the app
  catalogue marks `Soda` sugary — so the profiles were legitimizing an ambiguous
  term. Corrected; rationale in `loc_audit_changelog.md § Beverage catalogue naming`.
