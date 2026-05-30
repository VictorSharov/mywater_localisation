# Calibration profile — Indonesian (id)

## T-V / formality system

**binary T-V (T-form / V-form pronouns)**

Indonesian has a binary register split for second person:

- **T-form (casual): `kamu`** — friend, peer, younger person, informal app voice. Possessive enclitic `-mu` (`gelas**mu**` = "your glass"). Object form `kamu` (same).
- **V-form (formal): `Anda`** — strangers, business, legal, deferential tone. Always capitalized. Possessive `Anda` (`gelas **Anda**`).
- Also exists: `lo` / `lu` (Jakarta slang) — too colloquial, **never** for product UI; flag as wrong register.
- First person: `aku` (casual, pairs with `kamu`) vs `saya` (neutral-formal, pairs with `Anda` or stands alone). App self-reference "we" → **`kami`** (excludes addressee, correct for "our app speaks") — not `kita` (which includes the user).

**Hydration app default: `kamu` + `-mu` + `kami`** for app voice — the default on **all brand-voice surfaces** (the surface-based `ты`/`вы` split is retired, refined to the hybrid: `TRANSLATION_STYLE.md § Brand voice § Pronouns`, 2026-05-30). `kamu`/`-mu` covers errors, payment failures, permission prompts, paywall hero/CTA and account-deletion *confirmations* too (reserved tone, not `Anda`). The **one** carve-out is genuinely **legally-binding text** — Terms of Use, Privacy Policy, subscription **legal** terms, legally-weighted consent — drafted impersonally (`Pengguna…`) with `Anda` only as a direct-address fallback (`Register: formal`). Legacy `Anda` on former-formal **non-legal** surfaces is grandfathered (no mass sweep — flag only new / source-changed, severity `warn`). The base prompt's "T-form throughout" rule maps to `kamu`/`-mu`.

**Leak patterns to flag:**

- **Mixed register in connected text** — `"Selamat datang! Mari mulai melacak air minum Anda."` mixes friendly opener with `Anda` possessive → flag. Should be `air minum**mu**` or `air minummu`.
- **`Anda` in motivational / push / streak / achievement copy** — `"Hebat! Anda mencapai target hari ini."` is stiff; casual surface wants `"Hebat! Kamu mencapai target hari ini."` or even drop pronoun: `"Hebat! Target hari ini tercapai."`
- **`lo` / `lu` / `gue` / `gw`** — slang leak, wrong register for product. Flag.
- **`-nya` used as 2nd-person possessive** — `"gelasnya"` literally "his/her/its glass" or definite "the glass". Some lazy translators use `-nya` to dodge the T/V choice. In direct address context (e.g., progress message addressed to user), `-mu` is correct; `-nya` is a register-evasion smell. Acceptable only when truly impersonal (`Tambahkan minuman**nya**` = "add the drink" referring to a specific drink, not user-possessed).
- **`kami` vs `kita` confusion** — `kita` = inclusive "we (you + me)"; `kami` = exclusive "we (us, not you)". App brand voice "our app / we at My Water" → `kami`. `"Kita akan mengingatkan kamu"` ("we'll remind you" with inclusive "we" including the user) is logically wrong → should be `kami`.

**Imperatives:** Indonesian imperatives are register-flexible. Bare verb (`Minum`, `Tambah`, `Coba`) is neutral and short — natural for buttons / CTAs / push titles regardless of register. Softening particles change tone:

- `Ayo` (let's, encouraging) — friendly, fits brand voice: `"Ayo minum segelas air!"`
- `Yuk` (let's, very casual) — friendly but very colloquial, OK for push notifications, edgy on legal-adjacent screens.
- `Silakan` (please, polite) — Anda-zone marker; in casual surface feels overly formal.
- `Tolong` (please, requesting favor) — for requests, not promotional CTAs.
- `-lah` enclitic (`Minumlah`, `Cobalah`) — softens to suggestion / mild encouragement; slightly literary, acceptable but not the most casual register.

Mixing `Silakan` with `kamu` (`"Silakan tambahkan minumanmu"`) is a register clash → flag as inconsistency, not as outright error.

## Gender system in grammar

**Indonesian has NO grammatical gender.** Nouns, pronouns, verbs, adjectives, and articles do not inflect for gender. Third-person singular pronoun `dia` (or `ia`) covers he/she/it. Verbs do not conjugate for person, number, or gender.

**Consequence for gendered .strings keys:** EN keys with `_male` / `_female` / `_m` / `_f` suffixes will typically have **identical Indonesian values** — this is **correct** and must **not** be flagged as a duplication / copy-paste error. Indonesian simply lacks the grammatical machinery to differentiate.

Example:
- `streak_celebration_male` = `"Kamu hebat! Sudah 7 hari berturut-turut."`
- `streak_celebration_female` = `"Kamu hebat! Sudah 7 hari berturut-turut."`

→ **Identical values are correct.** Do not flag.

Rare exception: if a translation references a kinship / professional term that does have separate male/female forms (e.g., `pria`/`wanita`, `bapak`/`ibu`, `aktor`/`aktris`), then divergence is expected. For hydration-app copy this is essentially never relevant.

## Script & direction

Latin script, LTR. No special bidi handling. Standard ASCII alphabet plus diacritics on rare loanwords (`café` → usually written `kafe`). No `é` / `è` use needed in app domain.

## Punctuation conventions

- **Quotation marks:** `"..."` (straight double quotes) standard in modern Indonesian digital text. Curly `"..."` accepted in editorial / print but `"..."` is the safe app default. Single quotes `'...'` for nested quotes.
- **Decimal separator:** `,` (comma). E.g., `2,5 liter`, `1,5 gelas`. Thousands separator: `.` (period). E.g., `1.500 ml`, `10.000 ml`. **This is the opposite of EN convention** — common AI translator failure is leaving `2.5 liter` (English-style). Flag if source EN string contains a hardcoded number with `.` decimal and Indonesian translation copies it instead of converting (only relevant for hardcoded literal numbers in copy, not `%@` / `%d` placeholders which the app formats at runtime).
- **Time:** `08.00` or `08:00` both seen; `08.00` more traditional Indonesian, `08:00` more common in apps. Either acceptable.
- **Date:** day-month-year (`15 Mei 2026`). Month names: `Januari, Februari, Maret, April, Mei, Juni, Juli, Agustus, September, Oktober, November, Desember`.
- **Spacing:** standard Western spacing. No space before `:` `;` `!` `?`. Space after punctuation. Em-dash `—` per base prompt policy; Indonesian uses en-dash `–` for ranges (`08.00–10.00`) — keep base policy on em-dash.
- **Brand name "My Water":** keep as **"My Water"** (Latin, untranslated, two words, capitalized). Do **not** translate to `Air Saya` / `Air Kami`. App self-reference outside the brand name uses `kami` / `aplikasi kami` ("our app"). Acceptable phrasings: `"My Water"`, `"aplikasi My Water"`, `"di My Water"`. Flag literal translations of the brand name as errors.
- **Units:** `ml`, `l` (lowercase, no period), `oz` (if used). `gelas` (glass), `cangkir` (cup), `botol` (bottle), `liter` (full word also fine). Space between number and unit: `250 ml`, `1,5 l`. Indonesian standard does **not** put a space before `%`: `75%`, not `75 %`. Match what the source `.strings` format dictates if it includes/omits the space; flag inconsistencies across the file.

## Common EN→target calque patterns

- **EN:** `"Track your water intake"`
  **Literal calque ❌:** `"Lacak asupan air Anda"` (overly formal `Anda` + clinical `asupan` "intake")
  **Natural restructure ✓:** `"Pantau minum airmu"` or `"Catat berapa banyak air yang kamu minum"`
  (Reason: `asupan` is dietitian / medical-report vocabulary, clashes with friendly brand voice; `pantau` / `catat` is everyday "track / log"; `kamu` + `-mu` matches T-form register.)

- **EN:** `"You've reached your daily goal!"`
  **Literal calque ❌:** `"Anda telah mencapai tujuan harian Anda!"` (V-form, double `Anda`, formal aspect marker `telah`)
  **Natural restructure ✓:** `"Targetmu hari ini tercapai!"` or `"Kamu mencapai target hari ini!"`
  (Reason: `target` is the natural loanword for daily goal in fitness apps; `tujuan` reads as "purpose / destination" and is too abstract; `telah` is bureaucratic past-perfect marker, drop in casual UI; double possessive `Anda...Anda` is awkward.)

- **EN:** `"Don't forget to drink water"`
  **Literal calque ❌:** `"Jangan lupa untuk minum air"` (extra `untuk` "to" — calque from English infinitive)
  **Natural restructure ✓:** `"Jangan lupa minum air"` or `"Jangan lupa minum, ya!"`
  (Reason: Indonesian doesn't need `untuk` before a chained verb here; reads as translated English. Adding final particle `ya` for push-notification warmth is idiomatic.)

- **EN:** `"Add a glass of water"`
  **Literal calque ❌:** `"Tambahkan sebuah gelas air"` (`sebuah` is Indonesian's "a/an" classifier, but it sounds bookish here)
  **Natural restructure ✓:** `"Tambah segelas air"` or `"Tambah air"`
  (Reason: `segelas` = `se-` + `gelas` is the natural "a glass of" form; `sebuah gelas` is grammatically valid but textbook-stiff for a CTA button; the determiner `a` often drops entirely in casual Indonesian UI.)

- **EN:** `"My Water will remind you every 2 hours"`
  **Literal calque ❌:** `"My Water akan mengingatkan Anda setiap 2 jam"` (V-form leak; `kita`/`kami` confusion if rewritten)
  **Natural restructure ✓:** `"My Water akan mengingatkanmu setiap 2 jam"` or `"Kami akan mengingatkanmu setiap 2 jam"`
  (Reason: enclitic `-mu` is the natural casual object form; if subject is "we / the app" use `kami` (exclusive), never `kita` (inclusive — would mean "you and I will remind you", logically broken).)

- **EN:** `"Drink water and feel great"`
  **Literal calque ❌:** `"Minum air dan merasa hebat"` (calques EN coordination; `merasa hebat` is structurally off)
  **Natural restructure ✓:** `"Minum air, rasakan bedanya"` or `"Minum air biar makin segar"`
  (Reason: Indonesian motivational copy prefers a causative connector (`biar` "so that" — casual; `agar` — neutral) or a parallel imperative (`rasakan` "feel it") rather than the bare EN `and`-coordination.)

## Plural rules summary

Indonesian has **1 CLDR plural category: `other`**. There is no morphological plural agreement.

- A single form covers all counts: `"1 gelas"`, `"5 gelas"`, `"100 gelas"` — `gelas` does not inflect.
- Reduplication exists (`anak` → `anak-anak` "children", `buku` → `buku-buku` "books") to mark plurality / variety, but is **optional** and **omitted when a number / quantifier is present**: never `"5 gelas-gelas"`. With a counter word, the bare noun is correct.
- Counter / classifier words: `segelas` (a glass of), `secangkir` (a cup of), `sebotol` (a bottle of), `seliter` (a liter of); for plurals just use the number: `2 gelas`, `3 botol`.

**Audit flags for `.stringsdict`:**

- **Multiple plural variants for `id`** — if the `.stringsdict` for Indonesian defines `one`, `two`, `few`, `many` etc. with different strings, that's a misconfiguration. Indonesian needs **only `other`**. Flag.
- **Reduplicated form when number is present** — `"%d gelas-gelas air"` is wrong; should be `"%d gelas air"`. Flag.
- **Asymmetry vs source** — if EN has `one` / `other` variants ("1 glass" / "%d glasses") and the Indonesian `other` value is missing or reads as if only intended for the count-1 case, flag.

## Language-specific skip rules for audit

Beyond the base prompt's skip rules, for Indonesian **do not** flag the following as errors:

- **English loanwords in tech / lifestyle domain** are natural and expected:
  - `aplikasi` (app), `notifikasi` (notification), `widget` (kept as `widget`), `streak` (commonly kept as `streak` in fitness apps; native `rangkaian` / `beruntun` also fine), `premium`, `target`, `goal` (loanword `goal` used in fitness; native `target` more common), `reminder` (or `pengingat`), `update`.
  - Flag only if a loanword is used where a clearly more natural Indonesian word exists in everyday speech AND the loanword sounds forced / corporate (e.g., `"intake"` instead of `"konsumsi"` / `"jumlah minum"`).
- **Code-mixing in casual surfaces** — short English words in push notifications (`"Streak kamu 7 hari!"`) match how Indonesian fitness apps actually speak. Don't flag unless register clearly drifts toward Anglicized corporate.
- **Reduplication absence** — bare noun with a number is standard; do not flag missing reduplication as "incomplete plural".
- **Identical M/F gendered keys** — see "Gender system" above. Do **not** flag.
- **Affix dropping in CTAs** — buttons / CTAs commonly drop active-voice prefix `me(N)-`: `Tambah` instead of `Menambah(kan)`, `Mulai` instead of `Memulai`, `Hapus` instead of `Menghapus`. This is correct UI register; do not flag as "missing prefix".
- **Particle `kan` / `lah` / `ya` / `dong` / `kok` / `sih`** in push / motivational copy — these are casual register-builders, not errors. `dong` / `sih` skew very colloquial — flag only if used in legal / paywall / settings copy where they don't belong.
- **`-nya` as definite marker** (not as 3rd-person possessive) — `"Tambahkan minumannya"` "add the drink" referring to a just-selected item is fine.

**Indonesian-specific AI translator pitfalls to actively check:**

1. **`Anda` overuse** — most common LLM mistake: defaulting to formal `Anda` everywhere because EN "you" lacks register. Default expectation is `kamu` / `-mu` on **every** surface — including errors, payment/subscription failures, permission prompts and paywall hero/CTA (these stay `kamu` with a *reserved tone*, not `Anda`). The **only** carve-out is genuinely legally-binding text — Terms of Use, Privacy Policy, subscription **legal terms**, legally-weighted consent — drafted impersonally (`Pengguna…`), `Anda` only for unavoidable direct address (`Register: formal`). Flag `Anda` everywhere **except** that legal-binding set; legacy `Anda` on former-formal non-legal surfaces is grandfathered (flag only new / source-changed, `warn`).
2. **`kita` vs `kami` confusion** — LLMs frequently pick `kita` (inclusive "we") when the app refers to itself, which is logically wrong. App speaking → `kami`.
3. **`telah` / `sudah` / `akan` over-marking** — LLMs over-insert aspect markers calquing EN tense (`have reached` → `telah mencapai`). Casual Indonesian often drops or uses bare verb. `Sudah` is the casual perfect marker; `telah` is formal/literary.
4. **Decimal point left as `.`** — `2.5 liter` instead of `2,5 liter`. Check any hardcoded literal numbers (not `%@` placeholders).
5. **Brand name translated / inflected** — `Air Saya`, `Air Kami`, `air-ku` for "My Water" is wrong; brand stays in English.
6. **Direct calque of EN "your"** — repeated `kamu` / `Anda` / `-mu` in every slot where EN has "your" reads stiff. Indonesian often drops the possessive when it's contextually clear (`"Target tercapai!"` rather than `"Targetmu tercapai!"`). Don't flag drops as errors; do flag dense triple `-mu` chains as awkward style.
7. **Over-formal vocabulary substitution** — `asupan` (intake), `mengonsumsi` (consume), `hidrasi` (hydration), `cairan tubuh` (bodily fluids) — these belong in dietitian articles, not in a friendly tracker UI. Prefer `minum`, `air`, `jumlah`. Flag when register drifts clinical.
8. **Imperative softener clash** — `Silakan` (polite) appearing in the same screen as `kamu` (casual) → register inconsistency. Flag.
9. **`untuk` overuse** — calquing English infinitive `to` (`untuk minum`, `untuk melacak`) when bare verb chains naturally without it. Flag if it produces stiff bureaucratic feel.
10. **Wrong slang register (`lo` / `gue`)** — Jakarta-dialect pronouns are too colloquial for cross-regional app UI. Flag.
