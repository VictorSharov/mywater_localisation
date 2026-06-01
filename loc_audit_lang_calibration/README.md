# Per-language audit calibration profiles

Six profiles exist: **`ar`, `hi`, `vi`, `id`, `ms`** (the original weak-AI-signal set,
2026-05-15) and **`pl`** (lean, trap-focused, 2026-05-31 — not weak-signal but trap-dense:
4-form CLDR plural, gendered past tense, `ru→pl` Slavic calque; evidence-derived from a
2-batch Opus 4.8 pilot — see `loc_audit_changelog.md`).

Every other language in the 21-language corpus has **no** profile: Opus 4.8 Max has
native-grade convention knowledge for them, and the inline T-V / honorific map + gender table
in `loc_audit_prompt.md § Sub-agent prompt (calibrated)` suffices (the 2026-06-01 final-6
re-sweep — nb/nl/pt_BR/sv/tr/zh_CN — confirmed this by sweeping profile-free). `tr` / `ja` /
`ko` are the next candidates **only if** a full-language pass surfaces a recurring
false-positive class (see `loc_audit_changelog.md`).

Language codes here are the corpus / Lokalise ISO form (underscored: `pt_BR`, `zh_CN`) — the
exact `<lang>` you pass to `loc_audit_extract.py` / `loc_r_marked_translations.py`. They are
**not** the iOS `.lproj` hyphenated form (`pt-BR`, `zh-Hans`); the scripts reject an unknown
code with a hint.

## How these are consumed

A profile is inlined **verbatim** into the audit sub-agent prompt. The full canonical
injection order — header lines → glossary checklist (for **every** target) → calibration
profile (if any) → prompt — is owned by **`loc_audit_prompt.md § Run sub-agent`**; follow it
there, do not re-derive it here.

## What lives in each profile

Each `<lang>.md` follows the same 7-section structure:

- `## T-V / formality system` — pronoun / register tier for casual UI.
- `## Gender system in grammar` — whether past-tense / adjectives inflect for user gender.
- `## Script & direction` — Latin / Devanagari / Arabic / etc. + LTR / RTL implications.
- `## Punctuation conventions` — quotation marks, decimal separator, sentence-end markers.
- `## Common EN→target calque patterns` — concrete hydration / fitness-UI examples.
- `## Plural rules summary` — CLDR plural categories (1 / 2 / 6) and common `.stringsdict` traps.
- `## Language-specific skip rules for audit` — false positives a non-native auditor would raise.

**Authoring rule.** A profile must **not** restate base-prompt rules (rule #5 gender / rule
#15 em-dash) or non-audit iOS-render mechanics — point to them. Keep only what is per-language
and load-bearing (FP-trap guards, calque examples, script/plural specifics, brand/project
decisions); profiles are read verbatim, so every line must earn its place. But apparent
"boilerplate" is often load-bearing (e.g. `vi` diacritics-as-semantic, `ms` Jawi-script flag,
`ar` placeholder-ordering) — cut only true base-prompt duplication, not a per-language guard.

## When to update

- Add or refine a profile **only** when a full-language audit pass surfaces a recurring
  false-positive class (the standing `tr`/`ja`/`ko`-deferred bar). Profiles are
  **evidence-derived from a pilot**, not pre-generated.
- **Do NOT edit a profile mid-run** — it is copied verbatim into the sub-agent, so a mid-run
  edit desyncs batches. Update between runs only.

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
