# Practical 7 - Relevance, BM25, Boosting and Profiling

A Python notebook practical that measures and shapes Elasticsearch relevance:
BM25 scores, the Explain API, field boosts, `function_score` and the Profile
API, ending in a documented relevance-based search system.

## Objective

1. Search for a common keyword (`palm`).
2. Observe `_score` on the returned documents.
3. Compare scores across documents and signals.
4. Inspect the score with the Explain API.
5. Boost project-name matches.
6. Give different importance to different fields.
7. Implement `function_score` with business signals.
8. Compare rankings before and after boosting.
9. Investigate execution with the Profile API.

**Assignment:** exact project-name matches rank highest, partial name matches
lower, builder-name matches moderately, and location matches contribute to the
ranking - with the ranking differences documented.

## Files

| File | Description |
|------|-------------|
| `generate_data.py` | Deterministic generator (seed 42) for 60 projects. |
| `projects.json` | 60 real-estate records with ranking/popularity fields. |
| `practical_7.ipynb` | Main notebook: Tasks 1-9, assignment, BM25 appendix. |
| `README.md` | This file. |

Dependencies live in the shared `requirements.txt` at the repository root.

## Dataset

`projects` (60 documents, 39 apartments, 12 residences, 5 villas, 3 row
houses, 1 plot):

```json
{
  "project_id": "PJ011",
  "name": "Palm Beach",
  "description": "Palm Beach in Palm Beach Road, Navi Mumbai is a 2 BHK and 3 BHK homes apartment project by Palm Beach Developers. Amenities include clubhouse, swimming pool, 24x7 security. Possession by 2024-08. RERA approved. Rated 4.8 from 210 reviews.",
  "builder": "Palm Beach Developers",
  "locality": "Palm Beach Road",
  "city": "Navi Mumbai",
  "property_type": "Apartment",
  "status": "Ready to Move",
  "price_min": 11000000,
  "price_max": 16000000,
  "bhk": ["2 BHK", "3 BHK"],
  "amenities": ["clubhouse", "swimming pool", "24x7 security"],
  "possession_date": "2024-08-31",
  "created_at": "2024-04-10",
  "rera_approved": true,
  "rating": 4.8,
  "reviews_count": 210,
  "views": 52000,
  "featured": true
}
```

### Controlled signal cluster for `"palm beach"`

| ID | Name | Builder | Locality | Signal |
|----|------|---------|----------|--------|
| PJ011 | Palm Beach | Palm Beach Developers | Palm Beach Road | exact name + builder + location |
| PJ012 | Palm Beach Residences | Palm Beach Developers | Palm Beach Road | partial name + builder + location |
| PJ013 | Palm Beach Enclave | Skyline Builders | Palm Beach Road | partial name + location |
| PJ014 | Royal Palm Grove | Palm Estates | Palm Beach Road | location |
| PJ015 | Crescent Bay | Palm Beach Developers | Nerul | builder |

PJ016 (`Skyline`, builder Palm Estates) and PJ018 (`Crescent Bay Vista`,
builder Skyline Builders) isolate the name-vs-builder experiment. "Palm Beach
Road" and "Palm Beach Developers" are reserved for these fixtures, and no
generated project is named Skyline.

## Index design

- `name` - `text` plus `name.keyword` with a lowercase/asciifolding
  **normalizer** for case-insensitive exact matching
- `builder`, `locality`, `city` - `text` plus `keyword` sub-fields
- `description` - `text`
- `rating`, `reviews_count`, `views`, `featured`, `created_at` - popularity and
  freshness signals for `function_score`
- default **BM25** similarity (`k1=1.2`, `b=0.75`)

## Prerequisites

1. Elasticsearch + Kibana running from `Practical_1`:

   ```powershell
   cd ..\Practical_1
   docker compose up -d
   ```

   Wait until `http://localhost:9200` responds.
2. Python 3.10+ (tested with 3.14).

The notebook uses `http://127.0.0.1:9200` by default (`ES_URL` in setup).

## Virtual environment

Practical 7 shares the repository-level environment:

