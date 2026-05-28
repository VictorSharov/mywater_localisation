<!--
doc-role: canonical
doc-owner: TRANSLATION_STYLE.md (репозиторий mywater_localisation)
doc-scope: кросс-платформенный канон стиля/лингвистики локализации — brand voice, register/T-V/honorific, RU→EN reverse-calque, пунктуация/em-dash, per-language специфика, translator-context дисциплина
-->

# Translation style — кросс-платформенный канон лингвистики и brand voice

Канонический дом для **правил стиля и лингвистики** локализации MyWater, общих для всех платформ (iOS / Android / server). Здесь живут: brand voice, register (T-/V-form / honorific), RU→EN reverse-calque, пунктуация / em-dash, per-language специфика, clinical-term дисциплина, дисциплина translator-context комментариев.

Потребители канона:

- переводчики (люди и AI) — при переводе / правке существующих ключей;
- audit sub-agent — `loc_audit_prompt.md` **операционализирует** эти правила (flag/skip/severity) дословно для Opus 4.7 sub-agent'а; per-language калибровки — `loc_audit_lang_calibration/<lang>.md`;
- платформенные owner-доки ссылаются сюда, а не форкают: iOS `mywater_ios docs/LOCALIZATION.md`, server `mywater_server resources/locale/CLAUDE.md`.

**Граница со платформенной механикой.** Этот док — про *стиль и смысл* перевода. Платформенная *механика* кодирования строк живёт у каждой платформы и сюда не дублируется: iOS `.strings` / `.stringsdict` / `R.swift` / target membership — `mywater_ios docs/LOCALIZATION.md`; server locale-pack — плоский JSON `{ключ: строка}` — `mywater_server resources/locale/CLAUDE.md`; сериализация корпуса + маркер «не верифицировано / нужен перевод» (`unverified` + пустой target) — `CLAUDE.md § [CR-CORPUS-OWNER]` / `§ [CR-CORPUS-UNVERIFIED]`.

**Pipeline** (overview, canonical — `CLAUDE.md § Pipeline`): `Lokalise → loc_corpus_ndjson.py → strings.ndjson` (корпус читают AI/переводчики) → правки пишутся в корпус → `loc_corpus_import.py --apply` импортирует в Lokalise → Lokalise экспортирует под iOS `.strings` / Android `.xml` / server JSON.

## Translation discipline (target language)

Применяется, когда оператор **явно** даёт задачу на перевод существующих ключей в target language (не fanout новых ключей — `mywater_ios docs/ai/COMMON_MISTAKES.md § [CM-LOCALE-MASS-FANOUT]` остаётся default; create-flow новых ключей — платформенный: iOS `mywater_ios docs/LOCALIZATION.md § Rules for AI § Write-time flow`, корпус — `CLAUDE.md § Working on the corpus`). Перевод — отдельная дисциплина, не word-for-word substitution: EN source — ground truth для смысла, не для синтаксиса target language. Brand voice (`§ Brand voice`) — friendly health-conscious companion — применяется в **обоих** языках одинаково; clinical / medical / jargon формулировки в target language отклонять, даже если технически грамматически правильно. Это правило распространяется на все 21 язык, не только ru.

**Маркер «не верифицировано» (`unverified`) при translation-задаче.** Даже когда оператор явно поставил задачу перевести (этот раздел применим) и переводы делает агент, маркер `unverified` **не снимать**: перевод выполнен AI и ещё не верифицирован человеком. Снятие — отдельное действие **только** по явному запросу оператора либо когда human-verified перевод приходит round-trip через Lokalise. Завершённое состояние translation-задачи = переводы записаны + `unverified` на месте. Canonical owner маркера (общий для корпуса / iOS / сервера) — `CLAUDE.md § [CR-CORPUS-UNVERIFIED]`: корпус — поле `unverified` (плюс пустой `""`-target = «нужен перевод»); iOS / Android / server читают это состояние из Lokalise. Прежний `|R|`-маркер источника (iOS `en.lproj`, server `notes`) выведен из употребления.

**`ru` — со-источник, переводится сразу.** Исключение к «переводить только по явной задаче»: `ru` держится в паритете с `en` (команда ru-native, `ru` — anchor аудита). При добавлении / смене `en`-источника `ru` переводится **немедленно**, в той же правке, и остаётся `unverified` до проверки человеком; остальные 19 языков обнуляются в `""` и ждут отдельного прохода перевода. Канон — `CLAUDE.md § [CR-CORPUS-SOURCE-CHANGE]` / `§ Self-translation discipline`.

**Default register reminder (ru / de / fr / es / it / pl / tr / nl / pt-BR / zh-Hans / hi / id / ms / vi и аналогичные T-V split языки):** основная формулировка — **friendly T-form («ты»)** для casual surfaces (notifications, motivational, tips, awards, empty states, beverage / achievement names, widget hints, in-app feature cards). Formal V-form («вы») — exception для App Store / paywall hero / educational / legal / permission prompts / errors / Siri AppIntent description (полный список и pre-commit detection signal — `§ Brand voice § Pronouns`). AI default бесконтрольно вытягивает V-form из training data; проверять каждую новую translation на imperative suffix `-ите` / `-айте` / `-йте` / `-ьте` и pronoun `вы` / `ваш` ещё до записи в файл — детектор в `§ Brand voice § Pronouns § Pre-commit detection signal (ru)`.

### Принципы

1. **Naturalness > literal fidelity.** Перевод должен звучать как native speech в этом surface, не как калька. Если literal путь awkward — restructure: поменять word order, заменить verb, дропнуть calque preposition, использовать другую конструкцию (past participle substantive, interrogative form, noun phrase вместо verb phrase).

2. **Spoken plausibility test.** Прочитать candidate вслух или представить, как Siri / native speaker его произносит. Если в обычной беседе или в команде голосовому ассистенту так бы не сказали — отклонить, искать другой вариант. Test обязателен для voice-aloud surface (Siri, notifications, accessibility labels).

3. **Reject clinical / medical / jargon для casual surface.** Hydration tracker = casual companion, не medical chart. Не использовать `водный баланс`, `гидратация`, `потребление воды`, `консумация`, `насыщенность` (и эквиваленты в других языках) для friendly Siri / notification / UI, даже если технически правильно. Apple Health Russian термин `Потребление воды` — formal register Apple Health, не подходит нашему friendly tracker.

4. **Word applicability check.** Каждое выбранное target слово проверять на:
   - Семантическое соответствие — передаёт ли смысл EN source без drift?
   - Register fit — подходит для этого surface (casual / formal / clinical / playful)?
   - Domain fit — этот lexeme используется в этой области (hydration / fitness / casual UI)?
   - Collocation fit — естественно сочетается с соседними словами этого предложения и существующими переводами рядом?

5. **Calque detection — common anti-patterns (EN → ru).** Расширять по мере появления:
   - `прогресс по [noun]` для не-учебных subject — `прогресс по воде` ❌ (`прогресс по математике / истории` ✓ для учёбы); ru `прогресс по X` requires X = subject area / discipline
   - `[adj]ный баланс` для casual surface — `водный баланс` ❌ для Siri intent (clinical medical term)
   - Direct verb mapping `Show X` → `Показать X` грамматически OK, но clinically sounds когда X — clinical noun (`Показать гидратацию` ❌)
   - Direct preposition mapping (`of`, `on`, `for`, `with`) — EN preposition не всегда переходит в ru predicate; часто требуется restructure
   - Literal idiom translation (`hands-free` → `без рук` ❌; `голосом` ✓)

6. **Sibling surface check before commit.** `rg` по domain identifiers / theme / similar keys в target переводах:
   - Register consistency (`вы` vs `ты`) внутри одного surface — `§ Brand voice § Pronouns`;
   - Lexicon consistency (`goal` / `норма` mix policy, `вода` / `жидкость`, brand quoting) — `§ Brand voice § Lexicon § Legacy vs current`;
   - Tone consistency (encouraging / neutral / urgent / playful).

