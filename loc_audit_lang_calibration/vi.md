# Calibration profile — Vietnamese (vi)

## T-V / formality system

**tone-shift only (no pronoun T-V)** — Vietnamese uses a kinship-based address system, not a true T-V binary. There is no morphological politeness inflection on verbs; register is conveyed through pronoun choice, sentence-final particles (`nhé`, `nha`, `ạ`, `ơi`), and lexical formality.

**Canonical second-person for "My Water":** `bạn` (literally "friend") — neutral-casual, age-neutral, gender-neutral. This is the standard register for consumer apps addressing an unknown adult user. Always lowercase mid-sentence; capitalize only sentence-initial.

**Self-reference for the app:** `chúng tôi` (formal "we", excludes listener — appropriate when the app speaks as a company/team), or `My Water` as the brand name in marketing contexts. Avoid `chúng ta` ("we" including the listener) for app voice — it implies the app and the user are one party, which feels off in CTAs and notifications.

**Forms to flag as INAPPROPRIATE register:**
- `anh` / `chị` (older brother / older sister) — presumes user is younger than the speaker, gendered. Wrong for an app addressing arbitrary users. Acceptable only in specifically-targeted onboarding where age/gender is known.
- `em` (younger sibling) — condescending from app to user, presumes user is younger. Flag immediately.
- `quý khách` / `quý vị` ("esteemed customer/guests") — overly formal, hotel/airline register. Wrong for a casual health companion.
- `mày` / `tao` — rude/intimate slang. Never appropriate.
- `ngài` / `Ông` / `Bà` — formal honorifics, wrong tone.
- Bare imperatives without `bạn` or softening particle in user-facing CTAs — reads as commands, not invitations. Compare `Uống nước!` (commanding) vs `Uống nước nhé!` (friendly nudge) vs `Uống nước thôi nào!` (warm encouragement).

**V-form leak skip-rule from base prompt — translates as REGISTER CONSISTENCY rule:** The base prompt's "flag V-form leaks in T-form app" maps to "flag register drift" in Vietnamese. Same spirit, different mechanics:
- Within one string set, the pronoun must stay consistent. Mixing `bạn` in one push and `anh/chị` in another = flag.
- Sentence-final particle drift is also a register signal: a corpus that uses `nhé` / `nha` warmly in some strings and switches to bare declarative in others without reason = flag inconsistency.
- A single string that suddenly uses `quý khách` after 200 strings of `bạn` = leak, flag.

**Imperatives, vocatives, and bare sentences without `bạn`:** Vietnamese frequently omits the subject when it's clear from context. `Đã đến giờ uống nước!` ("Time to drink water!") with no `bạn` is natural and casual — do NOT flag this as missing pronoun. Flag only when omission produces ambiguity or coldness.

## Gender system in grammar

Vietnamese is an isolating language — verbs, adjectives, and nouns do NOT inflect for gender, number, or person. There is no grammatical gender on nouns. The same translation works for male and female users in nearly every case.

**Practical consequence for `.gendered` keys:** A typical iOS gendered-key pattern like:
- `welcome_message_male` → "Welcome back, ready for a refreshing drink?"
- `welcome_message_female` → "Welcome back, ready for a refreshing drink?"

Both Vietnamese values are typically **identical**. A pair of differing Vietnamese strings for an EN-gendered key is suspicious — flag as likely over-translation unless the EN itself differs by gender (e.g., "He / She drank...") and Vietnamese needs `anh ấy` vs `cô ấy`.

