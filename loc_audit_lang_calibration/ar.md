# Calibration profile — Arabic (ar)

## T-V / formality system

**System: tone-shift only (no pronoun T-V) + register choice (MSA vs colloquial)**

Arabic does not have a productive T-V pronoun distinction like French tu/vous. The pronoun أنتَ (anta, masc.) / أنتِ (anti, fem.) is used for both intimate and formal address. Formality is signaled instead by (a) register choice — Modern Standard Arabic (فُصحى, fuṣḥā) vs colloquial dialect, (b) honorific noun-phrases used in place of pronouns (حضرتك ḥaḍretak "your presence", سيادتك siyādatak "your eminence" — these are formal/respectful and inappropriate for a casual hydration app), and (c) verb mood / lexical politeness markers (يُرجى yurjā "is requested" is bureaucratic; خُذ khudh "take" is direct/casual).

For a casual health companion, the right register is **Simplified MSA** — fuṣḥā grammar but with everyday lexicon, short sentences, and imperative direct address using plain أنتَ/أنتِ. Avoid حضرتك, سيادتك, لِسَيادتكم, and avoid the deferential يُرجى منكم / نأمل من سيادتكم. Pure colloquial (Egyptian, Levantine, Gulf) is inappropriate for pan-Arab iOS distribution — choose one dialect and you alienate the others.

**Register (2026-05-30 hybrid):** the base prompt's surface-based `ты`/`вы` split is retired (`TRANSLATION_STYLE.md § Brand voice § Pronouns`) — friendly **Simplified MSA** is the register for the former-formal **non-legal** surfaces too (App Store / paywall / permission / error / Siri), with a reserved tone. Arabic has no pronoun T-V, so there is no pronoun swap. **One register exception — legally-binding text** (Terms / Privacy / subscription **legal** terms / legally-weighted consent, `Register: formal`): elevate to **fuṣḥā-formal + impersonal/passive** (يُعدّ، يوافق المستخدم على، تخضع هذه الشروط…) — do not flag a fuṣḥā-formal legal string as "over-formal." This is a *register* elevation, **not** an honorific one: حضرتك / سيادتك / يُرجى منكم stay wrong **everywhere, including legal** (they are personal-deferential; legal wants impersonal-contractual). Legacy formal-register strings on non-legal surfaces are grandfathered (no sweep); new non-legal strings use Simplified MSA.

## Gender system in grammar

**Yes — Arabic has mandatory grammatical gender, and second-person singular verbs/pronouns/adjectives all agree with the addressee's gender.**

This is a real problem for app UI: a single string cannot address both male and female users grammatically. iOS apps typically either (a) use masculine as default (current convention, accepted by most users but increasingly criticized), (b) use plural-you (أنتم antum / فعلوا) as a gender-neutral workaround — sounds slightly formal but acceptable, or (c) use gender-neutral verbal nouns / infinitives instead of imperatives (شرب الماء "drinking water" instead of اشرب "drink!").

Examples — "Drink water now":
- Masculine (default): اشرب الماء الآن (ishrab al-māʾ al-ān)
- Feminine: اشربي الماء الآن (ishrabī al-māʾ al-ān)
- Plural / neutral workaround: اشربوا الماء الآن (ishrabū al-māʾ al-ān)
- Verbal noun workaround: حان وقت شرب الماء (ḥāna waqt shurb al-māʾ — "time to drink water")

Examples — "You reached your goal!":
- Masculine: لقد حققتَ هدفك! (laqad ḥaqqaqta hadafak!)
- Feminine: لقد حققتِ هدفك! (laqad ḥaqqaqti hadafik!) — note both verb suffix AND possessive suffix change
- Neutral workaround: تم تحقيق الهدف! (tamma taḥqīq al-hadaf! — "the goal has been achieved", passive)

If the file uses masculine throughout, do **not** flag it as a bug — it's the prevailing convention. Flag only inconsistency (mix of masc/fem in the same flow) or jarring formal honorifics.

## Script & direction

Arabic uses the Arabic script and is **RTL (right-to-left)**. iOS implications:

- `Localizable.strings` files store text in logical order; iOS handles RTL layout via `UIView.semanticContentAttribute` and `NSLocale.characterDirection`.
- **Placeholder ordering with `%1$@ %2$@`**: indexed placeholders (`%1$@`, `%2$@`) are essential — Arabic word order often differs from English. Example: EN "Drink %1$@ of %2$@" (amount, beverage) → AR اشرب %1$@ من %2$@ — order coincidentally matches here, but for "%1$@ remaining to reach %2$@" (current, goal), Arabic naturally says يتبقى %1$@ للوصول إلى %2$@. Without `$` indexing, positional `%@ %@` will break when translator reorders.
- Bidirectional embedding: strings mixing Arabic + Latin digits / brand names ("My Water") need careful handling — iOS does this automatically with `NSWritingDirection`, but custom `NSAttributedString` ranges can break.
- Numerals: iOS by default uses Western Arabic numerals (0123456789) in Arabic locale, not Eastern Arabic-Indic (٠١٢٣٤٥٦٧٨٩). Both are acceptable; consistency within the app matters.
- **App name**: "My Water" can stay Latin or be transliterated ماي ووتر; brand decision. Do not auto-translate to ماء بلدي.
- **Brand name canonical form & cross-key consistency**: "My Water" must be ONE consistent form across all keys — either Latin `My Water` (preferred — matches Latin-script brand convention and the file's majority) or the transliteration `ماي ووتر`. Auto-translating to a semantic Arabic phrase (`ماء بلدي`, `مياهي`, `مياه بلدي`) is always wrong → flag as `brand-voice`. **Mixed treatment across keys is itself a finding:** if some keys use Latin `My Water`, others `مياهي`, others `مياهي "My Water"` (doubled), flag the non-canonical / doubled ones as `brand-voice` / `warn` with the canonical Latin `My Water` as the `suggestion` — do NOT propose a fresh transliteration when the file's majority is Latin. (Phase 2 ar pilot: `socialShareTextFbF` `مياهي`, `appstore.app.description` doubled `مياهي "My Water"`, other keys Latin — this clause makes the inconsistency explicitly flaggable and sets Latin as canonical.)

## Punctuation conventions

- **Quotation marks**: Arabic uses « » (French-style guillemets, U+00AB / U+00BB) OR " " (Latin curly quotes). ASCII straight quotes `"..."` are acceptable on mobile. Avoid 「」 (CJK). For UI strings, prefer whatever the .strings file already uses consistently; do not flag mixed unless it's egregious.
- **Question mark**: Arabic question mark **؟** (U+061F) — mirrored. Use ؟ at the end of questions, NOT ASCII `?`. Flag `?` as a typo in Arabic interrogatives.
- **Comma**: Arabic comma **،** (U+060C) — sits on the baseline differently than `,`. Use ، in Arabic prose. ASCII `,` in pure-Arabic strings is a minor issue but very common; flag only in formal contexts.
- **Semicolon**: Arabic semicolon **؛** (U+061B) exists but is rarely needed in app UI.
- **Decimal separator**: Western Arabic uses `.` (period) like English. Eastern Arabic-Indic context uses **٫** (U+066B). iOS apps overwhelmingly use `.` — do not flag `2.5` as wrong. If the file uses ٫ for consistency with ٠١٢ numerals, accept it.
- **Thousands separator**: `,` or **٬** (U+066C). Usually `,` in iOS apps.
- **Spacing**: No space before ؟ ، ؛ . (same as English). No double spaces. Arabic does not use Spanish-style opening ¿.
- **Honorific abbreviations**: ﷺ (after Prophet Muhammad's name) — not relevant for hydration app; flag if present (out of context).

## Common EN→target calque patterns

- EN: "Stay hydrated!"
  Literal calque ❌: ابقَ مُرَطَّبًا! (ibqa muraṭṭaban — "remain moistened/lubricated", clinical/odd, sounds like skin care)
  Natural restructure ✓: لا تنسَ شرب الماء! (lā tansa shurb al-māʾ — "don't forget to drink water!") or حافظ على ترطيب جسمك (ḥāfiẓ ʿalā tarṭīb jismak — "keep your body hydrated")
  (Reason: "hydrated" as adjective applied to a person doesn't exist idiomatically in Arabic; restructure into action verb)

- EN: "You crushed your goal today!"
  Literal calque ❌: لقد سحقت هدفك اليوم! (saḥaqta — "you pulverized", violent imagery)
  Natural restructure ✓: أحسنت! حققت هدفك اليوم 🎉 (aḥsant! ḥaqqaqta hadafak al-yawm — "well done! you achieved your goal today")
  (Reason: English motivational slang "crushed it" has no Arabic equivalent; use achievement vocabulary)

- EN: "Time to refill your cup"
  Literal calque ❌: حان الوقت لإعادة ملء كوبك (literally correct but stiff)
  Natural restructure ✓: حان وقت كوب آخر من الماء (ḥāna waqt kūb ākhar min al-māʾ — "time for another cup of water") or املأ كوبك من جديد (imlaʾ kūbak min jadīd — "fill your cup again")
  (Reason: "refill" as compound verb is calqued awkwardly; Arabic prefers "another cup" framing)

- EN: "Set a daily goal"
  Literal calque ❌: ضع هدفًا يوميًا (ḍaʿ — "place/put a goal", sounds like physically placing an object)
  Natural restructure ✓: حدد هدفك اليومي (ḥaddid hadafak al-yawmī — "specify/set your daily goal")
  (Reason: "set" in English has the abstract sense; Arabic ضع is too physical, use حدد or اختر)

- EN: "Tap to add water"
  Literal calque ❌: انقر لإضافة الماء (anqur — sounds like "click on" formally; لإضافة الماء — "to add THE water", definite article wrong)
  Natural restructure ✓: اضغط لإضافة كمية ماء (iḍghaṭ li-iḍāfat kammiyyat māʾ — "press to add a quantity of water") or simply أضف ماء (aḍif māʾ)
  (Reason: definite article ال is overused by translators; "add water" generic = indefinite ماء not الماء. Also اضغط more natural than انقر for touch interaction)

## Plural rules summary

Arabic has **all 6 CLDR plural categories**: zero, one, two, few, many, other. This is one of the strictest plural systems in CLDR and a frequent source of bugs in iOS `.stringsdict` files.

- **zero**: n = 0 (e.g., 0 كوب — "0 cups", requires its own form لا يوجد أكواب or 0 كوب)
- **one**: n = 1 (e.g., 1 كوب — "1 cup", uses singular)
- **two**: n = 2 — uses the Arabic **dual**, whose ending is **case-conditioned**: `-ān` in the nominative (كوبان "two cups"; يومان "two days") but `-ayn` in the accusative/genitive (object / adverbial position: مرتين "twice", مشروبين "two drinks"). Both are correct in their syntactic slot — do **not** "fix" a valid oblique `-ayn` to `-ān`.
- **few**: n % 100 = 3..10 (e.g., 3-10, 103-110 — counted noun in the **plural, genitive**: a *broken* plural like أكواب, or a *sound* plural like مرات / مشروبات — the plural type depends on the noun, e.g., 3 أكواب)
- **many**: n % 100 = 11..99 (e.g., 11-99, 111-199 — uses **accusative singular**, e.g., 11 كوبًا — note the tanwīn fatḥa)
- **other**: everything else, including fractions and n % 100 = 0 (e.g., 100, 200, 1000, 2.5 — uses **genitive singular**, e.g., 100 كوب)

Risks:
- **Missing zero/two/few/many categories** in `.stringsdict` is the #1 Arabic bug. Many translators only provide `one` and `other` (English-style), producing grammatically wrong forms for 0, 2, 3-10, and 11-99.
- **Two** is mandatory: Arabic has a real dual grammatical number (كوبان "two cups", not كوبين in nominative). Cannot fall back to `other`.
- **The noun form changes**: 1 = singular, 2 = dual, 3-10 = plural+singular-noun, 11-99 = singular accusative, 100+ = singular genitive. The translator must understand counted-noun grammar (تمييز العدد), not just plural form selection.
- **`%d`/`%@` format**: digits in `%d` will render in whatever numeral system iOS chooses; if the app forces Western digits, that's fine.
- For non-noun-counting strings (e.g., "%d days left"), the same 6 categories apply but the affected word is يوم (singular) → يومان (dual) → أيام (plural).

If `.stringsdict` is missing any of `zero`, `two`, `few`, `many` — flag as bug.

## Language-specific skip rules for audit

- **Loanwords now native** — do NOT flag as "should translate":
  - تطبيق (taṭbīq) for "app" — fully naturalized.
  - ويدجت (wijit) for "widget" — accepted; alternative أداة (adāh) also fine, don't flag either.
  - بريميوم (premium) — common in paywall context; البريميوم with definite article also fine. Alternative المميز is equally acceptable.
  - إشعار (ishʿār) for "notification" — standard.
  - سيري (Sīrī) for "Siri" — keep transliterated; never translate.
  - كوب (kūb), كأس (kaʾs) — both acceptable for "cup/glass"; don't flag interchange.
- **Allowed casual register markers** (these are NOT errors in a casual hydration app):
  - Dropping case endings (i.e., no تشكيل / harakāt) is standard for mobile UI.
  - Using رائع! (rāʾiʿ — "great!"), ممتاز! (mumtāz — "excellent!"), أحسنت! (aḥsant — "well done!") instead of formal أبدعت / تفوقت.
  - Direct imperatives (اشرب، أضف، تابع) without softening — this is appropriate casual tone, not rude.
- **Strict MSA, not dialect**: app UI should be in MSA. Do NOT inject dialectal forms like Egyptian إيه (eh — "what"), Levantine شو (shū), Gulf وش (wesh). If you see these in a string targeting pan-Arab `ar` locale, flag as wrong register. (Country-specific locales like `ar-EG` could use dialect, but `ar` should not.)
- **False positives an English-trained auditor might raise**:
  - **Definite article ال** prefix appearing on most nouns — this is grammatically normal in Arabic ("the water" = الماء as generic concept, not "the specific water"). Don't flag as over-articled.
  - **Word order inversion** (verb-subject-object instead of SVO) — Arabic VSO is the default; "drank Ahmad water" (شرب أحمد ماء) is correct syntax. Don't flag.
  - **Repetition of pronouns/possessives**: Arabic uses possessive suffixes (هدفك "your goal", كوبك "your cup") freely; appearing in every sentence is normal, not redundant.
  - **No capitalization**: Arabic script has no case distinction; "Beer" → بيرة (lowercase doesn't exist). Don't flag beverage names for missing capitalization.
  - **Long compound nouns with multiple إضافة (genitive chains)**: عدد أكواب الماء اليومي ("daily water cups count") is idiomatic, not over-nominalized.
  - **No "please"** in commands: Arabic imperatives are direct; adding من فضلك (min faḍlik — "please") to every button label is over-translation, not politeness. Casual UI omits it.
  - **`!` exclamation in motivational push** — fine to keep ASCII `!`; Arabic does not have a separate exclamation glyph.
- **Religious neutrality**: avoid إن شاء الله (in shāʾ Allāh — "God willing"), الحمد لله (al-ḥamdu lillāh — "praise be to God") in app strings. These are common in spoken Arabic but inappropriate in secular health-app UI for pan-Arab audience (mixed religious demographics). Flag if present.
- **Beverage names**: قهوة (qahwa — coffee), شاي (shāy — tea), ماء (māʾ — water), بيرة (bīra — beer), عصير (ʿaṣīr — juice), حليب (ḥalīb — milk) / لبن (laban — milk, Egyptian/Levantine). For "Beer" — note Arabic-speaking markets vary on alcohol acceptability; some apps localize to soft drink. Do not flag بيرة as wrong but be aware brand may choose to omit alcoholic beverages in `ar` locale entirely.