7. **Gender neutrality для voice surface.** Siri / voice assistant text без user-gender-context: prefer passive past participle (`выпито` вместо `выпил/а`), formal plural (`вы выпили` — plural form исторически gender-neutral), substantive noun (`выпитое`). Gendered M/F variants остаются canonical только для explicit M/F key split (`§ Brand voice § Gendered variants`); не создавать новые gendered keys для voice surface.

8. **EN source quality — RU→EN reverse calque discipline.** Команда — ru-native; main mental language — ru. EN source писался / пишется ru-speakers и **может содержать calques от русских формулировок** ("press on +", "fulfill your daily water intake", "rate of water a day", "we get consultations from", "amount of liquid drunk", "to / from", "information is not filled", "Last drinks will be displayed"). Это **не** translation issue (en — source) — это quality issue самого source. Каждую новую / редактируемую en-строку проверять spoken-plausibility test глазами native EN speaker: «native iOS / native US English copywriter так бы написал?». Common reverse-calque triggers — direct preposition mapping (`на` → `on`/`through`, `по` → `over`/`on`), passive `is + past participle` translations of ru reflexive (`не заполнено` → "is not filled"), nominalization (`динамика веса` → "weight dynamic"), translated commands (`нажать на` → "press on"). Audit existing en source через `loc_audit_prompt.md` (en-audit лента).

### AI cognitive budget for translation

Перевод **не** optimize-for-token-saving task. Recurring AI failure mode: агент выбирает first instinctive candidate (обычно literal calque), не проверяет naturalness, выпускает kalka-перевод. **Не экономить токены на reasoning** — translation требует multiple passes per key:

- **Generate ≥3 alternatives** перед commit'ом, изложить в чате с trade-off. First candidate почти всегда — literal calque; альтернативы выявляют natural-language path. Trade-off visible оператору — корректирует выбор до записи в файл.
- **Read translator comment целиком** (Surface, Type, Context, Placeholders, Constraints, Tone) — не сканировать ради скорости. Spend extra tokens на context understanding **до** formulation, не после. Если comment упоминает соседние surfaces / parity keys — открыть их через `rg`.
- **Neighbor check** через `rg`: similar keys в том же surface / target переводах / existing translations того же концепта в проекте. Не commit'ить перевод без проверки, как соседние ключи решили аналогичную задачу.
- **Spoken plausibility check** для voice-aloud surface: explicitly воспроизвести в голове, как native speaker слышит фразу. Если awkward — отвергнуть, не commit'ить «потому что lint pass».
- **Iterate after first draft.** First draft почти всегда literal. Re-examine: где calque? где clinical? где prepositional mapping? где register mismatch с соседями? Restructure. 2-3 passes — норма, не roundtrip overhead.

Anti-pattern: «перевожу N строк подряд за один проход без анализа контекста каждой». Это batch-fan-out режим, ловится в audit (`loc_audit_prompt.md`) как `awkward` / `calque` / `semantic-drift`. **Перевод — per-key task с per-key reasoning**, даже если N=20 ключей в batch'е. Token budget на batch ≠ token budget на key.

### Bad → Good examples (ru)

```
EN: "Show current hydration"  (Siri AppIntent title)
❌ "Показать водный баланс"        — clinical medical term для casual Siri
❌ "Показать прогресс по воде"     — calque "progress on [topic]"; вода ≠ subject area
❌ "Показать гидратацию"           — direct verb mapping, clinically sounds
✓ "Показать выпитое за день"      — native ru: past participle substantive, casual

EN: "Show today's hydration progress."  (Siri AppIntent description)
❌ "Показать прогресс водного баланса за сегодня."  — двойной clinical стек
❌ "Показать прогресс по воде за сегодня."          — calque "progress on water"
✓ "Показать, сколько воды выпито за сегодня."      — native ru construction "сколько ... выпито"

EN: "Use Siri or the Shortcuts app to log a drink hands-free."
❌ "...записывать напитки без рук."  — literal калька "hands-free"
✓ "...записывать напитки голосом."  — native ru: "голосом" (by voice)

EN: "Added [%1$s] of [%2$s]"  ([%1$s] = amount + unit, [%2$s] = drink name in nominative)
❌ "Добавлено [%1$s] [%2$s]"   — reads as "Добавлено 250 мл Вода"; drink в nominative awkward после количества
✓ "Добавлено: [%2$s], [%1$s]" — reorder + colon/comma label format = "Добавлено: Вода, 250 мл"

EN: "Hydration today"  (Live Activity title — Dynamic Island / lock screen)
❌ "Гидратация сегодня"  — clinical calque, native ru speakers так не говорят в casual UI; Apple Health term register
❌ "Водный баланс сегодня"  — clinical medical term для casual hydration tracker
✓ "Вода сегодня"           — native casual ru; "вода" в casual UI понимается как любая выпитая жидкость в контексте hydration trackerа
✓ "Сегодня"                — короче, без lexical category mismatch; работает в title-position
✓ "Выпито за день"        — past-participle substantive, native ru construction

EN: "Drink added"  (Live Activity / Dynamic Island confirmation)
❌ "Гидратация добавлена"  — clinical, ломает naturalness
✓ "Напиток добавлен"       — native ru, прямой и однозначный

EN: "Add drinks in one tap with My Water Premium!"  (in-app upsell hint, casual surface)
❌ "Добавляйте напитки в одно нажатие с My Water Premium!"  — V-form в casual surface (suffix `-айте`)
✓ "Добавляй напитки в одно нажатие с My Water Premium!"     — T-form, friendly default

EN: "Stay in the moment. Drink a glass of water and enjoy 💧"  (hypothetical casual notification)
❌ "Оставайтесь в настоящем. Выпейте стакан воды и наслаждайтесь моментом💧"  — V-form в notification
✓ "Останься в настоящем. Выпей стакан воды и наслаждайся моментом 💧"         — T-form, dropped trailing `-есь` / `-айтесь`

EN: "Don't get distracted by ads and use the app more efficiently"  (paywall benefit row, casual)
❌ "Не отвлекайтесь на рекламу и используйте приложение эффективней"  — двойной V-form leak
✓ "Не отвлекайся на рекламу и используй приложение эффективнее"      — T-form

EN: "Your health is in your hands. Take care of yourself today, drink enough water 💧"  (hypothetical casual notification)
❌ "Ваше здоровье в ваших руках. Позаботьтесь о себе сегодня, пейте достаточно воды 💧"  — `вы`-pronoun + V-form imperative
✓ "Твоё здоровье в твоих руках. Позаботься о себе сегодня, пей достаточно воды 💧"      — T-form pronouns + imperatives

EN: "Please give us permission to access your camera to take a photo for the avatar"  (`NSCameraUsageDescription`, permission prompt)
✓ "Пожалуйста, дайте нам разрешение на доступ к вашей камере, чтобы сделать фотографию на аватар"  — V-form correct: formal surface (permission prompt), see § Pronouns formal-surface list

EN: "No Internet connection. Please check your connection and try again later."  (error with recovery instructions)
✓ "Нет соединения с сервером. Пожалуйста, проверьте ваше интернет-соединение и попробуйте снова позже."  — V-form correct: formal surface (error recovery)

EN: "You drank 1.2 L of 2 L"  (widget / lock screen daily summary, casual surface)
❌ "Вы выпили 1,2 л из 2 л"   — V-form в casual widget surface
❌ "Ты выпил 1,2 л из 2 л"   — требует `*M` / `*F` split (`выпил` / `выпила`); pronoun adds little
✓ "Выпито 1,2 л из 2 л"      — pronoun-free, gender-neutral, native; см. § Pronouns § Pronoun economy

EN: "Time to take a sip"  (gentle reminder notification, casual surface)
❌ "Сделайте пару глотков"           — V-form imperative
❌ "Тебе пора сделать пару глотков"  — pronoun adds nothing, фраза тяжелее
✓ "Пора сделать пару глотков"        — impersonal nudge, friendly, native ru

EN: "Goal completed for today"  (Live Activity / Dynamic Island confirmation, casual surface)
❌ "Вы выполнили цель"          — V-form в casual confirmation
❌ "Ты выполнил цель"           — требует gender split
✓ "Цель на сегодня выполнена"  — stative, pronoun-free, native; работает в title-position

EN: "What goal shall we set for today?"  (onboarding goal-set prompt, casual interactive)
❌ "Какую цель вы поставите на сегодня?"  — V-form, дистанцированно
❌ "Какую цель ты поставишь на сегодня?"  — T-form ok, но прямой вопрос звучит как экзамен
✓ "Какую цель поставим на сегодня?"      — inclusive plural ("мы вместе"), partner-app tone
```

