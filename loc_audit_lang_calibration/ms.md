# Calibration profile — Malay (ms)

## T-V / formality system

**binary T-V (T-form / V-form pronouns)** — but softer than Slavic/Romance binary; address often dropped entirely in UI.

Malay second-person system:
- **awak** — casual, friendly, peer-level. Common in conversational apps, ads, casual UI. Default T-form for "My Water".
- **kamu** — casual/familiar, slightly more intimate or directive; common in song lyrics, casual writing, less common in polished app UI than `awak`.
- **anda** — formal/written/respectful. Standard in banking apps, government, corporate, formal notifications. V-form equivalent.
- **kau / engkau** — intimate/blunt; NEVER use in app UI (sounds rude or overly poetic).
- **aku** — intimate first-person; NEVER use in app UI.
- **saya** — neutral first-person; safe default when app speaks of itself in singular ("saya akan ingatkan awak" — but app usually refers to itself as "kami / aplikasi kami").

**For "My Water" (casual, friendly, T-form):**
- App self-reference: `kami` / `aplikasi kami` / `My Water` (we / our app).
- User address: prefer `awak` OR drop pronoun entirely (Malay frequently omits 2nd-person — imperative without subject reads as natural friendly tone).
- Example friendly: `Jangan lupa minum air!` (drop pronoun, imperative)
- Example with awak: `Awak dah minum air hari ini?`
- Example formal (WRONG voice for this app): `Adakah anda telah meminum air hari ini?`

**Audit flags:**
- `anda` is off-brand on every **brand-voice** surface — friendly `awak` (or dropped pronoun) is the default, including paywall, permission prompts and errors (reserved tone, not `anda`): the surface-based `ты`/`вы` split is retired (refined to the hybrid, `TRANSLATION_STYLE.md § Brand voice § Pronouns`, 2026-05-30). In casual notifications/CTAs/motivational push → V-form leak (flag). The **one** carve-out is genuinely **legally-binding text** (Terms / Privacy / subscription **legal** terms / legally-weighted consent): impersonal-first (`Pengguna…`), `anda` only as a direct-address fallback (`Register: formal`). On former-formal **non-legal** surfaces legacy `anda` is grandfathered — do not mass-flag; flag only new / source-changed strings, severity `warn`.
- `kau` / `engkau` / `aku` anywhere → register error.
- Indonesian `kamu` is fine in id but in ms feels childish/dated for app UI — prefer `awak` or drop.
- Mixing `awak` and `anda` within same screen → inconsistency.

**Malay vs Indonesian register trap:** Indonesian `Anda` is the default polite-neutral and very common in apps; Malay `anda` is noticeably more formal. An Indonesian-trained translator may overuse `anda` — flag if the entire file reads like Bahasa Indonesia formal register.

## Gender system in grammar