**Example:**
- EN male: `You've reached your goal today!`
- EN female: `You've reached your goal today!`
- VI both: `Bạn đã đạt mục tiêu hôm nay!` (identical — correct)
- ❌ Suspicious split: VI male `Anh đã đạt...` / VI female `Chị đã đạt...` — flag as inappropriate pronoun choice (see formality section above; `anh/chị` shouldn't be used app-wide).

## Script & direction

Latin script with diacritics (chữ Quốc ngữ), LTR. Vietnamese uses 6 tone marks (`a á à ả ã ạ`) and additional letter modifications (`ă â đ ê ô ơ ư`).

**Diacritic precision is semantically load-bearing — different diacritic = different word:**
- `nước` (water) vs `nước` is correct; `nuoc` is wrong/missing-diacritic and not a Vietnamese word
- `mà` (but) vs `má` (mother/cheek) vs `mả` (grave) vs `mã` (code) vs `mạ` (rice seedling) — all different words
- `uông` is not a word; `uống` (drink) is correct
- `mật` (honey) vs `mất` (lose) vs `mất` vs `mặt` (face) — flag any tone/diacritic that produces a different word

**Critical for audit:** Treat ANY missing or wrong diacritic as a likely typo/word-change error, not a stylistic choice. Particularly common AI errors:
- `nuoc` → must be `nước`
- `cafe` / `ca phe` → must be `cà phê`
- `tra` (ambiguous: tea? pay?) → `trà` (tea) — flag if missing the grave accent on a beverage name
- `muc tieu` → must be `mục tiêu` (goal)

## Punctuation conventions

- **Quotation marks:** Standard Latin `"..."` is widely accepted. Curly `"..."` also seen, particularly in editorial/print. Use whatever the en source uses, but be consistent. Guillemets `«...»` are NOT Vietnamese convention — flag if present.
- **Spacing around punctuation:** No space before `.` `,` `!` `?` `:` `;` — same as English. (Vietnamese does NOT follow French spacing rules despite the colonial history.)
- **Ellipsis:** Both `…` (single character) and `...` (three dots) are seen. Match the source.
- **Em-dash policy from base prompt:** Vietnamese does not idiomatically use em-dash for parenthetical asides — prefers comma or parentheses. Em-dash usage in EN should typically become a comma, parentheses, or be split into two sentences. Apply base prompt's em-dash policy strictly.
- **Decimal separator:** Comma `,` is the typical Vietnamese decimal separator (`1,5 lít`). However, modern app UIs frequently use period `.` matching the device locale formatter. Flag inconsistency within one app surface, not the choice itself. Thousand separator is period `.` (`1.500 ml`) in formal contexts; spaces also seen.
- **Units:** `ml`, `oz`, `kg`, `lít` (the last is Vietnamese for "liter" — note the diacritic). `ly` = glass, `cốc` = cup/glass (northern dialect), `tách` = small cup (for tea/coffee).
- **Brand name "My Water":** Keep as `My Water` in Latin script — DO NOT translate to `Nước Của Tôi` or similar. Vietnamese readers comfortably parse English brand names; translating brand = anti-pattern, flag if seen. The product is `My Water`, the generic concept is `nước` (water).

## Common EN→target calque patterns

Vietnamese is isolating, drops articles entirely, prefers SVO with topic-prominence, and favors native Vietnamese (or assimilated) vocabulary over Sino-Vietnamese in casual UI. Direct word-for-word EN→VI translation produces stiff, formal, or unnatural output.

- EN: `Stay hydrated!`
  Literal calque ❌: `Hãy giữ cho cơ thể đủ nước!` (literally "keep the body sufficient water" — clinical, sounds like a medical pamphlet)
  Natural restructure ✓: `Nhớ uống nước nhé!` ("Remember to drink water!" — warm, casual, uses companion-tone particle `nhé`)
  (reason: Vietnamese has no idiomatic equivalent for "hydrated" as state-of-being. Casual register uses the action verb `uống` directly. `cơ thể đủ nước` is medical jargon, wrong brand voice.)

- EN: `It's time to drink water`
  Literal calque ❌: `Đó là thời gian để uống nước` (literally "that is time to drink water" — uses pronoun `đó`, article-like structure copied from EN)
  Natural restructure ✓: `Đến giờ uống nước rồi!` ("Reached o'clock drink water already!" — natural Vietnamese sentence rhythm with `rồi` as completion particle)
  (reason: Vietnamese drops `it`-pronoun subjects, and `đến giờ X rồi` is the idiomatic "time to X" construction. Adding `đó là` is a direct calque from English `it is`.)

- EN: `You've reached your daily goal`
  Literal calque ❌: `Bạn đã đạt được mục tiêu hàng ngày của bạn` (double `bạn`, possessive `của bạn` is redundant — sounds like a machine translation)
  Natural restructure ✓: `Bạn đã đạt mục tiêu hôm nay!` ("You reached goal today!" — drops redundant pronoun and possessive, uses `hôm nay` "today" instead of stiff `hàng ngày của bạn` "your daily")
  (reason: Vietnamese omits possessives when ownership is obvious from context. `của bạn` after a noun the user just reached is redundant. `hôm nay` is warmer than `hàng ngày`.)

- EN: `Tap to add a glass of water`
  Literal calque ❌: `Chạm để thêm một ly của nước` (uses `của` "of" as direct calque of EN "of", which is wrong — Vietnamese uses bare juxtaposition for measure phrases)
  Natural restructure ✓: `Chạm để thêm một ly nước` ("Tap to add one glass water" — measure phrase `ly nước` needs no preposition)
  (reason: Vietnamese measure constructions are `[number] [classifier] [noun]` with no `của` / `of`. `một ly của nước` is a hallmark of MT calque.)

- EN: `Track your hydration habit`
  Literal calque ❌: `Theo dõi thói quen hydrat hóa của bạn` (`hydrat hóa` is a borrowed Sino-Vietnamese pseudo-scientific term — sounds like a chemistry textbook)
  Natural restructure ✓: `Theo dõi thói quen uống nước của bạn` ("Track your water-drinking habit")
  (reason: Vietnamese has no native single-word for "hydration" as a habit concept. The natural restructure uses the action verb `uống nước` which is what the user actually does. Pseudo-scientific calques violate the casual companion voice.)

## Plural rules summary

Vietnamese has **1 CLDR plural category: `other`**. Vietnamese is morphologically uninflected — nouns do NOT pluralize. `một ly` (one glass) and `năm ly` (five glasses) use the identical noun `ly`.

**Consequence for `.stringsdict`:** A correct `vi.lproj/Localizable.stringsdict` entry typically has exactly ONE `NSStringFormatValueTypeKey` variant under `other`. Multiple plural-form variants (`one`, `few`, `many`, etc.) for Vietnamese are wrong and should be flagged.

**Optional plural marking:** Vietnamese can mark plurality lexically with `các` (definite plural) or `những` (some/various plural) — but these are NOT required and adding them in stringsdict forms is over-translation. `Bạn đã uống 3 ly nước` is correct, NOT `Bạn đã uống 3 các ly nước`.

**Suspicious patterns to flag:**
- Vietnamese stringsdict entry with `one` AND `other` keys differing only in noun form (e.g., `1 ly` vs `2 lys`) — flag as MT artifact; Vietnamese doesn't pluralize.
- Variant attempting to inflect the noun (`lys`, `glasses` in Vietnamese position) — flag.
- A `.stringsdict` for vi that mirrors the EN structure exactly with `one` + `other` — frequently still valid if both values use the same noun form, but verify it's not an over-engineering hint.

## Language-specific skip rules for audit

Rules that supplement (not replace) the base prompt:

1. **Diacritic typos are NEVER stylistic — always flag.** A missing or wrong diacritic mark usually changes the word entirely. Treat `nuoc` / `mat` / `tra` (when meaning "tea") as errors, not stylistic variants. Common AI mistakes: dropping tone marks on `ướ`, `ơ`, `ư`, `ấ`, `ờ`, `ặ`.

2. **Loanwords are natural — do not flag.** Vietnamese has many normalized loanwords. These are NOT calques or translation errors:
   - `cà phê` (coffee, from French `café`) — natural, preferred over Sino-Vietnamese alternatives
   - `bia` (beer, from French `bière`) — natural
   - `sô-cô-la` / `socola` (chocolate) — natural
   - `app`, `ứng dụng` — both acceptable; `app` is fully assimilated in casual UI
   - `widget` — usually kept as English in tech contexts
   - `Premium`, `Pro` — brand-tier loanwords, keep as-is
   - `OK` — fully assimilated, fine in casual strings
   
   Flag only if the loanword has an obvious, idiomatic native equivalent that's clearly better (e.g., `download` should be `tải xuống` in formal UI).

   **UI-atom loanwords are acceptable BOTH ways — do NOT flag the choice in either direction:** `OK` ↔ `Đồng ý`, `Email` ↔ `Hộp thư` / `Thư điện tử`, `widget` ↔ `tiện ích`. Both the loanword and the native form are idiomatic for these short UI atoms; raise a finding only when the chosen form is semantically wrong for the *surface* — e.g. `Hộp thư` ("inbox/mailbox") used as the label of an email-*address* input field is a `semantic-drift`, not a loanword-vs-native call; a generic acknowledge button rendered `Đồng ý` instead of `OK` (or vice versa) is NOT a finding. (Phase 2 vi pilot: `OK`→`Đồng ý` and `Email`→`Hộp thư` were borderline; this clause resolves the ambiguity — only the address-field `Hộp thư` stays flaggable, as `semantic-drift`.)

3. **Beverage name conventions:**
   - `Water` → `Nước` (or `Nước lọc` for "filtered/plain water" if distinction needed)
   - `Coffee` → `Cà phê` (NOT `Cafe` without diacritics)
   - `Tea` → `Trà` (NOT `Tra`)
   - `Beer` → `Bia`
   - `Milk` → `Sữa`
   - `Juice` → `Nước ép` (literally "pressed water") or `Nước trái cây` (fruit water) for fruit juices
   - `Soda` / `Soft drink` → `Nước ngọt` (literally "sweet water"); `Soda` is also seen, both fine
   - Sports drinks, energy drinks — `Nước thể thao` / `Nước tăng lực` (natural), or keep brand name
   - Flag a beverage name that loses its diacritic (`Ca phe` instead of `Cà phê`) — looks like a typo, IS a typo.

4. **Sino-Vietnamese vs native register check.** Sino-Vietnamese (Hán-Việt) vocabulary is more formal/literary; native Vietnamese is more casual. For a friendly companion app, prefer native:
   - `mục tiêu` (Sino-Viet, goal) — fine in UI, widely used
   - `mục đích` (Sino-Viet, purpose) — slightly more formal, flag if used for daily-goal UI
   - `cơ thể` (Sino-Viet, body) — flag in casual hydration messages; usually unnecessary
   - `hydrat hóa` — pseudo-scientific, flag
   - Tendency to chain Sino-Viet compounds in CTA = clinical voice violation. Flag.

5. **Sentence-final particles convey warmth.** Particles like `nhé`, `nha`, `nào`, `đi`, `thôi` soften imperatives and add companion warmth. Their absence in CTAs/notifications is acceptable but flag as STYLE DRIFT if a corpus uses them in 80% of strings and suddenly drops them in one push. Conversely, overuse (`nhé` on every string) feels saccharine — flag if more than ~60% of strings end in `nhé`.

6. **Capitalization:** Vietnamese capitalizes only sentence-initial words and proper nouns. Title Case (as in EN headings) is NOT Vietnamese convention. A string like `Mục Tiêu Hàng Ngày` (Title Case) is a calque of EN style — flag. Correct: `Mục tiêu hàng ngày` (sentence case). Exception: brand names and product tier names (`My Water`, `Premium`).

7. **No-space concatenation in compound nouns.** Vietnamese writes compound nouns with spaces, NOT joined: `nước ép` (juice), NOT `nướcép`. Hyphens in Vietnamese are rare and mostly in loanwords (`sô-cô-la`). Flag joined-word artifacts as likely OCR/copy errors.

8. **AppIntent / Siri voice strings:** Siri uses TTS that reads diacritics correctly. Strings with missing diacritics will be mispronounced or read as unknown words. Treat diacritic correctness as a hard requirement for any string flagged as Siri-surface. Avoid abbreviations like `ml`, `oz` in voice strings — prefer spelled forms `mi-li-lít` or restructure to avoid the unit token entirely.

9. **Numbers + units:** Standard order is `[number] [unit/classifier] [noun]`: `500 ml nước`, `2 ly nước`. Reversed order `nước 500 ml` is also seen for product labels but unusual in active-voice UI. Flag word order that places number after the noun in CTA/notification context.

10. **Placeholder boundaries — Vietnamese has no articles, so placeholder context matters more.** Where English needs `a glass / the glass`, Vietnamese needs nothing before the noun. A placeholder like `Add %@ to your log` where `%@` is `glass of water` will produce `Thêm ly nước vào nhật ký` — the placeholder must not include the article, and the surrounding string must not assume any article slot. Flag translations that wrap a placeholder in extra words intended to absorb articles (`Thêm một %@ của bạn`).