Расширять examples при появлении новых typed mistakes из audit / operator feedback. Examples ru — наиболее частая target language; для других языков (de / fr / es / pl / tr / nl / pt-BR / zh-Hans / ja / ko / ar / hi / id / ms / vi и т.д.) принципы идентичны, конкретные calque patterns отличаются по target grammar.

## Brand voice

Зафиксировано на основе аудита корпуса `en` source ключей. Это descriptive guide — фиксирует **наблюдаемый** голос приложения, а не вводит новое направление. Переводчик поддерживает этот регистр в target language; AI агент держит этот регистр в **обоих** языках — clinical / medical / jargon формулировки в target language отклонять, даже если технически правильно. Translation-time дисциплина для target language (когда оператор явно даёт задачу на перевод) — `§ Translation discipline (target language)`.

Полноценный нормативный brand voice guide (с согласованием направления развития бренда) — отдельная задача.

**Overall character.** Приложение — friendly health-conscious компаньон, не медицинский авторитет и не корпоративный продукт. Голос — тёплый, поддерживающий, иногда playful; обращается к пользователю напрямую и позиционирует приложение как партнёра, который помогает («we will help», «we believe in you», «we are proud of you»). Без жаргона, без алармизма, без снисходительности.

### Pronouns

- **User → "you" / "your"** — direct address на «ты-эквиваленте» по нормам target language. Примеры: «Your body will thank you», «You did it!», «Take care of yourself today».

  - **Default — friendly T-form («ты»).** Это основная формулировка для всего casual user-facing текста в языках с T-V split. AI training data перекошен в сторону formal V-form («Добавьте текст», «Введите значение» — register IT-документации и customer service), поэтому первый instinctive candidate в ru / de / fr / es и т.д. почти всегда V-form. Это нужно сознательно отвергать на write-time; T-form — не stylistic option, а brand-voice default.

  - **Casual surfaces — T-form обязателен:**
    - Notifications: `notification1_*`, `tempPush*`, seasonal motivational pushes.
    - Motivational text: `text1_*..text4_*`.
    - Awards / streak / congratulations: `awardCongratulation*`, `allAwards*`, `haveAward*`, `achivment*`.
    - Tips: `tip1..N`.
    - Social shares (за исключением «I»-commitment first-person).
    - Empty states, onboarding hints / shorts (НЕ educational paragraphs — те остаются V-form, см. ниже).
    - Beverage names / achievement names и descriptions.
    - Widget gallery descriptions, widget hint text (`widgetText` и аналоги).
    - In-app feature card / upsell hint text (`tempAddOneTap`, `forgotWriteText`, `manyDrinksText`, `noAdText`, `tempFirstSteps`, `weightPromo*` и аналоги — feature-описания внутри приложения, не paywall hero).
    - Casual paywall asks («Не готов?», «Попробуй ещё»).

  - **Formal V-form («вы») — exception для surfaces, где clarity / authority / legal weight требует formal register:**
    - App Store metadata: `appstore.app.description`, `appstore.app.title`, `appstore.app.subscriptionTemsAppStore`, screenshot prose.
    - Paywall marketing hero / promo slides: `free.title*`, screenshot taglines, главные promo headlines с marketing claim (`apphud.offer.trial_extend.description*`).
    - Paywall CTA buttons / упоминания offer условий («Попробуйте 7 дней бесплатно», «Активируйте подписку») — **intentional single-register formal V-form**, единый register с paywall hero (осознанный выбор ради clarity + единства с hero, не «historical accident»). Применяется ко всем T-V / honorific языкам. **Carve-out остаётся binding и при ru-casual-T outlier:** если на отдельном paywall-CTA ключе проверенный ru оказался casual-T (известный legacy outlier — `reachTheGoal` = «Достигни цели», no live call-sites; sibling `try*` / `free.title*` / `apphud.offer.*` все V-form), это **не** отменяет carve-out и **не** делает formal target дефектом — ru на этом ключе outlier, а не anchor для register. Audit (`loc_audit_prompt.md` skip rule #1) на таких ключах formal target НЕ флагает.
    - Onboarding educational paragraphs со ссылкой на medical authority (доктор, body calculation rationale, goal recommendation rationale, `youShouldDrink0Digits` и аналоги).
    - Legal / privacy notices, Terms of Use.
    - Permission prompts (`NS*UsageDescription` в iOS `InfoPlist.strings`).
    - Error messages с recovery instructions: `noConnection`, `noFreeStorage`, `noRamError`, `favoriteDrinkCreateFailed`, watch / Siri / Premium fallback errors (`watchPremium*Unavailable`, `watchPremiumPurchaseNotCompleted`, `siriLogDrinkPremiumLocked`).
    - Siri AppIntent description / placeholder educational text (`siriPlaceHolder` и аналоги — инструкция, как пользоваться Siri).

    В этих surfaces V-form — intentional, не ошибка. Не помечать formal register как failure при audit, когда surface формальный.

  - **Key-level Register signal — write-time anchor для T-/V- решения.** Канонический per-key анкор для register-решения — поле `Register:` в translator-context (`§ Translator context § Опциональные поля`). Значения: `Register: casual T-form` / `Register: formal V-form` / `Register: neutral`. Поле не отменяет surface→register default map выше; оно фиксирует решение на write-time, чтобы AI-переводчик (training-prior которого тянет к formal V-form) не делал V-form leak в casual surface. Cross-platform — применимо ко всем 16 T-V / honorific языкам корпуса; на Scandinavian / `en` работает как tone-shift hint (lexical formality), не pronoun-swap. Audit-sub-agent читает `Register:` как authoritative override для surface-based default; отсутствие `Register:` **не** значит casual — fallback к surface-based default из списка выше.

  - **Pre-commit detection signal (ru) — обязательная проверка перед записью перевода в casual surface:**
    - **Imperative окончание** — `-ите` / `-айте` / `-йте` / `-ьте`? Подозрение на V-form leak. Swap to T-form `-и` / `-ай` / `-й` / `-ь`:
      - `добавьте` → `добавь`, `выпейте` → `выпей`, `пейте` → `пей`, `начните` → `начни`, `следуйте` → `следуй`, `оставайтесь` → `оставайся`, `не забывайте` → `не забывай`, `позаботьтесь` → `позаботься`, `освежите` → `освежи`, `используйте` → `используй`, `откройте` → `открой`, `попробуйте` → `попробуй`, `создайте` → `создай`, `выберите` → `выбери`, `сделайте` → `сделай`, `нажмите` → `нажми`, `проверьте` → `проверь`, `отслеживайте` → `отслеживай`, `учитывайте` → `учитывай`, `записывайте` → `записывай`, `рассчитайте` → `рассчитай`, `поставьте` → `поставь`.
    - **Личные местоимения** — `вы` / `вас` / `вам` / `вами` / `ваш` / `ваша` / `ваше` / `ваши` / `вашего` / `вашему` / `вашей` / `вашим` / `вашими` в casual surface? Swap to T-form: `ты` / `тебя` / `тебе` / `тобой` / `твой` / `твоя` / `твоё` / `твои` / `твоего` / `твоему` / `твоей` / `твоим` / `твоими`.
    - **Past participle / agreement** — `вы выпили`, `вы достигли`, `вы готовы` в casual surface? Swap to T-form по explicit M/F key split (`ты выпил` / `ты выпила`) либо к gender-neutral конструкции для voice / Siri surface (`выпито`, `выпитое` — см. `§ Translation discipline § Gender neutrality для voice surface`).
    - Если surface — formal по списку выше, V-form correct; править не нужно.

  - **Legacy V-form в casual ключах — grandfather, не drive-by.** Существующие casual ключи с V-form (`tempAddOneTap`, `forgotWriteText`, `manyDrinksText`, `noAdText`, `tempFirstSteps`, `widgetText`, и аналоги в других casual surfaces) — наследие предыдущего переводческого решения; не переписывать drive-by при touched-strings задачах. Mass sweep по `rg`-сигналу `-айте` / `-ите` в casual surface = `mywater_ios docs/ai/COMMON_MISTAKES.md § [CM-MECHANICAL-GREP-SWEEP]` поверх `§ [CM-LOCALE-MASS-FANOUT]`: vendor console Lokalise — canonical owner переводов, платформенный PR не инициирует mass retranslation.
    - При rewrite того же ключа (когда EN source меняется, ключ переименовывается или удаляется) — новая ru формулировка идёт в T-form по этой rule.
    - При adjacent правке в том же smallest surface block (например, переписываешь `pushRetention_1`, рядом в файле сидят `pushRetention_2..5` с V-form) — НЕ swap соседей; это другой ключ, другая задача.
    - Новые ключи в casual surface — сразу T-form, никакого grace period.
    - **Audited ru casual V-leak set — corrected (operator-gated, 2026-05-16, pre-G6 localization audit).** Точечный evidenced набор genuinely-casual ru ключей, где сам проверенный ru leaked V-form, исправлен на T-form по явному operator-решению — отдельная operator-gated задача, документированный exception к grandfather, **не** drive-by `rg`-sweep: `didgestSettingsTitle`, `pressOnPlusToAdd`, `drinkParamsNotionMessage`, `youShuldAddToFriend`, `notifSoundText`. Теперь canonical T-form — не возвращать к V-form. Остальной casual корпус ru (`notification*` / `text1_*..text4_*` / `tip*` / `award*` / …) V-form-чист и остаётся под grandfather выше. Settings-register surfaces (`appIconDescription`, `chooseAppStyle`, `tempChooseInterval`) намеренно НЕ входят в набор — Settings = собственный neutral register (§ По типу поверхности), отдельный register-вопрос, не casual-T leak.

  - Внутри одного surface держать единый register; не смешивать formal и informal в одном связном тексте.

  - **Pronoun economy — prefer pronoun-free / impersonal phrasing where natural.** Русский часто не требует местоимения вовсе; passive / impersonal / stative конструкции звучат native и не вытягивают `ты` в каждой строке. Это **не отмена** T-form default — это второй слой на нём: когда прямое обращение действительно нужно — `ты` / `твой`; когда фраза работает без местоимения — лучше без местоимения. Wellness habit-tracker по своей природе про личную привычку и тело; постоянное `ты выпил` / `ты достиг` / `у тебя` начинает звучать как сопровождающий комментатор, а не как partner-app.

    - **Default ranking** для нового перевода в casual surface:
      1. **Pronoun-free / impersonal** — пробовать первым, если фраза не теряет тёплый support tone.
      2. **T-form `ты` / `твой`** — для прямой адресации, congratulations, body-care, motivational push с emotional payload.
      3. **V-form `вы` / `ваш`** — только в formal surfaces по списку выше.

      Не использовать T-form ради T-form, если impersonal native звучит лучше; не использовать pronoun-free, если фраза становится bureaucratic / системной.

    - **Когда pronoun-free лучше:**
      - **Stative / результат**: «Цель на сегодня выполнена», «Осталось 500 мл до цели», «Хороший темп», «Норма выполнена» (вместо «Ты выполнил цель», «Тебе осталось 500 мл», «У тебя хороший темп»).
      - **Friendly nudges / reminders**: «Пора выпить воды», «Время сделать пару глотков», «Можно добавить напиток» (вместо «Тебе пора выпить воды», «Ты можешь добавить напиток»).
      - **Past-tense о выпитом / добавленном**: «Выпито 1,2 л из 2 л», «Сегодня добавлено мало», «Напиток добавлен» (вместо `*M` / `*F` split `ты выпил` / `ты выпила`).
      - **Inclusive plural в interactive prompts**: «Какую цель поставим на сегодня?», «Выберем напиток» — `мы`-инклюзивная форма как партнёр, не authoritative «выберите».

    - **Когда оставлять прямое обращение (`ты` / `твой`):**
      - **Direct congratulations / motivation**: «Ты почти достиг цели», «Ты молодец», «Отлично, ты справился» — личностное обращение усиливает emotional payload.
      - **Body / habit как personal**: «Позаботься о себе», «Твоё здоровье в твоих руках», «Твой организм скажет тебе спасибо» — self-care framing требует возвратной адресации.
      - Когда pronoun-free версия теряет тёплый support tone: «Цель не достигнута» — холодно и системно; «Сегодня немного не дотянул» / «Завтра наверстаем» — тёплый.

    - **Pragmatic bonus.** Pronoun-free past-tense (`выпито`, `добавлено`, `выполнено`) автоматически gender-neutral — обходит необходимость `*M` / `*F` split keys, упрощает translator workflow и удешевляет new copy. Это родственно `§ Translation discipline § Gender neutrality для voice surface`, но применяется шире — не только Siri / VoiceOver, а везде, где past-tense statement не требует личной адресации. Существующие gendered keys (`text1_*M` / `text1_*F`, `todayDrinkedM` / `todayDrinkedF` и т.п.) — grandfather по `§ Gendered variants`; новые pronoun-free формулировки не вынуждают вводить дополнительный gender split.

  - **Применять как pronoun-swap** (T-form / V-form грамматически различны): `ru` (ты / вы), `de` (du / Sie), `fr` (tu / vous), `es` (tú / usted), `it` (tu / Lei), `pl` (ty / Pan / Pani), `tr` (sen / siz), `nl` (jij / u), `pt-BR` (você / o senhor), `zh-Hans` (你 / 您), `hi` (tum / aap), `id` (kamu / anda), `ms` (awak / anda), `vi` (kinship-based: `bạn` по умолчанию — не грамматический T-V, см. calibration).
  - **Применять как tone-shift, не pronoun-swap** (T-V distinction отсутствует или V почти не используется): `en`, `ar`, `da`, `nb`, `sv` — formal surfaces отличаются lexical register / sentence structure, не местоимениями.
  - **Применять через honorific levels** (отдельная система формальности, не binary T-V): `ja` (敬語 keigo / です/ます ↔ casual), `ko` (해요체 / 합니다체 ↔ 해체) — formal surfaces используют higher honorific level, casual UX — нейтральный / informal level.

- **App → "we" / "our" / "our app" / "My Water"** — first-person plural, как партнёр / команда: «We will calculate your goal», «We are proud of you!», «We give a discount to help you». Не «the app», не «MyWater system».
- **User в social shares / онбординг commitment → "I" / "my"** — first-person singular: «I drank the required daily water volume», «I will try to achieve the goal every day for: …».

### По типу поверхности (observed)

| Поверхность | Tone | Примеры | Что разрешено |
|---|---|---|---|
| Motivational text (text1_*, text2_*, text3_*, text4_*) | friendly, encouraging, sometimes playful | "Hi, add the first glass of water", "You did it!", "Well done! Today you drank", "Don't stop!" | `!`, краткие фразы, natural wrapping для визуального ритма |
| Notifications (notification1_*, tempPush*) | encouraging, sometimes light teasing, варьируется | "Drink water, get better!" (`notification1_13`), "Can you reach your goal today?" (`notification1_50`), "Have a glass of water, and your body will thank you ;)" (`notification1_20`), "Don't let us down, reach your goal today!" (`notification1_23`) | `!`, `?`, rhetorical questions, эмодзи в новых push (см. ниже), легкий wink («body will thank you ;)») |
| Awards / streak / congratulations | celebratory, generous | "Congratulations! You earned an award!" (`awardCongratulationM/F`), "Well done, you've earned all the awards!" (`allAwardsM/F`), "Well done, you did it!" (`text4_11M`) | `!`, восторженные восклицания, natural wrapping |
| Onboarding tutorials | encouraging, instructional | "We will calculate your recommended water intake" (`calculateRecommendedDailyIntake`-family), "Choose your goals" (`chooseYourGoal`, plural в EN source), "Achievements will motivate you to keep going. Good luck!" (`tutSubtitle4`) | compact layouts handle wrapping; `!` в hooks |
| Settings / labels / sections | neutral, informative, prosaic | "Edit profile", "Daily goal", "Sound" (`sound`), "Color scheme", "Language" | без `!`, single-word или short noun phrases, Capitalized как заголовок |
| Errors | polite, action-oriented | "There is no connection to the server. Please check your internet connection and try again later. If the problem persists, please contact us." (`noConnection`), "An error occurred while sharing on Facebook. Please ensure that the Facebook app is installed and that sharing permissions have been granted." (`facebookSharingError`) | `Please` префикс в action recovery, последовательное описание; **не** обвинять пользователя |
| Permission prompts (NS*UsageDescription, в iOS `InfoPlist.strings`) | reasoned, direct | "We need access to your photos so you can choose a profile picture." (`NSPhotoLibraryUsageDescription`), "We need read access to Apple Health water, weight, and profile data so we can import your hydration history and calculate your daily goal." (`NSHealthShareUsageDescription`) | `We need …` + причина после («so you can …», «so we can …»); legacy `Please give us …` форма заменена на `We need …` |
| Paywall / subscription | promotional but warm, не aggressive | "Start drinking more water" (`onboardingSubscribeTitleFirstLine`, без `!`), "Try 3 days for free" (`tryThreeDaysLabel`), "Not ready?" (`notReady`) | `!` опционален, soft asks («Not ready?»), эмодзи в seasonal pushes |
| Empty states | gentle, action-prompting | "No drinks added during this period", "Add your first drink today" (`noDrinksTodayTest2`), "You haven't added anyone yet. Find and add your first friend" | без `!`, явное приглашение к действию |
| Tips (tip1..N) | informative, body-positive, plain-language | "Water carries nutrients to your cells and helps your body absorb water-soluble vitamins like B and C." (`tip6`), "Water can boost your metabolism. For a healthier lifestyle, drink more water." (`tip2`), "If you feel tired, drink a glass of water. It can help you feel more alert." (`tip11`) | без `!`, нейтральные declarative предложения, простой язык |

