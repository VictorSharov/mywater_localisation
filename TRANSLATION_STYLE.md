<!--
doc-role: canonical
doc-owner: TRANSLATION_STYLE.md (репозиторий mywater_localisation)
doc-scope: кросс-платформенный канон стиля/лингвистики локализации — brand voice, register/T-V/honorific, RU→EN reverse-calque, пунктуация/em-dash, per-language специфика, translator-context дисциплина; worked-примеры (Bad→Good) → TRANSLATION_EXAMPLES.md
-->

# Translation style — кросс-платформенный канон лингвистики и brand voice

Канонический дом для **правил стиля и лингвистики** локализации MyWater, общих для всех платформ (iOS / Android / server). Здесь живут: brand voice, register (T-/V-form / honorific), RU→EN reverse-calque, пунктуация / em-dash, per-language специфика, clinical-term дисциплина, дисциплина translator-context комментариев.

Потребители канона:

- переводчики (люди и AI) — при переводе / правке существующих ключей;
- audit sub-agent — `loc_audit_prompt.md` **операционализирует** эти правила (flag/skip/severity) дословно для Opus 4.7 sub-agent'а; per-language калибровки — `loc_audit_lang_calibration/<lang>.md`;
- платформенные owner-доки ссылаются сюда, а не форкают: iOS `mywater_ios docs/LOCALIZATION.md`, server `mywater_server resources/locale/CLAUDE.md`.

**Граница со платформенной механикой.** Этот док — про *стиль и смысл* перевода. Платформенная *механика* кодирования строк живёт у каждой платформы и сюда не дублируется: iOS `.strings` / `.stringsdict` / `R.swift` / target membership — `mywater_ios docs/LOCALIZATION.md`; server locale-pack — плоский JSON `{ключ: строка}` — `mywater_server resources/locale/CLAUDE.md`; сериализация корпуса + маркер «не верифицировано / нужен перевод» (`unverified` + пустой target) — `PIPELINE.md § [CR-CORPUS-OWNER]` / `§ [CR-CORPUS-UNVERIFIED]`.

**Pipeline.** Lokalise ↔ корпус (`strings.ndjson`) ↔ платформы (iOS / Android / server); полный конвейер (canonical) — `CLAUDE.md § Pipeline`.

## Translation discipline (target language)

Применяется, когда оператор **явно** даёт задачу на перевод существующих ключей в target language (не fanout новых ключей — `mywater_ios docs/ai/COMMON_MISTAKES.md § [CM-LOCALE-MASS-FANOUT]` остаётся default; create-flow новых ключей — платформенный: iOS `mywater_ios docs/LOCALIZATION.md § Rules for AI § Write-time flow`, корпус — `CLAUDE.md § Working on the corpus`). Перевод — отдельная дисциплина, не word-for-word substitution: EN source — ground truth для смысла, не для синтаксиса target language. Brand voice (`§ Brand voice`) — friendly health-conscious companion — применяется в **обоих** языках одинаково; clinical / medical / jargon формулировки в target language отклонять, даже если технически грамматически правильно. Это правило распространяется на все 21 язык, не только ru.

**Маркер «не верифицировано» (`unverified`) при translation-задаче.** Даже когда оператор явно поставил задачу перевести (этот раздел применим) и переводы делает агент, маркер `unverified` **не снимать**: перевод выполнен AI и ещё не верифицирован человеком. Снятие — отдельное действие **только** по явному запросу оператора либо когда human-verified перевод приходит round-trip через Lokalise. Завершённое состояние translation-задачи = переводы записаны + `unverified` на месте. Canonical owner маркера (общий для корпуса / iOS / сервера) — `PIPELINE.md § [CR-CORPUS-UNVERIFIED]`: корпус — поле `unverified` (плюс пустой `""`-target = «нужен перевод»); iOS / Android / server читают это состояние из Lokalise. Прежний `|R|`-маркер источника (iOS `en.lproj`, server `notes`) выведен из употребления.

**`ru` — со-источник, переводится сразу.** Исключение к «переводить только по явной задаче»: `ru` держится в паритете с `en` (команда ru-native, `ru` — anchor аудита). При добавлении / смене `en`-источника `ru` переводится **немедленно**, в той же правке, и остаётся `unverified` до проверки человеком; остальные 19 языков обнуляются в `""` и ждут отдельного прохода перевода. Канон — `PIPELINE.md § [CR-CORPUS-SOURCE-CHANGE]` / `CLAUDE.md § Self-translation discipline`.

