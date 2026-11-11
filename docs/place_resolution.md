# Feature: Place resolution

The detection model finds **words** that may be places ("Tigurum"). This step decides **which real place** it is,
where it is, and which country it is in, so the map can use it.

```
"Tigurum"  ->  place id l587  ->  Zürich, Schweiz, 47.36667 8.55  ->  country code CH
 (model)       (editors' tags)     (official place list)             (country_codes.py)
```

## Result for each word
| Status | Meaning |
|---|---|
| `resolved` | One place, with coordinates and a country code |
| `no_country` | One place found, but no usable country |
| `ambiguous` | Several different places fit. A person must decide. We never guess. |
| `no_candidates` | Nothing usable |

## The four pieces
| File (in `backend/services/`) | Job |
|---|---|
| `country_codes.py` | "Schweiz" -> "CH". England and Scotland -> "GB". Continents and old empires return `None`. |
| `candidates.py` | Takes the candidate places of one word. Merges duplicates (same name and under 10 km apart), prefers the one with a country, and returns the result above. |
| `place_variants.py` | Builds the spelling dictionary from the Bullinger letters: the editors tagged words like `<placeName ref="l587">Tigurum</placeName>`. Keeps a count per pair. |
| `place_lookup.py` | Joins the dictionary with the official place list (`localities.xml`). |

## Run
```bash
# Check the project, because this step is already done by our dev team. you may not need to run it again.
git clone https://github.com/stazh/bullinger-korpus-tei ~/Desktop/bullinger-korpus-tei   # itb should be outside the project

cd backend
python -m services.place_variants ~/Desktop/bullinger-korpus-tei resources/place_variants.json
cp ~/Desktop/bullinger-korpus-tei/data/index/localities.xml resources/localities.xml
python -m services.place_lookup resources/place_variants.json resources/localities.xml place_mentions.jsonl
```
The last command prints one line per word and a count like `{'resolved': ..., 'no_candidates': ...}`.

## Test
```bash
cd backend
pytest tests/test_country_codes.py tests/test_candidates.py tests/test_place_variants.py tests/test_place_lookup.py -v
```
`test_country_codes.py` contains all 83 country values from the real place list, so a new value fails the test until it is handled.

## Results on the sample file (60 words)
- Before the lookup: 3 resolved (Basel, Straßburg, Zürich), 57 `no_candidates`.
- With the full corpus dictionary:

## Limits
- 192 of 3,077 places in the list have no coordinates (for example Dublin), so they stay `no_candidates`.
- 171 entries are countries or regions with no town name (for example France). They resolve with `place_level: "country"`.