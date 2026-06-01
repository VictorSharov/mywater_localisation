# Lokalise QA Validation Batches

Source snapshot: `/Users/viktor/git/mywater_localisation/qa_issues.ndjson`

Generated with:

```sh
python3 loc_qa_issues_extract.py --all --out-dir /tmp/lokalise_qa_batches
```

Use one file per validation agent/language. Each entry includes:

- key name and platforms
- QA issue category from Lokalise
- translator context
- `en` source
- `ru` parity reference
- target-language value to judge

Task for the validation agent:

1. Decide whether each Lokalise QA flag is a real issue or a false positive.
2. For real issues, propose the corrected target value only.
3. Preserve placeholders, brand names, hashtags, register, and meaning.
4. Do not mark translations verified; fixes applied later remain `unverified`.

Batch counts:

```text
pt_BR  380
nl     353
ar     203
it     182
de     143
da     124
es     124
pl     111
sv      90
en      80
fr      78
ja      50
ru      38
zh_CN   21
ko      11
nb       3
hi       2
vi       2
id       1
ms       1
tr       1
```

HTML-derived span export:

`/tmp/lokalise_qa_export`

That export contains exact UI spans for the rows present in the saved DOM, but the saved HTML only contains 5 rendered keys while the page declares 633 keys. Use it only as auxiliary evidence, not as the complete source.
