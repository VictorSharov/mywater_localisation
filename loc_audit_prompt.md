<!--
doc-role: workflow
doc-owner: loc_audit_prompt.md (репозиторий mywater_localisation)
doc-scope: AI-assisted translation audit поверх cross-platform ndjson-корпуса — sub-agent prompt + workflow + skip rules
-->

# Localization audit — sub-agent prompt & workflow

Пошаговый workflow для AI-assisted audit переводов через Opus 4.7 sub-agent. Источник данных — **cross-platform ndjson-корпус** `strings.ndjson` в этом репозитории (все языки + все платформы): `loc_audit_extract.py` достаёт батчи `en`+`ru`+`<target>` из корпуса, validated findings применяются `loc_audit_apply.py` обратно **в** корпус (язык помечается `unverified`), затем `loc_corpus_import.py --apply` пушит правки в Lokalise, откуда они экспортируются в iOS / Android / server.

> **Историческая привязка.** Калибровка prompt'а и Phase 0..5 changelog ниже относятся к оригинальному iOS `.strings`-свипу (2026-05); пути вида `water/Supporting Files/Localization/*.lproj` и `make localization-lint` там — историческая трасса, оставленная как calibration trail. Linguistic-правила платформонезависимы и применяются к корпусу один-в-один.

Initial pilot (ru/en, keys 1–50, 2026-05-15): 22 findings, 12 applied, 10 false positives — на их основе калиброван prompt. Phase 0..2 extension (2026-05-15) generalized prompt с ru-only audit на `en+ru+target` triple input для full 19-language sweep.

## Зачем нужен этот документ

- Sub-agent prompt — длинный и зависит от learnings из pilot (skip rules). Хранить в conversation memory ненадёжно (auto-compact теряет nuances).
- Workflow воспроизводим: оператор может запустить любой batch без re-deriving rules.
- Calibration changes документируются здесь, не в чате.

## Workflow

### 1. Extract batch

```bash
# Reads strings.ndjson (corpus order, sorted by key_id); en+ru shown as anchors:
python3 loc_audit_extract.py de 1 200 /tmp/loc_audit_de_batch_001.txt
python3 loc_audit_extract.py fr 201 400 /tmp/loc_audit_fr_batch_002.txt --platform ios

# en source audit (lang=en) — every key in range, ru as reference:
python3 loc_audit_extract.py en 1 200 /tmp/loc_audit_en_batch_001.txt
```

Подсчёт total en/ru/target идёт в первых строках output-файла. Recommended batch size: **200 keys** (Opus 4.7 200K window держит triple input ~95KB; ru/en legacy audit можно держать на 50 keys).

### 2. Run sub-agent

Использовать Agent tool с `subagent_type: general-purpose`, `model: opus` (Opus 4.7).

`prompt:` — содержимое раздела `## Sub-agent prompt (calibrated)` ниже **дословно**, плюс две строки наверху:

```
Target language: de
Input: /tmp/loc_audit_de_batch_001.txt
```

Для weak-AI-signal языков (`ar`, `hi`, `vi`, `id`, `ms`) — также inline calibration profile из `loc_audit_lang_calibration/<lang>.md` сразу перед "Sub-agent prompt" блоком:

```
Target language: ar
Input: /tmp/loc_audit_ar_batch_001.txt

Calibration profile:
<full content of loc_audit_lang_calibration/ar.md>

<then full content of ## Sub-agent prompt (calibrated)>
```

Для legacy ru/en audit (no target column) — `Target language: ru` + `Input: ...`; prompt автоматически активирует Russian-specific examples block.

Это критично: в conversation memory не хранится prompt — копируется из этого doc.

### 3. Review findings

Sub-agent возвращает Markdown table со столбцами:

```
| # | key | lang | severity | category | current | suggestion | rationale |
```

Severity: `error` (clear bug) / `warn` (style/convention) / `info` (consider — dropped per calibration).

Оператор фильтрует findings и решает по каждой:
- Apply fix как есть.
- Apply с поправкой (другая formulation в suggestion).
- Skip как false positive (с обоснованием).

Для Phase 3 full sweep (19 languages) findings проходят через validator stage (skeptical native review) перед deterministic apply через `loc_audit_apply.py` — workflow описан в `ai_reports/tasks/2026-05-15_localization_audit_19_langs_plan.md § Phase 3`.

### 4. Apply fixes

- Применять validated accept/modify findings в корпус: `python3 loc_audit_apply.py <lang> <validated_findings.md>` — пишет `t[lang]` в `strings.ndjson` и помечает язык `unverified` (correction нуждается в human / Lokalise review). en-source правки (`<lang>=en`) делает оператор вручную в корпусе (dev language).
- Replace-only: ключ, которого нет в корпусе, не добавляется, а репортится (upstream transcription error). Plural-ключи findings-таблица не выражает — править их `t` в корпусе вручную.
- Не заводить новый ключ через audit: новые строки добавляются в корпус напрямую (видны всем платформам) и создаются в Lokalise при импорте.

### 5. Verify & import

```bash
git diff -- strings.ndjson                            # ревью-гейт: меняться должны только отредактированные ключи
python3 loc_corpus_import.py --lang <lang>            # dry-run: что уйдёт в Lokalise
python3 loc_corpus_import.py --lang <lang> --apply    # пуш в Lokalise (оператор, [CR-ACCESS])
```

Корпус-правки попадают к пользователям через Lokalise → экспорт в iOS / Android / server, не напрямую. iOS `make localization-lint` (`|R|` gate) к корпус-выходу не применяется: он проверяет iOS `.strings`, которые обновляются Lokalise-экспортом, а не этим workflow.