**Default register reminder.** Дружелюбная **«ты»** (T-form-эквивалент в каждом T-V / honorific языке) — регистр голоса бренда на **всех** поверхностях, **кроме юридически обязывающего текста** (`Register: formal`). AI-default тянет formal V-form из training data — проверять каждую новую (нелегальную) строку на V-form imperative-суффиксы и местоимения `вы` / `ваш` ещё до записи в файл. Полное правило (две оси регистра «форма × тон», pre-commit detector с таблицей суффиксов, per-language карта, § Фамильярность, § Юридический carve-out) — `§ Brand voice § Pronouns`.

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
  - Lexicon consistency (`goal` / `норма` mix policy, `вода` / `жидкость`, brand quoting) — `§ Brand voice § Lexicon`;
   - Tone consistency (encouraging / neutral / urgent / playful).

7. **Gender neutrality для voice surface.** Siri / voice assistant text без user-gender-context: prefer passive past participle (`выпито` вместо `выпил/а`), formal plural (`вы выпили` — plural form исторически gender-neutral), substantive noun (`выпитое`). Gendered M/F variants остаются canonical только для explicit M/F key split (`§ Brand voice § Gendered variants`); не создавать новые gendered keys для voice surface.

8. **EN source quality — RU→EN reverse calque discipline.** Команда — ru-native; main mental language — ru. EN source писался / пишется ru-speakers и **может содержать calques от русских формулировок** ("press on +", "fulfill your daily water intake", "rate of water a day", "we get consultations from", "amount of liquid drunk", "to / from", "information is not filled", "Last drinks will be displayed"). Это **не** translation issue (en — source) — это quality issue самого source. Каждую новую / редактируемую en-строку проверять spoken-plausibility test глазами native EN speaker: «native iOS / native US English copywriter так бы написал?». Common reverse-calque triggers — direct preposition mapping (`на` → `on`/`through`, `по` → `over`/`on`), passive `is + past participle` translations of ru reflexive (`не заполнено` → "is not filled"), nominalization (`динамика веса` → "weight dynamic"), translated commands (`нажать на` → "press on"). Audit existing en source через `loc_audit_prompt.md` (en-audit лента).

### AI cognitive budget for translation

Перевод **не** optimize-for-token-saving task. Recurring AI failure mode: агент выбирает first instinctive candidate (обычно literal calque), не проверяет naturalness, выпускает kalka-перевод. **Не экономить токены на reasoning** — translation требует multiple passes per key:

