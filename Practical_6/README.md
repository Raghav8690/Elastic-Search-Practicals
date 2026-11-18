# Practical 6 - Text Analysis, Synonyms, Autocomplete and Partial Search

A Python notebook practical that implements Elasticsearch **text analysis**:
built-in analyzer comparison, a custom lowercase + stop-word analyzer, business
synonyms, edge-ngram autocomplete, fragment search and case-insensitive exact
matching.

## Objective

- Inspect how `_analyze` tokenizes "Green Valley Residency in New Panvel" with
  the standard, simple, whitespace, stop, keyword and english analyzers
- Build a custom analyzer with `lowercase` and a stop-word filter
- Configure synonyms for apartment/flat, builder/developer and
  residence/residency, then prove the search behaviour
- Implement edge-ngram autocomplete while the user is typing
- Find a project from a fragment anywhere in its name
- Use a keyword **normalizer** for case-insensitive exact matching

## Files

| File | Description |
|------|-------------|
| `generate_data.py` | Deterministic generator (seed 42) for the project dataset. |
| `projects.json` | 50 real-estate project records. |
| `practical_6.ipynb` | Main notebook: six analysis tasks with printed evidence and assertions, executed with outputs. |
| `README.md` | This file. |

Dependencies live in the shared `requirements.txt` at the repository root.

## Dataset

`projects` (50 documents, 19 localities, 29 apartments, 11 residences, 5
villas, 4 row houses, 1 plot):

```json
{
  "project_id": "PJ001",
  "name": "Green Valley Residency",
  "description": "Green Valley Residency in New Panvel is a 2 BHK and 3 BHK homes apartment project by Greenfield Developers. It offers clubhouse, gym, swimming pool. Possession by 2024-12. RERA approved.",
  "builder": "Greenfield Developers",
  "locality": "New Panvel",
  "city": "Navi Mumbai",
  "property_type": "Apartment",
  "status": "Ready to Move",
  "price_min": 6500000,
  "price_max": 9500000,
  "bhk": ["2 BHK", "3 BHK"],
  "amenities": ["clubhouse", "gym", "swimming pool"],
  "possession_date": "2024-12-15",
  "rera_approved": true,
  "rating": 4.5
}
```

The vocabulary is deliberate: descriptions use apartment/flat,
builder/developer and residence/residency so the synonym analyzer can be
tested, and the names are built from a small set of prefixes and suffixes so
autocomplete and fragment searches have overlapping candidates.

## Index design

A single `projects` index holds every analyzer:

| Element | Definition |
|---------|------------|
| `case_insensitive` normalizer | `lowercase` + `asciifolding` |
| `lower_stop` analyzer | standard tokenizer, lowercase, custom stop words |
| `synonym_analyzer` | standard tokenizer, lowercase, business synonym filter |
| `autocomplete_index` | standard tokenizer, lowercase, `edge_ngram` 2-15 |
| `autocomplete_search` | standard tokenizer, lowercase (no n-grams) |
| `ngram_index` | standard tokenizer, lowercase, `ngram` 3-4 |

Sub-fields: `name.keyword`, `name.autocomplete`, `name.ngram`,
`description.clean`, `description.syn`, `locality.raw`. The raw locality field
is the control for the normalizer task.

## Prerequisites

1. Elasticsearch + Kibana running from `Practical_1`:

   ```powershell
   cd ..\Practical_1
   docker compose up -d
   ```

   Wait until `http://localhost:9200` responds.
2. Python 3.10+ (tested with 3.14).

The default endpoint is `http://127.0.0.1:9200` (`ES_URL` in the setup cell).

## Virtual environment

Practical 6 shares the repository-level environment:

```powershell
cd "C:\D-Drive\Elastic Search Practicals"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m ipykernel install --user --name es --display-name "Python (ES Practicals)"
```

## How to run

```powershell
cd "C:\D-Drive\Elastic Search Practicals\Practical_6"
& "..\.venv\Scripts\python.exe" generate_data.py
& "..\.venv\Scripts\python.exe" -m nbconvert --to notebook --execute --inplace `
    --ExecutePreprocessor.kernel_name=es practical_6.ipynb
```

Or open `practical_6.ipynb` and select the `Python (ES Practicals)` kernel. The
notebook drops and recreates `projects` at the start, so it is safe to re-run.

## Task map

| # | Task | Implementation | Observed result |
|---|------|----------------|-----------------|
| 1 | Analyze text | `_analyze` with seven analyzers | standard/simple/whitespace = 6 tokens, stop = 5, keyword = 1, english = 5 (`vallei`, `resid`), lower_stop = 5 |
| 2 | Custom analyzer | standard + lowercase + stop | sample = green/valley/residency/new/panvel; `in` query = 0 hits on clean field vs 50 on plain field |
| 3 | Synonyms | `synonym` filter with 3 groups | apartment=flat (29), builder=developer (31), residence=residency (14); `flat` baseline 9 vs 29 on synonym field |
| 4 | Autocomplete | `edge_ngram` 2-15 + search analyzer | `gre`=9, `sky`=3, `palm`=4, `resi`=10 prefixes; `green val` phrase = PJ001 |
| 5 | Partial search | `ngram` 3-4 + wildcard cross-check | `alley`: edge=0, ngram=1, wildcard=1; `valley`: ngram=1, wildcard=1 |
| 6 | Case-insensitive | keyword normalizer | `New Panvel`/`new panvel`/`NEW PANVEL` all match 4; raw matches only the canonical case |

### Task 5 nuance

N-gram AND matching is fast but not an exact substring guarantee. The query
`green` returns 10 projects while the wildcard returns 9: PJ007
("Sea Breeze Apartments") supplies the `ree`/`reen` grams from "Breeze". The
notebook prints this false positive and uses wildcard as the precise fallback.

## Verification

The committed notebook was executed end-to-end with `nbconvert`:

- 21 cells (11 code, 10 markdown), every code cell has output
- 0 error outputs
- `projects` = 50 documents
- all seven analyzer outputs asserted for the sample sentence
- synonym groups asserted equal to the expected description sets computed from
  the JSON
- autocomplete prefix sets asserted against the generator data
- partial-search sets asserted against both n-gram and wildcard results
- normalizer asserted across three case variants plus the raw control field

## Notes

- Analysis runs at index time and at query time; the field analyzer and search
  analyzer must agree or matches silently disappear.
- A custom `stop` filter **replaces** the default stop-word list; list every
  word that should be dropped.
- Use `synonym` for index-time single-word equivalence and `synonym_graph` for
  multi-word, query-time rules.
- `edge_ngram` covers prefixes only; `ngram` covers fragments anywhere in a
  token and makes the index larger.
- `normalizer` applies to `keyword` fields only and keeps exact whole-value
  matching, unlike an analyzer on a `text` field.
- Changing an analyzer requires reindexing; the notebook recreates the index
  each run for that reason.