### 6. Next batch

Повторить со следующим диапазоном (201..400, ...). Total en keys см. в первой строке extract output.

## Sub-agent prompt (calibrated)

> Copy-paste следующий блок в `prompt:` Agent tool. Заменить first lines `Target language: <code>` / `Input: …` на актуальные значения. **Не редактировать остальное** без обновления этого doc — иначе prompt drift.

> **Sync with canon (verbatim self-sufficiency).** Этот блок **операционализирует** канон `TRANSLATION_STYLE.md` (`§ Brand voice` / `§ Translation discipline` / `§ Translator context`) в audit-форме (flag / skip / severity / output). Operational-правила (T-V/honorific map, em-dash flag, gender flag, skip rules) обязаны оставаться **инлайн**: prompt копируется sub-agent'у дословно, и **у sub-agent'а нет доступа к докам в рантайме** — заменить правило ссылкой на `TRANSLATION_STYLE.md` нельзя, это сломает audit. Когда канон в `TRANSLATION_STYLE.md` меняется, зеркаль соответствующие operational-правила здесь (controlled duplication — намеренная, не дрейф). `TRANSLATION_STYLE.md` владеет authoring-каноном (почему / как звучит правильно); этот блок — audit-операционализацией (как флагать).

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
- **Proving-corpus scope (do not over-trust ru blindly).** ru's PROVEN status covers `Localizable.strings` only (the 27-batch + 2-calibration corpus). ru `.stringsdict` and ru `InfoPlist.strings` were NOT in that corpus — Phase 5 found a real ru `.stringsdict` defect there (`%li разы` → `%li раза`; CLDR `other` = fractions). So when the batch is `.stringsdict` / `InfoPlist.strings`, ru is still useful for natural phrasing / brand voice but is NOT a verified correctness anchor — anchor correctness on `en` semantics + CLDR plural rules, and a ru-mirrored choice there does not auto-clear a finding (skip rule #16's ru-mirror carve-out applies only to the proven `Localizable.strings` ru).
- Do NOT audit the `ru` value itself when `Target language` is not `ru`: `ru` is a read-only reference column. Never emit a finding row with `lang=ru` for a non-ru target (even if the ru text has a stray hyphen / em-dash / punctuation nit) — it is out of scope and the deterministic applier cannot act on it. The only auditable columns are `en` (operator Phase-0) and `<target>`.
- If `<target>` diverges from en semantically OR from ru's natural-phrasing style — flag.
- If `<target>` perfectly mirrors ru's restructure choice naturally — that's a good sign, no flag.

## What to audit

### For `en` (the source)

1. **Typos / grammar errors.**
2. **Awkward AI-tone phrasing** (canned, unnatural, over-formal for casual surfaces). **Also: RU→EN reverse calques** — team is ru-native; en source может содержать обратные кальки от русских формулировок. Common patterns: direct preposition mapping (`Press on +` от `Нажмите на +`; `to / from Apple Health` от `в / из`; `over the world` от `по миру`); passive `is + past participle` от ru reflexive (`information is not filled` от `информация не заполнена`); nominalization-as-noun-phrase (`Track the weight dynamic` от `динамика веса`); translated commands (`Open application` от `открыть приложение`); awkward verb-object (`fulfill your daily water intake` от `выполнить норму`; `we get consultations from` от `получаем консультации у`; `top up your water level` от `восполнить уровень`). Apply spoken-plausibility test as native US English copywriter. Anti-pattern catalog: `[CM-EN-SOURCE-RU-CALQUE]`.
3. **Brand voice violations** — app voice is friendly health-conscious companion, not medical authority:
   - User → "you" / "your" (direct).
   - App → "we" / "our app" / "My Water" (first-person plural, partner framing).
   - Plain language: prefer `drink`, `water`, `glass`, `goal`, `habit`, `body`, `healthy`.
   - Avoid: `hydration metrics`, `consumption logs`, `metabolic profile`, IT jargon, formal medical terms.
   - **`application` → `app`** in user-facing values is a hard convention (legacy mass-violation; flag every instance). Comment-acknowledged legacy keys (e.g. `appstore.app.subscriptionTemsAppStore § iTunes legacy text`) may keep, but new strings must use `app`.
4. **Lexicon drift** — flag only if `goal` and `norm` are mixed awkwardly in the SAME string. Standalone `norm` strings are intentional legacy (comments often say so) — DO NOT flag.
5. **US English consistency** — project uses US English. Flag British spellings in user-facing values: "Fulfil" → "Fulfill", "favourite" → "favorite", "colour" → "color", "centre" → "center", "behaviour" → "behavior", "organise" → "organize", "analyse" → "analyze". DO NOT flag "litre" — it's intentional British metric unit spelling per comment policy.
6. **Punctuation** — see § "What NOT to flag" for soft rules.
7. **Broken placeholders** — values store **Lokalise universal placeholders** (`[%s]` / `[%i]` / `[%.1f]` / `[%1$s]`; canonical: `TRANSLATION_STYLE.md § Placeholders`), which Lokalise converts per platform on export (`[%s]`→iOS `%@` / Android `%s`). Count them in en vs what the `Placeholders` comment field describes. A **bare** `%@` / `%d` / `%s` (not bracketed) in a value is itself a defect — flag as `placeholder`: the keys-API import stores it literally, so it won't convert. `%%` is the literal-percent escape; R.swift wraps every accessor in `String(format:)`, so a lone `%` (not `%%`, not `[%]`) in a **runtime** (ios/android) value is undefined behavior — flag it as a bug. App Store / server-only values (`platforms: ["other"]`) are not formatted, so a literal `%` there is fine. (`loc_placeholder_lint.py` enforces this mechanically.)
8. **Inconsistency with binding comment constraint** — see § Constraint policy below.