- **Generate ≥3 alternatives** перед commit'ом, изложить в чате с trade-off. First candidate почти всегда — literal calque; альтернативы выявляют natural-language path. Trade-off visible оператору — корректирует выбор до записи в файл.
- **Несколько проходов на ключ** (Принципы #2/#6): `context`-комментарий целиком, сосед-чек существующих переводов через `rg`, проверка на слух. First draft почти всегда literal calque — итерировать (2-3 passes — норма), вычищая calque / clinical / prepositional mapping / register mismatch с соседями.

Anti-pattern: «перевожу N строк подряд за один проход без анализа контекста каждой». Это batch-fan-out режим, ловится в audit (`loc_audit_prompt.md`) как `awkward` / `calque` / `semantic-drift`. **Перевод — per-key task с per-key reasoning**, даже если N=20 ключей в batch'е. Token budget на batch ≠ token budget на key.

### Bad → Good examples (ru)

Worked-корпус (clinical-term rejection, T-form vs V-form, calque avoidance) перенесён в **[`TRANSLATION_EXAMPLES.md`](TRANSLATION_EXAMPLES.md) § Translation Bad → Good (ru)** — append-only reference, вынесен из канона, чтобы канон оставался rule-only.

## Brand voice

Зафиксировано на основе аудита корпуса `en` source ключей. Это descriptive guide — фиксирует **наблюдаемый** голос приложения, а не вводит новое направление. Переводчик поддерживает этот регистр в target language; AI агент держит этот регистр в **обоих** языках — clinical / medical / jargon формулировки в target language отклонять, даже если технически правильно. Translation-time дисциплина для target language (когда оператор явно даёт задачу на перевод) — `§ Translation discipline (target language)`.

Полноценный нормативный brand voice guide (с согласованием направления развития бренда) — отдельная задача.

**Overall character.** Приложение — friendly health-conscious компаньон, не медицинский авторитет и не корпоративный продукт. Голос — тёплый, поддерживающий, иногда playful; обращается к пользователю напрямую и позиционирует приложение как партнёра, который помогает («we will help», «we believe in you», «we are proud of you»). Без жаргона, без алармизма, без снисходительности.

### Pronouns

- **User → «ты»-эквивалент** — direct address на T-form по нормам target language («Your body will thank you», «You did it!», «Take care of yourself today»). **App → «we» / «our» / «My Water»** — first-person plural, как партнёр / команда («We will calculate your goal», «We are proud of you!»); не «the app», не «MyWater system». **User в social shares / онбординг-commitment → «I» / «my»** — first-person singular («I drank the required daily water volume», «I will try to achieve the goal every day for: …»).

#### Регистр: «ты» по умолчанию, `formal` только в юр.-тексте

Дружелюбная неформальная форма — **«ты»** (T-form-эквивалент в каждом T-V / honorific языке, см. карту ниже) — регистр голоса бренда на **всех** поверхностях, **кроме юридически обязывающего текста** (Terms of Use, Privacy Policy, правовые условия подписки, согласия с правовым весом), где регистр `formal`. Прежний surface-based `ты`/`вы` split (формальные поверхности — App Store / paywall / educational / permission / errors / Siri — на «вы») отменён: ошибки, оплата, permission, App Store, paywall, мед.-обоснование — всё «ты».

- **Две независимые оси, не одна.** (1) *Форма обращения*: «ты» по умолчанию везде / `formal` только в юр.-тексте. (2) *Тон*: `playful ↔ reserved`, ортогонально местоимению. Серьёзность серьёзных поверхностей (ошибки, оплата, потеря данных, мед.-обоснование, permission) передаётся **сдержанным тоном** (`reserved`) и безличностью — **не** сменой местоимения на «вы» (вернул бы холод, который этот подход убирает); при этом «ты» там не должен скатываться в фамильярность (§ Фамильярность). Casual-поверхности (push, awards, motivational, tips, seasonal) — «ты» + допустимый `playful`.
- **AI bias → write-time проверка.** Training data перекошен в formal V-form («Добавьте», «Введите» — register IT-документации и customer service), поэтому первый instinctive candidate в ru / de / fr / es почти всегда V-form. T-form — не stylistic option, а brand-voice default; сознательно отвергать V-form на write-time (кроме юр.-текста).
- **Legacy «вы» грандфазерится.** Строки от старого split — и casual, и бывшие formal нелегальные (App Store / paywall / permission / errors / Siri) — **не** переписывать drive-by, mass-sweep **не** запускать (vendor-консоль Lokalise — owner переводов; `mywater_ios docs/ai/COMMON_MISTAKES.md § [CM-LOCALE-MASS-FANOUT]` / `§ [CM-MECHANICAL-GREP-SWEEP]`). «Старые фразы могут быть устаревшими» — ожидаемое следствие смены подхода, не дефект-к-немедленной-правке. В юр.-тексте «вы» / безличность — корректный `formal`, не leak.
- **Новые строки — сразу «ты»** (юр.-обязывающий текст — `formal`), без grace period: новая строка, rewrite при смене `en`-источника, переименованный ключ.
- **Write-time anchor — поле `Register:`** (`§ Translator context § Опциональные поля`): `casual T-form` (дефолт) / `neutral` (settings) / `formal` (юр.-текст). Audit-sub-agent читает его как authoritative override (`loc_audit_prompt.md § rule #8` / `skip rule #1`); отсутствие — surface-based дефолт (T-form на нелегальных, `formal` на юр.). Прежнее `formal V-form` устарело: на новых ключах не ставить; на legacy читать как `formal` (если ключ реально юр.) либо как «grandfathered «вы», не срочный дефект».
- **Единый register внутри одного surface** — не смешивать formal и informal в одном связном тексте.
- **Где V-form leak исторически частый (проверять в первую очередь):** notifications (`notification1_*`, `tempPush*`), motivational (`text1_*..text4_*`), awards (`awardCongratulation*`, `allAwards*`, `haveAward*`, `achivment*`), tips (`tip1..N`), social shares (кроме «I»-commitment), empty states / onboarding hints, beverage / achievement names и descriptions, widget hints (`widgetText`), in-app upsell (`tempAddOneTap`, `forgotWriteText`, `manyDrinksText`, `noAdText`, `tempFirstSteps`, `weightPromo*`), casual paywall asks. **Бывшие формальные нелегальные** (App Store metadata, paywall hero / CTA `free.title*` / `reachTheGoal`, onboarding мед.-обоснование `youShouldDrink0Digits`, permission `NS*UsageDescription`, errors `noConnection` / `noFreeStorage` / `noRamError` / `favoriteDrinkCreateFailed`, Siri `siriPlaceHolder`) — теперь «ты» + тон `reserved` / `reasoned`. **Граница на paywall:** короткий warm-ask = «ты»; формальный блок subscription terms (автопродление как правовое условие, EULA-ссылка) — это юр.-текст → `formal`.

#### Pre-commit detection signal (ru)

Обязательная проверка перед записью нового перевода (на нелегальных поверхностях — V-form off-brand; в юр.-тексте `formal` «вы» / безличность корректны, эти сигналы не применяются):

| Сигнал в новом переводе | Что значит | Swap → T-form |
|---|---|---|
| Imperative `-ите` / `-айте` / `-йте` / `-ьте` | V-form leak | `-и` / `-ай` / `-й` / `-ь`: `добавьте`→`добавь`, `выпейте`→`выпей`, `пейте`→`пей`, `начните`→`начни`, `следуйте`→`следуй`, `оставайтесь`→`оставайся`, `не забывайте`→`не забывай`, `позаботьтесь`→`позаботься`, `используйте`→`используй`, `откройте`→`открой`, `попробуйте`→`попробуй`, `создайте`→`создай`, `выберите`→`выбери`, `сделайте`→`сделай`, `нажмите`→`нажми`, `проверьте`→`проверь`, `отслеживайте`→`отслеживай`, `поставьте`→`поставь` |
| Местоимения `вы` / `вас` / `вам` / `вами` / `ваш…` | V-form | `ты` / `тебя` / `тебе` / `тобой` / `твой…` |
| `вы выпили` / `вы достигли` / `вы готовы` (past participle / agreement) | V-form | explicit M/F split (`ты выпил` / `ты выпила`) либо gender-neutral для voice / Siri (`выпито`, `выпитое` — `§ Translation discipline` принцип Gender neutrality) |
| На серьёзной поверхности — диминутивы / сленг / эмодзи / понукание / шутки про деньги-здоровье-данные | фамильярность | переписать (§ Фамильярность); «ты» — да, но `reserved`, без игры |

Legacy «вы» на нелегальной поверхности (включая бывшие formal) — под grandfather: drive-by не править; но новую строку всегда писать на «ты».

#### Pronoun economy — где natural, предпочитать безличность

Русский часто не требует местоимения вовсе; passive / impersonal / stative конструкции звучат native и не вытягивают `ты` в каждой строке. Это **не отмена** T-form default — второй слой на нём: прямое обращение нужно — `ты` / `твой`; фраза работает без местоимения — лучше без. Wellness habit-tracker по природе про личную привычку; постоянное `ты выпил` / `у тебя` начинает звучать как комментатор, а не partner-app.

- **Ranking для нового перевода** (нелегальная поверхность):
  1. **Pronoun-free / impersonal** — пробовать первым, если не теряется тёплый support tone. На серьёзных поверхностях (error / payment / data-loss / permission) — приоритетно: безличность снимает **обе** крайности — и холод «вы», и фамильярность игривого «ты» («Оплата не прошла», «Осталось 500 мл», «Не удалось сохранить»).
  2. **T-form `ты` / `твой`** — прямая адресация, congratulations, body-care, motivational с emotional payload, и там, где адресность реально нужна на серьёзной поверхности (мед.-обоснование о личной норме). На серьёзных — тон `reserved`; на casual — `playful` допустим.
  3. **V-form `вы` / `ваш`** — на нелегальных поверхностях off-brand (split отменён), в новых строках не использовать; legacy под grandfather. Живое исключение — только юр.-текст (`Register: formal`).
- **Pronoun-free лучше:** stative / результат («Цель на сегодня выполнена», «Осталось 500 мл до цели», «Хороший темп»); friendly nudges («Пора выпить воды», «Можно добавить напиток»); past-tense о выпитом / добавленном («Выпито 1,2 л из 2 л» вместо `*M` / `*F` split); inclusive plural в interactive prompts («Какую цель поставим на сегодня?»).
- **Оставлять `ты` / `твой`:** direct congratulations / motivation («Ты молодец», «Ты почти достиг цели»); body / habit как personal («Позаботься о себе», «Твоё здоровье в твоих руках»); и где pronoun-free теряет тёплый тон («Цель не достигнута» — холодно → «Сегодня немного не дотянул, завтра наверстаем» — тёплый).
- **Pragmatic bonus.** Pronoun-free past-tense (`выпито`, `добавлено`, `выполнено`) автоматически gender-neutral — обходит `*M` / `*F` split keys, упрощает workflow. Родственно `§ Translation discipline` (Gender neutrality для voice), но шире. Существующие gendered keys — grandfather (`§ Gendered variants`); новые pronoun-free формулировки не вынуждают вводить gender split.

#### Per-language T-/V- карта

Левая форма — **T-form (дефолт всех нелегальных поверхностей)**; правая — **формальная форма, живой регистр ТОЛЬКО для юр.-текста** (`Register: formal`, безличность-first, форма как fallback к прямому обращению); вне юр.-текста правая колонка — лишь reference для распознавания V-form leak.

| Класс | Языки — T-form / formal + специфика |
|---|---|
| **Pronoun-swap** (T / formal грамматически различны) | `ru` (ты / вы), `de` (du / Sie), `fr` (tu / vous), `es` (tú / usted), `it` (tu / Lei), `pl` (ty / Pan·Pani), `tr` (sen / siz), `nl` (jij / u), `pt-BR` (você / o senhor·a senhora), `zh-Hans` (你 / 您), `hi` (तुम / आप), `id` (kamu / Anda), `ms` (awak / anda) |
| **Tone-shift** (морфологического T-V нет; формальность — лексикой) | `en`, `ar`, `da`, `nb`, `sv`. `ar`: дефолт Simplified MSA, юр. — fuṣḥā-formal + безлично (honorific-фразы حضرتك / سيادتك неверны **везде, включая юр.**). `da` / `nb` / `sv`: разница только лексическая (audit rule #8 N/A) |
| **Honorific** (уровни вежливости, не binary T-V) | `ja` — дефолт 丁寧体 (です/ます), юр. — 丁寧体 + формальная лексика / номинализация (本規約、ユーザー), **не** 敬語. `ko` — дефолт 해요체 (~요), юр. — 합니다체 + безлично (이용자는), **не** 합쇼체 |
| **Kinship-based** | `vi` — дефолт `bạn`; формального местоимения-fallback **нет**, юр. ведётся безлично / нейтрально (`Người dùng…`, `Bằng việc sử dụng…`); `quý vị` / `quý khách` (hotel/airline регистр) неверны **везде, включая юр.** |

### Фамильярность (серьёзные поверхности — запрет)

«ты» — дружелюбное, но не фамильярное. На серьёзных поверхностях (error / payment / data-loss / медицинское / permission / юр.) дружелюбное «ты» переходит в неуместную фамильярность при любом из маркеров ниже — off-brand, переписывать (на casual-поверхностях эмодзи и лёгкая игра допустимы):

- **Уменьшительно-ласкательные:** «водичка», «глоточек», «кофеёк», «стаканчик», «попей водички». Норма — «вода», «глоток», «стакан».
- **Сленг / интернет-speak:** «го», «изи», «чекни», «жми давай», «потыкай», «погнали».
- **Эмодзи / подмигивания / шутки** на серьёзном экране: 😅 🙈 ;) «упс», «ой», «камон», «тю-тю». (На push / seasonal эмодзи разрешены — casual.)
- **Понукание / давление / упрёк:** «ну же», «давай-давай», «не ленись», «сколько можно», «ты опять не пьёшь».
- **Фальшивая интимность / перебор эмоций:** «мы так за тебя переживаем ❤️», «обнимаем», «скучали по тебе».
- **Шутки про деньги / здоровье / данные:** «денежки не прошли 😬», «а то засохнешь», «данные тю-тю» — зона нулевой игривости даже при «ты».
- Также: КАПС-крик, `!!!`, обращения «бро / дружище / чувак».
- **Pre-commit правило одной строкой:** на серьёзной поверхности строка проходит, если её можно прочитать спокойным голосом службы поддержки, которая на «ты», — без эмодзи, диминутива, шутки и понукания. Сорвался хоть один пункт → переписать (обычно к безличной форме, § Pronoun economy).

### Юридический carve-out (`Register: formal`)

Единственная поверхность с формальным регистром. **Что входит:** Terms of Use, Privacy / privacy notices, **правовые** условия подписки (формальный блок об автопродлении, EULA-ссылка), согласия с правовым весом. **Что НЕ входит:** короткий warm-ask на paywall («Попробуй 7 дней бесплатно — отменишь в любой момент») — голос бренда, «ты»; рутинный permission prompt (в т.ч. HealthKit) — «ты». Граница — по **правовому весу конкретной фразы**, не по экрану.

- **Как вести (ru):** безличность / номинализация — первый выбор («Продолжая использование, пользователь принимает Условия использования и Политику конфиденциальности»; «Используя приложение, пользователь даёт согласие на обработку персональных данных»). «вы» — fallback там, где без прямого обращения громоздко (короткий inline под кнопкой: «Продолжая, вы принимаете Условия использования и Политику конфиденциальности»). «ты» — нельзя; «пожалуйста» — не нужно; голос — юридическое лицо, не companion.
- **Кросс-язык:** см. колонку «formal» в карте выше — безличность-first, формальная форма как fallback; для `ja` / `ko` / `ar` / `vi` — register-elevation / безличность, **не** honorific-фраза. Детали и per-language realization — `loc_audit_prompt.md § rule #8` / `skip rule #1` и калибровки.

### По типу поверхности (observed)

| Поверхность | Tone | Примеры | Что разрешено |
|---|---|---|---|
| Motivational text (text1_*, text2_*, text3_*, text4_*) | friendly, encouraging, sometimes playful | "Hi, add the first glass of water", "You did it!", "Well done! Today you drank", "Don't stop!" | `!`, краткие фразы, natural wrapping для визуального ритма |
| Notifications (notification1_*, tempPush*) | encouraging, sometimes light teasing, варьируется | "Drink water, get better!" (`notification1_13`), "Can you reach your goal today?" (`notification1_50`), "Have a glass of water, and your body will thank you ;)" (`notification1_20`), "Don't let us down, reach your goal today!" (`notification1_23`) | `!`, `?`, rhetorical questions, эмодзи в новых push (см. ниже), легкий wink («body will thank you ;)») |
| Awards / streak / congratulations | celebratory, generous | "Congratulations! You earned an award!" (`awardCongratulationM/F`), "Well done, you've earned all the awards!" (`allAwardsM/F`), "Well done, you did it!" (`text4_11M`) | `!`, восторженные восклицания, natural wrapping |
| Onboarding tutorials | encouraging, instructional | "We will calculate your recommended water intake" (`calculateRecommendedDailyIntake`-family), "Choose your goals" (`chooseYourGoal`, plural в EN source), "Achievements will motivate you to keep going. Good luck!" (`tutSubtitle4`) | compact layouts handle wrapping; `!` в hooks |
| Settings / labels / sections | neutral, informative, prosaic | "Edit profile", "Daily goal", "Sound" (`sound`), "Color scheme", "Language" | без `!`, single-word или short noun phrases, Capitalized как заголовок |
| Errors | polite, action-oriented, **reserved** («ты», не playful) | "There is no connection to the server. Please check your internet connection and try again later. If the problem persists, please contact us." (`noConnection`), "An error occurred while sharing on Facebook. Please ensure that the Facebook app is installed and that sharing permissions have been granted." (`facebookSharingError`) | `Please` префикс в action recovery, последовательное описание; **не** обвинять; безличность-first; эмодзи/шутки/диминутивы запрещены (§ Фамильярность) |
| Permission prompts (NS*UsageDescription, в iOS `InfoPlist.strings`) | reasoned, **reserved** («ты», не playful) | "We need access to your photos so you can choose a profile picture." (`NSPhotoLibraryUsageDescription`), "We need read access to Apple Health water, weight, and profile data so we can import your hydration history and calculate your daily goal." (`NSHealthShareUsageDescription`) | `We need …` + причина после («so you can …», «so we can …»); legacy `Please give us …` форма заменена на `We need …`. Routine-permission = «ты»; ≠ юр. согласие-договор (то — `formal`) |
| Paywall / subscription | promotional but warm, не aggressive | "Start drinking more water" (`onboardingSubscribeTitleFirstLine`, без `!`), "Try 3 days for free" (`tryThreeDaysLabel`), "Not ready?" (`notReady`) | `!` опционален, soft asks («Not ready?»), эмодзи в seasonal pushes. **Маркетинговый ask — «ты»; формальный блок subscription terms / автопродление — `formal`** (юр., § Юридический carve-out) |
| Legal / Terms / Privacy / правовые условия подписки / согласия | reserved, impersonal (`Register: formal`) | "Продолжая использование, пользователь принимает Условия использования и Политику конфиденциальности", subscription legal terms (автопродление, EULA-ссылка) | безличность-first; «вы» — fallback к прямому обращению; **«ты» — нельзя**; без эмодзи/тепла; § Юридический carve-out |
| Empty states | gentle, action-prompting | "No drinks added during this period", "Add your first drink today" (`noDrinksTodayTest2`), "You haven't added anyone yet. Find and add your first friend" | без `!`, явное приглашение к действию |
| Tips (tip1..N) | informative, body-positive, plain-language | "Water carries nutrients to your cells and helps your body absorb water-soluble vitamins like B and C." (`tip6`), "Water can boost your metabolism. For a healthier lifestyle, drink more water." (`tip2`), "If you feel tired, drink a glass of water. It can help you feel more alert." (`tip11`) | без `!`, нейтральные declarative предложения, простой язык |

