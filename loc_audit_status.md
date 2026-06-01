<!--
doc-role: status + execution log
doc-owner: loc_audit_status.md (mywater_localisation repo)
doc-scope: current per-language audit STATE (source of truth) + open follow-ups + the
  dated execution log for the localization value-audit & context-audit. Calibration
  rationale (skip/audit rules, binding decisions, anti-regression) is the sibling
  loc_audit_changelog.md. Neither file is read by the audit sub-agent.
-->

# Localization audit — status & execution log

> **How to read.** The **STATE table** below is the single source of truth for "is
> language X audited / applied / pushed / verified?". Do **NOT** infer current state from a
> historical entry in the execution archive — a past entry describes a moment, not now (the
> cost-blowup entry's "0 applied" was true only for that read-only workflow; the work was
> applied right after). Update the STATE table on every apply / push / verify.
>
> **Push ≠ verify.** A pushed value stays `unverified` until human / Lokalise review
> ([CR-CORPUS-UNVERIFIED]). As of **2026-06-01 `dirty` is empty corpus-wide** ⇒ every pass
> below is pushed; any per-entry "pending operator push" wording is **historical** — check
> `make push-dry` for the live backlog.
>
> **Auto-commit gotcha.** This repo auto-commits (`batch`), so `git diff` vs HEAD reads
> empty mid-session — verify a session's corpus work with
> `git diff <session-start-commit> -- strings.ndjson`.
>
> **Standing apply discipline (so entries below need not restate it).** Every applied pass
> below passed the standard gate: findings test-applied to a `--corpus` copy first
> (`unmatched=0`, changed-set == apply-set, 0 cross-language collateral), `make lint`
> (placeholder + qa) 0/0, serial single-writer apply (`loc_apply_lang` / `loc_audit_apply`),
> and the agent ran **no** `--apply` against Lokalise — the operator pushes ([CR-ACCESS]).
> Entries note only **deviations**, per-pass yield, and durable lessons.

## STATE — per-language audit status (source of truth; verified 2026-06-01)

| lang | role | last audit pass (date / vehicle) | fixes applied | pushed | review | open |
|---|---|---|---|---|---|---|
| en | source | 2026-05-31 Phase 6 (ru+en, Workflow) | 21 source-quote/calque | ✓ | n/a (source never `unverified`) | sv `pushRetention_3/10` en meaning-change → operator (cascades to 20 targets) |
| ru | co-source | 2026-05-31 Phase 6 | 42 | ✓ | unverified | — |
| pl | target (profile) | 2026-05-31 pilot + scoped | 17 + scoped | ✓ | unverified | — |
| ar | target (profile) | 2026-05-31 re-sweep salvage | 32 | ✓ | unverified | — |
| hi | target (profile) | 2026-05-31 salvage + scoped | 35 (+3) | ✓ | unverified | — |
| vi | target (profile) | 2026-05-31 salvage + glass/cup reconcile | 25 (+glass/cup) | ✓ | unverified | — |
| id | target (profile) | 2026-05-31 salvage | 22 | ✓ | unverified | — |
| ms | target (profile) | 2026-05-31 salvage + brand decision | 29 | ✓ | unverified | — |
| ja | target | 2026-05-31 salvage **+ ja-only full** | 16 → **102** | ✓ | unverified | 2 glossary-owner items → § OPEN follow-ups |
| da | target | 2026-06-01 re-sweep ¹ | ✓ ¹ | ✓ | unverified | ¹ |
| de | target | 2026-06-01 re-sweep ¹ | ✓ ¹ | ✓ | unverified | ¹ |
| es | target | 2026-06-01 re-sweep ¹ | ✓ ¹ | ✓ | unverified | ¹ |
| fr | target | 2026-06-01 re-sweep ¹ | ✓ ¹ | ✓ | unverified | ¹ |
| it | target | 2026-06-01 re-sweep ¹ | ✓ ¹ | ✓ | unverified | ¹ |
| ko | target | 2026-06-01 re-sweep ¹ | ✓ ¹ | ✓ | unverified | ¹ |
| nb | target | 2026-06-01 re-sweep | ✓ ² | ✓ | unverified | — |
| nl | target | 2026-06-01 re-sweep | ✓ ² | ✓ | unverified | — |
| pt_BR | target | 2026-06-01 re-sweep | ✓ ² | ✓ | unverified | — |
| sv | target | 2026-06-01 re-sweep | ✓ ² | ✓ | unverified | en-side pushRetention (see `en` row) |
| tr | target | 2026-06-01 re-sweep | ✓ ² | ✓ | unverified | — |
| zh_CN | target | 2026-06-01 re-sweep | ✓ ² | ✓ | unverified | — |