### Lexicon

- **Preferred** — `drink`, `water`, `glass`, `goal`, `habit`, `lifestyle`, `body`, `healthy`, `track`, `reminder`. Plain language.
- **Avoid** — `hydration metrics`, `consumption logs`, `metabolic profile`, IT-жаргон (`backend`, `sync engine`, `middleware`), formal medical terms.
- **Legacy vs current** — старые строки используют `norm` (`Fulfil the norm today!`); новые предпочитают `goal` (`Achieve your goal`). При новых строках использовать `goal`. Существующие `norm` не drive-by переписывать; при rewrite — заменять на `goal`.
- **Premium tier** — `Full version` (legacy), `My Water Premium` (current). Новые строки — `My Water Premium`.
- **Self-care framing** — `your body`, `yourself`, `take care of yourself`, `your health`. Подчёркивает personal benefit.
- **`application` → `app`** в user-facing значениях — hard convention (legacy mass-violation; флагать каждый instance). Comment-acknowledged legacy ключи (например `appstore.app.subscriptionTemsAppStore § iTunes legacy text`) можно оставить, но новые строки — `app`.

### Punctuation

- **Button labels** — без точки в конце. `Save`, `Add a drink`, `Try free`, `Connect`.
- **Точка в конце — разделитель, не финализатор (UI-микрокопи).** В user-facing значении точка ставится **только** между двумя предложениями как разделитель, не в самом конце. Заголовок / кнопка / label / subtitle / tip / Siri-dialog / widget-описание / share-subtitle с **одним** предложением — **без trailing period**. Body из **двух и более** предложений — точка между ними, но **без trailing period** после последнего. `?` / `!` / `:` остаются (это не точка): `Stop re-sync? Drinks already uploaded will stay in Apple Health` — ок.
  - ✅ `Show today's hydration progress` (1 предложение — без точки) — ❌ `Show today's hydration progress.`
  - ✅ `Join me on My Water. Drinking water is easier together` (2 предложения — точка-разделитель, без trailing) — ❌ `…easier together.`
  - **Исключения:** (1) **error message с recovery-инструкцией** следует полной прозе и **заканчивается точкой** (см. буллет «Errors» ниже — `…please contact us.`); (2) намеренный **visual-style** trailing period как часть дизайна (`Energized.` / `Hydrated.` / `Done.` — share-карточки, где comment явно фиксирует «trailing period is part of the visual style»).
  - **Применять** к `en`-источнику **и** ко всем target-переводам (mirror EN-пунктуацию; не добавлять trailing point в локалях). Read-aloud Siri-dialog (`ProvidesDialog`) — тоже без trailing: TTS читает завершающую интонацию по контексту, trailing period не нужен как «finalization signal». Translator-comment constraint: `Single sentence — no trailing period` или `Period between the sentences only — no trailing period after "<last word>"`. Существующие legacy-строки drive-by не переписывать (§ Translation discipline); enforced при новом ключе / смене `en`-источника.
