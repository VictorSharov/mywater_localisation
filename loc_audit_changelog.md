<!--
doc-role: reference (calibration canon)
doc-owner: loc_audit_changelog.md (mywater_localisation repo)
doc-scope: durable calibration rationale for the localization value-audit — why each
  skip / audit / format rule + binding linguistic/policy decision exists. NOT a state
  ledger and NOT an execution log: current per-language status, open follow-ups and the
  dated run-by-run execution trail live in loc_audit_status.md. The LIVE workflow +
  calibrated sub-agent prompt is loc_audit_prompt.md; the sub-agent reads NONE of these.
-->

# Localization audit — calibration canon

> **Split (2026-06-01).** This file is **calibration rationale only** — skip/audit/format
> rules, anti-regression mechanisms, and binding linguistic/policy decisions (the *why*,
> so an operator can run any batch without re-deriving). The current per-language **STATE**
> (audited / applied / pushed / verified), the **open follow-ups**, and the dated
> **execution log** (re-sweep / apply / push passes, the cost-blowup incident, the
> context-audit and beverage changesets) moved to **`loc_audit_status.md`**.
>
> To answer *"is language X done / pushed?"* read **`loc_audit_status.md` § STATE** — never
> infer current state from a historical entry. (Reading a past entry as present truth — e.g.
> the blowup entry's "0 applied" — is exactly the confusion this split removes.)
>
> Neither file is read by the audit sub-agent (it reads only `loc_audit_prompt.md`); both
> are operator/orchestrator references. New prompt/skip/output rule changes still get a
> dated one-line rationale entry **here**; new sweep/apply passes get an execution entry in
> `loc_audit_status.md`.
>
> **Upkeep (keep it lean, keep it shared).** Optimize for the agent-reader doing the next
> task — the human operator rarely reads these. Cut redundancy / self-narration, resolve
> contradictions in place. Durable project knowledge (state, decisions, conventions, gotchas)
> belongs in these tracked repo docs — **never only in an agent's private memory**, which is
> per-developer and unshared, so the other contributor's agent never sees it and the idea is
> lost. Private memory is for an individual's working preferences only.

## Skip rules (§ What NOT to flag — pilot/group-calibrated false-positive patterns)

- **#1 formal register — correct ONLY on legally-binding text (current rule).** Do **not** flag formal V-form/honorific on genuinely legal text (Terms / Privacy / subscription-legal / consent; `Register: formal`). Every former-formal **non-legal** surface (App Store / paywall hero+CTA / permission / error-with-recovery / medical-educational / Siri-educational) is informal **T-form, reserved tone**; legacy «вы» there is grandfathered (not swept), flag only new/source-changed (`warn`). The casual-surface V-form sweep (rule #8) is unchanged; paywall-CTA is in scope (`reachTheGoal` legacy outlier). *(History: pilot 1-50 flagged all «вы» → formal-surface carve-out generalized Phase 1, codified Pre-G6 (Face A) → narrowed to legal-only 2026-05-30; rationale in the 2026-05-30 (rev.) entry below.)*
- **#2 legacy hard line break handling** — pilot 1-50 over-flagged mismatch; current policy is stricter: user-facing values should not contain manual hard line breaks.
- **#3 straight quotes / #4 trailing period on errors / #5 legacy please-comma / #6 comment-explained lexicon / #8 simple-noun beverage / #9 comment-explained casing / #11 pure stylistic / #12 British-in-comments** — pilot 1-50 FP buckets (separate sweeps or legacy-acknowledged).
- **#7 empty (`""`) `unverified` target = untranslated, not a defect** — do NOT flag or auto-fill an empty target during audit; it awaits a translation pass / Lokalise ([CR-CORPUS-UNVERIFIED]). Supersedes the retired `|R|`-source-marker model (the original post-13-27 rule guarded English-text fallbacks under en `|R|` — incident: 18 siri/signup keys wrongly removed + restored).
- **#10 same defect en+target → flag en only** — cross-language dedup; en is the root.
- **#13 singular/plural en for multi-select** — post-13-27: fix at en source, don't pluralize target (`chooseYourGoal`).
- **#14 gendered count-caption** — post-13-27: don't flip M-sg → plural as a "fix" (reads as "multiple subjects"); needs `M`/`F` split (`sharesOfTheApp`).
- **#15 em-dash `—` U+2014** — post-Phase-0; **2026-05-16 policy: only `—` U+2014 forbidden in user-facing values (AI tell users dislike); `-` U+002D sanctioned incl. ` - ` separator; `–` U+2013 unregulated; doc-prose `—` unaffected.** Never *propose* `—` as a suggestion; replacement anchored on en (comma/period/colon/restructure; script-correct for ar/CJK). **Refined 2026-05-31 (operator):** default is now **restructure** (colon/period/comma per `en`, or drop the connector); hyphen `-` is a fallback only, not the default — an em-dash usually signals a loosely-built sentence, and Google's dev-docs style guide prefers a colon or period over a dash. Canonical — `TRANSLATION_STYLE.md § Brand voice § Punctuation`.
- **#16 target mirrors proven-ru restructure → not drift** — G2: codifies "How to use ru as reference" as an enforceable skip (recurring sole semantic-drift FP class). Scoped to the proven `Localizable.strings` ru only (see 2026-05-17 ru caveat).
- **#17 Danish optional pre-subordinate-clause comma** — G2: sanctioned by Dansk Sprognævn ("nyt komma"); `da`-specific carve-out, not a punctuation defect.

**Skip-rule #6 refinement (2026-05-31, operator-driven — `text1_9` reversal).** A comment
that merely *glosses / denotes* an en term (e.g. `"water balance" is app terminology…`) is
**not** a skip-#6 *preserve* sanction; skip #6 needs an explicit preserve directive (its
example: "preserve `norm` legacy phrasing"). The operative test is **surface register**, not
literal en-fidelity or a meaning-gloss: on a casual surface a clinical calque (`bilans
wodny`, `водный баланс`-equivalents) is a defect per `TRANSLATION_STYLE.md § Translation
discipline` Принцип #3 even when "faithful to en". (This reversed an earlier recorded
`text1_9` *rejection*; the original mistaken call + its reversal are in the execution log —
`loc_audit_status.md`, 2026-05-31 "scoped ar/hi" + "pl pilot" entries.)