¹ da/de/es/fr/it/ko re-swept 2026-06-01 (clean, pushed); this log has no per-pass entry for
them — recover precise diffs via `git log -- strings.ndjson` if ever needed.
² Aggregate: **81 target-language fixes + 1 `en` source-quote fix across 62 keys**
(nb/nl/pt_BR/sv/tr/zh_CN, 2026-06-01 re-sweep; see the archive entry).

**21-language Opus-4.8 re-sweep: COMPLETE & PUSHED** — with **one** deliberately-deferred
item: the `en` meaning-change on sv `pushRetention_3/10` (clinical "water balance" on a casual
push) is left to the operator, since fixing `en` cascades to all 20 targets
([CR-CORPUS-SOURCE-CHANGE]); see § OPEN follow-ups. All targets are `unverified` (AI/edited,
awaiting human / Lokalise verification — operator/Lokalise-owned, NOT cleared by the audit;
[CR-CORPUS-UNVERIFIED]).

## OPEN follow-ups (the only place open items live; on close → strike + link the closing pass)

- **[glossary-owner]** `ja`: `full version` フル版 → フルバージョン (corpus-dominant); `glass`
  グラス vs measure-phrase 一杯 in ~5 keys (vessel keys keep グラス). — raised 2026-05-31 ja-only.
- **[glossary-owner]** `vi`: optional `cup`=`tách` glossary term to lock the glass/cup
  distinction (deferred — would need filling across 20 langs). — raised 2026-05-31 vi-cup.
- **[operator]** Backfill `Register: formal` onto the legal-binding key set (Terms / Privacy /
  subscription-legal / consent) so the auditor's legal carve-out keys off an authoritative
  flag, not Surface/Type heuristics. — raised 2026-05-30 (rev., `loc_audit_changelog.md`).
- **[operator — en meaning-change]** `en` sv `pushRetention_3` "water balance" /
  `pushRetention_10` "replenish your water balance" — clinical on a casual push; fixing `en`
  cascades to all 20 targets ([CR-CORPUS-SOURCE-CHANGE]) → deliberately not auto-applied.
  — raised 2026-06-01 nb/nl re-sweep.

**~~CLOSED~~:** vi `glass`→`cốc` (closed 2026-05-31 vi-glass); vi `cup`→`tách` collision
(closed 2026-05-31 vi-cup); "ja under-covered → future ja-only pass warranted" (closed
2026-05-31 ja-only full audit, 102 edits).

## Execution archive (dated passes — newest first; HISTORICAL, not current state)

> Older **Phase 0..5** execution log (19-lang sweep, 2026-05-15..16, COMPLETE) lives in
> `mywater_ios ai_reports/tasks/2026-05-17_localization_audit_phase0-5_execution_log.md`;
> per-language applied status is also recoverable from `git log -- strings.ndjson`.