```powershell
cd "C:\D-Drive\Elastic Search Practicals"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m ipykernel install --user --name es --display-name "Python (ES Practicals)"
```

## How to run

```powershell
cd "C:\D-Drive\Elastic Search Practicals\Practical_7"
& "..\.venv\Scripts\python.exe" generate_data.py
& "..\.venv\Scripts\python.exe" -m nbconvert --to notebook --execute --inplace `
    --ExecutePreprocessor.kernel_name=es practical_7.ipynb
```

Or open `practical_7.ipynb` and select the `Python (ES Practicals)` kernel. The
notebook drops and recreates `projects` at the start, so it is safe to re-run.

## Results

### Task 1 - common keyword `palm`

14 matches. Top score **2.2261**; scores descend, several documents tie
(PJ011, PJ012 and PJ014 at 2.2261) even though their signal mix differs.

### Task 2 - `_score` observation

`multi_match("palm beach")` also returns 14 matches and **ties the exact name
PJ011 and the partial name PJ012 at 5.9543**. The shared builder/locality
matches dominate, and BM25's length norm does not encode "exact name is
better". That tie motivates the field boosts.

### Task 3 - score comparison by signal

Single-field probes (`match` on one field at a time):

| Probe | Top result | Score |
|-------|-----------|-------|
| `name: "palm beach"` | PJ011 Palm Beach | 5.0007 |
| `name: "palm beach"` | PJ012 / PJ013 (partial) | 4.1881 |
| `builder: "palm beach"` | PJ011 / PJ012 / PJ015 | 3.8665 |
| `locality: "palm beach"` | PJ011-PJ014 | 3.2593 |

The boosted signal query then produces:

```
PJ011 170.6335  exact-name + builder + location + description
PJ012  52.9702  partial-name + builder + location + description
PJ013  40.9871  partial-name + location + description
PJ015  13.4704  builder + description
PJ014   6.7597  location + description
```

### Task 4 - Explain API

`_explain` for PJ011 returns the same `170.6335` and exposes `idf`, `tf`,
`dl`, `avgdl` and boosted leaves. PJ012 (`52.9702`) and PJ015 (`13.4704`)
show the smaller signal mix. The notebook asserts the values equal the search
scores and that all four BM25 fields are present.

### Task 5 - name boost

`name^8` breaks the exact/partial tie and pushes the location-only document
down:

| Document | Baseline | `name^8` |
|----------|----------|----------|
| PJ011 Palm Beach (exact) | 5.9543 | 40.0056 |
| PJ012 Palm Beach Residences (partial) | 5.9543 | 33.5045 |
| PJ014 Royal Palm Grove (location) | rank 4 | rank 8 |

The match set is unchanged (14 documents); only the ranking changes.

### Task 6 - field importance

Query `skyline`:

- `name^10, builder^1`: PJ016 `Skyline` (name-only) is first, score 36.7235.
- `name^0.1, builder^10`: the top hit is PJ002 `Skyline Heights` by **Skyline
  Builders** (26.6693; PJ013, PJ017 and PJ018 tie on the builder field), and
  PJ016 falls from rank 1 to 5.

Field weight decides which field drives the ranking.

### Task 7 - function_score

Configuration: `rating` (`factor=2.0`, `log1p`), `views` (`factor=0.005`,
`log1p`), a `gauss` decay on `created_at` (origin 2025-01-01, scale 365d,
offset 30d, decay 0.5) and a `featured` filter weight of 8; `score_mode=sum`,
`boost_mode=sum`.

| Document | Relevance | + function_score |
|----------|-----------|------------------|
| PJ011 Palm Beach | 170.6335 | 182.8239 |
| PJ012 Palm Beach Residences | 52.9702 | 57.0530 |
| PJ013 Palm Beach Enclave | 40.9871 | 44.3851 |
| PJ014 Royal Palm Grove | 6.7597 (rank 5) | 19.5289 (rank 4) |
| PJ015 Crescent Bay | 13.4704 (rank 4) | 17.0140 (rank 5) |

Popularity promotes the featured, highly viewed PJ014 above the builder-only
PJ015; the exact name remains first.

### Task 8 - before and after

| ID | baseline | `name^8` | relevance | relevance + function |
|----|----------|----------|-----------|----------------------|
| PJ011 | 1 | 1 | 1 | 1 |
| PJ012 | 2 | 2 | 2 | 2 |
| PJ013 | 3 | 3 | 3 | 3 |
| PJ015 | 5 | 9 | 4 | 5 |
| PJ014 | 4 | 8 | 5 | 4 |
| PJ010 | 6 | 4 | - | - |
| PJ003 | 9 | 7 | - | - |

`-` means the document does not match the phrase-based signal query. The
lower-rank swap between PJ014 and PJ015 is the documented popularity effect.

### Task 9 - Profile API

- Baseline `multi_match`: top query type `DisjunctionMaxQuery`, children
  `BooleanQuery` and `TermQuery`; timing breakdown includes
  `create_weight`, `build_scorer`, `next_doc`, `advance`, `score`, `match`.
- Relevance + `function_score`: top query type `FunctionScoreQuery`, with
  `BoostQuery`, `PhraseQuery` and `TermQuery` children.

Timings are machine-specific (the run reported roughly 4.9 ms vs 1.7 ms);
the notebook asserts the query types and the presence of the timing breakdown,
not exact durations.

### Assignment ranking

| Rank | ID | Name | Signals | Score |
|------|----|------|---------|-------|
| 1 | PJ011 | Palm Beach | exact name + builder + location + description | 170.6335 |
| 2 | PJ012 | Palm Beach Residences | partial name + builder + location + description | 52.9702 |
| 3 | PJ013 | Palm Beach Enclave | partial name + location + description | 40.9871 |
| 4 | PJ015 | Crescent Bay | builder + description | 13.4704 |
| 5 | PJ014 | Royal Palm Grove | location + description | 6.7597 |

With `popularity=True`, exact name stays #1 and PJ014 moves to #4.

Probe queries:

| Probe | Query | Result |
|-------|-------|--------|
| Exact name | `palm beach` | PJ011 first |
| Partial name | `palm beach enclave` | PJ013 first |
| Builder | `palm beach developers` | PJ011, PJ012, PJ015 tie at 16.7955 |
| Location | `palm beach road` | PJ011-PJ014, all in Palm Beach Road |

## BM25 summary

```
idf(t)   = ln(1 + (N - n(t) + 0.5) / (n(t) + 0.5))