No grammatical gender (`dia` = he/she/it; verbs don't conjugate) — base prompt rule #5 applies: identical M/F values are **correct**, do not flag. If a translator artificially differentiates M/F (adds `lelaki` / `perempuan`), flag as over-translation.

## Script & direction

**Latin (Rumi), LTR.**

- Jawi (Arabic-script Malay) is not used in modern apps → flag Jawi characters as wrong script.
- No diacritics in standard Malay; accented Latin chars usually signal untranslated source.
- Sentence case standard; Title Case OK for buttons, not over-applied like English.

## Punctuation conventions

- **Quotation marks:** `" ... "` straight double quotes standard in digital Malay. Curly `"..."` acceptable. Single `'...'` for nested.
- **Decimal separator:** `.` (period) in Malaysia — **distinct from Indonesia which uses `,`**. So `2.5 liter` is correct ms; `2,5 liter` is id and should be flagged in ms files.
- **Thousand separator:** `,` (comma) — e.g. `1,500 ml`.
- **Spacing:** standard Latin; single space after period/comma; no space before punctuation (unlike French).
- **Colon/semicolon:** standard usage; colon often followed by single space.
- **Currency:** `RM` prefix without space → `RM10` or `RM 10` (both acceptable; `RM10` more common in casual app UI).
- **Time:** 12-hour with `pagi / tengah hari / petang / malam` casual, or 24-hour `09:30` formal/system.
- **Ellipsis:** `...` (three dots) — single character `…` also fine.
- **No Oxford comma convention** — Malay rarely uses serial comma.

**Audit flags:**
- `2,5 L` or `1.500 ml` (Indonesian number format) in ms file → flag.
- Multiple exclamation `!!!` or emoji-heavy punctuation in formal contexts → flag (but casual notifications can have one `!`).

## Common EN→target calque patterns

- **EN:** "You're doing great!"
  **Literal calque ❌:** "Awak sedang melakukan hebat!"
  **Natural restructure ✓:** "Syabas!" or "Bagus, teruskan!"
  *(reason: "doing great" is an EN idiom; literal verb+adjective combo is awkward. Malay prefers short interjection or compliment.)*

- **EN:** "Stay hydrated"
  **Literal calque ❌:** "Kekal terhidrat" / "Kekal berhidrat"
  **Natural restructure ✓:** "Minum air dengan kerap" or "Jangan lupa minum"
  *(reason: `terhidrat`/`hidrasi` are technical/clinical loanwords; brand voice prefers plain "drink water often" / "don't forget to drink".)*

- **EN:** "Track your water intake"
  **Literal calque ❌:** "Jejaki pengambilan air anda"
  **Natural restructure ✓:** "Rekod air yang awak minum" or "Pantau air yang diminum"
  *(reason: `pengambilan` is formal/medical-report register; `rekod / pantau` + verb is friendlier and matches casual T-voice. Also drops `anda`.)*

- **EN:** "Daily goal reached"
  **Literal calque ❌:** "Matlamat harian dicapai"
  **Natural restructure ✓:** "Matlamat hari ini tercapai!" or "Dah capai matlamat hari ini!"
  *(reason: passive `dicapai` is bureaucratic. `tercapai` (involuntary/accomplished aspect) or active `dah capai` reads achievement-like.)*

- **EN:** "Set a reminder" (button)
  **Literal calque ❌:** "Tetapkan satu peringatan"
  **Natural restructure ✓:** "Tetapkan peringatan" or "Pasang peringatan"
  *(reason: Malay does not need indefinite article `satu`; literal `satu` is calque from English `a/an`.)*

- **ms vs id distinction — EN:** "Office reminder"
  **Indonesian (WRONG for ms) ❌:** "Pengingat kantor"
  **Malay ✓:** "Peringatan di pejabat"
  *(reason: `kantor` (id) = `pejabat` (ms) for "office". Also `pengingat` (id) vs `peringatan` (ms) for "reminder". Critically `pejabat` in Indonesian means "official/officer" — a translator using Indonesian-trained intuition will mistranslate badly.)*

- **ms vs id distinction — EN:** "Free trial"
  **Indonesian (WRONG for ms) ❌:** "Uji coba gratis" / "Coba gratis"
  **Malay ✓:** "Percubaan percuma"
  *(reason: `gratis` (id, from Dutch) vs `percuma` (ms); `uji coba / coba` (id) vs `cuba / percubaan` (ms). Flag `gratis` in ms file.)*

- **ms vs id distinction — EN:** "Speak with Siri"
  **Indonesian (WRONG for ms) ❌:** "Bicara dengan Siri"
  **Malay ✓:** "Bercakap dengan Siri"
  *(reason: `berbicara / bicara` is Indonesian default; Malay uses `bercakap`. Both languages know both words but the default natural register differs.)*

## Plural rules summary

Malay has **1 CLDR plural category: `other`**.

- No morphological plural marking.
- Plural expressed by: (a) reduplication — `kanak-kanak` (children), `buku-buku` (books); (b) quantifier/numeral — `tiga gelas air` (three glasses of water); (c) context only.
- For count strings in `.stringsdict`, the `other` category is the only required one — same form covers `1`, `2`, `5`, `100`.
- Counter words (penjodoh bilangan) often used with numbers: `segelas air` (a glass of water), `dua gelas air` (two glasses), `tiga botol` (three bottles). Do not require translator to drop these — natural ms uses them.
- Reduplication is **NOT** mandatory for plurals when count is explicit: `3 hari` is fine, `3 hari-hari` is wrong.

**Audit flags:**
- Stringsdict with `one` / `few` / `many` variants — all should resolve to same `other` value. If translator put different morphology in fake `one` vs `other` keys, flag.
- Forced reduplication after a numeral (`5 botol-botol`) → flag.

## Language-specific skip rules for audit

Beyond base prompt rules, for Malay specifically:

1. **English loanwords are natural in tech UI** — do NOT flag these as calques or anglicisms:
   - `aplikasi`, `notifikasi`, `kalori`, `data`, `log`, `widget`, `Siri`, `premium`, `langganan`, `pakej`, `subscribe` (sometimes localized as `langgan`).
   - Platform / 3rd-party brands stay verbatim (do NOT translate): `Apple Health`, `HealthKit`, `Apple Watch`, `iCloud`, `Siri`.
   - **Product brand `My Water` is LOCALIZED in ms → canonical sentence-case `Air saya`** (literal "my water", parallel to ru «Моя вода» / de "Mein Wasser"). Per `glossary.ndjson` (`My Water`) the wordmark is localized per locale and mirrors `CFBundleDisplayName` exactly — 17 of 21 locales localize it; Latin "My Water" is the deliberate exception only for ar/id/vi. Do **NOT** flag `Air saya` as a brand-translation error and do **NOT** suggest reverting it to Latin. DO flag: non-canonical casing (`Air Saya` / `AIR SAYA`), the intimate `Airku` (off-brand `-ku` register, see T-V), or meaning-shifted `Air Kami` / `Air Kita` ("our water"). `My Water Premium` & standalone `Premium` stay Latin (verbatim) — only the base wordmark localizes.

2. **Indonesian-Malay false-friend trap (high priority — flag if found):**
   - **`pejabat`** — ms: "office (place)" ✓ / id: "official (person)" ❌
   - **`butuh`** — id: "need" ✓ / ms: vulgar/sexual ❌ — NEVER use in ms; use `perlu` instead. **Critical flag.**
   - **`pusing`** — id: "dizzy" / ms: "to turn / go around / make a round" — context-sensitive but `pusing kepala` would sound wrong in ms idiom.
   - **`bisa`** — id: "can/able" / ms: "venom / poison" — ms uses `boleh` for "can". `Bisa minum` in ms = "poison to drink" ❌.
   - **`cakap`** — ms: "to speak/say" ✓ (informal) / id: rare. Indonesian translator may avoid it.
   - **`gratis`** — id: "free of charge" / ms: not standard, use `percuma`.
   - **`kantor`** — id: "office" / ms: use `pejabat`.
   - **`mobil`** — id: "car" / ms: use `kereta`.
   - **`kentang`** — both: "potato" (false friend false — actually same). Skip.
   - **`bila`** — ms: "when" (interrogative + conjunction) / id: rare, uses `kapan`. Indonesian translator may write `kapan` which is wrong for ms.

3. **Reduplication is optional, not mandatory** — `peringatan` and `peringatan-peringatan` both valid for plurals; do not flag absence of reduplication.

4. **`-lah` / `-kan` / `-nya` particles** — natural in casual Malay imperatives and softeners:
   - `Minumlah air!` (drink up!) — friendly imperative ✓
   - `Tetapkan matlamat` (set a goal) — `-kan` causative ✓
   - `Air ditambahnya` (he added water) — `-nya` 3rd-person possessive/marker ✓
   - Do not flag these as redundant; absence in casual context may itself be unnatural.

5. **Dropped pronouns are idiomatic** — Malay frequently omits 2nd person in imperatives and questions. `Dah minum air?` (had water?) is more natural than `Awak dah minum air?` for casual notifications. Do not flag missing pronoun as incomplete translation.

6. **`dah` vs `sudah`** — `dah` (contracted) is casual/spoken/SMS register; `sudah` is neutral. `dah` fits the whole app voice including notifications, widgets, **paywall and errors** (informal-universal). `sudah` / neutral phrasing fits **legally-binding text** (Terms / Privacy / subscription legal terms). Flag only a genuine register clash — e.g. `dah` inside Terms of Service (legal reserved register) — **not** `dah` on a paywall or error string.

7. **Time-of-day greetings** — Malay distinguishes:
   - `Selamat pagi` (morning, ~5am–12pm)
   - `Selamat tengah hari` (~12pm–2pm, sometimes folded into pagi/petang)
   - `Selamat petang` (~2pm–7pm)
   - `Selamat malam` (~7pm onwards; also "good night")
   - Indonesian `Selamat siang` (midday) is NOT standard ms — flag if appears.

8. **Beverage name conventions** (drink catalogue):
   - Water → `Air` (just "water"; do NOT translate as `Air kosong` unless emphasizing "plain water")
   - Tea → `Teh`
   - Coffee → `Kopi`
   - Beer → `Bir` (loanword, standard)
   - Milk → `Susu`
   - Juice → `Jus`
   - Soda / Soft drink → `Minuman ringan` (standard term for a sweet carbonated soft drink — the app catalogue `Soda` is sugary). Do **not** render the sweet-soda catalogue item as bare `Soda`: in Malay `soda` / `air soda` is unsweetened soda **water** (cf. Sparkling water below), a different drink. (Corrected 2026-05-31 — the prior "or `Soda`" legitimized an ambiguous term; see `loc_audit_changelog.md § Beverage catalogue naming`.)
   - Energy drink → `Minuman tenaga`
   - Wine → `Wain`
   - Sparkling water → `Air berkarbonat` or `Air soda`
   - Do NOT flag English brand-style names left in English (e.g. "Cola") — these are product names.

9. **Honorific drops in casual app voice** — titles like `encik / puan / cik` (Mr/Mrs/Miss) should NOT appear in casual hydration notifications. If found in user-addressed strings, flag as register mismatch (wrong voice tier).

10. **Mixed-code English insertions** — Malaysian Malay often code-switches with English in casual speech (`Jom drink air sekarang!`). For app UI, prefer monolingual ms; flag heavy code-switching as informal-beyond-brand. Single tech terms (`widget`, `app`) are OK.

11. **Avoid clinical/medical register** in motivational/notification strings:
   - `hidrasi`, `terhidrat`, `dehidrasi`, `pengambilan cecair`, `keseimbangan elektrolit` — too clinical for casual hydration nudges. Prefer `minum air`, `air dalam badan`, `cukup air`.
   - Acceptable in onboarding/educational screens with intentional informational tone.

12. **Em-dash** (base rule #15): ms rarely uses `—`; replace with comma / period / parentheses.