- **Notifications** — `!` или `?` допустимы и часто используются. Не cluster: один `!` или `?` на сообщение, не `!!!`.
- **Errors** — точка в конце; запятая после `Please` (legacy: `Please, restart...` — оставлять как есть; новые строки — без запятой: `Please restart...`).
- **Awards / motivational** — `!` поощряется; manual hard line breaks не использовать, rhythm держать через copy и layout wrapping.
- **Settings / labels** — без punctuation suffix.
- **Brand name** — `"My Water"` (кавычки в body text как brand emphasis), `«My Water»` (guillemets в onboarding tutorial). В target language — locale-standard quotation marks: `«»` ru/fr, `„"` de, `「」` ja.
- **Длинное тире (em-dash `—`, U+2014) в user-facing строках — НЕ использовать.** Его пишут почти только AI вместо обычного тире — многим это не нравится. Три разных символа, AI их путает — не считать за один: длинное тире `—` U+2014 (**запрещено** в user-facing значениях) / en-dash `–` U+2013 (проектом не регулируется — отдельно не вводить, но и не «чинить» drive-by; это не em-dash) / обычное тире (hyphen-minus `-` U+002D, **разрешено**, в т.ч. как разделитель между слов `« - »`). Default замена существующего `—` — **обычное тире `-`** там, где по смыслу нужен dash (`Пей воду - будь в тонусе!`). Другой знак — по ситуации, ориентир = `en`-значение того же ключа: comma для parallel imperatives; period для двух полных clause / Siri-voice (`…daily goal. %1$@ of %2$@. Great job!`); colon для label:value (`%1$@: %2$d%% of total`). Для `ar` / CJK — script-correct знак (`ar` `،` U+060C; CJK `，` / `、`). Применять во всех 21 языке. Область правила — **только user-facing значения**; em-dash как канонический знак русской прозы в doc-прозе (`mywater_ios docs/ai/DOCS_MAINTENANCE.md`) этим правилом НЕ затрагивается. Детерминированно проверяется `loc_qa.py` (em-dash check, ERROR; user-facing значения, не `context`).

### Emoji policy

Допустимы избирательно, не везде:

- **Push retention / seasonal promotions** — частое использование: 💧 😊 ❤️ ✨ 🌿 😍 🙌 🎁 ☀️ ⏰ 🖤 (`pushRetention_*`, `tempPushSummer*`, `tempPushDiscount2023*`, `blackFridayTitle`).
- **App emotional micro-copy** — иногда: ☕️🧋🧃 (`pushAboutOwnDrinks` — про создание своего напитка).
- **Не используются** — в errors, settings, permissions, button labels, motivational text старого поколения (text1_*..text4_*), achievement names/descriptions, tips, onboarding labels, paywall основной copy.

Default: при добавлении новой строки эмодзи **не** добавлять, если только не push retention / seasonal promo. Существующие эмодзи в строках сохранять. В target language — использовать тот же эмодзи (он universal), не заменять локальной альтернативой.

### Gendered variants

Старая часть приложения (motivational + некоторые notification suffixes) имеет варианты M / F:

- `text1_1M` / `text1_1F`, `text2_3M` / `text2_3F`, ..., `text4_19M` / `text4_19F` — gendered onboarding-like motivational text по streak/state.
- `awardCongratulationM` / `awardCongratulationF`, `allAwardsM` / `allAwardsF`, `notifErrorM` / `notifErrorF`, `socialShareTextFbM` / `socialShareTextFbF`, `haveAward1M` / `haveAward1F`, `achivmentTextShareFacebookM` / `achivmentTextShareFacebookF`.

**Зачем** — в языках с грамматическим родом (ru, ar, he, и др.) past-tense verbs / adjectives / participles согласуются с полом пользователя. В английском обе версии часто идентичны; в target language — корректировать согласование по полу пользователя.

**При переводе** — обе версии (`*M` и `*F`) переводить отдельно; не делать одинаковыми, если язык поддерживает гендер. Смысл правила: если выкинуть гендер, теряется correctness для половины пользователей.

### Length tendencies

Эмпирические rangeы, не строгие правила:

| Тип | Длина |
|---|---|
| Button label | 1-3 words, ≤15 chars |
| Settings row title | 1-4 words, ≤25 chars |
| Section header | 1-3 words, ≤20 chars |
| Notification body | 1 sentence, ≤80 chars |
| Motivational text1_*..text4_* | 1-2 natural-wrapped lines, 5-12 words |
| Tip | 1-2 sentences, 15-30 words |
| Onboarding paragraph | 1-3 sentences, 20-50 words |
| Error message | 1-2 sentences, 8-20 words |
| Permission prompt | 1 sentence, 10-20 words |
| Paywall hero / promo | 1 sentence, 8-15 words |
| Award name | 1-3 words |
| Award description | 1 short sentence, 5-12 words |

Translator может отклоняться по language length expansion (ru / de / fr типично длиннее en на 15-30%); это нормально пока не нарушаются hard UI constraints, указанные в `Constraints` поле комментария.

### Caveats

