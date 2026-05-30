<!--
doc-role: reference
doc-owner: TRANSLATION_EXAMPLES.md (репозиторий mywater_localisation)
doc-scope: worked Bad→Good примеры перевода и translator-context, иллюстрирующие TRANSLATION_STYLE.md. Append-only reference, вынесены из канона, чтобы он оставался rule-only. Правила → TRANSLATION_STYLE.md.
-->

# Translation examples — worked Bad → Good corpus

Reference-компаньон к [`TRANSLATION_STYLE.md`](TRANSLATION_STYLE.md): worked-примеры, иллюстрирующие правила канона (отклонение clinical-терминов, T-form регистр, избегание калек, translator-context комментарии). Вынесены из канона, чтобы он оставался rule-only; файл растёт append-only по мере появления новых typed mistakes из audit / operator feedback. **Правила** канонические в `TRANSLATION_STYLE.md` — здесь только демонстрация, не новое правило.

## Translation Bad → Good (ru)

Иллюстрирует `TRANSLATION_STYLE.md § Translation discipline` (naturalness, отклонение clinical-терминов, calque detection) и `§ Brand voice § Pronouns` (T-form регистр, pronoun economy, § Фамильярность, § Юридический carve-out).

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

EN: "Please give us permission to access your camera to take a photo for the avatar"  (`NSCameraUsageDescription`, permission prompt — серьёзная нелегальная поверхность)
❌ "Пожалуйста, дайте нам разрешение на доступ к вашей камере, чтобы сделать фотографию на аватар"  — V-form: холодно, дистанцированно; permission prompt больше не formal surface
❌ "Дай камеру, без неё аватарку не заснять 😉 ну камон"  — перефамильярно: сленг + эмодзи + понукание (§ Фамильярность)
✓ "Нужен доступ к камере, чтобы сделать фото для аватара"  — «ты»/безлично, тон reasoned: причина адресная, без холода и без игры

EN: "No Internet connection. Please check your connection and try again later."  (error with recovery instructions — серьёзная нелегальная поверхность)
❌ "Нет соединения с сервером. Пожалуйста, проверьте ваше интернет-соединение и попробуйте снова позже."  — V-form: устаревший холодный регистр
❌ "Упс, инет отвалился 😅 Чекни сеть и жми ещё раз!"  — перефамильярно: эмодзи + сленг на ошибке (§ Фамильярность)
✓ "Нет соединения с сервером. Проверь интернет и попробуй ещё раз."  — «ты», тон reserved; спокойно, без шуток и обвинения

EN: "We couldn't process your payment. Please try again."  (payment failure — серьёзная нелегальная поверхность)
❌ "Не удалось обработать ваш платёж. Пожалуйста, повторите попытку."  — V-form
❌ "Ой, денежки не прошли 😬 Попробуй другую карту, го!"  — перефамильярно: шутка про деньги (зона нулевой игривости, § Фамильярность)
✓ "Оплата не прошла. Проверь платёжные данные и попробуй ещё раз."  — «ты», reserved; безличный заголовок-first

EN: "By continuing, you accept the Terms of Use and Privacy Policy."  (Terms gate — ЮРИДИЧЕСКИ ОБЯЗЫВАЮЩИЙ ТЕКСТ)
❌ "Продолжая, ты соглашаешься с условиями и политикой конфиденциальности."  — «ты» в документе с правовым весом = фамильярность не к месту (юр. — другой речевой акт)
✓ "Продолжая использование, пользователь принимает Условия использования и Политику конфиденциальности."  — `Register: formal`, безличность-first
✓ "Продолжая, вы принимаете Условия использования и Политику конфиденциальности."  — `formal`, «вы»-fallback для короткого inline (§ Юридический carve-out)

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

## Translator context — Good examples

Иллюстрирует `TRANSLATION_STYLE.md § Translator context` (формат комментария, поля, Register / Tone).

```
/*
  Surface: Goal calculation result screen, below the recommended goal number.
  Type: paragraph (educational)
  Context: Explains that the calculated goal is approximate; suggests consulting a doctor for exact value.
  Placeholders:
    [%1$.0f] — daily goal amount (whole number, e.g. 1500)
    [%2$s] — measurement unit ("ml" / "l" / "fl oz")
  Register: casual T-form — onboarding medical-authority rationale: «ты» с тоном reserved/reasoned (без алармизма и шуток про тело). Это НЕ юр.-текст — `formal` живёт только в Terms/Privacy/правовых условиях подписки. See § Brand voice § Pronouns / § Юридический carve-out.
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
  Register: casual T-form — paywall marketing hero (голос бренда, «ты»). Маркетинговый paywall — «ты»; формальный блок subscription terms / автопродление — отдельный юр.-текст (`Register: formal`). See § Brand voice § Pronouns / § Юридический carve-out.
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

## Translator context — Bad → fixed examples

Иллюстрирует `TRANSLATION_STYLE.md § Translator context`: устаревший / дублирующий комментарий → переписан с Surface / Type / Context.

**Комментарий устарел** — больше не отражает текущее значение:

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

**Комментарий дублирует значение**, не даёт surface / type:

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