tfNorm   = tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl))

score(t) = idf(t) * tfNorm * boost
```

- `N` = 60 documents, `n(t)` = documents containing the term.
- `tf` = term frequency, `dl`/`avgdl` = field length and average field length.
- `k1=1.2` (term-frequency saturation) and `b=0.75` (length normalisation) are
  the Elasticsearch defaults used here.
- Boosts multiply clause scores; `function_score` then adds or multiplies
  business signals after BM25.

## Verification

The committed notebook was executed end-to-end with `nbconvert`:

- 31 cells (16 code, 15 markdown), every code cell has output
- 0 error outputs
- `projects` = 60 documents
- all nine task headings present plus assignment and BM25 appendix
- score ordering, tie, boost, field-weight flip, function-score promotion,
  explain components and profile query types are asserted in code
- assignment asserts exact > partial > builder > location on the fixture
  cluster

## Notes

- Raw BM25 has no business rules; exact and partial names can tie when shared
  fields dominate. Encode priorities with explicit clauses and boosts.
- `match_phrase` on the signal fields makes the assignment stricter (5 matches)
  than the term-based baseline (14 matches); that is intentional - "palm" alone
  is not "palm beach".
- Use `function_score` for signals BM25 cannot see (rating, views, freshness,
  featured). Keep the weights modest so an exact name still wins.
- `_explain` inspects one document and one query; `_profile` inspects the whole
  execution tree. Profile adds overhead, so do not leave it on in production.
- The exact-name clause uses a keyword normalizer, so it is case-insensitive
  without tokenizing the value.
- Changing boosts or similarity settings does not require reindexing for
  boosts; changing analyzers or normalizers does.