## Audit rules (§ What to audit)

- **rule #8 T-V/honorific map (all 21) + binding OPERATOR POLICY (current rule).** T-form is the default on **all surfaces except legally-binding text** (`Register: formal` carve-out — formal correct there). Casual-surface V-form is a **confirmed project-wide defect**: enumerate per-row (no Summary-consolidation, no deferral, validator must accept). Former-formal **non-legal** surfaces are informal-T, reserved tone (advisory `warn`, no sweep, legacy grandfathered); on serious non-legal surfaces also flag over-familiarity (diminutive / slang / emoji / nagging). Scandinavian = skip #8 entirely (no morphological T-V). *(History: per-language map inlined Phase 1; casual-V confirmed-defect G1; ru-parity tension closed Pre-G6; narrowed to the legal carve-out 2026-05-30 (rev.).)*
- **rule #9 script-appropriate punctuation** — D1/Phase-2 added the CJK clause (ja half/full-width blind spot); **G6 DELTA-G6-1 added the RTL/Arabic-script clause** (rule was CJK-only, masked by `ar.md`; structural blind spot for Phase 4 all-21 pass). Latin/Cyrillic unaffected; Devanagari integrity is a `typo` matter (`hi.md`).
- **rule #5 gendered variants** — Phase-1: identical M/F is CORRECT for genderless langs (id/ms/vi/ja/ko/zh-Hans/tr-partial); D3/Phase-2: the carve-out suppresses ONLY the gender-agreement finding, never per-variant typo/calque/semantic; G3: CJK M/F expectation **inverted** (a DIFFERING pair is the scrutiny target); G4 Delta-C: key the finding on the *defective* variant (exact-match apply on the better one is a no-op).
- **rule #2 `<target>` calque/restructure** — post-Phase-0 added RU→EN reverse-calque awareness to the `en` audit + `application`→`app` convention (`[CM-LOCALE-LINGUISTIC-CANON]`); G4 Delta-B made the ru cross-check **mandatory pre-flag** (cuts the largest weak-signal FP class at source); G5-2 lifted "sibling-language contamination is a PRIMARY defect class" from `ms.md` into the base prompt, generalized to hi/ar.