### For `<target>` (the translation)

1. **Typos / grammar errors** (native target-language speaker check).
2. **Unnatural phrasing / calque / clinical terms.** Literal calque from English, AI-translation feel, clinical-medical-jargon lexicon. Project's brand voice is friendly health-conscious companion, not medical chart — `<target>` должен звучать как написанный native target-language UX-копирайтером, а не как буквальный перевод EN. Generic patterns:
   - Clinical / medical-formal lexicon for casual surfaces — terms equivalent to `hydration / water balance / consumption of water / hydration metrics` when natural casual alternative exists in target language.
   - Direct verb mapping `Show X → <Verb in target> X` when X is a clinical noun (e.g. `Show hydration` rendered with formal noun for "hydration" instead of casual "drank today / water today").
   - Literal idiom translation: `hands-free → "without hands"` ❌ (✓ "by voice" in target).
   - Direct preposition mapping (`of`, `with`, `for`) — часто требует restructure в target language, не lexical substitution.
   - For `Target language: ru`, see Russian-specific clinical-term blacklist at end of prompt.
   - For `ar`/`hi`/`vi`/`id`/`ms`, calibration profile inlined above prompt enumerates language-specific patterns.
   Prefer plain native target vocabulary. Spoken plausibility test обязателен: представить, как native speaker произнёс бы фразу в обычной беседе или Siri-команде; если awkward — flag.
   Mandatory ru cross-check BEFORE flagging any restructure / lexical-choice / "calque" / "semantic-drift" finding: re-read the `ru` value for the same key. If `ru` (the proven anchor) made the SAME lexical or structural choice the `<target>` made (e.g. target `取决于` ≈ ru `зависит от`; target broadened "any water"→"drinks" ≈ ru broadened to "ничего"; target keeps "in the app" ≈ ru `в приложении`), this is the calque-avoidance the audit WANTS — do NOT flag (skip rule #16). Only flag if `<target>` ALSO diverges from ru's choice OR introduces meaning absent from en. This check is especially load-bearing for CJK targets where natural restructure from English is the norm.

   **Sibling-language contamination is a primary defect class (not stylistic).** Если target-файл систематически содержит токены близкородственного языка (Bahasa Indonesia в `ms`; Urdu / Hinglish / Latin-transliteration в `hi`; MSA↔colloquial или Farsi / Urdu loan-drift в `ar`), это working-text defect — флагать каждый instance как `semantic-drift` / `lexicon`, НЕ подавлять как stylistic preference (skip rule #11). Calibration profile языка перечисляет конкретные false-friend / wrong-register токены — применять как hard checklist, не как «по вкусу». Surface: G5 ms — весь файл был контаминирован Bahasa Indonesia (`bisa`=poison, `butuh`=vulgar, `gratis`/`kantor`/`besok`/`kemarin`); ms-калибровка §2 поймала это end-to-end (~244 valid rows) только потому, что rule был sticky.
3. **Semantic mismatch with en source** — different meaning, wrong tone, missing/added content.
4. **Placeholder count** must match en exactly (same universal `[%s]` / `[%i]` / `[%.1f]` set; reordering via `[%1$s]` / `[%2$s]` indexing is fine when target grammar requires it — see ru placeholder swap example above). Dropping the brackets (`[%s]` → bare `%s`) is itself a defect — the keys-API import would store it literally and mis-export. `%%` in target is the **correct** escape for a literal `%` — do NOT flag as a placeholder count mismatch even when en has a lone `%`. The en source with lone `%` is the bug; target preserving `%%` is correct.
5. **Gendered variants** — if key ends in `M` or `F`, target values for M and F should typically differ when target language requires gender agreement (past-tense, adjectives, participles). If identical AND target language requires gender agreement here, flag. **Languages without grammatical gender** (`id`, `ms`, `vi`, `ja`, `ko`, `zh-Hans`, `tr` partially) — identical M/F values are CORRECT and do NOT require flagging. For `ja` / `ko` / `zh-Hans` specifically the expectation is inverted: M and F SHOULD normally be identical, so a `*M` / `*F` pair that DIFFERS is the thing to scrutinize (usually a copy-paste slip or one-variant mistranslation), not the identity. When a `*M`/`*F` pair diverges, identify WHICH variant carries the worse wording and emit the finding row keyed on THAT (the defective) variant, with the `current` copied from the defective variant's line — never key it on the variant that already holds the better wording (an exact-match apply there is a no-op and cannot reach the divergent sibling). If both variants are in the same batch, emit one row per defective variant. Imperatives, nominative-case nouns, and adjectives agreeing with non-speaker subjects also don't show gender in gendered languages — identity is fine then. **Independent of M/F identity:** each gendered variant key is still a normal entry — audit every variant for typos, calque, semantic / source-meaning fidelity and register on its own merits. The "identical M/F is correct" carve-out suppresses ONLY the gender-agreement finding, NEVER the per-variant content checks (an `*M` / `*F` key that mistranslates or inverts the en meaning is flagged regardless of whether M and F match).
6. **Brand quote convention** — target should use locale-typographic quotes per its convention (ru: «My Water»; de: „My Water"; fr: «My Water»; ja: 「My Water」; zh-Hans: full-width "..."; ASCII curly fine for Scandinavian / SE Asian Latin without specific rule). **DO NOT flag in this audit** — quotes are a separate project-wide sweep; see § What NOT to flag.
7. **Mixed register within one surface** — target uses both T-form and V-form (or honorific tiers) in the same connected text without semantic reason. Applies to all T-V / honorific languages: ru, de, fr, es, it, pl, tr, nl, pt-BR, zh-Hans, hi, id, ms, vi, ja, ko.
8. **Formal V-form imperative in casual surface** — flag when target uses V-form / honorific / formal register in a **casual** surface (notification, motivational, tip, award, empty state, beverage / achievement name, widget hint, in-app feature card / upsell). Per `TRANSLATION_STYLE.md § Brand voice § Pronouns` — friendly T-form is brand-voice default for casual surfaces; V-form is exception only for formal surfaces explicitly listed in § What NOT to flag rule 1. Failure mode catalog: `[CM-LOCALE-V-FORM-LEAK]`.

   **OPERATOR POLICY (2026-05-16, Phase 3 sweep — binding):** casual-surface V-form / honorific is a **CONFIRMED project-wide defect to fix across all 19 languages**. It is NOT an intentional single-register locale choice (the "may be deliberate like the historical paywall-CTA single-register" consideration is resolved — it is not). Therefore: (a) enumerate **every** casual-surface V-form key as its own individual finding row — do NOT consolidate V-form occurrences into one Summary note, and do NOT defer the question as "an operator-level call"; (b) where `ru` (proven anchor) uses casual T-form on the same key, the T-form rewrite is the expected fix; (c) the validator stage must **accept** these findings (not reject them as stylistic / intentional-register). Skip rule #1 formal-surface carve-outs still fully apply (App Store, paywall hero, legal, permission prompts, error-with-recovery, medical-authority educational, Siri educational) — those stay V-form and are NOT flagged.

   **CARRIED RU-PARITY ITEM — RESOLVED (2026-05-16, pre-G6, operator-gated).** The carried open question (G3-Delta5 / G4 / G5 changelog entries) — *casual-surface V-form leak is real but the proven `ru` anchor is itself V-form on that same key, accept-condition (b) unmet → RU-PARITY-DEFER* — is **closed by operator decision**. The evidenced genuinely-casual ru V-leak set was re-audited and corrected to T-form in `ru.lproj`: `yearResultsPushTitleTemp`, `didgestSettingsTitle`, `pressOnPlusToAdd`, `drinkParamsNotionMessage`, `youShuldAddToFriend`, `notifSoundText`, `drinksReorderText` (canonical owner — `TRANSLATION_STYLE.md § Brand voice § Pronouns`). Accept-condition (b) is now MET for these keys (ru is T-form) → normal **accept** path, not defer. RU-PARITY-DEFER remains in the validator only as a safety net for any *unforeseen new* ru-V-on-casual key — NOT a known-open cluster; G6 (hi / ar) must NOT expect a defer cluster on these keys. Face A (paywall-CTA / hero) stays intentional single-register formal even where ru is casual-T (`reachTheGoal` outlier) — see skip rule #1.

   **T-V / honorific map (default casual / formal markers per language):**
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

   For `<target>` in {da, nb, sv}: do NOT raise V-form leak findings — rule #8 is N/A.
   For `<target>` in {ar, hi, vi, id, ms}: see calibration profile prefixed to this prompt.
   For `<target>` = `ru`: see Russian-specific examples (final section) for full V-form leak detail.

9. **CJK script-appropriate punctuation** (targets `ja`, `zh-Hans`, `ko`) — flag ASCII half-width `!` `?` `:` `,` mixed into CJK text where the script convention is full-width (`！` `？` `：` `、` / `，`) AND the value is internally inconsistent with sibling strings in the same comment-Type bucket (e.g. one notification banner uses `！`, another `!`), OR a clear script violation (ASCII `?` ending a Japanese interrogative while the rest of the file uses `？`). Category `punctuation`, severity `warn`. This is DISTINCT from the brand-quote sweep (rule #6 / skip rule #3) — quotes stay out of scope; this covers sentence / clause punctuation only. Do NOT flag a consistently half-width corpus as wrong (some apps standardize on ASCII) — flag the inconsistency or the clear violation, not the global choice. For `ja`: the Japanese comma is `、` (読点) and period `。` (句点); a `,` / `.` mid-Japanese-sentence is flaggable only when inconsistent with siblings. **RTL / Arabic-script punctuation** (target `ar`, and any future Arabic-script target) — mirrors the CJK clause for RTL: flag ASCII `,` `?` `;` mixed into Arabic text where the script convention is `،` (U+060C) / `؟` (U+061F) / `؛` (U+061B) AND the value is internally inconsistent with sibling strings in the same comment-Type bucket OR a clear violation (ASCII `?` ending an Arabic interrogative while siblings use `؟`). Also flag: a space *before* `،` / `؟` / `!` / `.` (Arabic takes no leading space before these, as in English); a missing space *after* a sentence-terminating `.` / `،` / `:` that runs two words or sentences together. Numerals: do NOT flag Western `0-9` vs Eastern `٠-٩` choice per se — flag only internal inconsistency within one string. Category `punctuation`, severity `warn` (`error` only when two sentences run together with no separator). The canonical per-language detail for `ar` lives in `loc_audit_lang_calibration/ar.md § Punctuation conventions`. Latin / Cyrillic / Devanagari-script targets are unaffected by this rule (Devanagari script-integrity — matra / halant / nukta corruption / mojibake — is a `typo` finding per the hi calibration profile, not a punctuation-convention matter).

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

1. **Formal V-form / honorific in formal surfaces** — App Store metadata (`appstore.app.*`), paywall marketing hero / promo slides (`free.title*`, screenshot taglines), paywall CTA buttons (**intentional single-register formal V-form**, single register with hero; carve-out stays binding even when the proven `ru` is casual-T on a CTA key — known legacy outlier `reachTheGoal`, no live call-sites — do NOT flag the formal target there; canonical — `TRANSLATION_STYLE.md § Brand voice § Pronouns`), onboarding educational paragraphs referencing medical authority (doctor, body calculation, goal recommendation rationale), legal / privacy notices, permission prompts (`NS*UsageDescription` in `InfoPlist.strings`), error messages with recovery instructions (`noConnection`, `noFreeStorage`, `noRamError`, `favoriteDrinkCreateFailed`, watch / Siri / Premium fallback errors), Siri AppIntent description / placeholder educational text (`siriPlaceHolder` и аналоги). Per `TRANSLATION_STYLE.md § Brand voice § Pronouns § Formal V-form surfaces` — formal register split is intentional. **Applies to ALL T-V / honorific languages** (ru / de / fr / es / it / pl / tr / nl / pt-BR / zh-Hans / hi / id / ms / vi / ja / ko / ar — replace V-form with target-language equivalent: Sie, vous, usted, Lei, o senhor, Pan/Pani, siz, u, 您, आप, Anda, anda, formal kinship, 敬語, 합쇼체, fuṣḥā formal). **Legacy formal-form в casual ключах** (e.g., `pushRetention_*`, `tempAddOneTap`, `forgotWriteText`, `manyDrinksText`, `noAdText`, `tempFirstSteps`, `widgetText`, `NewYearMotivationalText`) — **flag** as `brand-voice` / `[CM-LOCALE-V-FORM-LEAK]` per audit rule #8; не путать с intentional formal split.
2. **Legacy manual hard line breaks in target value** — no longer a skip bucket. Flag escaped line-break tokens in user-facing values unless the row is a non-user-facing structural format.
3. **Straight quotes** `"My Water"` — separate project-wide sweep. Skip in this audit.
4. **Trailing period on error messages** — soft rule with many legacy exceptions. Flag only if error is a complete sentence AND inconsistent with neighbors in the same comment-Type bucket.
5. **Legacy "please" comma equivalent** in target — comment may explicitly say "preserve legacy punctuation".
6. **Lexicon items intentionally explained in comment** (e.g. "preserve `norm` legacy phrasing for this surface").
7. **Strings with `|R|` prefix in en** — agent-added markers awaiting Lokalise. Flag only if grammar / semantic broken beyond the marker. **Crucially:** if en has `|R|` and target holds an English-text fallback (untranslated), do NOT remove or auto-translate the target entry. The English fallback is an intentional stop-gap until Lokalise OTA translates the new key; removing it strips the user-visible value to nothing. Leave it as-is.
8. **Beverage names that are simple nouns** (`Beer` = `Beer`, `Save` = `Save`) — flag only if actually wrong.
9. **Casing variants intentionally explained in comment** (e.g. "Lowercase per i18n style").
10. **Same issue twice** — once at en level and again at target level if target just inherited the en issue. Flag at en only.
11. **Stylistic preferences** with no rule violation.
12. **British spellings in comments** (translator context) — only flag British spellings in user-facing values.
13. **Singular vs plural in en source for multi-select surfaces** — do NOT propose pluralizing target just because en uses singular. If the comment describes the surface as "multi-select" / "list of options" and target uses plural, that may be the correct rendering. Flag en (source) as the bug, not target. Cross-check by reading the comment Surface/Context lines for "list" / "multi-select" / "options" cues before flagging a singular/plural mismatch.
14. **Gendered target-language verb form for count-driven stat captions** (`count + verb-phrase` UI pattern in gendered languages: ru, pl, ar, hi etc.) — past-tense verbs carry gender, so a single fixed form excludes some users. Do NOT propose flipping masculine to plural as a "fix" — plural reads as "they / multiple subjects shared", which is also wrong for a single-user stat. Flag the gender issue at en or in a separate gender-aware refactor with `M` / `F` key variants; do not silently change the form.
15. **Em-dash `—` (U+2014) in any user-facing value** — DO flag as `punctuation`/`style`. Project policy (`TRANSLATION_STYLE.md § Brand voice § Punctuation`, updated 2026-05-16): длинное тире `—` NOT used in any of 21 languages (AI tell). **NOT flagged by this rule:** обычное тире / spaced hyphen ` - ` (U+002D — sanctioned separator) and en-dash `–` (U+2013 — project-unregulated, distinct char, not em-dash) — do not flag either as a punctuation defect; flag and replace only `—` U+2014. **CRUCIAL: never propose em-dash `—` as a `suggestion`.** Suggested replacement for a flagged `—`: **(default) обычное тире `-`**; otherwise по ситуации, anchored on the key's `en` value — (a) **comma** for parallel imperatives; (b) **period** for two complete clauses / Siri-voice (`…daily goal. %1$@ of %2$@. Great job!`); (c) **colon** for label:value (`%1$@: %2$d%% of total`); (d) restructure to drop the connector; for `ar` / CJK targets use the script-correct sign (`،` U+060C / `，` / `、`). Anti-pattern catalog: `[CM-EM-DASH-OVERUSE]`. Applies symmetrically to all 21 languages.
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
- **Suggestion quality bar — same rules as a new translation.** Твой `suggestion` в таблице обязан проходить **тот же** brand voice / naturalness / clinical-term filter, что и first-time translation native переводчиком. Не предлагать literal calque, clinical term, AI-feel replacement или "точную" транслитерацию EN lexicon только потому, что это closer to EN literal. EN literal fidelity **не оправдывает** clinical / unnatural target — brand voice integrity важнее. Если не приходит native-sounding alternative — оставь `suggestion` = `—` и объясни в rationale, **не** protect "технически точный" вариант. Пример (ru): EN `Hydration today` → `Вода сегодня` / `Сегодня` / `Выпито за день` (native casual ru); НЕ `Гидратация сегодня` (clinical calque, violates `TRANSLATION_STYLE.md § Translation discipline § Принципы § 3`). **Self-check перед записью suggestion (язык/регистр чистота):** если флагаемый дефект — wrong-language / wrong-register token (Bahasa Indonesia в `ms`, intimate pronoun, V-form leak, MSA-vs-colloquial для `ar`, transliteration drift для `hi`), `suggestion` обязан быть **полностью** в целевом языке и целевом регистре. Проверить: не содержит ли мой `suggestion` тот же класс дефекта (другой язык, formal/honorific leak, clinical term), который я флагаю? Если да — переписать или поставить `—` + rationale. Surface: G5 ms — auditor дважды сам внёс Indonesian / V-form `anda` в собственный `suggestion`.
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

Flag ru imperative ending in `-ите` / `-айте` / `-йте` / `-ьте` (`добавьте`, `выпейте`, `пейте`, `начните`, `следуйте`, `оставайтесь`, `не забывайте`, `позаботьтесь`, `используйте`, `откройте`, `попробуйте`, `создайте`, `выберите`, `сделайте`, `нажмите`, `проверьте`, `отслеживайте`, `учитывайте`, `записывайте`, `рассчитайте`, `поставьте`), OR pronoun `вы` / `вас` / `вам` / `ваш` / `ваша` / `ваше` / `ваши` used in a **casual** surface. Per `TRANSLATION_STYLE.md § Brand voice § Pronouns` — friendly T-form («ты») is brand-voice default for casual surfaces; V-form is exception only for formal surfaces (skip rule #1).

### Russian brand quote convention (rule #6 detail for ru)

ru should use guillemets `«My Water»` / `«Моя вода»`, not straight ASCII quotes. (DO NOT flag in this audit — quotes are a separate project-wide sweep; see § What NOT to flag.)

### Russian mixed-register patterns

If a connected ru text uses both «ты» and «вы» without semantic reason, flag.

## Calibration changelog

Durable-rationale only: **why** each calibration / skip rule / binding policy exists, so an operator can run any batch without re-deriving. The full per-group execution trail (sweep counts, per-batch accept/modify/reject, reject-rate %, risk-flags, `/tmp` report paths, incident narratives, per-session owner-doc bookkeeping, Lokalise-OTA boilerplate) is **frozen history, not live workflow** — relocated verbatim to:

> **Phase 0..5 execution log** (19-language sweep, 2026-05-15..2026-05-16, COMPLETE): [`ai_reports/tasks/2026-05-17_localization_audit_phase0-5_execution_log.md`](../ai_reports/tasks/2026-05-17_localization_audit_phase0-5_execution_log.md). Per-language **applied** status is authoritative in `git log -- "water/Supporting Files/Localization/"` (branch `localization`), not here.

Each entry below: `decision — why/origin — where it lives now`. New material prompt/skip/output changes still get a dated entry here (durable rationale, one line) **and** an execution-log append if they came from a sweep.

### Skip rules (§ What NOT to flag — pilot/group-calibrated false-positive patterns)

- **#1 formal V-form/honorific in formal surfaces** — pilot 1-50 flagged all «вы»; formal register is intentional on ASC / paywall hero+CTA / legal / permission / error-with-recovery / medical-educational / Siri-educational. Generalized to all T-V/honorific langs (Phase 1). Paywall-CTA stays formal even when proven ru is casual-T (`reachTheGoal` legacy outlier, no live call-sites) — codified Pre-G6 (Face A).
- **#2 legacy hard line break handling** — pilot 1-50 over-flagged mismatch; current policy is stricter: user-facing values should not contain manual hard line breaks.
- **#3 straight quotes / #4 trailing period on errors / #5 legacy please-comma / #6 comment-explained lexicon / #8 simple-noun beverage / #9 comment-explained casing / #11 pure stylistic / #12 British-in-comments** — pilot 1-50 FP buckets (separate sweeps or legacy-acknowledged).
- **#7 `|R|` + English-fallback in target** — post-13-27: do NOT delete / AI-translate a target entry holding English text when en has `|R|` (intentional stop-gap until Lokalise OTA). Incident: 18 siri/signup keys wrongly removed + restored.
- **#10 same defect en+target → flag en only** — cross-language dedup; en is the root.
- **#13 singular/plural en for multi-select** — post-13-27: fix at en source, don't pluralize target (`chooseYourGoal`).
- **#14 gendered count-caption** — post-13-27: don't flip M-sg → plural as a "fix" (reads as "multiple subjects"); needs `M`/`F` split (`sharesOfTheApp`).
- **#15 em-dash `—` U+2014** — post-Phase-0; **2026-05-16 policy: only `—` U+2014 forbidden in user-facing values (AI tell users dislike); `-` U+002D sanctioned incl. ` - ` separator; `–` U+2013 unregulated; doc-prose `—` unaffected.** Never *propose* `—` as a suggestion; replacement anchored on en (comma/period/colon/restructure; script-correct for ar/CJK). Canonical — `TRANSLATION_STYLE.md § Brand voice § Punctuation` + `mywater_ios docs/ai/COMMON_MISTAKES.md § [CM-EM-DASH-OVERUSE]`.
- **#16 target mirrors proven-ru restructure → not drift** — G2: codifies "How to use ru as reference" as an enforceable skip (recurring sole semantic-drift FP class). Scoped to the proven `Localizable.strings` ru only (see 2026-05-17 ru caveat).
- **#17 Danish optional pre-subordinate-clause comma** — G2: sanctioned by Dansk Sprognævn ("nyt komma"); `da`-specific carve-out, not a punctuation defect.

### Audit rules (§ What to audit)

- **rule #8 T-V/honorific map (all 21) + binding OPERATOR POLICY** — Phase 1 inlined the per-language casual/formal map (Scandinavian = "skip #8 entirely, no morphological T-V"); G1 made casual-surface V-form a **confirmed project-wide defect** (enumerate per-row, no Summary-consolidation / no deferral, validator must accept). Carried ru-parity tension CLOSED Pre-G6.
- **rule #9 script-appropriate punctuation** — D1/Phase-2 added the CJK clause (ja half/full-width blind spot); **G6 DELTA-G6-1 added the RTL/Arabic-script clause** (rule was CJK-only, masked by `ar.md`; structural blind spot for Phase 4 all-21 pass). Latin/Cyrillic unaffected; Devanagari integrity is a `typo` matter (`hi.md`).
- **rule #5 gendered variants** — Phase-1: identical M/F is CORRECT for genderless langs (id/ms/vi/ja/ko/zh-Hans/tr-partial); D3/Phase-2: the carve-out suppresses ONLY the gender-agreement finding, never per-variant typo/calque/semantic; G3: CJK M/F expectation **inverted** (a DIFFERING pair is the scrutiny target); G4 Delta-C: key the finding on the *defective* variant (exact-match apply on the better one is a no-op).
- **rule #2 `<target>` calque/restructure** — post-Phase-0 added RU→EN reverse-calque awareness to the `en` audit + `application`→`app` convention (`[CM-EN-SOURCE-RU-CALQUE]`); G4 Delta-B made the ru cross-check **mandatory pre-flag** (cuts the largest weak-signal FP class at source); G5-2 lifted "sibling-language contamination is a PRIMARY defect class" from `ms.md` into the base prompt, generalized to hi/ar.

### Format / infra / constraints

- **Triple `en+ru+target` input, ru as reference (not audit target), batch 200, ru-specific block optional, weak-AI calibration profiles inlined, `Target language:`/`Input:` first lines** — Phase 1 infra for the 19-lang sweep; `loc_audit_extract.py` 4-arg signature (legacy 3-arg numeric preserved).
- **Column discipline** (§ Input format) — G2: a defect quoted from the `en` line is `lang=en` even when co-occurring with a target issue; `current` must match the `lang` column.
- **Suggestion quality bar = a new-translation's bar** (§ Important constraints) — post-AI-translation: the auditor's own `suggestion` must pass the same brand-voice / clinical-term / spoken-plausibility filter (else `—` + rationale, never protect a "technically precise" calque); G2 added constraint-binding **suggestion completeness** (no 60-char truncation on brand-freeze / placeholder / hard-line-break rows); G5-1 added a language/register-purity self-check (auditor twice self-injected wrong-language tokens into its own suggestion).
- **`info` severity dropped; explicit hard/soft constraint split** — pilot 1-50 (noise without value; binding vs soft constraints).

### Anti-regression mechanisms

- **3-stage dead-key defense** — G3 `tr` incident (auditor lowercased a key → validator blind → `loc_audit_apply.py` silently appended a dead duplicate-casing key, real typo left unfixed). Mitigated at three independent stages: Delta-1 auditor byte-for-byte key copy (§ Output format), Delta-2 validator byte-for-byte key cross-check (validator prompt), Delta-3 applier loud-fail-no-append (`--allow-append` default off). Confirmed scaling G3→G6 (0 recurrence across 4 groups); mode is dead.
- **`RU-PARITY-DEFER:` routing** — G3 Delta-5 `[tech debt]`: surfaces a latent ru-side V-leak (ru itself V-form on a casual key) without auto-applying; true root cause was a separate operator decision, **closed Pre-G6** (now a safety net only, no known-open cluster).
- **No `lang=ru` audit rows for non-ru targets** — G4 Delta-A: the ru reference column is read-only; the deterministic applier cannot act on it.
- **Phase-3 collection architecture** — audit/validator sub-agents self-write `/tmp/..._findings.md` and return only summary counts (overrides the prompt's "no file writes" for the Phase-3 collection step only; at ~139 runs, routing every table through the orchestrator risked auto-compaction loss). Operator-approved.
- **7 batches/lang** — G1: `loc_audit_extract.py` indexes by en (1352), not target (1157); a 6-batch loop silently dropped en 1201-1352 (~102 entries/lang). Correct coverage = 7 windows.

### Binding operator decisions

- **Pre-G6 ru-anchor V-form parity — CLOSED `[root cause]`** — Face B: 7 evidenced genuinely-casual ru keys swapped V→T in `ru.lproj` (`yearResultsPushTitleTemp`, `didgestSettingsTitle`, `pressOnPlusToAdd`, `drinkParamsNotionMessage`, `youShuldAddToFriend`, `drinksReorderText`, `notifSoundText`) — restores anchor trust so all 19 langs self-heal on the normal accept path; Face A: paywall-CTA codified intentionally-formal. Settings-register keys deliberately excluded (own neutral register). Canonical owner — `TRANSLATION_STYLE.md § Brand voice § Pronouns`. Rejected `[over-engineering]` non-ru casual reference infra; rejected `[tech debt]` codify-as-formal.
- **Bespoke-prompt skip-rule import** — Phase 4 em-dash incident: a bespoke (non-audit-sub-agent) cross-language/consistency prompt does NOT inherit § What NOT to flag and recommended `—` mirroring a ru anchor that itself violates #15. Lesson: any future bespoke cross-language prompt MUST explicitly carry the no-em-dash constraint or import skip rules (Phase 5 prompts already do).
- **Mass-apply over submission-affecting files** — Phase 5: a deterministic Bash applier over many `InfoPlist.strings` is auto-mode-permission-blocked (correctly; `dangerouslyDisableSandbox` does not cover that classifier). Design the applier **idempotent** (key-only match, force-target, insert-if-absent) so partial Edit-tool progress + a later operator-run full pass compose cleanly. `[CR-SUBMISSION]`: Phase 5 changed localized permission *purpose* strings + added localized `NSCalendarsUsageDescription` (20 langs); hard-gated items untouched; store-review evidence = `NEEDS_ASC`.
- **ru `.stringsdict` / `InfoPlist.strings` were OUTSIDE the 27-batch proving corpus** — Phase 5 surfaced a real ru `.stringsdict` defect (`%li разы`→`%li раза`, CLDR `other`=fractions). Basis for the 2026-05-17 ru proving-corpus caveat below; do not treat ru as an infallible correctness anchor for `.stringsdict` / `InfoPlist`.

**Status:** 19-language audit **Phase 0..5 COMPLETE** (per the execution log). RU-PARITY-DEFER is a safety net only. Phase-3 collection-architecture & 7-batch coverage corrections are reflected in `ai_reports/tasks/2026-05-15_localization_audit_19_langs_plan.md`.

- **2026-05-17 — doc-reconciliation pass (no sweep; owner-doc drift fixes, operator-requested):**
  - **Suggest ≠ translate reconciliation** — prompt intro reworded: "NOT to translate yourself" forbids silently overwriting shipped values, NOT emitting the reviewed `suggestion` (which passes the operator + validator gate). Removes a real actionability ambiguity vs § Important constraints "suggestion quality bar = new-translation rules" — a weak model could otherwise refuse to give suggestions or, conversely, self-apply.
  - **ru proving-corpus scope caveat** — § How to use ru as reference + the `ru` input-format line now state ru is PROVEN for `Localizable.strings` only; ru `.stringsdict` / `InfoPlist.strings` were outside the 27-batch corpus (Phase 5 surfaced a real ru `.stringsdict` defect `%li разы`→`%li раза`). Caveat moved from frozen changelog history to where the anchor is actually used; scoped skip-#16's ru-mirror carve-out to the proven corpus.
  - **lint coverage boundary** — § Verify clarifies `localization_lint.py` checks only non-en `Localizable.strings`; `.stringsdict` / `widget14.strings` / `InfoPlist.strings` are NOT covered → manual check, do not over-trust a green `make verify`. No script change (documents the boundary, does not widen the lint).
  - Paired owner-doc edits (same pass, outside this file): `docs/LOCALIZATION.md` (lint-coverage boundary on the write-time validate step; en-ahead key-count model corrected — `delta` is the translation backlog and is **not** required to equal `count(|R|)`, since `|R|` also sits on keys present in all 21 locales; § Новый язык create-list +`InfoPlist.strings`), `docs/ai/DOC_ROUTING.md` (phantom `Intents.strings` / `Base.lproj/Intents.intentdefinition` localization pool — non-existent on FS — replaced with the real `widget14.strings` + `widget14.intentdefinition` widget-intent pool; new-language fanout checklist corrected to `Localizable.strings` + `Localizable.stringsdict` + `InfoPlist.strings` + `widget14.strings`).
  - No new skip/audit rule; no `.strings` / `.stringsdict` value changes; no calibration delta. Verification = `make docs-check` (doc-only, no Swift touched).

## Related

- `loc_corpus.py` / `loc_corpus_ndjson.py` / `loc_corpus_import.py` — corpus read-write lib, Lokalise→ndjson generator, ndjson→Lokalise importer.
- `loc_audit_extract.py` — extract en+ru+target batches from the corpus for audit.
- `loc_audit_apply.py` — deterministic applier of validated findings into the corpus.
- `loc_r_marked_translations.py` / `loc_apply_lang.py` / `loc_merge_languages.py` — translation backlog, `{key:value}` apply, language-set merge (all corpus-backed).
- `loc_audit_lang_calibration/<lang>.md` — per-language calibration profiles for weak-AI-signal targets (ar, hi, vi, id, ms).
- `TRANSLATION_STYLE.md` — canonical style / linguistics (this repo: § Translation discipline, § Brand voice, § Translator context); `mywater_ios docs/LOCALIZATION.md § Shared localisation corpus & tooling` — iOS-side pipeline overview, `§ Comment encoding` — iOS `.strings` comment mechanics.
- `mywater_ios utility/localization/localization_lint.py` — iOS-only `|R|` lint on iOS `.strings` (not this corpus).
- `ai_reports/tasks/2026-05-15_localization_audit_19_langs_plan.md` (mywater_ios) — historical 19-language iOS `.strings` audit plan.
- Pilot results were applied in commits leading up to 2026-05-15 (`git log -- "water/Supporting Files/Localization/"`).