- Это **observed** guide, не normative — есть inconsistencies (например, `norm` vs `goal` смешано; некоторые motivational strings слегка nagging — «Don't let us down»). Не «исправлять» эти inconsistencies drive-by; при правке существующей строки maintain её tone.
- Brand voice может эволюционировать; этот раздел обновляется по результатам аудита, не drive-by при touched-strings.
- Если конкретная строка отклоняется от default tone — указать в поле `Tone` комментария (`Tone: formal` для legal / privacy строк, `Tone: urgent` для critical alerts, `Tone: playful` для seasonal pushes).

## Placeholders (Lokalise universal format)

Значения в корпусе (`strings.ndjson`) и в Lokalise хранятся в **Lokalise
universal placeholder**-формате — НЕ в платформенном `%@` / `%s`. Lokalise
конвертирует universal → платформенный формат на **экспорте**. Обратная
конверсия (платформенный → universal) происходит ТОЛЬКО при загрузке файла; наш
импорт идёт через keys API (`loc_corpus_import.py`), который хранит строку как
есть и НЕ конвертирует. Поэтому голый `%@` / `%s` / `%d`, попавший в значение,
не сконвертируется и сломает экспорт (на iOS останется `%s` вместо `%@`).

| Тип | Universal (хранится так) | iOS `.strings` | Android XML | server JSON |
|---|---|---|---|---|
| строка | `[%s]`, `[%1$s]` | `%@`, `%1$@` | `%s`, `%1$s` | `{{0}}` |
| целое | `[%i]`, `[%1$i]` | `%li` | `%d` | `{{1}}` |
| float | `[%.1f]`, `[%.0f]` | `%.1f` | `%.1f` | `{{2}}` |
| литеральный `%` | `[%]` | `%%` | `%` | `%` |

- **Аргумент → universal-скобки.** Любая подстановка пишется `[%s]` / `[%i]` /
  `[%.1f]`. Никогда не оставлять голый `%@` / `%d` / `%s` в значении.
- **Один аргумент → `[%s]`; два и более → индексированные `[%1$s]` / `[%2$s]` во
  ВСЕХ языках ключа.** Индекс позволяет переводу переставлять аргументы под
  порядок слов целевого языка (`[%2$s] … [%1$s]`), не ломая подстановку. **Нельзя
  смешивать** `[%s]` и `[%1$s]` между языками одного ключа — bare-форма
  привязана к позиции и не умеет переставлять (fragile). Все языки одного ключа
  обязаны нести **одинаковый набор плейсхолдеров (тип и количество)** — это
  runtime-контракт (один и тот же набор аргументов на всех языках). Проверяется
  `loc_placeholder_lint.py` (`placeholder-count` — расхождение набора;
  `placeholder-indexing` — смесь bare/indexed или неиндексированный multi-ключ).
- **Литеральный процент → `[%]`.** Знак процента, который надо ОТОБРАЗИТЬ (не
  подстановка), хранится как universal `[%]` — Lokalise сам экранирует его под
  платформу на экспорте: `[%]` → `%%` для printf/iOS; → одиночный `%`, если в
  строке нет других плейсхолдеров (→ `%%`, если есть). iOS-бандл вдобавок включает
  «Convert all [%] → %%» (README § iOS), поэтому даже standalone `[%]` уходит как
  `%%` и безопасен под R.swift `String(format:)`. Голый `%%` **не** хранить: это
  iOS-овый printf-escape, а keys-API кладёт его буквально (без конверсии) — на
  Android/server, читающих строку без форматтера, он протечёт как два знака.
  Одиночный `%` в runtime-значении тоже нельзя (тот же `String(format:)`
  undefined). **Carve-out:** значения только для App Store / server
  (`platforms: ["other"]`) не форматируются — там литеральный `%` («70%»)
  допустим.
- **iOS `.stringsdict` (`%#@var@`)** не имеет universal-формы. Это признак ключа,
  который ДОЛЖЕН быть Lokalise **plural** (`is_plural`, CLDR-формы с `[%i]`), но
  был импортирован плоским (нативный nested-plural «развернулся» в строку
  `%#@format@`). Не сочинять перевод для `%#@format@` — ремоделировать ключ как
  plural (источник форм — iOS `Localizable.stringsdict`).
- **Проверка:** `python3 loc_placeholder_lint.py` (и pre-flight внутри
  `loc_corpus_import.py`) флагает голые плейсхолдеры, одиночный `%` (на
  ios/android) и stringsdict-ключи. Сигнатурная проверка в
  `loc_r_marked_translations.py` сверяет набор плейсхолдеров source↔target и
  различает `[%s]` и `%s`.

Примеры в § Translator context ниже используют iOS `.strings`-обёртку (C-style
блок `/* */` + `"key" = "value";`) для узнаваемости, но **плейсхолдеры в них
записаны в корпусной universal-форме** (`[%s]`, `[%1$.0f]`) — её же указывает поле
Placeholders, потому что `context` импортируется в Lokalise `description`
кросс-платформенно и должен ссылаться на те же токены, что хранятся в значении.
Платформенный вид (`%@` / `%.0f`) Lokalise производит на экспорте (§ Placeholders).

## Translator context (key comment / description)

Контекст ключа = canonical источник для переводчика (людей и AI). Один блок контекста на ключ. Без него переводчик может ошибиться в неоднозначных коротких строках («Save» / «Edit» / «Today» — глагол / существительное / time filter?), пропустить семантику placeholders или нарушить ограничения по длине. Дисциплина кросс-платформенная: при добавлении ключа для **любой** платформы контекст пишется одинаково. Платформенное *кодирование* контекста разное (в Lokalise импортируется как key description; iOS — C-style комментарий перед ключом в `.strings`; server — поле `notes`; корпус — поле `context`) — детали кодирования у платформенного owner'а (iOS `mywater_ios docs/LOCALIZATION.md`, server `mywater_server resources/locale/CLAUDE.md`).

Контекст живёт только в **source language**; не fanout-ить / не переводить контекст в target-локали.

### Когда писать комментарий

- Любая новая или существенно изменённая user-facing строка, если key не явно тривиален и однозначен (`ml`, `kg` — допустимо без комментария, если контекст ясен из значения).
- При rename-sweep ключа — перенести / переписать комментарий вместе с новым ключом.
- Перед выгрузкой партии строк в Lokalise — провести аудит существующих комментариев и привести к этому формату.

### Формат (поля)

Поля с фиксированными префиксами по одному на строку. Пустые поля **пропускать полностью** (не писать `Surface: -` или `Placeholders: none`). Ниже шаблон показан в iOS-нотации (C-style блок), но набор и смысл полей — кросс-платформенный:

```
/*
  Surface: <screen / section / surface — main app, widget, watch, Siri, notification>
  Type: <one value from the canonical Type vocabulary (see below) — optional `(subtype)` qualifier>
  Context: <one-sentence what the string communicates and when shown>
  Placeholders: <each [%s] / [%i] / [%.0f] / [%1$s] with what it represents — universal form, matching the stored value; if value has placeholders>
  Constraints: <max length, abbreviation, line breaks, casing — only if real-world constraint exists>
  Register: <casual T-form | formal V-form | neutral — when the T-/V- / honorific decision is non-trivial; see § Brand voice § Pronouns>
  Tone: <encouraging | urgent | playful | celebratory | promotional | reasoned | etc. — affective layer only, NEVER T-/V-form (use Register: for that); only if non-default for this Surface/Type>
*/
"key" = "value";
```

### Обязательные поля

- **Surface** — где появляется строка. Один экран («Goal calculation result screen»), секция («Settings → Integrations section header»), несколько мест («Reminders detail screen + onboarding step 3») или маркер `app-wide` для reusable строк (`Save`, `OK`, `Next`, `Cancel`).
- **Type** — структурный тип элемента **из закрытого словаря** ниже. Цель закрытости: audit бакетит ключи по равенству Type (`loc_audit_prompt.md` rule #4 / rule #9 «inconsistent with neighbors in the same comment-Type bucket»), и каждый синоним тихо расщепляет бакет надвое (`button label` vs `button label (alert confirmation)` ≠ один bucket; `settings row value` vs `toggle state label` ≠ один bucket). Если ничего из словаря не подходит — `paragraph` (для прозы) или `label` (для коротких UI-фрагментов) по умолчанию; **не изобретать новое значение**. Допустим необязательный жанрово-/тональный уточнитель в скобках (`paragraph (marketing claim)`, `section header (eyebrow)`, `status message (multi-line)`) — это под-тип, а не синоним. Значение Type — **без trailing-точки** (`motivational text`, не `motivational text.`): один и тот же тип с точкой и без неё расщепили бы bucket. Канонический словарь (расширять только через PR к этому документу — не drive-by в корпусе):
  - **Buttons & controls:** `button label`, `badge`, `toggle`, `picker option`, `segmented option`.
  - **Headers & titles:** `screen title`, `section header`, `card title`, `feature row title`, `popup title`, `alert title`, `confirmation alert title`, `tab title`.
  - **Settings:** `settings row title`, `settings row value`, `settings row label`, `option label`.
  - **Body text:** `paragraph`, `paragraph (educational)`, `paragraph (marketing claim)`, `paragraph (subscription terms)`, `paragraph (instructional)`, `paragraph (informational)`, `paragraph (disclaimer)`, `paragraph (social share)`, `paragraph (encouraging)`, `paragraph (celebratory)`, `paragraph (empty state)`.
  - **Messaging:** `notification title`, `notification body`, `alert message`, `error message`, `success message`, `status message`, `warning message`, `motivational text`, `tip`, `tip headline`.
  - **Domain:** `beverage name`, `unit abbreviation`, `container name`, `character name`, `achievement title`, `achievement description`.
  - **Widget / system:** `widget gallery title`, `widget gallery description`, `permission prompt`, `home screen quick action label`, `screenshot caption`, `App Store title`, `App Store keywords`, `accessibility label`, `accessibility hint`.
  - **Siri / voice:** `AppIntent title`, `AppIntent description`, `AppIntent dialog`, `AppIntent prompt`, `AppIntent parameter label`, `Siri snippet`.
  - **Onboarding / forms:** `tutorial step`, `form field label`, `placeholder`.
  - **Generic fallback:** `paragraph` (для прозы), `label` (для коротких UI-фрагментов).
- **Context** — одно предложение: что строка коммуницирует пользователю и в какой момент показывается. Для reusable строк (`Save`) — указать grammatical role (imperative verb / noun) и общий смысл действия. **Не использовать слово `Educational` для casual surfaces** (tips / motivational / notifications): это слово AI-переводчику читается как сигнал formal V-form, тогда как brand voice для tips — casual T-form (`§ Brand voice § По типу поверхности`). Для tips писать «Plain-language hydration tip — …», не «Educational hydration tip — …».

### Опциональные поля

- **Placeholders** — обязательно, если в значении есть плейсхолдер (`[%s]`, `[%i]`, `[%.1f]`, `[%1$s]`, `[%2$s]` — **universal-форма**, § Placeholders). Перечислить каждый отдельной строкой с подписью и примером значения. Indexed placeholders (`[%1$s]`, `[%2$s]`) проговорить явно, чтобы переводчик мог менять порядок без потери семантики. **Сам поле Placeholders записывать в universal-форме**, как и значение: `[%s]` / `[%i]` / `[%.1f]` / `[%1$s]` — никогда не iOS-native (`%@` / `%li` / `%ld`), Android-native (`%s` без скобок / `%d`) или server-template (`{{0}}`). Контекст импортируется в Lokalise `description` кросс-платформенно и должен ссылаться на те же токены, что хранятся в значении (`§ Placeholders`, [CR-PLACEHOLDER]); рассинхронизация поля Placeholders с фактическим набором — типичный legacy-баг старых iOS-комментариев и ловится pre-flight'ом `loc_placeholder_lint.py`.
- **Constraints** — указывать когда есть real-world ограничение: widget short title (≤ ~12 chars), watch complication, button width на узких устройствах, запрет хрупких ручных `\n` в reactive-wrap copy (см. правило ниже), сокращения единиц («ml», не «millilitres»), запрет точки в конце button label.
  - **Length numbers (`≤N chars`) — рекомендации, не hard limits.** Цель — короткое и качественное; если в target language нет качественной короткой формулировки, допустимо превысить указанное число. Большинство UI surfaces используют авто-перенос / auto-shrink, поэтому перевод на 1-5 символов длиннее не ломает layout. Не flag-ать перевод как ошибку только из-за превышения `≤N` рекомендации, если короткой натуральной альтернативы нет.
  - **Hard structural constraints — остаются binding** (не «рекомендации»): запрет точки в конце button label, точное соответствие universal-плейсхолдеров `[%s]` / `[%i]` / `[%.1f]` (count и порядка; § Placeholders), обязательное соблюдение abbreviation form («ml» vs «millilitres», «yr» vs «year»), preservation hashtags / brand quotes / emoji.
  - **Хрупкие ручные переносы (`\n`) — не использовать в reactive-wrap copy.** Для текста, который рендерится в авто-переносимый label (Dynamic Type, auto-shrink, multi-line wrap), визуальный ритм даёт UI-движок и layout, а не escaped `\n` внутри значения: hard `\n` ломается при росте шрифта и при более длинном переводе. EN — source of truth для смысла, не для visual line positions. Если значение стало читабельнее за счёт `\n` — предпочесть пунктуацию / реструктуризацию предложения. Platform-specific carve-out (где `\n` намеренный — fixed-canvas image/PDF рендеры, structural списки-буллеты, разделение дискретных items в alert, не-user-facing структурные сепараторы) — у платформенного owner'а (iOS `mywater_ios docs/LOCALIZATION.md § Comment encoding (iOS .strings)`); перед flag-ом `\n` проверить, не попадает ли consumer в carve-out.
  - **`platforms: ["other"]` carve-out для литерального `%`.** Если key — App Store / server-only (значение не форматируется), литеральный «70%» допустим без `[%]`-обёртки. Если значение содержит литеральный `%` без формат-аргумента, это стоит проговорить в Constraints, чтобы переводчик не «починил» в `[%]` (`§ Placeholders` carve-out).
- **Register** — `casual T-form` | `formal V-form` | `neutral`. **Не отменяет** surface→register default map из `§ Brand voice § Pronouns`; служит явным сигналом write-time AI-переводчику, чьи training-priors перекошены в сторону formal V-form. Когда указывать:
  - **Указывать обязательно** на ключах, где default register **не очевиден из Surface/Type** или где Context содержит слова, провоцирующие V-form leak (`Educational`, `Instruct`, «system message», «statement» — AI читает как formal). Примеры обязательного указания: tips, motivational text, push retention, awards, paywall casual asks, social share text, in-app feature card / upsell copy в casual register.
  - **Указывать рекомендуется** на ключах формальных surfaces (permission prompts, App Store, paywall hero/CTA, error-with-recovery, Siri educational placeholder, legal notice): фиксирует intentional formal carve-out и проходит через audit skip rule #1 как явно formal, не «забыли».
  - **Можно пропустить** на тривиальных ключах (`ml`, `kg`, beverage-names как «Beer» — без T-/V-выбора в принципе) и на reusable buttons (`Save`, `OK`, `Cancel` — нет грамматического спряжения для choice).
  - Применимо ко **всем 16 T-V / honorific языкам** (ru, de, fr, es, it, pl, tr, nl, pt-BR, zh-Hans, hi, id, ms, vi, ja, ko, plus ar tone-shift). На Scandinavian (`da`, `nb`, `sv`) и `en` Register не имеет морфологического носителя — поле работает как tone-shift hint (lexical formality), audit rule #8 там N/A.
  - Семантика значений: `casual T-form` = ты / du / tu / tú / 你 / tum (не आप) / kamu / 해요체-default; `formal V-form` = вы / Sie / vous / usted / 您 / आप-default / Anda / 합쇼체. Для ja / ko / ar / vi проговаривать кратко: `Register: casual (해요체)`, `Register: formal (敬語)`, `Register: formal (MSA)`, `Register: casual (bạn)`.
  - **Когда Register conflicts с Tone:** Tone — affective слой (encouraging / playful / celebratory / promotional / urgent). Никогда не использовать Tone для T-/V- выбора (`Tone: friendly` ≠ T-form сигнал, его надо записать в Register). Tone применяется поверх Register: `Register: casual T-form` + `Tone: celebratory` для awards-congratulation; `Register: formal V-form` + `Tone: reasoned` для permission prompts. Tone редко указывают на settings / labels / generic — default tone берётся из Surface/Type через `§ Brand voice § По типу поверхности`.
- **Tone** — affective tone (`encouraging`, `urgent`, `playful`, `celebratory`, `promotional`, `reasoned`, `gentle`, `testimonial`, `apologetic`). **Только** если строка отклоняется от default tone для своего Surface/Type (см. tone-table в `§ Brand voice § По типу поверхности`). **Не использовать Tone для T-/V-form** — это всегда Register. Большинство строк Tone не указывают.

### Reusable / generic ключи

Если ключ используется на нескольких экранах (`Save`, `OK`, `Next`, `Edit`, `Cancel`, `Delete`, `share`):

- `Surface: app-wide` (без перечисления всех экранов).
- `Context` называет grammatical role и общий смысл: `Imperative verb. Generic save action used across forms (profile, drink editor, settings).`
- `Constraints` указать если есть: `Keep short (≤10 chars on narrow screens).`

### Good examples

```
/*
  Surface: Goal calculation result screen, below the recommended goal number.
  Type: paragraph (educational)
  Context: Explains that the calculated goal is approximate; suggests consulting a doctor for exact value.
  Placeholders:
    [%1$.0f] — daily goal amount (whole number, e.g. 1500)
    [%2$s] — measurement unit ("ml" / "l" / "fl oz")
  Register: formal V-form — onboarding educational paragraph references medical authority (doctor); see § Brand voice § Pronouns formal-surface list.
*/
"youShouldDrink0Digits" = "Based on your parameters, your estimated goal is [%1$.0f] [%2$s] of water. Your doctor can determine the exact goal for you.";

/*
  Surface: app-wide.
  Type: button label
  Context: Imperative verb. Generic save action used across forms (profile, drink editor, settings, beverage editor).
  Constraints: Keep short (≤10 chars on narrow screens).
*/
"Save" = "Save";

/*
  Surface: Drink coefficients screen, beverage row title.
  Type: beverage name
  Context: Display name for herbal tea in the standard beverage catalog. Lowercase per i18n style for non-proper-noun beverage names.
*/
"herbalTea" = "Herbal tea";

/*
  Surface: Onboarding promo screen 1 / paywall hero header.
  Type: paragraph (marketing claim)
  Context: Marketing claim about user count. Translate the equivalent short form in target language if EN source ever abbreviates ("млн" in ru, "Mio." in de, etc.); current EN source uses full word "million".
  Constraints: Fits hero header on one line.
  Register: formal V-form — paywall marketing hero (intentional single-register, paired with paywall CTA); see § Brand voice § Pronouns formal-surface list.
*/
"more5MillionUsers" = "More than 7 million happy users";

/*
  Surface: Tips screen — single tip card / tip-of-the-day notification body.
  Type: tip
  Context: Plain-language hydration tip — drinking a glass of water helps the body cells clear metabolic waste.
  Register: casual T-form — tips are friendly health-conscious companion voice, not medical lecture (see § Brand voice § По типу поверхности). Default for AI training data is formal V-form; setting Register here prevents V-form leak.
*/
"tip8" = "A glass of water helps your body flush out waste.";

/*
  Surface: Push retention notification — body text, sent to inactive users to re-engage them.
  Type: notification body
  Context: Encourages self-care framing — adequate hydration helps the body feel better. Emoji intentional per brand voice for retention pushes; translators preserve the same emoji.
  Register: casual T-form — push retention is casual companion voice (T-form across all T-V / honorific languages).
  Tone: encouraging
*/
"pushRetention_2" = "Enough water helps your body feel better. Take care of yourself today 😊";
```

### Bad → fixed examples

Старый комментарий устарел / больше не отражает текущее значение:

```
/* Save 50% */                              ← устарело: ключ теперь используется как verb "Save" в paywall savings badge, не как описание скидки "Save 50%"
"1yeardiscount" = "Save";

→ rewritten:
/*
  Surface: Paywall yearly subscription card, savings badge under price.
  Type: badge / button label.
  Context: Verb meaning "save money" (CTA on yearly subscription that saves vs monthly). Not the generic form-save action.
  Constraints: Keep short (≤6 chars), no exclamation.
*/
"1yeardiscount" = "Save";
```

Комментарий дублирует значение, не даёт surface / type:

```
/* 100 ml of decaffeinated coffee */
"Cicoriy" = "Decaf coffee";

→ rewritten:
/*
  Surface: Drink coefficients screen, beverage row title.
  Type: beverage name.
  Context: Display name for chicory / decaf coffee in standard beverage catalog (key spelling preserved as historical typo of "Chicory").
*/
"Cicoriy" = "Decaf coffee";
```

## Related

- `loc_audit_prompt.md` — audit sub-agent prompt + workflow: **операционализирует** этот канон (flag/skip/severity/output) дословно для Opus 4.7 sub-agent'а.
- `loc_audit_lang_calibration/<lang>.md` — per-language калибровки (ar / hi / vi / id / ms): script / plural CLDR / per-language calque / skip rules.
- `CLAUDE.md` — agent contract + pipeline + `[CR-CORPUS-OWNER]` / `[CR-CORPUS-UNVERIFIED]`.
- Платформенные owner-доки (механика кодирования, не стиль): iOS `mywater_ios docs/LOCALIZATION.md`; server `mywater_server resources/locale/CLAUDE.md`.
- Кросс-платформенные лингвистические anti-patterns (V-form leak / RU→EN reverse-calque / em-dash) и дисциплина маркера `unverified` — канон **в этом репо** (выше + `CLAUDE.md § [CR-CORPUS-UNVERIFIED]`); платформенные доки тонко ссылаются сюда, не форкают.
- iOS-специфичные localization anti-patterns (file-fanout / mechanical `rg`-sweep механика): `mywater_ios docs/ai/COMMON_MISTAKES.md § [CM-LOCALE-MASS-FANOUT]` / `§ [CM-MECHANICAL-GREP-SWEEP]`.