## Format / infra / constraints

- **Triple `en+ru+target` input, ru as reference (not audit target), batch 200, ru-specific block optional, weak-AI calibration profiles inlined, `Target language:`/`Input:` first lines** — Phase 1 infra for the 19-lang sweep; `loc_audit_extract.py` 4-arg signature (legacy 3-arg numeric preserved).
- **Column discipline** (§ Input format) — G2: a defect quoted from the `en` line is `lang=en` even when co-occurring with a target issue; `current` must match the `lang` column.
- **Suggestion quality bar = a new-translation's bar** (§ Important constraints) — post-AI-translation: the auditor's own `suggestion` must pass the same brand-voice / clinical-term / spoken-plausibility filter (else `—` + rationale, never protect a "technically precise" calque); G2 added constraint-binding **suggestion completeness** (no 60-char truncation on brand-freeze / placeholder / hard-line-break rows); G5-1 added a language/register-purity self-check (auditor twice self-injected wrong-language tokens into its own suggestion).
- **`info` severity dropped; explicit hard/soft constraint split** — pilot 1-50 (noise without value; binding vs soft constraints).
- **Glossary terminology lane (2026-05-31)** — `<target>`-rule #10 + a per-language checklist inlined above the prompt (`loc_audit_glossary.py <lang>`, generated from `glossary.ndjson`). Brings the glossary — which postdates the Phase 0–5 sweep — into the audit: brand-freeze (verbatim, with the localized-brand carve-outs `My Water` / `Health app` / `Apple Account`), forbidden jargon (cross-language Принцип #3 clinical-equivalent ban), and canonical per-language rendering (consistency anchor, not a correctness proof). The flag rule is inline in the prompt (sub-agent has no doc access); the ~100-term renderings are generated so they never drift (`CLAUDE.md § Reverse routing`). Phase-6 prep for the Opus-4.8 re-sweep; the `bilans wodny` reversal (below) is the motivating false-negative class.

## Anti-regression mechanisms

