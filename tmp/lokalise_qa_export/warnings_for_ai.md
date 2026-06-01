# Lokalise QA warnings export

- declared_keys_count: 633
- extracted_keys_count: 5
- extracted_translations_count: 105
- issue_records_count: 17
- filter: builtin_20

**Coverage warning:** Saved HTML declares 633 keys, but contains render data for only 5 keys. Lokalise appears to virtualize/lazy-load rows; export is incomplete unless additional editor-search responses are captured.

## socialShareTextFbF

### ar · Arabic · trans_id=8526711797

**QA:** Spelling and/or grammar errors

**Source**

```text
I reached my daily water goal today! Help your body, download "My Water"! #mywater
```

**Target**

```text
لقد حققت هدفي اليومي من الماء اليوم! ساعد جسمك أيضًا، حمّل "My Water"! #mywater
```

**Marked spans**

- start=60 length=2 group=1 rule=128897806 fragment="My"
- start=63 length=5 group=1 rule=128897806 fragment="Water"
- start=72 length=7 group=1 rule=128897806 fragment="mywater"

### da · Danish · trans_id=8526710111

**QA:** Spelling and/or grammar errors

**Source**

```text
I reached my daily water goal today! Help your body, download "My Water"! #mywater
```

**Target**

```text
Jeg nåede mit daglige vandmål i dag! Hjælp din krop, download "Mit vand"! #mywater
```

### de · German · trans_id=8526708532

**QA:** Spelling and/or grammar errors

**Source**

```text
I reached my daily water goal today! Help your body, download "My Water"! #mywater
```

**Target**

```text
Ich habe heute mein Tagesziel erreicht! Hilf deinem Körper, lade "Mein Wasser" herunter! #mywater
```

### en · English · trans_id=8526710533

**QA:** Spelling and/or grammar errors

**Source**

```text
I reached my daily water goal today! Help your body, download "My Water"! #mywater
```

**Target**

```text
I reached my daily water goal today! Help your body, download "My Water"! #mywater
```

**Marked spans**

- start=75 length=7 group=1 rule=5 fragment="mywater"

### es · Spanish (Spain) · trans_id=8526710450

**QA:** Spelling and/or grammar errors

**Source**

```text
I reached my daily water goal today! Help your body, download "My Water"! #mywater
```

**Target**

```text
¡Hoy he alcanzado mi meta diaria de agua! Ayuda a tu cuerpo, ¡descarga "My Water"! #mywater
```

### fr · French · trans_id=8526704872

**QA:** Spelling and/or grammar errors

**Source**

```text
I reached my daily water goal today! Help your body, download "My Water"! #mywater
```

**Target**

```text
J'ai atteint mon objectif quotidien. Aide ton corps, télécharge My Water ! #mywater
```

**Marked spans**

- start=64 length=2 group=1 rule=208 fragment="My"

### it · Italian · trans_id=8526704612

**QA:** Spelling and/or grammar errors

**Source**

```text
I reached my daily water goal today! Help your body, download "My Water"! #mywater
```

**Target**

```text
Oggi ho raggiunto il mio obiettivo d'acqua! Aiuta il tuo corpo, scarica "La mia acqua"! #mywater
```

### nl · Dutch · trans_id=8526711113

**QA:** Spelling and/or grammar errors

**Source**

```text
I reached my daily water goal today! Help your body, download "My Water"! #mywater
```

**Target**

```text
Ik heb vandaag mijn dagelijkse waterdoel gehaald! Help je lichaam, download "My Water"! #mywater
```

### pl · Polish · trans_id=8526706535

**QA:** Spelling and/or grammar errors

**Source**

```text
I reached my daily water goal today! Help your body, download "My Water"! #mywater
```

**Target**

```text
Dziś osiągnęłam swój dzienny cel wody! Pomóż swojemu ciału, pobierz "Moja woda"! #mywater
```

### pt_BR · Portuguese (Brazil) · trans_id=8526705517

**QA:** Spelling and/or grammar errors

**Source**

```text
I reached my daily water goal today! Help your body, download "My Water"! #mywater
```

**Target**

```text
Atingi minha meta diária de água hoje! Ajude seu corpo, baixe o "My Water"! #mywater
```

### sv · Swedish · trans_id=8526717856

**QA:** Spelling and/or grammar errors

**Source**

```text
I reached my daily water goal today! Help your body, download "My Water"! #mywater
```

**Target**

```text
Jag nådde mitt dagliga vattenmål idag! Hjälp din kropp, ladda ner "Mitt Vatten"! #mywater
```

## text2_3F

### de · German · trans_id=8526707432

**QA:** Spelling and/or grammar errors

**Source**

```text
Hi, today you drank
```

**Target**

```text
Hallo! Heute hast du getrunken
```

### pt_BR · Portuguese (Brazil) · trans_id=8526706566

**QA:** Spelling and/or grammar errors

**Source**

```text
Hi, today you drank
```

**Target**

```text
Olá, hoje você bebeu
```

## text3_10M

### nl · Dutch · trans_id=8526709470

**QA:** Spelling and/or grammar errors

**Source**

```text
Don't stop!
```

**Target**

```text
Stop niet!
```

## text3_1F

### en · English · trans_id=8526709998

**QA:** Spelling and/or grammar errors

**Source**

```text
Still a little bit left!
```

**Target**

```text
Still a little bit left!
```

**Marked spans**

- start=0 length=5 group=2 rule=56 fragment="Still"
- start=8 length=10 group=3 rule=64266 fragment="little bit"

## youShouldDrink0Digits

### ja · Japanese · trans_id=8526704955

**QA:** Different numbers

**Source**

```text
Based on your parameters, your estimated goal is [%1$.0f] [%2$s] of water. Your doctor can determine the exact goal for you.
```

**Target**

```text
入力した情報から算出した1日の目標水分量の目安は [%1$.0f] [%2$s] です。正確な量については医師にご相談ください。
```

### nl · Dutch · trans_id=8526706609

**QA:** Spelling and/or grammar errors

**Source**

```text
Based on your parameters, your estimated goal is [%1$.0f] [%2$s] of water. Your doctor can determine the exact goal for you.
```

**Target**

```text
Op basis van je gegevens is je geschatte doel [%1$.0f] [%2$s] water. Je arts kan het exacte doel voor je bepalen.
```

**Marked spans**

- start=0 length=12 group=3 rule=48122 fragment="Op basis van"
