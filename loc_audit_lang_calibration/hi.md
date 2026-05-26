# Calibration profile — Hindi (hi)

## T-V / formality system

**System type: honorific levels (multiple register tiers)**

Hindi has a three-tier pronoun system:
- **तू (tū)** — intimate / very familiar (close friends, lovers, deity, younger child, or rude/aggressive when misused). **Inappropriate** for any app UI — reads as condescending or insulting to an adult user.
- **तुम (tum)** — informal, friendly, peer-level. **Default for this app.** Friend-to-friend register, matches the "casual hydration companion" brand voice. Maps closest to colloquial English "you" used by Duolingo, fitness apps, casual notifications.
- **आप (āp)** — polite / formal / respectful. Default of Google products, banking apps, government services. Sounds distant and bureaucratic for motivational hydration prompts.

**Verb agreement is the leak surface, not just the pronoun.** Hindi conjugates the verb to match register even when the pronoun is omitted (common in imperatives). The skip rule must inspect verb endings:

| Register | Imperative "Drink water!" | "You drank water" | "Are you ready?" |
|---|---|---|---|
| तू | पानी पी! | तूने पानी पिया | क्या तू तैयार है? |
| तुम (use this) | पानी पियो! | तुमने पानी पिया | क्या तुम तैयार हो? |
| आप | पानी पीजिए / पानी पीएँ | आपने पानी पिया | क्या आप तैयार हैं? |

**तुम → आप leak (most common):** translator drifts into formal register because "professional UI = आप." Symptoms: imperatives ending in **-इए / -एँ** (पीजिए, लीजिए, चलिए, करें), verbs taking **हैं** instead of **हो** with second-person subject (तुम तैयार हैं ❌), pronoun **आप** appearing in casual notification/widget/Siri strings. Flag as **V-form leak (formal)** with severity = high if surface is notification/motivational/widget; medium if generic onboarding body copy.

**तू → तुम leak (rare but possible):** intimate-tier verbs ending in bare stem **-Ø** (पी!, ले!, चल!) or pronoun **तू**. Flag as **register-too-intimate** — never appropriate, sounds rude even if translator intended "warm."

**आप appropriate (do NOT flag as V-form leak):**
- Permission prompts ("क्या यह ऐप आपको नोटिफिकेशन भेज सकता है?")
- Paywall hero / legal copy / Terms / Privacy
- Error recovery requiring trust ("कुछ गलत हो गया। कृपया दोबारा कोशिश करें।")
- HealthKit / sensitive data consent
- First-time auth flow CTAs

**Mixed-register within one screen is a real bug.** If the paywall hero uses आप but the CTA button uses तुम, flag as consistency issue.

## Gender system in grammar

Hindi has **two grammatical genders (masculine / feminine)** and verb past-tense + many adjectives + predicates agree with the **subject's** gender. This collides directly with apps that don't know the user's gender at runtime.

**The leak pattern is past-tense verb endings and predicate adjectives:**

| EN source | Masc. user | Fem. user | Issue |
|---|---|---|---|
| You drank 250 ml of water | तुमने 250 मिली पानी **पिया** | तुमने 250 मिली पानी **पी** | Past participle ending |
| You're ready! | तुम **तैयार** हो | तुम **तैयार** हो | Safe — adjective doesn't inflect here |
| You did it! | तुमने कर **दिया**! | तुमने कर **दी**! | Compound verb agreement |
| You're awesome | तुम **शानदार** हो | तुम **शानदार** हो | Safe (invariant -ार adj) |
| You're hydrated | तुम **हाइड्रेटेड** हो | तुम **हाइड्रेटेड** हो | Safe (English loan, invariant) |
| Great job, champion! | शानदार, **चैंपियन**! | शानदार, **चैंपियन**! | Safe (vocative noun, no agreement) |