### Lexicon

- **Preferred** — `drink`, `water`, `glass`, `goal`, `habit`, `lifestyle`, `body`, `healthy`, `track`, `reminder`. Plain language.
- **Avoid** — `hydration metrics`, `consumption logs`, `metabolic profile`, IT-жаргон (`backend`, `sync engine`, `middleware`), formal medical terms.
- **Legacy vs current** — старые строки используют `norm` (`Fulfil the norm today!`); новые предпочитают `goal` (`Achieve your goal`). При новых строках использовать `goal`. Существующие `norm` не drive-by переписывать; при rewrite — заменять на `goal`.
- **Premium tier** — `Full version` (legacy), `My Water Premium` (current). Новые строки — `My Water Premium`.
- **Self-care framing** — `your body`, `yourself`, `take care of yourself`, `your health`. Подчёркивает personal benefit.
- **`application` → `app`** в user-facing значениях — hard convention (legacy mass-violation; флагать каждый instance). Comment-acknowledged legacy ключи (например `appstore.app.subscriptionTemsAppStore § iTunes legacy text`) можно оставить, но новые строки — `app`.
- **Каноничные пер-язык. переводы терминов — в глоссарии.** Согласованный рендеринг каждого термина (бренд, domain-существительные, единицы, запрещённый жаргон) по всем языкам ведётся в `glossary.ndjson` ([`GLOSSARY.md`](GLOSSARY.md)) — единый словарь, выгружаемый в Lokalise glossary. Этот раздел фиксирует *какое слово* предпочесть; глоссарий фиксирует его *перевод* на каждый язык. Меняешь preferred / brand / premium-term здесь → обнови соответствующий термин в глоссарии (`CLAUDE.md § Reverse routing`).

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
  «Convert all [%] → %%» (EXPORT.md § iOS), поэтому даже standalone `[%]` уходит как
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
  Register: <casual T-form | neutral | formal (юр.-обязывающий текст: безличность-first, «вы»-fallback); `formal V-form` устарел; см. § Brand voice § Pronouns>
  Tone: <encouraging | urgent | playful | celebratory | promotional | reasoned | reserved | gentle | etc. — affective layer only, NEVER T-/V-form (use Register: for that); only if non-default for this Surface/Type>
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
- **Register** — `casual T-form` | `neutral` | `formal`. `casual T-form` — дружелюбный «ты» (дефолт почти везде). `neutral` — settings-регистр. **`formal`** — **только юридически обязывающий текст** (Terms / Privacy / правовые условия подписки / согласия с правовым весом): означает безличность-first + «вы»-fallback, это единственный живой формальный регистр (§ Brand voice § Юридический carve-out), **не** возврат старого surface-based split. (`formal V-form` — **устаревшее** значение: на новых ключах не ставить; на legacy неоднозначно — если ключ реально юр., читать как `formal`, иначе как «grandfathered «вы», не срочный дефект».) Поле служит явным сигналом write-time AI-переводчику, чьи training-priors перекошены в сторону formal V-form. Когда указывать:
  - **Указывать обязательно** на ключах, где default register **не очевиден из Surface/Type** или где Context содержит слова, провоцирующие V-form leak (`Educational`, `Instruct`, «system message», «statement» — AI читает как formal). Примеры обязательного указания: tips, motivational text, push retention, awards, paywall casual asks, social share text, in-app feature card / upsell copy в casual register. **И — обязательно `Register: formal` на каждом юр.-обязывающем ключе** (Terms / Privacy / subscription legal terms / consent): это authoritative-сигнал, по которому audit отличает корректный формальный регистр от V-form leak.
  - **Бывшие формальные нелегальные surfaces** (permission prompts, App Store, paywall hero/CTA, error-with-recovery, Siri educational placeholder) — теперь `casual T-form` со сдержанным тоном. Ставить `Register: casual T-form` + при серьёзности `Tone: reserved` / `reasoned`; legacy «вы» там — grandfather. **Юр.-обязывающий текст из этого списка (legal notice, формальный блок subscription terms) — наоборот, `Register: formal`** (не casual).
  - **Можно пропустить** на тривиальных ключах (`ml`, `kg`, beverage-names как «Beer» — без T-/V-выбора в принципе) и на reusable buttons (`Save`, `OK`, `Cancel` — нет грамматического спряжения для choice).
  - Применимо ко **всем 16 T-V / honorific языкам** (ru, de, fr, es, it, pl, tr, nl, pt-BR, zh-Hans, hi, id, ms, vi, ja, ko, plus ar tone-shift). На Scandinavian (`da`, `nb`, `sv`) и `en` Register не имеет морфологического носителя — поле работает как tone-shift hint (lexical formality: `casual T-form` ↔ `formal` lexicon), audit rule #8 там N/A.
  - Реализация значений per-language (какая T-form / formal-форма в каждом языке) — см. карту T-/V- в `§ Brand voice § Pronouns`.
  - **Register и Tone — ортогональны** (Register = T/V / формальность; Tone = аффект): аффективный слой — отдельное поле **Tone** (ниже).
