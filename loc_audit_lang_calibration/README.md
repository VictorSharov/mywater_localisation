# Per-language audit calibration profiles

Generated 2026-05-15 for weak-AI-signal languages: `ar`, `hi`, `vi`, `id`, `ms`.

For the other 14 languages of the 19-language sweep (`de`, `fr`, `es`, `it`,
`nl`, `pt_BR`, `da`, `nb`, `sv`, `pl`, `tr`, `ja`, `ko`, `zh_CN`) Opus 4.7
has native-grade convention knowledge; the inline T-V / honorific map and
gender table in `loc_audit_prompt.md` § Sub-agent prompt (calibrated)
suffices.

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