**Key audit rule:** flag any past-tense verb form (**-या / -ी / -ए / -ईं** endings: किया/की, पिया/पी, गया/गई, हुआ/हुई) addressed to the user as a **gender leak**. Same for compound verbs (कर दिया / कर दी, ले लिया / ले ली, पी लिया / पी ली).

**Mitigation patterns translators should use (recommend in audit findings):**

1. **Restructure to imperative/infinitive** — no past-tense agreement: "पानी पियो" (drink water), "लक्ष्य पूरा करो" (complete goal), instead of "तुमने पानी पिया."
2. **Restructure to nominal/present** — "तुम्हारा लक्ष्य पूरा!" (your goal complete!) instead of "तुमने लक्ष्य पूरा किया."
3. **Use stat-noun phrasing** — "आज: 250 मिली पानी ✓" instead of "तुमने 250 मिली पानी पिया."
4. **English loan adjective** — "तुम हाइड्रेटेड हो" doesn't inflect.

**Keys-ending-in-M/F pattern from base prompt:** if the project ships parallel keys like `streak_completed_male` / `streak_completed_female`, both must be present and the gendered forms must actually differ. Flag if:
- Only one variant exists,
- Variants are identical (translator didn't gender-adapt),
- Variants are swapped (M ending used in `_female` key).

Hydration app realistic examples:
- `goal_reached_male` → "तुमने आज का लक्ष्य पूरा कर **लिया**!" vs `goal_reached_female` → "तुमने आज का लक्ष्य पूरा कर **ली**!" — both required, must differ.
- If only neutral key exists, the safest translation is restructured: "आज का लक्ष्य पूरा!" — flag the gendered participle form as a gender leak when no gender info is available.

## Script & direction

- Script: **Devanagari (देवनागरी)**.
- Direction: **LTR**.
- No RTL mirroring concerns. Numerals: ASCII Arabic (1, 2, 3) are standard in modern UI; Devanagari numerals (१, २, ३) read as old-fashioned / textbook and should be flagged if used in stats/counters (250 मिली ✓, २५० मिली ❌ in app context).

## Punctuation conventions

- **Sentence-end marker:** Modern Indian mobile/web UI overwhelmingly uses **ASCII period `.`** for English-loan-heavy sentences and short UI strings. **Devanagari danda `।` (U+0964)** is correct for fully-Hindi prose, literary, or formal/governmental tone. For this app's casual register, ASCII `.` is acceptable and common; `।` is also acceptable for pure-Devanagari sentences. **Do not flag either as an error** unless mixed inconsistently within the same string or used incorrectly (danda after an exclamation, double punctuation `।.`).
- **Exclamation / question:** ASCII `!` and `?` are standard in modern UI. Devanagari has no native equivalents.
- **Quotation marks:** ASCII `"..."` widely accepted; curly `"..."` also fine. No language-specific style required.
- **Decimal separator:** **period `.`** (250.5 मिली). Comma is **not** a decimal separator in Hindi — flag `250,5` as wrong.
- **Thousands separator:** Indian numbering uses lakh/crore grouping (1,00,000 = one lakh). For app stats this is rarely needed (volumes under 10,000 ml). For step counts or large numbers, flag Western-style `100,000` only if app convention is Indian grouping; otherwise both acceptable.
- **Mixed-script handling:** English brand "My Water" — **keep in Latin script** within Hindi sentences. "My Water में आपका स्वागत है" is correct. Transliterating to "माई वॉटर" is acceptable but inconsistent if other surfaces keep Latin; flag only if mixed within same screen/feature. Same applies to "Apple Health", "Siri", "Apple Watch" — keep in Latin.
- **No space before `!` / `?` / `:`** (unlike French). Flag `पियो !` as wrong spacing.

## Common EN→target calque patterns

- EN: "Drink water"  Literal calque ❌: "पानी पिओ" (terse, missing register marker)  Natural restructure ✓: "**पानी पियो**" / "**पानी पीते रहो**" (drink-keep-going, more habitual)  (reason: bare imperative `पिओ` sounds curt; `पियो` with proper तुम-imperative form sounds natural; for repeated daily reminders, `पीते रहो` matches habit-building tone)

- EN: "Stay hydrated!"  Literal calque ❌: "हाइड्रेटेड रहो!" (acceptable, but...)  Natural restructure ✓: "**पानी पीते रहो!**" or "**खुद को हाइड्रेटेड रखो!**"  (reason: "हाइड्रेटेड रहो" is grammatically fine and English-loanword-acceptable in modern Hindi UI, but reads slightly clinical/medical; "पानी पीते रहो" (keep drinking water) is friendlier and matches the brand voice. Both acceptable — flag only if context demands warmer tone)

- EN: "You reached your goal!"  Literal calque ❌: "तुमने अपने लक्ष्य तक पहुँच गए!" (broken grammar — case/agreement)  Natural restructure ✓: "**लक्ष्य पूरा हुआ!**" or "**तुम्हारा लक्ष्य पूरा!**"  (reason: literal "reach the goal" doesn't map; Hindi naturally says "goal completed/done." Also avoids the past-participle gender leak.)

- EN: "Tap to add a drink"  Literal calque ❌: "एक ड्रिंक जोड़ने के लिए टैप करें" (uses आप-form `करें` + redundant article)  Natural restructure ✓: "**ड्रिंक जोड़ने के लिए टैप करो**" or "**ड्रिंक जोड़ने के लिए दबाओ**"  (reason: drop `एक` (article does not idiomatically exist in Hindi for indefinite count); use तुम-form `करो` for casual instruction. "टैप" widely understood; "दबाओ" (press) also natural.)

- EN: "Set your daily goal"  Literal calque ❌: "अपना दैनिक लक्ष्य सेट करें" (आप-form + dryly Sanskritic `दैनिक`)  Natural restructure ✓: "**अपना डेली गोल सेट करो**" or "**रोज़ का लक्ष्य तय करो**"  (reason: `दैनिक` is correct but sounds bureaucratic/textbook; `रोज़ का` (everyday) is colloquial. Hinglish "डेली गोल" is widely accepted in fitness app UX. Use तुम-form imperative `करो / तय करो`.)

- EN: "You've earned a badge"  Literal calque ❌: "तुमने एक बैज कमाया है" (gendered past participle + odd verb choice)  Natural restructure ✓: "**नया बैज मिला!**" / "**तुम्हें एक बैज मिला!**"  (reason: "earn a badge" is an English collocation; Hindi prefers "मिला" (got/received). Also avoids gender agreement issue — `मिला` is M, `मिली` is F if "बैज" is treated as feminine, but बैज is treated as masculine in modern usage so `मिला` is safe. Nominal restructure "नया बैज!" is safest.)

## Plural rules summary

Hindi has **2 CLDR plural categories: `one` (n=1) and `other` (n=0, 2+)**.

**Common translator mistake:** over-translating with multiple plural variants (adding `few`, `many`, etc.) that Hindi doesn't use. Flag any `.stringsdict` entry for Hindi with categories beyond `one` / `other` as redundant.

**Realistic patterns:**

| Count | Form | Example |
|---|---|---|
| 0 | other | "0 गिलास" (0 glasses) — uses plural form |
| 1 | one | "1 गिलास" (1 glass) — singular |
| 2+ | other | "5 गिलास" (5 glasses) — but the noun गिलास often stays unchanged in nominative; oblique case adds `-ों` (गिलासों) |

**Note on noun inflection:** In nominative direct case, many masculine nouns ending in consonants (बैज, गिलास, नोटिफिकेशन) do **not** change form between singular/plural. So the entire plural difference may live in the **number word** or surrounding text, not the noun itself. Don't flag missing plural marker on the noun if oblique case isn't triggered.

**`%d ml` / `%d glass` patterns:** "1 गिलास" vs "5 गिलास" — same noun form, count word changes. This is correct Hindi, not an under-translation.

## Language-specific skip rules for audit

**Do NOT flag the following as errors:**

1. **English loanwords are native register in modern Hindi UI.** The following are widely accepted and often preferred over Sanskritic equivalents in casual app contexts:
   - **नोटिफिकेशन** (notification) > सूचना (more formal)
   - **बटन** (button) > often no good native equivalent
   - **ऐप** (app) > अनुप्रयोग (textbook/governmental)
   - **टैप** (tap), **स्वाइप** (swipe), **स्क्रॉल** (scroll), **क्लिक** (click)
   - **सेट करो** (set), **सेव करो** (save), **डिलीट करो** (delete) > native equivalents exist but loan verbs are register-natural
   - **गोल** (goal), **टार्गेट** (target) alongside लक्ष्य
   - **हाइड्रेटेड** (hydrated), **हेल्थ** (health), **फिटनेस** (fitness)
   - **बैज** (badge), **स्ट्रीक** (streak — though "लगातार" also works), **लेवल** (level)
   - **पेमेंट** (payment), **सब्सक्रिप्शन** (subscription), **प्रीमियम** (premium), **अपग्रेड** (upgrade)
   - **रिमाइंडर** (reminder) > अनुस्मारक (way too formal for app)
   - **विजेट** (widget)

   Do **not** flag these as "untranslated" or "missing localization." They are the natural register. **Flag the opposite**: if a casual surface uses overly Sanskritic equivalents (अनुप्रयोग, अनुस्मारक, सूचना in casual notification body) when loanword is the natural choice.

2. **Hinglish (mixed Hindi-English) is acceptable** for casual surfaces (notifications, motivational copy, widget hints, Siri prompts). "अपना डेली गोल पूरा करो!" mixes "डेली गोल" (English-origin) with Hindi verb — this is natural modern UX register, not a quality issue. **Threshold:** if more than ~40% of content words in a short string are English loans AND a clean Hindi equivalent exists at the same register, flag as "over-Anglicized" (low severity). Otherwise accept.

3. **Brand and product names stay in Latin script** ("My Water", "Apple Health", "Siri", "Apple Watch", "HealthKit"). Do not flag as untranslated.

4. **ASCII numerals** (0-9) in Devanagari sentences are correct modern usage. Do not require Devanagari numerals (१२३) — those would actually be flagged as old-fashioned for an app.

5. **Both `.` and `।` as sentence terminators are acceptable** in app UI. Flag only if mixed inconsistently within the same screen or used incorrectly.

6. **Past-participle endings -या/-ई are gender forms, not typos.** Do not flag `पी` (fem.) as a misspelling of `पिया` — it is the correct feminine past participle. Flag only when the gendered form leaks into a gender-unknown context (see Gender section).

**Auditor false-positive patterns common to Hindi:**

- **"Looks like English"** — flagging नोटिफिकेशन / बटन / ऐप as untranslated. These are the natural Hindi UI register, not laziness.
- **"Missing honorific" / "rude tone"** — flagging तुम-form as disrespectful. For a casual hydration companion, तुम is the correct brand register; आप would be too distant.
- **"Wrong plural"** — flagging "5 गिलास" because गिलास didn't pluralize. Many masculine nouns don't inflect in nominative direct case; this is correct.
- **"Spelling error"** — flagging gendered verb form (पी vs पिया, गई vs गया) as misspelling. These are correct feminine/masculine forms.
- **"Period missing"** — demanding Devanagari danda `।` instead of ASCII `.`. ASCII is fine in modern UI.
- **"Different from base"** — flagging when translator dropped articles ("a / an / the") in Hindi. Hindi has no indefinite article and uses bare nouns; keeping `एक` from EN literal often sounds worse.
- **"Sanskritic word missing"** — pushing अनुप्रयोग instead of ऐप, अनुस्मारक instead of रिमाइंडर. These translations sound textbook/governmental for a casual fitness app and should not be required.