- **Tone** — affective tone (`encouraging`, `urgent`, `playful`, `celebratory`, `promotional`, `reasoned`, `reserved`, `gentle`, `testimonial`, `apologetic`). **Только** если строка отклоняется от default tone для своего Surface/Type (см. tone-table в `§ Brand voice § По типу поверхности`). `reserved` — сдержанный тон серьёзных нелегальных поверхностей (error / payment / data-loss / permission): «ты» без эмодзи / диминутивов / шуток (§ Фамильярность). **Не использовать Tone для T-/V-form** — это всегда Register. Большинство строк Tone не указывают.

### Reusable / generic ключи

Если ключ используется на нескольких экранах (`Save`, `OK`, `Next`, `Edit`, `Cancel`, `Delete`, `share`):

- `Surface: app-wide` (без перечисления всех экранов).
- `Context` называет grammatical role и общий смысл: `Imperative verb. Generic save action used across forms (profile, drink editor, settings).`
- `Constraints` указать если есть: `Keep short (≤10 chars on narrow screens).`

### Examples

Worked-примеры translator-context комментариев (Good + Bad → fixed) — в **[`TRANSLATION_EXAMPLES.md`](TRANSLATION_EXAMPLES.md) § Translator context** (append-only reference, вынесено из канона).

## Related

