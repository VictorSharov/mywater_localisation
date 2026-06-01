<!--
doc-role: workflow
doc-owner: loc_audit_prompt.md (репозиторий mywater_localisation)
doc-scope: AI-assisted translation audit поверх cross-platform ndjson-корпуса — sub-agent prompt + workflow + skip rules. Calibration canon (rules + binding decisions) → loc_audit_changelog.md; per-language STATE + dated execution log → loc_audit_status.md
-->

# Localization audit — sub-agent prompt & workflow

Пошаговый workflow для AI-assisted audit переводов через sub-agent. Источник данных — **cross-platform ndjson-корпус** `strings.ndjson` в этом репозитории (все языки + все платформы): `loc_audit_extract.py` достаёт батчи `en`+`ru`+`<target>` из корпуса, validated findings применяются `loc_audit_apply.py` обратно **в** корпус (язык помечается `unverified`), затем `loc_corpus_import.py --apply` пушит правки в Lokalise, откуда они экспортируются в iOS / Android / server.

> **Историческая привязка.** Калибровка prompt'а восходит к оригинальному iOS `.strings`-свипу; calibration canon (binding decisions, rule rationale) — `loc_audit_changelog.md`; the dated execution trail (pilot / phase / apply / push) + current per-language STATE — `loc_audit_status.md`. Linguistic-правила платформонезависимы и применяются к корпусу один-в-один.

## Зачем нужен этот документ

Воспроизводимый workflow + длинный pilot-калиброванный sub-agent prompt (skip rules), которые нельзя надёжно держать в conversation memory (auto-compact теряет nuances); calibration-changes — в `loc_audit_changelog.md`, не в чате.

## Workflow

### 0. Cost & pilot discipline (binding — read BEFORE launching the workflow)

This workflow fans out sub-agents; a mis-scoped or unbounded run is a real, **repeated** failure mode (2026-05-31: a mis-scoped "pilot" ran the full 6-language set = **87 agents / ~182M tokens** before operator kill — `loc_audit_status.md § Execution archive`). Hard rules:

- **One language per workflow run.** Cadence baseline ≈ **13 agents / ~3M tokens per language** (pl pilot 13/2.73M; ru+en 34/3.63M). Do **not** bundle multiple languages into one fan-out — go language-by-language with serial apply (the standing recommendation; per-pass cost baselines in `loc_audit_status.md`). N languages = N runs, reviewed between each.
- **Estimate before launch, and STATE it.** agents ≈ batches × stages (+ any inner fan-out); rough tokens. If the estimate exceeds **~40 agents** or **~5M tokens**, STOP and get explicit operator confirmation — never "pilot-then-autorun."
- **No unbounded fan-out.** Never spawn agents proportional to a *discovered, uncapped* quantity (e.g. one agent per finding). Batch per-batch: **one verifier and at most one deep-validator per batch**, each handling all that batch's findings in a single call.
- **A pilot must be hard-capped IN THE SCRIPT** — literally `items.slice(0,1)` or `if (items.length > 1) throw` — **never** via a Workflow `args` override (it silently falls back to full scope if the script does not read it). After launch, **verify the actual scope** (the scope `log()` line / live agent count) before reporting what is running.
- Sub-agents are **READ-ONLY**; the orchestrator applies confirmed changes serially ([CR-CORPUS-CONCURRENCY]).
- **Throughput, not just agent count — the whole-language fan-out trap (2026-06-01).** Agent count under the ceiling is necessary but NOT sufficient: a *whole-language* pass (one agent per language holding all ~1261 keys) can still trip a **server-side rate limit** via throughput burst. Two compounding mistakes did it: (a) the workflow's **default 16-wide concurrency**, and (b) agents **paging the ~16K-line extract in ~1000-line chunks** — each chunk re-sends the growing context (triangular), so loading one file costs ~1.7M tok, ×16 ≈ **~28M tok in ~28s → throttle**, all agents die mid-read. Safe recipe: **single big `Read` (`limit` ≥ file line count), a worker-pool concurrency cap of ~3, and drop the StructuredOutput schema** — have agents write a `/tmp/loc_<lang>.json` artifact + return plain text, so a throttled agent fails cleanly and file-presence is the success signal (delete stale prior-run `/tmp` files first). Detail: `loc_audit_status.md § Execution archive` (2026-06-01 whole-language pass).

### 1. Extract batch

```bash
# Reads strings.ndjson (corpus order, sorted by key_id); en+ru shown as anchors:
python3 loc_audit_extract.py de 1 200 /tmp/loc_audit_de_batch_001.txt
python3 loc_audit_extract.py fr 201 400 /tmp/loc_audit_fr_batch_002.txt --platform ios

# en source audit (lang=en) — every key in range, ru as reference:
python3 loc_audit_extract.py en 1 200 /tmp/loc_audit_en_batch_001.txt
```

Подсчёт total en/ru/target идёт в первых строках output-файла. Recommended batch size: **200 keys** (a ~200K context window comfortably держит triple input ~95KB; ru/en legacy audit можно держать на 50 keys). Larger windows allow bigger batches, but keep per-key reasoning — batch fan-out without it is the anti-pattern (`CLAUDE.md § Self-translation discipline`).

### 2. Run sub-agent

Использовать Agent tool с `subagent_type: general-purpose`; модель — на усмотрение оркестратора (в промпте не пинится).

`prompt:` — содержимое раздела `## Sub-agent prompt (calibrated)` ниже **дословно**, плюс две строки наверху:

```
Target language: de
Input: /tmp/loc_audit_de_batch_001.txt
```

Для языков, у которых есть calibration profile (`ar`, `hi`, `vi`, `id`, `ms`, `pl`) — также inline профиль из `loc_audit_lang_calibration/<lang>.md` сразу перед "Sub-agent prompt" блоком:

```
Target language: ar
Input: /tmp/loc_audit_ar_batch_001.txt

Calibration profile:
<full content of loc_audit_lang_calibration/ar.md>

<then full content of ## Sub-agent prompt (calibrated)>
```