- **2026-06-01 — Opus-4.8 Max re-sweep of the final 6 languages (`nb` / `nl` / `pt_BR` / `sv` / `tr` / `zh_CN`); 82 corpus edits across 62 keys (81 target + 1 `en` source-quote), `dirty`+`unverified` (the `en` edit `dirty`-only).** Completes the 21-language 4.8 re-sweep (prior entries cover en/ru/pl/ar/hi/vi/id/ms/ja + da/de/es/fr/it/ko). These 6 have **no calibration profile** (4.8 native-grade); the inline T-V/gender map + a lean run-scoped calibration sufficed — **no new profile** (no recurring FP class; same call as the ja pass). Vehicle: ONE full-context auditor + ONE independent validator + conditional doubt-resolver per language, single dynamic Workflow over the 6 langs (15 agents / ~3.3M tokens — within the `loc_audit_prompt.md § Workflow 0` ceiling).
  - **Yield — 81 target fixes (nb 13, nl 12, pt_BR 14, sv 8, tr 13, zh_CN 21).** Dominant class = **clinical "water-balance" calque on casual surfaces** (`vannbalanse` / `waterbalans` / `balanço hídrico` / `vattenbalans` / `su dengesi` on `text1_9` + `tip*` + `pushRetention_*`) where the proven `ru` anchor went plain — glossary `water balance` is feature-label/store only. **Genderless-M/F divergence** (nb/sv/nl/tr/zh_CN have no user-sex agreement → a *DIFFERING* `*M`/`*F` pair is the defect, like ja/ko — unified, keyed on the worse variant). **Two-directional brand consistency (nb):** base brand `My Water`→`Mitt Vann` (matches CFBundleDisplayName + siblings + ru) **and the inverse** — the FROZEN tier `My Water Premium` (glossary `translatable:false`) restored from a wrong `Mitt Vann Premium` (ZWNJ + `[%s]` + literal quotes byte-preserved). Plus: tr ASO `su takipçisi`→`su takibi` + grammar + V-form leaks on casual-T paywall/ASO; zh_CN CJK punctuation hygiene (half-width space after full-width `。/！/，/：`) + plural `streakDaysTitle` + stale `widgetText`; sv `newPasswordDontMatch` semantic bug + `Dagligt mål` glossary; pt_BR brand casing.
  - **Independent-validator value (not a rubber-stamp):** sv validator moved 2 to `en_findings` (the `en` SOURCE itself says "water balance" → faithful sv is not a target calque); nb validator caught the `My Water Premium` freeze **MISS** (4 keys the base-brand pass overlooked); pt_BR reduced an auditor over-reach to casing-only; zh_CN caught an ASC subscription-terms space MISS. Anti-circularity held — water-balance flags corroborated on the `ru` anchor + native grounds, not glossary authority alone.
  - **`en`-side ([CR-CORPUS-SOURCE-CHANGE]):** (a) **deferred to operator** (meaning-affecting → cascades to 20 targets): sv `pushRetention_3/10` "water balance" on a casual push (ru already plain) → § OPEN follow-ups. (b) **applied on operator request:** `achivmentTextShareVkM` `en` quote-structure harmonized to its VkF sibling (`\"My Water\"` quoted, `app` outside) — meaning-preserving, so no target blanking, no `ru` re-author, `en` stays verified (`dirty`-only).
  - **Deviation:** one `zh_CN` findings row's escaped pipe broke the findings-table parser (silently skipped) → applied via a corpus transform instead. The latent-bug guard is now in `loc_audit_changelog.md § Anti-regression mechanisms`.

> ⚠️ The "0 applied" in the blowup entry below was that **read-only** workflow only — the
> salvaged findings **were** applied (the SALVAGE+APPLY entry below + the ja-only pass).
> Don't read it as current state (§ STATE is the truth).

- **2026-05-31 — ⚠️ WORKFLOW COST BLOWUP (re-sweep of ar/hi/vi/id/ms/ja) — root-caused.** A workflow launched as a "1-batch pilot" silently ran the **full 6-lang × 7-batch set** before operator interrupt: **~87 agents / ~182M input tokens, 0 applied** (corpus untouched; findings salvaged to disk). **Two root-cause bugs:** (1) the pilot scope was a Workflow `args` override the script *defaulted past* when unread → it ran full scope **silently** (a pilot MUST be hard-capped **in-script** — `items.slice(0,1)` / `throw if >1` — never a defaulting arg; and verify the launched scope before reporting "pilot running"); (2) **deep-validate fan-out was per-finding (unbounded)**. This incident produced the binding cost/pilot guard → **`loc_audit_prompt.md § Workflow 0`** (one language per run; estimate-and-state agents×tokens; stop above ~40 agents / ~5M tokens; no unbounded per-finding fan-out). Salvaged findings were then validated + applied — see below.