- `loc_audit_prompt.md` — audit sub-agent prompt + workflow: **операционализирует** этот канон (flag/skip/severity/output) дословно для Opus 4.7 sub-agent'а.
- `TRANSLATION_EXAMPLES.md` — worked Bad→Good примеры (translation + translator-context), вынесены из канона; append-only reference.
- `loc_audit_lang_calibration/<lang>.md` — per-language калибровки (ar / hi / vi / id / ms): script / plural CLDR / per-language calque / skip rules.
- [`GLOSSARY.md`](GLOSSARY.md) — терминологический глоссарий (бренд / UI / domain / единицы / запрещённый жаргон), один согласованный перевод на язык; выгружается в Lokalise glossary. Канон фиксирует *слово*, глоссарий — его перевод на каждый язык.
- `CLAUDE.md` — agent contract + pipeline + `[CR-CORPUS-OWNER]` / `[CR-CORPUS-UNVERIFIED]`.
- Платформенные owner-доки (механика кодирования, не стиль): iOS `mywater_ios docs/LOCALIZATION.md`; server `mywater_server resources/locale/CLAUDE.md`.
- Кросс-платформенные лингвистические anti-patterns (V-form leak / RU→EN reverse-calque / em-dash) и дисциплина маркера `unverified` — канон **в этом репо** (выше + `PIPELINE.md § [CR-CORPUS-UNVERIFIED]`); платформенные доки тонко ссылаются сюда, не форкают.
- iOS-специфичные localization anti-patterns (file-fanout / mechanical `rg`-sweep механика): `mywater_ios docs/ai/COMMON_MISTAKES.md § [CM-LOCALE-MASS-FANOUT]` / `§ [CM-MECHANICAL-GREP-SWEEP]`.