- **3-stage dead-key defense** — G3 `tr` incident (auditor lowercased a key → validator blind → `loc_audit_apply.py` silently appended a dead duplicate-casing key, real typo left unfixed). Mitigated at three independent stages: Delta-1 auditor byte-for-byte key copy (§ Output format), Delta-2 validator byte-for-byte key cross-check (validator prompt), Delta-3 applier loud-fail-no-append (`--allow-append` default off). Confirmed scaling G3→G6 (0 recurrence across 4 groups); mode is dead.
- **`RU-PARITY-DEFER:` routing** — G3 Delta-5 `[tech debt]`: surfaces a latent ru-side V-leak (ru itself V-form on a casual key) without auto-applying; true root cause was a separate operator decision, **closed Pre-G6** (now a safety net only, no known-open cluster).
- **No `lang=ru` audit rows for non-ru targets** — G4 Delta-A: the ru reference column is read-only; the deterministic applier cannot act on it.
- **Phase-3 collection architecture** — audit/validator sub-agents self-write `/tmp/..._findings.md` and return only summary counts (overrides the prompt's "no file writes" for the Phase-3 collection step only; routing many tables through the orchestrator risks auto-compaction loss). Operator-approved.
- **Batch loops index by `en`-count, not target-count** — G1: `loc_audit_extract.py` indexes by `en` (which exceeds the target count), so a fixed batch loop must span the full `en` range or it silently drops the tail (a 6-batch loop once dropped ~100 entries/lang). *(Superseded in practice by full-context single-pass auditing, which sidesteps batch windows entirely — see `loc_audit_status.md`.)*
- **Cross-batch reconciliation needed before apply (pl-pilot FN class)** — per-batch
  isolation is blind to cross-key consistency: a label renamed in one batch can orphan
  sibling strings naming the old label in other batches (`feed`→3 `*TrackingFeedOnlyMessage`
  siblings). A full multi-batch run needs an explicit reconciliation phase before apply.
  (Full-language-per-agent single-pass auditing — the current preferred vehicle — sidesteps
  this by design.) Detail: `loc_audit_status.md`, 2026-05-31 pl-pilot entry.
- **Auditor cold-start hallucination is backstopped, not prevented** — a batch auditor may
  emit fabricated keys before reading its input, then self-correct. The replace-only +
  copy-precheck invariant (`unmatched=0`/`added=0` on a `--corpus` copy) is what keeps a
  dead key from landing — keep it. Detail: same pl-pilot entry.
- **`loc_audit_apply.parse_table` silently skips a findings row whose cell contains a
  backslash-escaped pipe (`\|`)** — an escaped pipe in *any* cell (even a non-applied one)
  desyncs the Markdown column split, so the whole row is dropped with no error and the real
  defect stays unfixed. Keep findings-table cells pipe-free, and confirm the apply
  changed-set == the intended set (a silently-skipped row will not otherwise surface).
  Surfaced 2026-06-01 6-lang re-sweep (`zh_CN appstore_app_subscriptionTemsAppStore`).
- **Context-audit (translator `context` field) calibration** — the Tier-0 linter
  (`loc_context_lint.py`) is high-noise (e.g. `surface_mismatch` ~42/44 false-positive);
  the per-category confirmed-FP "do-NOT-re-adjudicate" lists + the linter de-noising history
  live with their passes in `loc_audit_status.md § Context-audit`.

## Binding linguistic / policy decisions & lessons (dated)

Durable decisions and process lessons (the *why*). Execution facts (what/when applied,
push state) for these passes are in `loc_audit_status.md`. Newest-first by topic.

- **Pre-G6 ru-anchor V-form parity — CLOSED `[root cause]`** — Face B: 7 evidenced genuinely-casual ru keys swapped V→T in `ru.lproj` (`yearResultsPushTitleTemp`, `didgestSettingsTitle`, `pressOnPlusToAdd`, `drinkParamsNotionMessage`, `youShuldAddToFriend`, `drinksReorderText`, `notifSoundText`) — restores anchor trust so all 19 langs self-heal on the normal accept path; Face A: paywall-CTA codified intentionally-formal. Settings-register keys deliberately excluded (own neutral register). Canonical owner — `TRANSLATION_STYLE.md § Brand voice § Pronouns`.

- **Bespoke-prompt skip-rule import** — Phase 4 em-dash incident: a bespoke (non-audit-sub-agent) cross-language/consistency prompt does NOT inherit § What NOT to flag and recommended `—` mirroring a ru anchor that itself violates #15. Lesson: any future bespoke cross-language prompt MUST explicitly carry the no-em-dash constraint or import skip rules (Phase 5 prompts already do).

- **Mass-apply over submission-affecting files** — Phase 5: a deterministic Bash applier over many `InfoPlist.strings` is auto-mode-permission-blocked (correctly; `dangerouslyDisableSandbox` does not cover that classifier). Design the applier **idempotent** (key-only match, force-target, insert-if-absent) so partial Edit-tool progress + a later operator-run full pass compose cleanly. `mywater_ios [CR-SUBMISSION]`: Phase 5 changed localized permission *purpose* strings + added localized `NSCalendarsUsageDescription` (20 langs); hard-gated items untouched; store-review evidence = `NEEDS_ASC`.

- **ru `.stringsdict` / `InfoPlist.strings` were OUTSIDE the 27-batch proving corpus** — Phase 5 surfaced a real ru `.stringsdict` defect (`%li разы`→`%li раза`, CLDR `other`=fractions). Basis for the 2026-05-17 ru proving-corpus caveat below; do not treat ru as an infallible correctness anchor for `.stringsdict` / `InfoPlist`.

- **2026-05-31 — `pl` calibration profile added (lean, evidence-derived from a 2-batch Opus 4.8 pilot):**
  - **What** — new `loc_audit_lang_calibration/pl.md` (~100 lines, lean), the **sixth** profile after ar/hi/vi/id/ms. Wired into `loc_audit_prompt.md` (the four "inline the profile when auditing this lang" references — reframed *weak-AI-signal* → *"has a calibration profile"* and added `pl`) and the dir `README.md` (`pl` moved out of the now-13 native-grade languages; stale "Opus 4.7" → "Opus 4.8 Max").
  - **Why** — `pl` is medium-resource (not weak-signal) but **trap-dense**: 4-form CLDR plural, gendered past tense, and `ru→pl` Slavic calque (the ru-native team + the audit's ru-anchor make this project-specific). A 2-batch pilot (223 keys, Opus 4.8 as auditor, **NO** profile) confirmed: batch-1 (200 mature core keys) was near-clean (1 `warn`); batch-2 (23 **targeted** plural + legal/permission keys) surfaced **2 errors + 2 warns** — a real masculine-personal `few`-form plural bug (`howMuchPeopleUseAppPlural`) and a legal-compliance content gap (`termsSubscriptionDescription` dropped the renewal-charge clause). 4.8 Max caught all of them **unaided** ⇒ the profile is **consistency insurance + FP-guards + an explicit 4-form-plural check**, NOT a model-blindness fix — hence lean. Methodological note for future calibration: defect density lives in the plural / legal / gender zones and is near-zero in mature core copy, so **sample the hard zones, not key-order**.
  - **Profile payload (all evidence-derived, not speculative):** plural `few`(nom-pl masc-personal `-li`) ≠ `many`(gen-pl) check + legitimate-identity guards (`many`==`other`; `razy`/`dni` all-coincide — do not false-flag); `ru→pl` clinical-calque blacklist (`bilans wodny` …) + the skip-#16 caveat that a Slavic-mirror of ru can still be a pl calque; legal = suppress register but keep content/completeness checks active; permission/paywall "we + `ty`" is on-brand, not a mixed-register leak; `rejestr`/`miary` are established terms; explicit brand/proper-noun constraint outranks the ru-mirror skip #16.
  - **Findings — validated (skeptical native-pl sub-agent) → 3 applied, 2 rejected:** of 5 candidates, **3 applied** to the corpus via `loc_apply_lang.py pl` (→ `dirty`+`unverified`, pending operator push): `termsSubscriptionDescription` (AMEND — restored the dropped mandatory renewal-charge + cost legal clause, a real App Store-disclosure gap), `howMuchPeopleUseAppPlural` (ACCEPT — `few` `użytkowników zaczęło` → nom-pl masc-personal `użytkownicy zaczęli`; one/many/other already correct), `privacyPolicyandterms` (AMEND — `Warunki` → `Warunki korzystania z usługi`). **2 REJECTED as non-defects:** `appstore_app_title` (ASC store-title localization is an intentional ASO / operator decision — ru localized it too); and `text1_9F` `bilans wodny` — *initially* mis-rejected as skip-#6-sanctioned, but **REVERSED 2026-05-31: it is a clinical calque** (a denotation-gloss is **not** a skip-#6 *preserve* directive — the operative test is surface register; see the § Skip rules `text1_9` reversal above). Fixed to plain `Pij wodę regularnie!`; **do not re-flag the original rejection.** The legal-clause restoration still merits a final human/legal glance before the Lokalise push (the `unverified` + operator-push gate is that checkpoint).
  - **Verification** — profile/wiring = doc-only (no `.py` changed; four prompt references + README `## ` section contract intact). Findings apply = 3 `pl` corpus keys: a snapshot-diff (`/tmp/corpus_before_apply.ndjson`) confirmed **exactly those 3 keys** changed — a concurrent uncommitted corpus edit was preserved byte-identically — and lint (placeholder + qa) is 0/0 over 1261 keys. Next profile candidates (`tr`, then `ja`/`ko`) deferred pending evidence.

- **Calibration-profile authoring rule (2026-05-31, from a profile redundancy trim).** A
  profile must not restate base-prompt rules or iOS-render mechanics, only per-language
  load-bearing content (read verbatim → every line must earn its place) — full rule in
  `loc_audit_lang_calibration/README.md § What lives in each profile`.

- **2026-05-30 — surface-based `ты`/`вы` split retired (superseded same-day; tombstone).**
  The operator first retired the formal-surface carve-out for a flat **T-form-on-every-surface**
  rule, then **same-day narrowed it to the hybrid** below — flat-universal collapsed two
  independent axes (address-form × tone) into one and left no way to stay friendly without
  sliding into over-familiarity on serious surfaces. Current policy + full rationale → the
  **2026-05-30 (rev.)** entry below. (Doc-only, grandfather, NO sweep — unchanged across both
  steps; the 2026-05-16 casual-surface sweep is untouched.)

- **2026-05-30 (rev. — hybrid: narrow legal carve-out + reserved-tone axis; doc-only, grandfather, NO sweep):**
  - **Why** — the same-day flat "T-form universal on **every** surface" overshot: it gave no mechanism to stay friendly without sliding into over-familiarity on serious surfaces, and it collapsed two independent axes (pronoun = tone) into one. Operator refinement: keep T-form as the universal default, but (a) carve out genuinely **legally-binding text** (a contract is a different speech act, not brand voice), and (b) model register as **two axes** — address-form (T default / `formal` only for legal) × tone (`playful` ↔ `reserved`), pronoun-independent.
  - **What** — `TRANSLATION_STYLE.md § Brand voice § Pronouns` gains `§ Фамильярность` (the over-familiarity ban + ru checklist) and `§ Юридический carve-out` (legal register: impersonal-first, formal-token fallback); `Register: formal` **revived** as the legal-binding register (working values `casual T-form` / `neutral` / `formal`); `Tone: reserved` added. Mirrored here: rule #8 reframed "universal" → "T default except legally-binding text" with a 3-way severity split + an over-familiarity finding; skip rule #1 reframed "deprecated" → narrow legal carve-out; the `Register:` override block defines `Register: formal`; the T-V map header + a legal carve-out routing note (ja=丁寧体 not 敬語, ko=합니다체 not 합쇼체, ar=fuṣḥā not honorific, vi=impersonal not `quý vị`, da/nb/sv=lexical only); ru V-leak detail gains the legal exception + over-familiarity flag. Calibration sync: `id.md` / `ms.md` (paywall/error-vs-legal contradictions removed, legal carve-out restored), `hi.md` (permission ≠ consent-contract distinction), `ar.md` / `vi.md` (additive legal-realization notes — honorific stays wrong even in legal).
  - **Scope — doc-only, grandfather, NO sweep.** Legacy «вы» on non-legal surfaces stays grandfathered; the 2026-05-16 casual sweep is unchanged. Only new / source-changed / renamed strings are bound (T-form on non-legal, `formal` on legal). The two flipped doc examples (`youShouldDrink0Digits` = medical-rationale, `more5MillionUsers` = marketing) stay `casual T-form` — neither is legal.
  - **Open follow-up (operator-gated, NOT done here):** there is no first-class "legal-binding" flag in the corpus — `Register: formal` coverage is sparse (the 2026-05-28 backfill targeted the casual-Type leaf set, not legal keys). Recommend a one-time `loc_apply_meta` backfill of `Register: formal` onto the legal-binding key set (Terms / Privacy / subscription-legal / consent) so the auditor's legal carve-out keys off an authoritative signal, not Surface/Type heuristics. Until then the auditor falls back to Type + Surface and resolves uncertainty toward `warn` (never force-rewrite a possibly-legal string to T-form).
  - **Verification** — doc-only: `loc_qa.py` / `loc_placeholder_lint.py` unaffected (value hygiene, not register); no `loc_corpus.py` change; no corpus value edits in this pass.

- **2026-05-28 — key-level `Register:` field introduced as write-time T-/V- anchor (no sweep; doc-only):**
  - **Why** — context-coverage analysis (post-Phase-5) found register signal almost absent from the corpus, and Surface/Type alone did not disambiguate register (`Tone:` carries affective semantics only — "encouraging" / "promotional" — never T-/V-form). So a key-level `Register:` write-time anchor was added. V-form leak is the largest audit finding class; closing it at write-time prevents it re-arriving at audit time.
  - **What** — new optional comment field `Register:` (introduced as `casual T-form` / `formal V-form` / `neutral`) in `TRANSLATION_STYLE.md § Translator context § Опциональные поля`; cross-referenced from `§ Brand voice § Pronouns` as the per-key write-time anchor. Audit rule #8 treats `Register:` as an authoritative override when present: **casual** → rule #8 binding even on ambiguous surface; **neutral** → suppress register findings (keep per-variant content checks); **formal** → legal-binding register. *(The original mapping `formal → skip rule #1` was superseded 2026-05-30 (rev.): the surface split was deprecated and `formal` is now the legal-binding value, not a formal-surface carve-out; `formal V-form` is legacy-only.)* Absence of `Register:` falls back to surface-based default — at field introduction the corpus held 6 keys with `Register:` (0.5%), all hand-authored on NS\*UsageDescription + two ad-hoc T-form keys; the same-day casual-Type backfill below brought coverage to 18% corpus-wide and 100% on the casual-Type leaf set ({tip, tip headline, motivational text, notification body / title, achievement description}).
  - **Scope** — doc-only at field introduction. The 2026-05-28 casual-Type backfill (227 keys) followed in the same pass and is the only mass-edit so far; further surfaces (formal carve-outs, settings-neutral) stay surface-default until evidenced. The `Register:` clause is **additive** (an extra authoritative signal when present), not a replacement of surface-based defaults.
  - **Paired doc edits (same pass):** Type vocabulary closed (audit buckets by Type equality; 306 distinct values had drifted from the original ~18-entry exemplar list — re-opening drift was breaking sibling-consistency bucketing); Placeholders rule tightened (the `Placeholders:` field must itself be in universal-form, not iOS-native — caught a real leak where `%li` had survived in the comment field while the value already used universal `[%i]`); `Educational` flagged as a V-form-leak-provoking word in casual contexts (tips); `platforms: ["other"]` literal-`%` carve-out gets explicit Constraints note convention.
  - **Verification** — `python3 -m py_compile` N/A (doc-only); `loc_qa.py` and `loc_placeholder_lint.py` unaffected (rules are about *value* hygiene, not context fields); corpus round-trip byte-identical (no `loc_corpus.py` change). The 4 broken NS* ad-SDK permissions + 2 keys with iOS-native `%li` in the `Placeholders:` comment field were fixed in the same pass via `loc_apply_meta.py` (concrete bugs, not the field-introduction change itself).

- **2026-05-17 — doc-reconciliation pass (no sweep; owner-doc drift fixes, operator-requested):**
  - **Suggest ≠ translate reconciliation** — prompt intro reworded: "NOT to translate yourself" forbids silently overwriting shipped values, NOT emitting the reviewed `suggestion` (which passes the operator + validator gate). Removes a real actionability ambiguity vs § Important constraints "suggestion quality bar = new-translation rules" — a weak model could otherwise refuse to give suggestions or, conversely, self-apply.
  - **ru proving-corpus scope caveat** — § How to use ru as reference + the `ru` input-format line now state ru is PROVEN for `Localizable.strings` only; ru `.stringsdict` / `InfoPlist.strings` were outside the 27-batch corpus (Phase 5 surfaced a real ru `.stringsdict` defect `%li разы`→`%li раза`). Caveat moved from frozen changelog history to where the anchor is actually used; scoped skip-#16's ru-mirror carve-out to the proven corpus.
  - **lint coverage boundary** — § Verify clarifies `localization_lint.py` checks only non-en `Localizable.strings`; `.stringsdict` / `widget14.strings` / `InfoPlist.strings` are NOT covered → manual check, do not over-trust a green `make verify`. No script change (documents the boundary, does not widen the lint).
  - Paired owner-doc edits (same pass, outside this file): `docs/LOCALIZATION.md` (lint-coverage boundary on the write-time validate step; en-ahead key-count model corrected — `delta` is the translation backlog and is **not** required to equal `count(|R|)`, since `|R|` also sits on keys present in all 21 locales; § Новый язык create-list +`InfoPlist.strings`), `docs/ai/DOC_ROUTING.md` (phantom `Intents.strings` / `Base.lproj/Intents.intentdefinition` localization pool — non-existent on FS — replaced with the real `widget14.strings` + `widget14.intentdefinition` widget-intent pool; new-language fanout checklist corrected to `Localizable.strings` + `Localizable.stringsdict` + `InfoPlist.strings` + `widget14.strings`).
  - No new skip/audit rule; no `.strings` / `.stringsdict` value changes; no calibration delta. Verification = `make docs-check` (doc-only, no Swift touched).

## Beverage catalogue naming (cross-language)

Durable rationale for the 33-key drink catalogue (`mywater_ios …/DefaultBeverageCatalog.swift`, field `name` = corpus key). Newest first.

- *(The dated drink-name **changeset** — what was applied per language, when — is in
  `loc_audit_status.md`; the durable cross-language naming principles stay below.)*
- **`Soda` = sweet carbonated soft drink, NOT soda water** (cross-language trap). App data: catalogue `Soda` (drinkTag 4) carries `freeSugarGramsPer100Ml: 10.6` → sugary; ru co-source `Газировка`. A language whose bare "soda" denotes unsweetened soda *water* must use its soft-drink word: de `Softdrink`, pl `Napój gazowany`, ko `탄산음료`, da `Sodavand`, **tr `Gazlı içecek`**, **ms `Minuman ringan`**. Where bare "soda" already reads as a sweet drink (fr, ja, hi, ar; vi colloquial) it may stay. tr + ms were missed earlier because the `ms.md` / `vi.md` calibration profiles had sanctioned bare "Soda" (see next).
- **Calibration profiles legitimized an ambiguous term → anti-circularity rule.** `ms.md:161` ("`Minuman ringan` or `Soda`") and `vi.md:126` ("`Soda` … both fine") were AI-authored assertions sanctioning bare "Soda" for the sweet-soda item; caught only by external dictionaries (Malay/Vietnamese "soda" → soda *water*) + the catalogue sugar field, never by the corpus. Both profiles corrected 2026-05-31; provenance caveat added to `loc_audit_lang_calibration/README.md § Provenance & validation`. **Principle:** a doc written by the same agent class as the translations cannot independently verify them — validate against app code/data + external human authority, never by cross-checking one AI artifact against another.
- **Legacy key ≠ display value** (do NOT "fix" by renaming the key — [CR-KEY-NAME]): `Cicoriy`→"Decaf coffee" (chicory shown as decaf — a product-level en simplification, not a translation defect), `Boullion`→"Broth", `combucha`→"Kombucha", `cocnutWater`→"Coconut water", `Jogurt`→"Yogurt". Audit the value, not the key spelling.
