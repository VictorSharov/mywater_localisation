# Calibration profile — Polish (pl)

Lean, evidence-derived profile (2-batch Opus 4.8 pilot, 223 keys, 2026-05-31 — see
`loc_audit_changelog.md`). Polish is medium-resource and Opus 4.8 audits it cleanly
unaided; this profile is **consistency insurance + false-positive guards + the explicit
4-form-plural check**, NOT a remedy for model blindness. Keep it lean — do not pad with
general Polish grammar the model already knows.

## T-V / formality system

**binary T-V** — T = `ty` (2nd-sg verbs `-isz` / `-esz`, imperative `-j` / `-ij`: `pij`,
`dodaj`); V = `Pan` / `Pani` + 3rd-person verb (`niech Pan wypije`), possessive `Pana` / `Pani`.

Friendly `ty` is the brand default on every surface **except genuinely legally-binding
text** (Terms / Privacy / subscription **legal** terms / consent, `Register: formal`), where
formal/impersonal is correct (rule #8 / skip #1). Pilot evidence: the corpus realizes pl
legal/permission register as **impersonal + plural-"we" (`Potrzebujemy…`) + singular-`ty`
address to the user** (`twój`, `rejestrujesz`), **not** `Pan`/`Pani`. Therefore:
- Permission prompts (`NS*UsageDescription`) and paywall: a "we + `ty`" rendering is
  **correct — do NOT flag as a mixed-register defect** even when the key carries a legacy
  `Register: formal V-form` tag (the tag is grandfathered; the shipped we+ty is on-brand).
- A true `Pan`/`Pani` honorific on a casual surface is still a confirmed-defect V-leak
  (rule #8) — none seen in the pilot, so this is currently theoretical for pl.

## Gender system in grammar

Polish past tense and adjectives inflect for gender → `*M`/`*F` keys must **differ** where
the verb/adjective agrees with the user, and are correctly **identical** where the
construction is impersonal / imperative / a noun phrase.
- DIFFER (flag if identical): past tense (`wypiłeś`/`wypiłaś`, `osiągnąłeś`/`osiągnęłaś`),
  predicate adjectives (`dumny`/`dumna`, `gotowy`/`gotowa`).
- IDENTICAL is correct (do NOT flag as missing-variant): impersonal `udało ci się…`,
  imperatives (`pij`, `dodaj`), pure noun phrases (`Twój cel`), invariant loan adjectives.
- The pilot's M/F pairs were handled correctly throughout — this section guards against
  false-flagging the legitimately-identical impersonal pairs; it is not a known defect area.

## Script & direction

Latin (Polish diacritics `ą ć ę ł ń ó ś ź ż`), LTR. A missing/wrong diacritic is a `typo`
that changes the word (`być` ≠ `byc`, `łeb` ≠ `leb`) — never a stylistic choice.

## Punctuation conventions

- **Decimal separator `,` (comma):** `0,5 l`, `2,5 szklanki`; thousands = space or `.`.
  Flag a `.`-decimal copied from an en literal number (not `[%i]`/`%@` placeholders, which
  the app formats at runtime).
- **Quotation marks:** Polish `„…"` (low-opening / high-closing); ASCII `"…"` common in app
  UI. Quotes are a separate project sweep — skip per skip-rule #3.
- **Em-dash `—` (U+2014):** banned (rule #15); ` - ` (U+002D) and `–` (U+2013) are fine.
- No space before `,` `.` `!` `?` `:` (as in English, unlike French).

## Common EN→target calque patterns

The primary pl risk is **ru→pl Slavic calque** — the team is ru-native and the audit anchors
on `ru`, so pl can inherit a Russian structure / case-government / clinical term that is
wrong or unidiomatic in Polish.
- EN `Stay hydrated!` → clinical calque ❌ `Utrzymuj swój bilans wodny!` (`bilans wodny` =
  physiological "water balance", clinical on a casual card) → ✓ `Pij wodę regularnie!`.
  (Pilot finding `text1_9F`; the ru anchor avoided the calque too.)
- Clinical-term watchlist for casual surfaces: `bilans wodny`, `nawodnienie`,
  `gospodarka wodna`, `spożycie / przyjmowanie płynów` → prefer `pij wodę`, `picie wody`,
  `ile wypiłeś`.
- **ru→pl skip-#16 caveat:** pl and ru are both Slavic, so "pl mirrors ru" does NOT
  auto-clear a finding the way it does for distant languages — a mirrored Slavic structure
  can still be a pl calque. Cross-check that the mirrored choice is *idiomatic Polish*, not
  merely *parallel to Russian*.

## Plural rules summary

Polish CLDR uses **four** categories — `one` (n=1), `few` (n=2–4, NOT 12–14), `many`
(n=0, 5–21, the teens, most), `other` (fractions). A `.stringsdict` missing `few` or `many`
is a defect.

**The recurring real defect (pilot `howMuchPeopleUseAppPlural`): `few` collapsed into the
`many` (genitive-plural) form.** For **masculine-personal** nouns the `few` form must shift
BOTH the noun to nominative plural AND the past-tense verb to the `-li` masc-personal
ending: `2 użytkownicy zaczęli` (few) vs `5 użytkowników zaczęło` (many). Check
masc-personal `few` ≠ `many` explicitly.

**Legitimate identity — do NOT false-flag:** `many` == `other` (both genitive plural) is
normal; `few` == `many` == `other` is correct when the counted noun's plural/genitive
coincide (`razy` for 2+, `dni` for 2+). Flag only a *grammatically wrong* form or a *missing
required* form — never mere text-identity across forms.

## Language-specific skip rules for audit

1. **Identical impersonal M/F pairs** (`udało ci się`, imperatives, noun phrases) — correct,
   not a missing-gender-variant defect.
2. **Plural form-identity where Polish grammar coincides** (`many`==`other`; `razy`/`dni`
   all-coincide) — correct, not an under-translation.
3. **`rejestr`** (= "log") and **`miary`** (= preset drink volumes) — established in-app
   terminology, applied consistently; not bureaucratic-drift, and not "drift from ru" even
   though ru uses different words.
4. **Permission / paywall "we + `ty`"** under a legacy `Register: formal V-form` tag —
   grandfathered and on-brand; not a mixed-register leak.
5. **Loanwords** `aplikacja`, `powiadomienia`, `widżet`, `premium`, `smoothie` — natural pl
   UI register, not anglicisms. `application → app` is an en-only rule, does not transfer.
6. **Explicit constraint beats the ru-mirror skip (#16):** a brand / proper-noun / mandatory
   placeholder / hashtag constraint outranks "pl mirrors ru" — flag the violation (e.g. a
   translated brand in `appstore_app_title`) even though ru also diverged.
