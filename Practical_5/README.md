# Practical 5 - Compound Queries, Filtering and Relevance

A Python notebook practical that combines query clauses with `bool`, contrasts
scoring (`must`) against filtering (`filter`), controls relevance with `boost`
and `minimum_should_match`, and shows why `object` arrays give false positives
while `nested` queries keep the correlation.

## Objective

- `bool` with `must`, `filter`, `should`, `must_not`
- Combine term, range and full-text clauses in one query
- `minimum_should_match` on a set of `should` clauses
- Boost a preferred group with a positive `boost` value
- `nested` queries, `inner_hits` and the object-array false positive
- Scored vs constant-score evaluation, verified with the `_explain` API
- Ten documented requirements with requirement / query / expected / actual /
  explanation

## Files

| File | Description |
|------|-------------|
| `generate_data.py` | Deterministic generator (seed 42) for both datasets, including nested reviews. |
| `employees.json` | 120 employee records (84 active). |
| `products.json` | 60 product records with `reviews`, `reviews_flat` and `supplier`. |
| `practical_5.ipynb` | Main notebook: concept demos and the ten requirement queries, executed with outputs. |
| `README.md` | This file. |

Dependencies live in the shared `requirements.txt` at the repository root.

## Datasets

`employees` (120 documents) - same shape as Practical 4:

```json
{
  "employee_id": 101,
  "name": "Nikhil Gupta",
  "department": "Engineering",
  "designation": "Software Engineer",
  "salary": 36500,
  "city": "Chennai",
  "joining_date": "2020-09-30",
  "active": true,
  "email": "nikhil.gupta101@example.com"
}
```

`products` (60 documents) - adds nested reviews and a supplier object:

```json
{
  "product_id": "P001",
  "name": "Wireless Noise-Cancelling Headphones",
  "description": "Acme Wireless Noise-Cancelling Headphones ...",
  "brand": "Acme",
  "category": "Electronics",
  "price": 299.99,
  "available": false,
  "created_at": "2025-08-05",
  "reviews": [
    {"author": "alice", "rating": 5, "comment": "excellent quality and sound", "date": "2024-03-12"},
    {"author": "bob", "rating": 4, "comment": "good for the price", "date": "2024-06-02"},
    {"author": "carol", "rating": 3, "comment": "okay", "date": "2024-08-19"}
  ],
  "reviews_flat": [{"author": "alice", "rating": 5}, {"author": "bob", "rating": 4}],
  "supplier": {"name": "...", "country": "Germany", "lead_time_days": 12}
}
```

`reviews` is mapped as `nested`; `reviews_flat` is a plain `object` array used
to demonstrate the cross-element false positive (P002 has alice/2 and bob/5 and
wrongly matches the flat query).

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

Practical 5 shares the repository-level environment:

```powershell
cd "C:\D-Drive\Elastic Search Practicals"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m ipykernel install --user --name es --display-name "Python (ES Practicals)"
```

## How to run

```powershell
cd "C:\D-Drive\Elastic Search Practicals\Practical_5"
& "..\.venv\Scripts\python.exe" generate_data.py
& "..\.venv\Scripts\python.exe" -m nbconvert --to notebook --execute --inplace `
    --ExecutePreprocessor.kernel_name=es practical_5.ipynb
```

Or open `practical_5.ipynb` and select the `Python (ES Practicals)` kernel.
The notebook drops and recreates `employees` and `products` at the start, so it
is safe to re-run.

## Task map

| # | Requirement | Query shapes | Result |
|---|-------------|--------------|--------|
| 1 | Active employees in Mumbai | `term` + `term` in `must` | 10 |
| 2 | Engineering or Sales employees | `terms` in `should`, `minimum_should_match: 1` | 35 |
| 3 | Salary strictly between 50000 and 100000 | `range` (`gt`, `lt`) | 48 |
| 4 | Available Electronics products | `term` + `term` | 9 |
| 5 | Acme wireless products, 100-10000, created since 2023 | `match` + `term` + `range` + `range` | 2 |
| 6 | Products describing any of four keywords | four `should` (default matching) | 4 |
| 7 | At least two of those keywords | four `should` + `minimum_should_match: 2` | 2 |
| 8 | Prefer Home & Kitchen in `set` results | `must` + boosted `should` `term` | 5 (rows reordered) |
| 9 | One review by alice rated 4+ | flat `bool` (21, false positive) vs `nested` + `inner_hits` (9) | 21 vs 9 |
| 10 | Five-condition catalog query | `must` (scored) vs `filter` (unscored) | 3, scores > 0 vs 0 |

## What the notebook demonstrates

- `must` contributes to `_score`; identical clauses in `filter` return
  `_score` 0 and are cacheable.
- `minimum_should_match` turns a preference set into a hard requirement.
- A boosted `should` clause reorders results: without the boost the top hit is
  Sports (P022, 2.46); with a `boost: 5` on Home & Kitchen the three Home
  products jump to 10.97 / 10.97 / 10.74.
- The flat `reviews_flat` query returns 21 products because alice/2 and bob/5
  can be satisfied by different array elements; the `nested` query returns 9
  and P002 is excluded. `inner_hits` returns only the review that matched.
- `_explain` on P006 shows a real BM25 sum in `must` context versus a constant
  0 evaluation in `filter` context.

## Verification

The committed notebook was executed end-to-end with `nbconvert`:

- 30 cells (14 code, 16 markdown), every code cell has output
- 0 error outputs
- `employees` = 120 documents, `products` = 60 documents
- all ten requirements have exact-count assertions and appear in the summary
  table
- boost assertion checks the Home & Kitchen reorder against the unboosted run
- nested assertion checks 9 hits and non-empty `inner_hits`
- `_explain` assertion checks a positive score in `must` and 0 in `filter`

## Notes

- Use `filter` for business constraints and `must` only for clauses that should
  affect relevance; this keeps the query cache warm.
- When `must` is present, `minimum_should_match` defaults to 0, so `should`
  clauses only boost unless you raise it.
- `nested` queries are slower than flattened fields; only map as `nested` when
  correlations inside one array element matter.
- `boost` multiplies the clause score - it changes ranking, never the match set.