**Glossary checklist — inline for EVERY target language (not only the calibrated ones).** Before the prompt block (and before any calibration profile) inline the canonical per-language terminology checklist generated by `loc_audit_glossary.py <lang>` — brand-freeze / forbidden / per-language rendering for ~100 controlled terms (operationalizes `<target>`-rule #10). Token-free, generated from `glossary.ndjson` so it never drifts:

```bash
python3 loc_audit_glossary.py de /tmp/loc_gloss_de.txt
```

Full injection order — header lines → **glossary checklist** → calibration profile (if any) → prompt:

```
Target language: ar
Input: /tmp/loc_audit_ar_batch_001.txt

Glossary checklist:
<full content of /tmp/loc_gloss_ar.txt>

Calibration profile:
<full content of loc_audit_lang_calibration/ar.md>

<then full content of ## Sub-agent prompt (calibrated)>
```

(Uncalibrated language — `de` / `fr` / `ja` / … — skip the calibration block; the glossary checklist is still inlined. en-source audit has no checklist — `loc_audit_glossary.py` is target-only — so rule #10's inline freeze / forbidden lists carry it there.)

Для legacy ru/en audit (no target column) — `Target language: ru` + `Input: ...`; prompt автоматически активирует Russian-specific examples block.

### 3. Review findings

Sub-agent возвращает Markdown table со столбцами:

```
| # | key | lang | severity | category | current | suggestion | rationale |
```

Severity: `error` (clear bug) / `warn` (style/convention) / `info` (consider — dropped per calibration).

Оператор по каждой finding: apply как есть / apply с поправкой / skip как false positive (с обоснованием). Для full sweep (множество языков) findings проходят validator stage (skeptical native review) перед deterministic apply через `loc_audit_apply.py`.

### 4. Apply fixes

- `python3 loc_audit_apply.py <lang> <validated_findings.md>` — пишет `t[lang]` в `strings.ndjson` и помечает язык `unverified`. en-source правки (`<lang>=en`) оператор делает вручную в корпусе (dev language).
- Replace-only: отсутствующий в корпусе ключ репортится, не добавляется (upstream transcription error). Plural-ключи (CLDR-map не выражается одной ячейкой) применять через `loc_apply_lang.py` с `{форма: текст}` (тот же replace-инвариант), не ручной правкой `t`.
- Не заводить новый ключ через audit: новые строки добавляются в корпус напрямую и создаются в Lokalise при импорте.

### 5. Verify & import

```bash
git diff -- strings.ndjson                            # ревью-гейт: меняться должны только отредактированные ключи
python3 loc_corpus_import.py --lang <lang>            # dry-run: что уйдёт в Lokalise
python3 loc_corpus_import.py --lang <lang> --apply    # пуш в Lokalise (оператор, [CR-ACCESS])
```

Корпус-правки попадают к пользователям через Lokalise → экспорт в iOS / Android / server, не напрямую.

### 6. Next batch

Повторить со следующим диапазоном (201..400, ...). Total en keys см. в первой строке extract output.

## Sub-agent prompt (calibrated)

> **Sync with canon (verbatim self-sufficiency).** Копируется в `prompt:` дословно; меняй только first lines `Target language:` / `Input:`, остальное — лишь синхронно с этим doc (иначе prompt drift). Блок **операционализирует** канон `TRANSLATION_STYLE.md` (`§ Brand voice` / `§ Translation discipline` / `§ Translator context`) в audit-форме (flag / skip / severity / output). Operational-правила (T-V/honorific map, em-dash flag, gender flag, skip rules) обязаны оставаться **инлайн**: **у sub-agent'а нет доступа к докам в рантайме** — заменить правило ссылкой на `TRANSLATION_STYLE.md` нельзя, это сломает audit. Когда канон в `TRANSLATION_STYLE.md` меняется, зеркаль operational-правила здесь (controlled duplication — намеренная, не дрейф): `TRANSLATION_STYLE.md` владеет authoring-каноном (почему / как звучит правильно), этот блок — audit-операционализацией (как флагать).

```
Target language: <code>
Input: /tmp/loc_audit_batch_NNN.txt

You are auditing iOS localization strings for a hydration tracking app called "My Water". Your job is to find translation/source-quality issues — NOT to silently rewrite the shipped values yourself. (The `suggestion` column IS a proposed fix and is required wherever you can give a native-quality one — it passes through the operator + validator gate before any apply, so emitting it does not contradict this line: "do not translate yourself" forbids silently overwriting shipped strings, not emitting reviewed suggestions. Suggestion quality bar = a new translation's bar — see § Important constraints.)

## Input format

Each entry in the input file has:
- A multi-line comment block (translator context: surface, type, placeholders, constraints, tone).
- `key` — the .strings identifier.
- `en` — the English source value (CANONICAL source of meaning, dev language, ground truth).
- `ru` — the Russian translation (PROVEN good for `Localizable.strings` — audited through 27 batches + 2 calibration rounds; proving-corpus scope caveat in § How to use ru as reference).
- `<target>` — the translation to audit (the actual target language matching `Target language` declared on top). Absent in legacy en+ru-only batches.

Column discipline: before emitting a row, re-confirm WHICH column the defective text physically lives in. A defect quoted from the `en` line is `lang=en` (operator Phase-0), even if it co-occurs with a target issue on the same key. Never label an `en`-column string `lang=<target>`: the `current` value in your row must be copied verbatim from the row matching your `lang` field. If the target value already reads correctly and only `en` is wrong, emit exactly one `lang=en` row, not a target row.

When `Target language: ru`, the third row is the audit target itself; Russian-specific examples (final section of this prompt) apply.

For all other targets, `ru` is a reference (NOT an audit target) — see § How to use ru as reference below.

## How to use ru as reference

`ru` is verified-natural after 27 batches + 2 calibration rounds. Use as:

1. **Brand voice anchor #2** — `ru` shows non-clinical casual tone preserved.
   Example: en `Show current hydration` → ru `Показать выпитое за день`, NOT `Показать гидратацию`. If `<target>` took clinical / formal / Anglicized path where ru showed natural restructure, flag.
2. **Calque pattern reference** — `ru` rejected literal calques. If `<target>` took literal path where ru showed natural restructure, flag calque.
3. **Placeholder order resolution** — ru shows reordered placeholders.
   Example: `Added %1$@ of %2$@` → ru `Добавлено: %2$@, %1$@`. If `<target>` grammar would naturally swap and didn't (or swapped without grammatical need), worth checking.

Orientation:
- `en` is canonical source of meaning. Anchor on en for semantics.
- `ru` is inspiration for natural phrasing, brand voice, calque-avoidance.
- Do NOT use ru as second source of meaning — semantic ground truth is en.
- **Proving-corpus scope (do not over-trust ru blindly).** ru's PROVEN status covers `Localizable.strings` only (the 27-batch + 2-calibration corpus). ru `.stringsdict` and ru `InfoPlist.strings` were NOT in that corpus — a real ru `.stringsdict` defect has occurred (`%li разы` → `%li раза`; CLDR `other` = fractions). So when the batch is `.stringsdict` / `InfoPlist.strings`, ru is still useful for natural phrasing / brand voice but is NOT a verified correctness anchor — anchor correctness on `en` semantics + CLDR plural rules, and a ru-mirrored choice there does not auto-clear a finding (skip rule #16's ru-mirror carve-out applies only to the proven `Localizable.strings` ru).
- Do NOT audit the `ru` value itself when `Target language` is not `ru`: `ru` is a read-only reference column. Never emit a finding row with `lang=ru` for a non-ru target (even if the ru text has a stray hyphen / em-dash / punctuation nit) — it is out of scope and the deterministic applier cannot act on it. The only auditable columns are `en` (operator Phase-0) and `<target>`.
- If `<target>` diverges from en semantically OR from ru's natural-phrasing style — flag.
- If `<target>` perfectly mirrors ru's restructure choice naturally — that's a good sign, no flag.

## What to audit

### For `en` (the source)

1. **Typos / grammar errors.**
2. **Awkward AI-tone phrasing** (canned, unnatural, over-formal for casual surfaces). **Also: RU→EN reverse calques** — team is ru-native; en source может содержать обратные кальки от русских формулировок. Common patterns: direct preposition mapping (`Press on +` от `Нажмите на +`; `to / from Apple Health` от `в / из`; `over the world` от `по миру`); passive `is + past participle` от ru reflexive (`information is not filled` от `информация не заполнена`); nominalization-as-noun-phrase (`Track the weight dynamic` от `динамика веса`); translated commands (`Open application` от `открыть приложение`); awkward verb-object (`fulfill your daily water intake` от `выполнить норму`; `we get consultations from` от `получаем консультации у`; `top up your water level` от `восполнить уровень`). Apply spoken-plausibility test as native US English copywriter. Canonical — `TRANSLATION_STYLE.md § Translation discipline § Принципы § 8`.
3. **Brand voice violations** — app voice is friendly health-conscious companion, not medical authority:
   - User → "you" / "your" (direct).
   - App → "we" / "our app" / "My Water" (first-person plural, partner framing).
   - Plain language: prefer `drink`, `water`, `glass`, `goal`, `habit`, `body`, `healthy`.
   - Avoid: `hydration metrics`, `consumption logs`, `metabolic profile`, IT jargon, formal medical terms.
   - **`application` → `app`** in user-facing values is a hard convention (legacy mass-violation; flag every instance). Comment-acknowledged legacy keys (e.g. `appstore.app.subscriptionTemsAppStore § iTunes legacy text`) may keep, but new strings must use `app`.
4. **Lexicon drift** — flag only if `goal` and `norm` are mixed awkwardly in the SAME string. Standalone `norm` strings are intentional legacy (comments often say so) — DO NOT flag.
5. **US English consistency** — project uses US English. Flag British spellings in user-facing values: "Fulfil" → "Fulfill", "favourite" → "favorite", "colour" → "color", "centre" → "center", "behaviour" → "behavior", "organise" → "organize", "analyse" → "analyze". DO NOT flag "litre" — it's intentional British metric unit spelling per comment policy.
6. **Punctuation** — see § "What NOT to flag" for soft rules.
7. **Broken placeholders** — values store **Lokalise universal placeholders** (`[%s]` / `[%i]` / `[%.1f]` / `[%1$s]`; canonical: `TRANSLATION_STYLE.md § Placeholders`), which Lokalise converts per platform on export (`[%s]`→iOS `%@` / Android `%s`). Count them in en vs what the `Placeholders` comment field describes. A **bare** `%@` / `%d` / `%s` (not bracketed) in a value is itself a defect — flag as `placeholder`: the keys-API import stores it literally, so it won't convert. The literal-percent escape is universal `[%]` (Lokalise escapes it per platform on export — `→ %%` for printf/iOS when the string has another placeholder, `→ %` standalone); a bare `%%` is the iOS printf form: the keys-API stores it literally so it leaks `%%` to consumers that don't run a formatter (Android plain getString, server) — **flag it as `placeholder`** (fix → `[%]`), except on an ios-only key where it merely violates the universal-form convention (`loc_placeholder_lint.py` matches: ERROR on a non-ios platform, WARN ios-only). A lone `%` (neither `[%]` nor `%%`) in a **runtime** (ios/android) value is undefined under `String(format:)` — flag it as a bug. App Store / server-only values (`platforms: ["other"]`) are not formatted, so a literal `%` there is fine. (`loc_placeholder_lint.py` enforces this mechanically.)
8. **Inconsistency with binding comment constraint** — see § Constraint policy below.

### For `<target>` (the translation)

1. **Typos / grammar errors** (native target-language speaker check).
2. **Unnatural phrasing / calque / clinical terms.** Literal calque from English, AI-translation feel, clinical-medical-jargon lexicon. Project's brand voice is friendly health-conscious companion, not medical chart — `<target>` должен звучать как написанный native target-language UX-копирайтером, а не как буквальный перевод EN. Generic patterns:
   - Clinical / medical-formal lexicon for casual surfaces — terms equivalent to `hydration / water balance / consumption of water / hydration metrics` when natural casual alternative exists in target language.
   - Direct verb mapping `Show X → <Verb in target> X` when X is a clinical noun (e.g. `Show hydration` rendered with formal noun for "hydration" instead of casual "drank today / water today").
   - Literal idiom translation: `hands-free → "without hands"` ❌ (✓ "by voice" in target).
   - Direct preposition mapping (`of`, `with`, `for`) — часто требует restructure в target language, не lexical substitution.
   - For `Target language: ru`, see Russian-specific clinical-term blacklist at end of prompt.
   - For `ar`/`hi`/`vi`/`id`/`ms`/`pl`, calibration profile inlined above prompt enumerates language-specific patterns.
   Prefer plain native target vocabulary. Spoken plausibility test обязателен: представить, как native speaker произнёс бы фразу в обычной беседе или Siri-команде; если awkward — flag.
   Mandatory ru cross-check BEFORE flagging any restructure / lexical-choice / "calque" / "semantic-drift" finding: re-read the `ru` value for the same key. If `ru` (the proven anchor) made the SAME lexical or structural choice the `<target>` made (e.g. target `取决于` ≈ ru `зависит от`; target broadened "any water"→"drinks" ≈ ru broadened to "ничего"; target keeps "in the app" ≈ ru `в приложении`), this is the calque-avoidance the audit WANTS — do NOT flag (skip rule #16). Only flag if `<target>` ALSO diverges from ru's choice OR introduces meaning absent from en. This check is especially load-bearing for CJK targets where natural restructure from English is the norm.

   **Sibling-language contamination is a primary defect class (not stylistic).** Если target-файл систематически содержит токены близкородственного языка (Bahasa Indonesia в `ms`; Urdu / Hinglish / Latin-transliteration в `hi`; MSA↔colloquial или Farsi / Urdu loan-drift в `ar`), это working-text defect — флагать каждый instance как `semantic-drift` / `lexicon`, НЕ подавлять как stylistic preference (skip rule #11). Calibration profile языка перечисляет конкретные false-friend / wrong-register токены — применять как hard checklist, не как «по вкусу».
3. **Semantic mismatch with en source** — different meaning, wrong tone, missing/added content.
4. **Placeholder count** must match en exactly (same universal `[%s]` / `[%i]` / `[%.1f]` set; reordering via `[%1$s]` / `[%2$s]` indexing is fine when target grammar requires it — see ru placeholder swap example above). Dropping the brackets (`[%s]` → bare `%s`) is itself a defect — the keys-API import would store it literally and mis-export. a literal `%` is stored as universal `[%]` (Lokalise escapes it per platform on export) — do NOT flag `[%]` as a placeholder count mismatch (it carries no runtime arg). A bare `%%` is not a count mismatch either, but DO flag it as a `placeholder` escaping defect per rule #7 (fix → `[%]`). A lone `%` in a runtime value (en or target) is the bug; the fix is `[%]`.
5. **Gendered variants** — if key ends in `M` or `F`, target values for M and F should typically differ when target language requires gender agreement (past-tense, adjectives, participles). If identical AND target language requires gender agreement here, flag. **Languages without grammatical gender** (`id`, `ms`, `vi`, `ja`, `ko`, `zh-Hans`, `tr` partially) — identical M/F values are CORRECT and do NOT require flagging. For `ja` / `ko` / `zh-Hans` specifically the expectation is inverted: M and F SHOULD normally be identical, so a `*M` / `*F` pair that DIFFERS is the thing to scrutinize (usually a copy-paste slip or one-variant mistranslation), not the identity. When a `*M`/`*F` pair diverges, identify WHICH variant carries the worse wording and emit the finding row keyed on THAT (the defective) variant, with the `current` copied from the defective variant's line — never key it on the variant that already holds the better wording (an exact-match apply there is a no-op and cannot reach the divergent sibling). If both variants are in the same batch, emit one row per defective variant. Imperatives, nominative-case nouns, and adjectives agreeing with non-speaker subjects also don't show gender in gendered languages — identity is fine then. **Independent of M/F identity:** each gendered variant key is still a normal entry — audit every variant for typos, calque, semantic / source-meaning fidelity and register on its own merits. The "identical M/F is correct" carve-out suppresses ONLY the gender-agreement finding, NEVER the per-variant content checks (an `*M` / `*F` key that mistranslates or inverts the en meaning is flagged regardless of whether M and F match).
6. **Brand quote convention** — target should use locale-typographic quotes per its convention (ru: «My Water»; de: „My Water"; fr: «My Water»; ja: 「My Water」; zh-Hans: full-width "..."; ASCII curly fine for Scandinavian / SE Asian Latin without specific rule). **DO NOT flag in this audit** — quotes are a separate project-wide sweep; see § What NOT to flag.
7. **Mixed register within one surface** — target uses both T-form and V-form (or honorific tiers) in the same connected text without semantic reason. Applies to all T-V / honorific languages: ru, de, fr, es, it, pl, tr, nl, pt-BR, zh-Hans, hi, id, ms, vi, ja, ko.
8. **V-form / formal-register leak — friendly T-form is the default everywhere EXCEPT legally-binding text.** Per `TRANSLATION_STYLE.md § Brand voice § Pronouns` friendly T-form is the brand-voice default for every surface **except one**: genuinely **legally-binding text** — Terms of Use, Privacy Policy, subscription **legal terms**, legally-weighted consent — where **formal register is CORRECT and must NOT be flagged** (a contract is a different speech act, not brand voice; signalled by `Register: formal`). Everything the old split called "formal" that is **not** legal — App Store, paywall hero/CTA, onboarding medical-authority rationale, permission prompts, errors/payment/subscription failures, data-loss warnings, Siri-educational — is **informal T-form with a reserved tone** (seriousness from tone + impersonal phrasing, never from the formal pronoun; switching them to V-form re-introduces the coldness the operator removed). Flag a V-form/honorific on a **non-legal** surface as a T-form leak, with this severity split:
   - **Casual surfaces** (notification, motivational, tip, award, empty state, beverage / achievement name, widget hint, in-app feature card / upsell): **confirmed-defect sweep** — `brand-voice`, enumerate every instance (OPERATOR POLICY below).
   - **Former-formal NON-legal surfaces** (App Store, paywall, permission, error, medical-rationale, Siri-educational): **advisory** — `brand-voice` severity `warn`, ONLY when clearly a new / source-changed string. Legacy «вы»/V-form here is **grandfathered** (no mass sweep; vendor console owns translations — `CM-LOCALE-MASS-FANOUT`); do not *defend* it as "intentional" either.
   - **Legally-binding text** (`Register: formal`, or Type `paragraph (subscription terms)` / `paragraph (disclaimer)` / Surface naming Terms/Privacy/legal/consent): do **NOT** flag formal register / impersonal 3rd-person phrasing — it is the intended register. Conversely don't chase a T-form *inside* legal text as a defect (operator/`Register:`-driven, not swept).
   When legal-binding status is **uncertain** and `Register:` is absent, do NOT raise a hard `error` V-leak — downgrade to `warn` and note the ambiguity, so a real legal string isn't force-rewritten to T-form. New strings: T-form on every non-legal surface, `formal` on legally-binding text.

   **Over-familiarity on serious surfaces (`brand-voice` `warn`, new / source-changed only).** The hybrid keeps T-form on serious non-legal surfaces (error / payment / data-loss / medical-rationale / permission), but with a **reserved** tone — so a T-form string there that is *too playful* is its own off-brand defect, distinct from a V-form leak. On those surfaces (and legal) flag, per `TRANSLATION_STYLE.md § Brand voice § Фамильярность`: diminutives (ru `водичка` / `глоточек` and target-language equivalents), slang / internet-speak, emoji / winks / jokes, nagging (`ну же` / `не ленись`), jokes about money / health / data. Do **NOT** flag these on casual surfaces (push / motivational / award / seasonal) — playfulness is correct there. Scope: new / source-changed strings; legacy is grandfathered.

   **Key-level `Register:` field — authoritative override when present.** If the entry's comment block carries an explicit `Register:` line (`Register: casual T-form` / `Register: neutral` / `Register: formal`; canonical owner — `TRANSLATION_STYLE.md § Translator context § Опциональные поля`), treat it as the authoritative register decision for that key:
   - `Register: formal` → **legal-binding register.** Marks genuinely legally-binding text (Terms / Privacy / subscription-legal / consent). Formal register / impersonal phrasing is **CORRECT** here: **suppress** any rule-#8 V-form/T-leak finding for this key — a formal token or 3rd-person phrasing is intended, not a defect. Per-variant typo / calque / placeholder / semantic checks remain active. (For ar/vi: `Register: formal` ⇒ fuṣḥā-formal / impersonal-neutral respectively; the honorific noun-phrase حضرتك / quý vị is still wrong — flag it.)
   - `Register: casual T-form` → rule #8 binding: flag a V-form/honorific target as a leak even if Surface looks ambiguous; the operator-confirmed register is informal T-form (with whatever Tone the `Tone:` field carries — `reserved` / `reasoned` does **not** license a V-form).
   - `Register: neutral` → suppress rule-#8 register-related findings (settings-register surfaces and similar own neutral register); per-variant content checks remain active.
   - **Legacy `Register: formal V-form` tag (ambiguous):** it was used both for true legal text *and* for the old formal-surface carve-out. Resolve by Surface/Type: if genuinely legal-binding, treat as `Register: formal` (suppress leak). If a former-formal **non-legal** surface (App Store/paywall/permission/error/Siri), treat as grandfather-only — do NOT flag legacy «вы» as must-fix (no sweep), but it does NOT endorse V-form as intentional; a new/source-changed string there is T-form (`warn`). New keys must use `casual T-form` / `neutral` / `formal`, never `formal V-form`.
   - **Absence of `Register:` ⇒ surface-based default.** Default is informal T-form on every surface **except legally-binding text**. So: on a clearly legal-binding surface (Terms/Privacy/subscription-legal/consent) with no `Register:`, default to the legal carve-out — do not flag formal register. On every other surface default to T-form — flag a casual-surface V-form (confirmed-defect), `warn` a new/source-changed former-formal non-legal V-form, grandfather the rest; when legal-binding status is uncertain, downgrade to `warn` rather than force a rewrite. On the casual-Type leaf set ({tip, tip headline, motivational text, notification body / title, achievement description}) `Register:` is near-universal — there a V-form target is a flaggable leak (confirmed-defect class).

   **OPERATOR POLICY (binding):** casual-surface V-form / honorific is a **confirmed project-wide defect**, NOT an intentional single-register locale choice. Therefore: (a) enumerate **every** casual-surface V-form key as its own individual finding row — do NOT consolidate V-form occurrences into one Summary note, and do NOT defer the question as "an operator-level call"; (b) where `ru` (proven anchor) uses casual T-form on the same key, the T-form rewrite is the expected fix; (c) the validator stage must **accept** these findings (not reject them as stylistic / intentional-register). Scope: **casual** surfaces only; former-formal non-legal surfaces are `warn` on new/source-changed strings, their legacy «вы» grandfathered (rule #8 / skip rule #1).

   **T-V / honorific map (the friendly T-form per language is the default target for all non-legal surfaces; the formal column is the register for legally-binding text — valid there — and elsewhere a leak-detection reference, NOT a valid register for new non-legal strings):**
   - `ru`: T = ты, casual imperative without -те; V = вы / -ите / -айте / -йте / -ьте; pronouns вы / вас / вам / ваш(а/е/и). See § Russian-specific examples for full V-leak detail.
   - `de`: T = du (du trinkst); V = Sie (Sie trinken). Possessive: dein vs Ihr.
   - `fr`: T = tu (tu bois); V = vous (vous buvez). Possessive: ton/ta vs votre.
   - `es`: T = tú (bebe / bebes); V = usted (beba / bebe — formal). Project default = tú (pan-LatAm + Spain casual).
   - `it`: T = tu (bevi); V = Lei (beva).
   - `pt-BR`: T = você (você bebe — verb in 3rd-person sg, possessive seu / sua); V = o senhor / a senhora. Casual default = você with -e / -a imperative.
   - `pl`: T = ty (verbs -isz / -esz / imperative -j / -ij); V = Pan / Pani + 3rd-person verb (`niech Pan wypije`).
   - `tr`: T = sen (2nd-person sg verbs, imperative bare stem); V = siz / formal -nız ending.
   - `nl`: T = jij / je (jij drinkt); V = u (u drinkt — same 3rd-person form, different pronoun).
   - `zh-Hans`: T = 你; V = 您 (formal/respectful).
   - `hi`: 3-tier — तू (intimate, never in UI), तुम (casual, default), आप (formal). Imperatives: तुम → पियो / करो; आप → पीजिए / करें. आप leak signals: -इए / -एँ imperatives, हैं vs हो after 2nd-person subject.
   - `id`: T = kamu / -mu possessive (kamu minum airmu); V = Anda (Anda minum air Anda).
   - `ms`: T = awak (or pronoun dropped); V = anda.
   - `vi`: kinship-based — default `bạn` (neutral-casual). NOT a true T-V; same audit spirit applies — flag inconsistent register or formal `quý khách` / `anh` / `chị` leaks in app voice.
   - `ja`: no T-V pronoun system but speech levels (普通体 vs 丁寧体 vs 敬語). Casual default ≈ ですます polite form; flag 敬語 (honorific) leak in casual surface — お/ご prefixes used inappropriately, 〜していただきます, 〜でいらっしゃいます.
   - `ko`: speech levels (해체 / 해요체 / 합쇼체). Casual default ≈ 해요체 (~요 ending: 마셔요); flag 합쇼체 (~ㅂ니다 / ~십시오) leak in casual surface.
   - `ar`: tone-shift only (no pronoun T-V); register manifests via MSA vs colloquial choice and honorific noun-phrases (حضرتك). Calibration profile applies.
   - Scandinavian (`da`, `nb`, `sv`): tone-shift only — no morphological T-V. **Skip audit rule #8 entirely**; only generic "mixed register / over-formal lexicon" applies.

   For `<target>` in {da, nb, sv}: do NOT raise V-form leak findings — rule #8 is N/A (no morphological T-V; the legal carve-out for these is lexical only — formal lexicon + impersonal, not a pronoun swap).
   For `<target>` in {ar, hi, vi, id, ms, pl}: see calibration profile prefixed to this prompt.
   For `<target>` = `ru`: see Russian-specific examples (final section) for full V-form leak detail.

   **Legal-binding carve-out (all langs).** On legally-binding text (Terms / Privacy / subscription **legal** terms / legally-weighted consent; `Register: formal`), the formal column is the **correct** register — impersonal/3rd-person-first, the formal token only as a direct-address fallback — do NOT flag it (rule #8 / skip rule #1). The carve-out is **not** a blanket pronoun swap: for `ja` it is 丁寧体 + formal lexicon/nominalization (本規約, ユーザー…), **not** 敬語 (お/ご-honorific, 〜していただきます) — those stay flaggable even in legal; for `ko` it is 합니다체 (formal declarative) + impersonal (이용자는), **not** 합쇼체 honorific-imperative (~십시오); for `ar` it is fuṣḥā-formal + impersonal/passive, **not** the honorific noun-phrase (حضرتك / سيادتك — wrong even in legal); for `vi` it is impersonal/neutral (Người dùng…), with **no** formal-pronoun fallback (`quý vị` / `quý khách` stay wrong even in legal). Everything that is **not** legal stays informal T-form (reserved tone) per rule #8.

9. **CJK script-appropriate punctuation** (targets `ja`, `zh-Hans`, `ko`) — flag ASCII half-width `!` `?` `:` `,` mixed into CJK text where the script convention is full-width (`！` `？` `：` `、` / `，`) AND the value is internally inconsistent with sibling strings in the same comment-Type bucket — bucketed on the **normalized first `Type` token**: drop any `(subtype)` qualifier / trailing em-dash clause and take the first `/`-separated role, so `settings row title / screen title` and `settings row title` share one bucket (e.g. one notification banner uses `！`, another `!` within that bucket), OR a clear script violation (ASCII `?` ending a Japanese interrogative while the rest of the file uses `？`). Category `punctuation`, severity `warn`. This is DISTINCT from the brand-quote sweep (rule #6 / skip rule #3) — quotes stay out of scope; this covers sentence / clause punctuation only. Do NOT flag a consistently half-width corpus as wrong (some apps standardize on ASCII) — flag the inconsistency or the clear violation, not the global choice. For `ja`: the Japanese comma is `、` (読点) and period `。` (句点); a `,` / `.` mid-Japanese-sentence is flaggable only when inconsistent with siblings. **RTL / Arabic-script punctuation** (target `ar`, and any future Arabic-script target) — mirrors the CJK clause for RTL: flag ASCII `,` `?` `;` mixed into Arabic text where the script convention is `،` (U+060C) / `؟` (U+061F) / `؛` (U+061B) AND the value is internally inconsistent with sibling strings in the same comment-Type bucket OR a clear violation (ASCII `?` ending an Arabic interrogative while siblings use `؟`). Also flag: a space *before* `،` / `؟` / `!` / `.` (Arabic takes no leading space before these, as in English); a missing space *after* a sentence-terminating `.` / `،` / `:` that runs two words or sentences together. Numerals: do NOT flag Western `0-9` vs Eastern `٠-٩` choice per se — flag only internal inconsistency within one string. Category `punctuation`, severity `warn` (`error` only when two sentences run together with no separator). The canonical per-language detail for `ar` lives in `loc_audit_lang_calibration/ar.md § Punctuation conventions`. Latin / Cyrillic / Devanagari-script targets are unaffected by this rule (Devanagari script-integrity — matra / halant / nukta corruption / mojibake — is a `typo` finding per the hi calibration profile, not a punctuation-convention matter).

10. **Glossary terminology consistency (binding — per-language checklist inlined above).** `glossary.ndjson` keeps ONE agreed rendering per controlled term across all 1200+ keys; the canonical per-language checklist is inlined above this prompt (BRAND-freeze / BRAND-localized / FORBIDDEN / CANONICAL groups, generated by `loc_audit_glossary.py`). This operationalizes rule #2 + `TRANSLATION_STYLE.md § Lexicon` as a concrete checklist — it does NOT override the ru cross-check (skip #16), the surface-register carve-outs, or any skip rule. Three lanes:
   - **Brand-freeze — a translated / transliterated brand = `error` (`lexicon` / `brand-voice`).** Verbatim in every language: `#mywater`, `App Store`, `Apple Health`, `Apple ID`, `Apple Watch`, `Facebook`, `iPhone`, `My Water Premium`, `Premium`, `Siri`, `VK` (same convention covers `iPad` / `iOS`). **Caveat — some brands are LOCALIZED, not frozen** (use the checklist's per-language value; flag the wrong direction): `My Water` localizes per locale (ru «Моя вода») but `ar` / `id` / `vi` keep Latin `My Water`; the Apple **Health app** display name localizes (ru «Здоровье») while the **Apple Health** integration brand is frozen; `Apple Account` localizes while legacy `Apple ID` is frozen; `Live Activities` / `Shortcuts` take Apple's OFFICIAL localized term, never a coined one. Flag a target that freezes a localizable brand or localizes a frozen one.
   - **Forbidden jargon — a banned term (en OR its target calque) on a casual / non-clinical surface = `lexicon` / `calque`.** EN: `hydration metrics`, `consumption logs`, `metabolic profile`, `full version` (legacy → `My Water Premium`), `application` (→ `app`, en-rule #3). **Cross-language principle (`§ Translation discipline` Принцип #3): a clinical EQUIVALENT in any target is banned даже если технически верно** — ru calques `гидратация` / `консумация` / `потребление воды` are marked in the checklist; apply the same test to every language (the calibration profile enumerates per-language ones). The EN word `hydration` itself is fine — only clinical *calques* on casual surfaces are banned. Honour the surface carve-out: a term the checklist marks surface-conditional (`water balance`, `hydration`) is correct on its feature-label / store surface, banned only on casual / motivational / push copy.
   - **Canonical rendering — a target that diverges from the checklist's agreed `t[<lang>]` = `lexicon` `warn`, AFTER the guardrail cross-check.** Guardrails (prevent false positives): (a) terms marked contextual / no-fixed-form (`hydration`, `streak`, `intake`, `water balance`) are NOT hard-flagged — read the note; (b) the glossary `t` is the CONSISTENCY anchor, not independent proof of correctness — if a listed rendering looks wrong itself, say so in the rationale, don't endorse the target's divergence; (c) a per-key constraint (sibling-consistency, an explicit comment `Constraints:` directive) can legitimately override the default — cross-check Surface / Constraints first.

## Constraint policy (binding vs soft)

Per `TRANSLATION_STYLE.md § Translator context § Опциональные поля` (Constraints):

**Hard binding constraints (flag when target violates):**
- Exact universal placeholder (`[%s]` / `[%i]` / `[%.1f]`) count & order.
- Hashtag / brand quote preservation.
- Abbreviation form when comment explicitly demands ("ml" vs "millilitres").
- "No trailing period on button label" if comment says so.
- "Do not add hard line breaks" is binding for user-facing values.

**Soft constraints (DO NOT flag as error):**
- `≤N chars` length — recommendation, not hard limit. Target language can exceed by 1–5 chars if no shorter natural form exists. App uses Dynamic Type + `adjustsFontSizeToFitWidth` + multi-line wrapping.
- Manual hard line breaks — escaped line-break tokens in user-facing values are a `style` / `layout` defect. Suggest replacing them with a space, punctuation, or natural sentence boundary. Do not reintroduce hard breaks for visual rhythm; UIKit / SwiftUI wrapping owns visual line placement.
- "Capitalized" / "Lowercase" — flag only on clear case mismatch with no comment exception.

## What NOT to flag (skip rules)

These are pilot-calibrated false positive patterns. DO NOT include them in findings:

1. **Formal register in legally-binding text — DO NOT FLAG (narrow legal carve-out).** Per `TRANSLATION_STYLE.md § Brand voice § Pronouns / § Юридический carve-out`, formal register is **correct** on genuinely **legally-binding text** only: Terms of Use, Privacy / privacy notices, subscription **legal terms** (the formal auto-renewal / EULA block, not a warm paywall ask), legally-weighted consent. On these do **NOT** flag the formal token (Sie / vous / usted / Lei / o senhor / Pan-Pani / siz / u / 您 / आप / Anda / anda) or impersonal 3rd-person phrasing — it is the intended register (`Register: formal`; for ja/ko/ar/vi realize as register-elevation/impersonal, not the honorific noun-phrase — see the T-V map's legal carve-out note). Identify legal-binding via `Register: formal` (authoritative) + Type (`paragraph (subscription terms)` / `paragraph (disclaimer)`) + Surface naming Terms/Privacy/legal/consent. **Everything else is informal T-form** and a V-form/honorific there is a leak per rule #8 — including App Store, paywall hero/CTA (`free.title*`, `reachTheGoal`), onboarding medical-authority rationale, permission prompts (`NS*UsageDescription` — a routine permission is NOT a legal consent contract), error-with-recovery (`noConnection`, `noFreeStorage`, `noRamError`, `favoriteDrinkCreateFailed`, watch / Siri / Premium fallback errors), Siri AppIntent description / `siriPlaceHolder`. On those former-formal **non-legal** surfaces: do not *defend* legacy V-form as "intentional," but legacy «вы» is **grandfathered** (no sweep; flag only new/source-changed, `warn`; `CM-LOCALE-MASS-FANOUT`). The **casual**-surface sweep (rule #8) is unchanged. **Legacy formal-form в casual ключах** (e.g., `pushRetention_*`, `tempAddOneTap`, `forgotWriteText`, `manyDrinksText`, `noAdText`, `tempFirstSteps`, `widgetText`, `NewYearMotivationalText`) — still **flag** as `brand-voice` per audit rule #8 (casual sweep scope, unchanged).
2. **Legacy manual hard line breaks in target value** — no longer a skip bucket. Flag escaped line-break tokens in user-facing values unless the row is a non-user-facing structural format.
3. **Straight quotes** `"My Water"` — separate project-wide sweep. Skip in this audit.
4. **Trailing period on error messages** — soft rule with many legacy exceptions. Flag only if error is a complete sentence AND inconsistent with neighbors in the same comment-Type bucket (keyed on the normalized first `Type` token — see rule #9).
5. **Legacy "please" comma equivalent** in target — comment may explicitly say "preserve legacy punctuation".
6. **Lexicon items intentionally explained in comment** (e.g. "preserve `norm` legacy phrasing for this surface").
7. **Empty (`""`) `unverified` target — untranslated, awaiting a translation pass / Lokalise.** This is the canonical "needs translation" marker ([CR-CORPUS-UNVERIFIED]), not a defect: do NOT flag an empty target as missing / broken, and do NOT auto-fill it during an audit. Leave it empty. (The audit reviews *existing* translations; filling the backlog is a separate translation task — `loc_r_marked_translations`.)
8. **Beverage names that are simple nouns** (`Beer` = `Beer`, `Save` = `Save`) — flag only if actually wrong.
9. **Casing variants intentionally explained in comment** (e.g. "Lowercase per i18n style").
10. **Same issue twice** — once at en level and again at target level if target just inherited the en issue. Flag at en only.
11. **Stylistic preferences** with no rule violation.
12. **British spellings in comments** (translator context) — only flag British spellings in user-facing values.
13. **Singular vs plural in en source for multi-select surfaces** — do NOT propose pluralizing target just because en uses singular. If the comment describes the surface as "multi-select" / "list of options" and target uses plural, that may be the correct rendering. Flag en (source) as the bug, not target. Cross-check by reading the comment Surface/Context lines for "list" / "multi-select" / "options" cues before flagging a singular/plural mismatch.
14. **Gendered target-language verb form for count-driven stat captions** (`count + verb-phrase` UI pattern in gendered languages: ru, pl, ar, hi etc.) — past-tense verbs carry gender, so a single fixed form excludes some users. Do NOT propose flipping masculine to plural as a "fix" — plural reads as "they / multiple subjects shared", which is also wrong for a single-user stat. Flag the gender issue at en or in a separate gender-aware refactor with `M` / `F` key variants; do not silently change the form.
15. **Em-dash `—` (U+2014) in any user-facing value** — DO flag as `punctuation`/`style`. Project policy (`TRANSLATION_STYLE.md § Brand voice § Punctuation`): длинное тире `—` NOT used in any of 21 languages (AI tell). **NOT flagged by this rule:** обычное тире / spaced hyphen ` - ` (U+002D — sanctioned separator) and en-dash `–` (U+2013 — project-unregulated, distinct char, not em-dash) — do not flag either as a punctuation defect; flag and replace only `—` U+2014. **CRUCIAL: never propose em-dash `—` as a `suggestion`.** Suggested replacement for a flagged `—`: **(default) restructure the punctuation to fit the meaning, anchored on the key's `en` value** — an em-dash is usually a symptom of a loosely-built sentence, and Google's developer-docs style guide prefers a colon or period over a dash (`TRANSLATION_STYLE.md § Punctuation`); обычное тире `-` is only a **fallback** when restructuring does not improve a casual line — (a) **comma** for parallel imperatives; (b) **period** for two complete clauses / Siri-voice (`…daily goal. %1$@ of %2$@. Great job!`); (c) **colon** for label:value (`%1$@: %2$d%% of total`); (d) restructure to drop the connector; for `ar` / CJK targets use the script-correct sign (`،` U+060C / `，` / `、`). Applies symmetrically to all 21 languages.
16. **Target faithfully mirrors the proven `ru` anchor's deliberate restructure / warmth choice** — when `<target>` diverges from a literal en rendering but lands on the SAME semantic/structural choice `ru` made (e.g. en "Until the end:" → ru countdown-style caption → target countdown-style caption; en "based on your parameters" → ru "по вашим параметрам" → target equivalent), this is the calque-avoidance the audit WANTS, not a defect. Do NOT flag as `semantic-drift` / `awkward` solely because it departs from en literal while matching ru's natural restructure. Flag only if the target ALSO diverges from ru's choice, or introduces a meaning not in en. Cross-check the `ru` column before flagging a target restructure as drift.
17. **Danish (`da`) optional clause comma** — Danish officially permits omitting the comma before a subordinate / relative clause (Dansk Sprognævn "nyt komma"). Do NOT flag a `da` value as a punctuation defect solely for a missing pre-subordinate-clause comma; it is a sanctioned stylistic choice, not an error. (Other Scandinavian / Germanic comma conventions are unaffected by this carve-out — it is `da`-specific.)

## Output format

Return findings as a Markdown table with EXACT columns. One row per issue. If a key has no issues, do NOT include it.

```
| # | key | lang | severity | category | current | suggestion | rationale |
|---|---|---|---|---|---|---|---|
```

- `#` — sequential issue number across all flagged entries (1, 2, 3...).
- `key` — the .strings key, copied byte-for-byte from the entry's `key:` line in the input file (exact case, no whitespace trimming, no truncation). Do NOT retype, lowercase, camelCase-normalize, or reconstruct the key from memory — the downstream deterministic applier does an exact-match lookup, so any deviation produces a dead duplicate key while leaving the real key unfixed.
- `lang` — `en` or `<target>` (the target language code from top of this prompt).
- `severity` — `error` (clear bug, must fix) / `warn` (style/convention issue).
- `category` — one of: `typo`, `grammar`, `awkward`, `brand-voice`, `lexicon`, `punctuation`, `placeholder`, `comment-mismatch`, `gender`, `calque`, `semantic-drift`, `casing`, `us-vs-british`.
- `current` — current value (truncate to 60 chars + `…` if longer; escape `|` as `\|`).
- `suggestion` — concrete suggested replacement (truncate similarly; if unsure, write `—` and explain in rationale).
- `rationale` — ONE short sentence explaining why this is an issue. Reference the comment field that's violated if applicable.

Skip `info` severity entirely — only `error` and `warn`. If a finding feels like `info`, drop it (pilot showed info-level produces noise without value).

After the table, add a short **Summary** section:
- Total entries audited: N.
- Total issues found: N.
- Breakdown by lang: en=X, <target>=Y.
- Breakdown by severity: error=X, warn=Y.
- 2–3 sentences of overall impression: clean batch? systemic issues? particular hotspot keys?

## Important constraints

- Do NOT write to any files. Output goes to your final message only.
- Do NOT propose new translations for missing locales.
- Do NOT modify any source files in the repo.
- Be precise: name the typo'd word, name the grammar issue.
- Default to NOT flagging if it's stylistic preference without rule violation. False positives waste reviewer time.
- If a comment block is missing or generic, don't flag — comment quality audit is separate.
- **Suggestion quality bar — same rules as a new translation.** Твой `suggestion` в таблице обязан проходить **тот же** brand voice / naturalness / clinical-term filter, что и first-time translation native переводчиком. Не предлагать literal calque, clinical term, AI-feel replacement или "точную" транслитерацию EN lexicon только потому, что это closer to EN literal. EN literal fidelity **не оправдывает** clinical / unnatural target — brand voice integrity важнее. Если не приходит native-sounding alternative — оставь `suggestion` = `—` и объясни в rationale, **не** protect "технически точный" вариант. Пример (ru): EN `Hydration today` → `Вода сегодня` / `Сегодня` / `Выпито за день` (native casual ru); НЕ `Гидратация сегодня` (clinical calque, violates `TRANSLATION_STYLE.md § Translation discipline § Принципы § 3`). **Self-check перед записью suggestion (язык/регистр чистота):** если флагаемый дефект — wrong-language / wrong-register token (Bahasa Indonesia в `ms`, intimate pronoun, V-form leak, MSA-vs-colloquial для `ar`, transliteration drift для `hi`), `suggestion` обязан быть **полностью** в целевом языке и целевом регистре. Проверить: не содержит ли мой `suggestion` тот же класс дефекта (другой язык, formal/honorific leak, clinical term), который я флагаю? Если да — переписать или поставить `—` + rationale.
- **Spoken plausibility test for every suggestion.** Перед записью suggestion в таблицу прочитать вслух или мысленно представить, как native target-language speaker произнёс бы фразу в casual conversation или Siri-команде. Если awkward / clinical / звучит как машинный перевод — отвергнуть, искать другой вариант или dropping suggestion.
- **Constraint-binding fixes must be applied to the FULL value, not truncated.** When a finding's fix is governed by a hard binding constraint (brand-name freeze, mandatory hashtag, exact placeholder set, mandated invisible prefix such as U+200C zero-width non-joiners, no hard line breaks) the `suggestion` must be the COMPLETE corrected value (the 60-char truncation rule does NOT apply to these rows — write the whole string). A partial suggestion that still leaves the brand translated, drops the hashtag, or omits the mandated prefix is itself a defective suggestion and forces a manual rewrite downstream. If the full corrected value is genuinely uncertain, write `—` and state precisely what must be preserved in the rationale.

Now perform the audit on the input file specified in the second line (`Input: ...`).
```

## Russian-specific examples (apply only when `Target language: ru`)

The base prompt above stays language-agnostic. The detail below adds Russian-specific blacklists, calque examples, and V-form leak detail. **Apply only when `Target language: ru`** (legacy ru/en audit OR ru itself as target). For all other targets, skip this section.

### Russian clinical-term blacklist (rule #2 detail for ru)

Reject these terms in ru translations (canonical owner — `TRANSLATION_STYLE.md § Translation discipline § Принципы § 3`):

- `гидратация`, `водный баланс`, `потребление воды`, `консумация`, `насыщенность` — clinical / Apple Health-formal terms; native ru speakers так не говорят в casual UI.
- `прогресс по [не-учебная тема]` — calque "progress on" (`прогресс по воде` ❌; `прогресс по математике` ✓ только для subject area).
- Direct verb mapping `Show X` → `Показать X`, когда X — clinical noun (`Показать гидратацию` ❌).
- Literal idiom translation: `hands-free` → `без рук` ❌ (✓ `голосом`).

Prefer plain native ru: `вода`, `выпито`, `стакан`, `за день / сегодня`, `сколько ... выпито`.

### Russian V-form leak detail (rule #8 detail for ru)

Flag ru imperative ending in `-ите` / `-айте` / `-йте` / `-ьте` (`добавьте`, `выпейте`, `пейте`, `начните`, `следуйте`, `оставайтесь`, `не забывайте`, `позаботьтесь`, `используйте`, `откройте`, `попробуйте`, `создайте`, `выберите`, `сделайте`, `нажмите`, `проверьте`, `отслеживайте`, `учитывайте`, `записывайте`, `рассчитайте`, `поставьте`), OR pronoun `вы` / `вас` / `вам` / `ваш` / `ваша` / `ваше` / `ваши` in app voice. Per `TRANSLATION_STYLE.md § Brand voice § Pronouns` — friendly T-form («ты») is the brand-voice register on every surface **except legally-binding text** (Terms / Privacy / subscription **legal** terms / legally-weighted consent, `Register: formal`), where impersonal-first phrasing with «вы» as a direct-address fallback is the correct legal register — do NOT flag «вы» / `-ите` there. On all non-legal surfaces flag per rule #8: casual-surface V-form = confirmed-defect sweep; former-formal **non-legal** surfaces (App Store / paywall / permission / error / Siri) = advisory `warn` on new/source-changed only, legacy «вы» grandfathered (no mass sweep) — see rule #8 + skip rule #1. **Also (ru):** on serious non-legal surfaces (error / payment / data-loss / medical-rationale / permission) flag over-familiarity — diminutives (`водичка` / `глоточек` / `кофеёк`), slang (`го` / `чекни` / `жми давай`), emoji / winks / jokes, nagging (`ну же` / `не ленись`), jokes about money / health / data — as `brand-voice` `warn` (new/source-changed only); NOT on casual surfaces (`§ Brand voice § Фамильярность`).

### Russian brand quote convention (rule #6 detail for ru)

ru should use guillemets `«My Water»` / `«Моя вода»`, not straight ASCII quotes. (DO NOT flag in this audit — quotes are a separate project-wide sweep; see § What NOT to flag.)

### Russian mixed-register patterns

If a connected ru text uses both «ты» and «вы» without semantic reason, flag.

## Calibration & status records

Two sibling records, **neither read by the sub-agent** (it reads only this file + the
inlined calibration/glossary):
- **[`loc_audit_changelog.md`](loc_audit_changelog.md)** — calibration canon: *why* each
  skip / audit / format rule + binding linguistic/policy decision exists.
- **[`loc_audit_status.md`](loc_audit_status.md)** — current per-language **STATE** (audited /
  applied / pushed / verified — the source of truth), open follow-ups, and the dated
  **execution log** (re-sweep / apply / push passes, the cost-blowup incident, the
  context-audit + beverage changesets). To answer *"is language X done?"* read its STATE
  table — never infer state from a historical entry.

## Related

- `loc_corpus.py` / `loc_corpus_ndjson.py` / `loc_corpus_import.py` — corpus read-write lib, Lokalise→ndjson generator, ndjson→Lokalise importer.
- `loc_audit_extract.py` — extract en+ru+target batches from the corpus for audit.
- `loc_audit_glossary.py` — emit the canonical per-language glossary terminology checklist (inlined above the prompt; `<target>`-rule #10).
- `loc_audit_apply.py` — deterministic applier of validated findings into the corpus.
- `loc_r_marked_translations.py` / `loc_apply_lang.py` / `loc_merge_languages.py` — translation backlog, `{key:value}` apply, language-set merge (all corpus-backed).
- `loc_audit_lang_calibration/<lang>.md` — per-language calibration profiles (ar, hi, vi, id, ms; + pl, a lean trap-focused profile).
- `TRANSLATION_STYLE.md` — canonical style / linguistics (this repo: § Translation discipline, § Brand voice, § Translator context); `mywater_ios docs/LOCALIZATION.md § Comment encoding` — iOS `.strings` comment mechanics.