- **2026-05-31 — re-sweep SALVAGE + APPLY (ar/hi/vi/id/ms/ja); 159 corpus edits, `dirty`+`unverified`.** Recovered the interrupted run's findings from disk (**0 new audit agents**), then ran the corrected lean vehicle: **6 validators (1 per language)**, each the final native-grade gate over its language's salvaged candidates (default-reject, non-circular anchors, spoken-plausibility test). **159 applied (ar 32, hi 35, vi 25, id 22, ms 29, ja 16)** = 155 validator-approved + 4 orchestrator gendered-sibling propagations (`vi text3_2M`, `ms text1_9M`/`text3_11M`, `ja text1_9M`). **ja under-covered** (only 1/7 verify batches ran pre-interrupt; unverified-audit remainder mostly rejected as restyle) → a future ja-only pass warranted **[CLOSED — the ja-only full audit below, 102 edits]**. **Open follow-up surfaced (vi validator):** glossary pins `vi glass = ly`, but the corpus uses `cốc nước` 37:2 → reconcile to `cốc` **[CLOSED — vi-glass entry below]**.

- **2026-05-31 — ja-only full audit (Opus 4.8 Max — the "future ja-only pass" the SALVAGE entry called for); 102 `ja` edits, `dirty`+`unverified`.** One full-context auditor over ALL 1261 keys in a SINGLE pass (to exploit the cross-key consistency the 7-batch split is structurally blind to — the pl-pilot FN class) → one skeptical native-ja validator → a doubt-resolver that **OVERRODE the auditor on 5 of 14** doubts (en-faithfulness + motivational-family distinctiveness beat the auditor's smoothing — e.g. `text4_19` kept "again tomorrow" distinct from `text4_18`, `text1_5` stayed en-faithful not ru-broadened) and a long-form-space resolver that kept **all 4** App-Store/legal strings unchanged (interior spaces are inter-sentence separators, not artifacts). Orchestrator pre-calibrated both with **evidence-derived** ja guardrails (divergent-M/F hotlist, interior-space hotlist cross-checked vs the zh_CN sibling), not blind glossary obedience.
  - **Yield — 102:** **44 genderless M/F pairs unified** (80 keys; ja has no gender → a *DIFFERING* `*M`/`*F` pair is the defect — now byte-equal); **13 interior-CJK-space removals** (artifacts — the zh_CN sibling omits the space in 43/48 of the same keys); **9 lexicon/consistency** (kana `出来ました→できました`, glossary `身体→体`, slang/clinical de-stiffening, legacy `完全版→フルバージョン`).
  - **NOT changed (guardrails — surfaced, not forced):** body-copy Latin **`My Water`** kept (35+ keys — the in-body wordmark is the JA-app convention; only the OS app name `CFBundleDisplayName`/`appName` localizes to 「わたしの水」, so the glossary's blanket "ja localizes My Water" is over-broad for body copy); the 6 ja plural keys are clean (ja CLDR = single `other`); plain ですます/丁寧体 is the correct casual default (no 敬語 leak); no em-dash / placeholder / invisible-char defect corpus-wide.
  - **Open follow-ups (glossary owner):** (a) `full version` ja **フル版 → フルバージョン** (corpus-dominant); (b) `glass` グラス vs the natural measure-phrase 一杯(35)/コップ(9) — vessel keys legitimately keep グラス, but 5 measure-phrase `グラス一杯` keys (`notification1_9/11/20/36`, `tip1`) could harmonize → § OPEN follow-ups. **No `ja.md` profile added** (4.8 caught the systematic defects unaided; no recurring FP class).
  - **Concurrent-edit note ([CR-CORPUS-WORKTREE]):** a concurrent session's vi-glass reconciliation (3 `vi` keys + glossary/`vi.md`/changelog) was in the working tree and **preserved byte-identically** (the ja apply reads-mutates-writes ja keys only; 0 collateral verified).

- **2026-05-31 — vi `glass` reconciled to `cốc` (CLOSES the vi-validator follow-up above); glossary + 3 corpus stragglers + `vi.md` aligned.** Re-derived **independently** (not majority-deference, per the operator's "don't trust AI-written docs" note): `cốc` is the standard-register / dictionary-headword word for a drinking glass — the pan-Vietnam default (no Southern/HCMC targeting to justify `ly`); the human-**verified** `glass` container key is `cốc`; verified-corpus consensus is **33 `cốc` : 2 `ly`** (the 2 `ly` are stragglers). `ly` survived **only** in AI-authored canon (glossary + `vi.md`) never cross-checked against the verified corpus — so the docs, not the corpus, were the outlier. **Applied:** glossary `glass` vi `ly`→`cốc`; `loc_apply_lang.py vi` on 3 keys (`pushRetention_16`, `glassOfWaterCharacter`, `shotGlass` `ly nhỏ`→`cốc nhỏ`); `vi.md` Units rewritten + all 8 illustrative `ly`→`cốc` (the calibration is read verbatim by the sub-agent — leaving `ly` would re-teach the drift). **Lower-confidence:** `shotGlass`→`cốc nhỏ` is a *different* container (trivial single-key revert if the operator prefers `ly nhỏ`).

- **2026-05-31 — vi `cup` disambiguated to `tách` (CLOSES the `glass`/`cup` collision above).** Operator confirmed the presets stay distinct (`glass` = water glass; `cup` = coffee/tea cup). Re-derived from the **verified corpus** (not the calibration doc's suggestion): the project already renders "Cup"/«Чашка» as `Tách` in the verified `beverageCharacter` (and "Mug"/«Кружка» as `ca`/`cái ca` in `mugCharacter`) — only the `cup` *preset* had drifted to `cốc`, colliding with `glass`=`cốc`. **Applied:** `cup` `cốc`→`tách`. Container vocabulary now distinct: **`cốc`** = water glass [`glass`, `shotGlass`, `glassOfWaterCharacter`]; **`tách`** = coffee/tea cup [`cup`, `beverageCharacter`]; **`ca`/`cái ca`** = mug. **Optional:** a glossary `cup`=`tách` (vi) term — deferred (needs filling across 20 langs) → § OPEN follow-ups.

- **2026-05-31 — Phase 6 Opus-4.8 re-sweep — `ru` + `en` full pass (Workflow); 62 keys (42 `ru` `dirty`+`unverified`; 21 `en` `dirty`, source-only, never `unverified`).** Vehicle: dynamic Workflow, pipeline FIND → CONFIRM → DOUBT (per-language validators → skeptical confirm → per-phrase doubt validator). **64 confirmed → 60 applied / 4 rejected; 0 en meaning-changes (cascade-safe).** Classes: clinical/AI-tone destiff (`tip5/8/9`, `notification1_29`), film-dub calque (`text4_13` «Ты сделала это»→«У тебя получилось»), wrong-sense (`soundMessage` «Весна» season→«Пружина» spring-coil), brand freeze/localize (`watchPremiumSubtitle`→`Premium`; `NSHealthUpdateUsageDescription` `My Water`→«Моя вода»), glossary consistency, single-key gender mis-agreement (`tempFirstSteps`), legal-block mixed register (`termsSubscriptionDescription`), en RU→EN reverse-calque (`yourOwnGoal`, `ourSocialNetworks` →social media, `socialShareTextVk`, `drinksReorderTitle`). Orchestrator added 5 gendered-sibling propagations.
  - **Em-dash policy refined (operator decision):** default replacement is now **restructure** (colon/period/comma per the `en` value, or drop the connector), NOT a mechanical hyphen swap (`-` is a fallback only); `—` U+2014 stays a `loc_qa.py` ERROR. Canon → `TRANSLATION_STYLE.md § Punctuation`; skip rule #15 synced.

- **2026-05-31 — Phase 6 Opus-4.8 re-sweep PILOT on `pl` (Workflow); 17 corpus edits, all `pl`, `dirty`+`unverified`.** Vehicle: dynamic Workflow, 7 batches, each a calibrated audit sub-agent (injection order: header → `loc_audit_glossary.py pl` checklist → `pl.md` → prompt, all verbatim) → skeptical-native adversarial validator. **Yield — 14 audit + 3 cross-batch propagation = 17.** High-value: `NSUserTrackingUsageDescription` (ATT purpose-string **semantic loss** — pl dropped the advertising-partners + performance-measurement components; compliance), the **feed-style naming bug** (4 keys), `liveActivity*` brand-localization (4 keys → «Aktywność na żywo»), and the Принцип #3 clinical-calque class (`siriShowHydration*` `nawodnienie`→plain, `pushRetention_14` `bilans wodny`→plain — the glossary lane working as designed).
  - **1 REVERSED — `appstore_appname` (auditor FP the validator wrongly ACCEPTED; do NOT re-flag).** Auditor froze the pl brand to English `My Water Balance:` citing the key's `context` "keep untranslated as a proper noun" line. Reverted byte-identical to `Mój Bilans Wodny:` on **three** independent grounds: (a) glossary — `My Water` is **localized** (pl `Moja woda`), `water balance` is `bilans wodny`, and there is **no** frozen `My Water Balance` term; (b) **all 20 locales localize it** (freezing pl = the lone English outlier); (c) the binding operator decision keeping the sibling `appstore_app_title` localized. **LESSON:** a `context` Constraints line is NOT authoritative over the glossary + sibling-locale renderings + a prior operator decision; a brand-FREEZE finding must cross-check those three before accept.
  - **2 systemic vehicle findings (anti-regression; rule canonized in `loc_audit_changelog.md § Anti-regression mechanisms`):** (a) **FN class — per-batch isolation is blind to cross-key consistency:** `feed` (batch 3) renamed the pl picker label `Nowoczesny`→`Aktualności`, orphaning **3 sibling `*TrackingFeedOnlyMessage` strings** (alcohol/caffeine/sugar) in other batches; no agent caught it (different batches), the orchestrator propagated all 3 (ru is internally consistent). A full-20 run needs an explicit **cross-batch reconciliation phase** before apply. (b) **Auditor cold-start hallucination:** the batch-1 auditor emitted 2 invalid StructuredOutput calls naming **fabricated keys** before reading its input, then self-corrected; the replace-only + copy-precheck invariant (`unmatched=0`/`added=0` on a copy) backstopped it — keep it.
  - **Scope read for Phases 6.x:** `pl` is the best-calibrated, "cleanest" language and **still** yielded 17 real fixes incl. a compliance defect and a functional bug; a **Tier-1-narrow** scope (glossary + calque + register only) would have **MISSED** the two highest-value finds (both `semantic-drift`) → the full audit, not the narrowed lane, + the reconciliation phase, all 20 languages language-by-language with serial apply.

- **2026-05-31 — scoped ar/hi audit, ms brand decision, + CORRECTION of the `text1_9` clinical-calque rejection:**
  - **CORRECTION (reverses the `text1_9` rejection recorded in `loc_audit_changelog.md § pl calibration profile added`, the "2 REJECTED" clause).** That entry recorded `text1_9` (`bilans wodny`) as a non-defect ("faithful to en, context-sanctioned per skip #6"). **That was wrong — now reversed.** On a casual motivational surface `bilans wodny` is a **clinical calque**: `TRANSLATION_STYLE.md` Принцип #3 bans `водный баланс` **+ equivalents даже если технически правильно**, so "faithful to en" is the *overridden* defense; `ru` proves the surface split (clinical on the feature label + store, **plain** in all motivation/push). **Root error:** skip #6 needs an explicit *preserve* directive; the `text1_9` comment merely *glosses* the en term and is tagged `Register: casual T-form` — a denotation-gloss is **not** a skip-#6 sanction. **The operative test is surface register, not literal en-fidelity.** **Applied (plain, casual T-form):** pl `text1_9M/F`=`Pij wodę regularnie!`, `pushRetention_3/4/10/15` de-clinicalized; hi `text1_9M/F`=`पानी पीते रहो!`. `pl.md`'s calque example corrected (had cited the wrong en).
  - **ms brand — KEEP localized «Air saya» (corrects `ms.md`).** Per `glossary.ndjson` the brand is localized per-locale (17/21 locales; ar/id/vi keep Latin). `ms.md` skip-rule #1 wrongly grouped `My Water` with the verbatim Apple brands → corrected: `My Water`→`Air saya` is LOCALIZED (do not flag / do not revert to Latin). Casing standardized to glossary-canonical sentence-case `Air saya` (the lone Title-case `appstore_appname`→`Air saya`). Native-Malay sub-agent confirmed.
  - **Scoped ar/hi (validated):** ar's 6 CLDR plural keys + hi split-ergativity across 58 M/F pairs confirmed clean (the grammar detail lives in `ar.md`/`hi.md`). 3 non-gender hi defects found + fixed: `achivmentTextShareVkM/F` brand `मेरा पानी`→`My Water`, `socialShareTextVkM/F` over-escaped `\\"`→`\"`, `text3_6M/F` gratuitous M/F divergence aligned.
  - **Profiles decision:** keep the 6; add none (ar/ko/zh clean on deterministic markers; ja/ko/zh/tr deferred — no recurring-FP evidence).


---

### Context-audit sub-workstream (translator `context` field)

Durable calibration for the **`context`-field** audit (workflow + prompt: `loc_context_audit_prompt.md`; deterministic pre-lint: `loc_context_lint.py`). Distinct from the value-audit above — this audits the translator description, not the translations. Newest first.

- **2026-05-31 — Tier B cap-grounding (resolves the deferred ~31 caps); 28 `context`-only keys.** A deterministic fan-out workflow grounded each deferred cap against its iOS/Android render sites. **Outcome on the 31 deferred: 28 → relax (applied), 3 → KEEP (FP).** **Grounded finding:** no render site has a real hard character limit (labels wrap / `adjustsFontSizeToFitWidth`; nav-bar & notification-action titles system-truncate; store keys are external metadata; the widget is WidgetKit-owned) → each invented `≤N chars` was replaced with a grounded qualitative `Constraints:` line that preserves real non-numeric constraints (literal `[%]` on `offBigLabel`, trailing `?` on `notReady`, "Restore purchases" wording on `restoreButton`, do-not-translate brand on the store keys). **3 FALSE POSITIVES (KEEP; do NOT re-adjudicate):** `runningManCharacter` (en "Man"), `womanFullFaceCharacter` (en "Woman"), `shortQuerySearch` ("Please enter more than 3 characters…") — none carries a `Constraints:` line; the linter inferred a "cap" from value length / the "3 characters" prose. Workflow agents READ-ONLY; the 28 edits applied agent-free via `loc_apply_meta` (only the `Constraints:` line changed per key).

- **2026-05-31 — Tier B (deep LLM audit on linter-flagged keys); 8 `context`-only keys.** Tier-0 signals: cap_violations ×44, register_inconsistent ×5, placeholder_unexplained ×1. **8 edits**; remainder KEEP (FP) or deferred (now resolved by the cap-grounding entry above).
  - **Screenshot-caption caps relaxed (7):** all `platforms:["other"]`, `Type: screenshot caption` — marketing headlines baked into App Store images by design, not app-rendered, so the `(≤N chars)` cap has no enforceable limit and the longest shipped translation already exceeds it → removed the numeric parenthetical, kept the qualitative "fits screenshot headline on one line".
  - **`signUpButton` Register added (`casual T-form`):** the primary imperative submit-button CTA lacked a Register line (sibling `signUpButton2` already had one); `signUpButton1` ("Don't have an account?") left as-is (different surface — paragraph/inline-question — so same-surface family consistency does not bind it, skip #5).
  - **FP categories (do NOT re-adjudicate):** web/server validation caps (`short_login` ≤5, `short_password` ≤6, `long_name` ≤30, `invalid_transaction_id` ≤30, `too_short_query_param` ≤3) carry **no** `Constraints:` cap — the linter misreads the "N characters" prose as a limit; context is accurate, KEEP. `appstore_app_keywords` ≤100 is the **REAL** ASC keywords hard limit — KEEP (the 140-char `id` over-length is a value-layer defect, out of context scope). `statisticsBeverageTimeOfDaySubtitle` `[%]` is a **literal** percent ([CR-PLACEHOLDER]), not a runtime placeholder — KEEP (the linter should exclude `[%]`).

- **2026-05-31 — Tier A (deterministic / boilerplate fixes); 19 `context`-only keys** (building on 11 pilot-baseline keys committed earlier).
  - **notification1 boilerplate de-dup (15 keys `_10`…`_24`):** removed the fabricated `Constraints: Keep within ~80 characters to fit a single-line iOS notification banner` line — verified false against iOS code (the reminder body is a multi-line `UNMutableNotificationContent.body` with title + optional subtitle + rich long-look; no single-line/80-char limit anywhere; the standard pool is `(1...51)`). Only 15 of 51 carried the false line; removal made the family uniform.
  - **text1 / text4 Surface harmonization (35 keys):** both families carried Surface drift; harmonized each to one pilot-blessed canonical read verbatim from a reference key (**only** the Surface line changed; per-key Context/Type/Register/Tone preserved).
  - **surface-mismatch — the linter signal is HIGH-NOISE (44 flags → 2 real, ~42 FP); do NOT re-adjudicate.** The FPs are all legitimate **non-surface grounding** (skip #6): (a) VC-vs-VM same screen; (b) SDK/framework type as mechanism (`HKQuantityTypeIdentifier`, `UIApplication`, `UIAccessibility`, `StoreKit`); (c) data-source / formatter / service ref; (d) destination ref (the screen the string OPENS, not where it renders); (e) multi-surface / app-wide atom; (f) error-enum ref; (g) sibling-key ref; (h) a11y-id namespace; (i) prose mis-tokenized (`Mail`, `FitBit`). **2 real fixed:** `month` (cited Statistics period picker is false → renders in the Weight chart Month/Year toggle), `liveActivity` (cited Settings→App Style is false → Settings→Notifications).
  - **dead-citation (5 → 2 real):** `yourHeight`/`yourAge` cited `OnboardingHeightViewController` but the real file is the misspelled `OndoardingHeightViewController.swift` (a typo in the iOS source itself) → dropped the misspelled class. FPs (KEEP): `SpecialPrie` (a documented key-name typo), `R.swift` (the codegen library), `ShareKit` (= `FBSDKShareKit`).
  - **Linter de-noising (done this pass):** added `UIApplication`/`UIAccessibility`/`HKQuantityTypeIdentifier`/`StoreKit`/`A11y` to `loc_context_lint.SDK_ALLOW` + `R.swift` to a new `SWIFT_FILE_ALLOW` → surface_mismatch 41→33, dead 3→2. The semantic categories above stay LLM-adjudicated (a global allowlist there could hide a real mismatch) — they are the confirmed-FP list, so Tier B need not re-derive them.


---

### Beverage catalogue — drink-name changeset (value-layer)

> Durable cross-language naming **principles** (Soda trap, anti-circularity, legacy-key≠value) are in `loc_audit_changelog.md § Beverage catalogue naming`.

- **2026-05-31 — drink-name changeset (8 edits / 5 langs), value-layer.** Applied via `loc_apply_lang` (serial, one lang at a time): tr `Soda→Gazlı içecek`, `Boullion`(Broth) `Kemik suyu→Et suyu`; ms `Soda→Minuman ringan`, `Other→Lain-lain`; da+nb `limonade Lemonade→Limonade`; vi `Soda→Nước ngọt`, `proteinShake Sinh tố protein→Sữa lắc protein`. All `dirty+unverified` — await human-native verify (NOT operator-cleared). Grounded in **external dictionaries + app catalogue data**, never corpus self-reference. NOT applied (operator's call): tr Title-Case normalization of the drink set; tr `Compot` `Hoşaf` vs `Kompot`/`Komposto`.
