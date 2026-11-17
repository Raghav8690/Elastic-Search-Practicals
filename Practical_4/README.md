# Practical 4 - Elasticsearch Query DSL

A Python notebook practical that implements the full Elasticsearch **Query
DSL** - basic, range, full-text, advanced and pagination/sorting queries - and
then solves **32 documented business queries** against employee and product
datasets.

## Objective

Master the Query DSL and implement different types of searches:

- Basic: `match_all`, `match`, `term`, `terms`, `exists`, `ids`
- Range: price, salary and date ranges
- Full-text: `match_phrase`, `multi_match`, `query_string`,
  `simple_query_string`
- Advanced: `fuzzy`, `prefix`, `wildcard`, `regexp`
- Pagination and sorting, source filtering, highlighting
- 30+ additional business queries with requirement / query / expected / actual /
  explanation

## Files

| File | Description |
|------|-------------|
| `generate_data.py` | Deterministic generator (seed 42) for both datasets. |
| `employees.json` | 120 employee records. |
| `products.json` | 60 product records. |
| `practical_4.ipynb` | Main notebook: all tasks and the 32-query assignment, executed with outputs. |
| `requirements.txt` | Python dependencies. |
| `README.md` | This file. |

## Datasets

`employees` (120 documents):

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

`email` (~80%) and `bonus` (~50%) are intentionally sparse so `exists`
queries are meaningful.

`products` (60 documents):

```json
{
  "product_id": "P001",
  "name": "Wireless Noise-Cancelling Headphones",
  "description": "Acme Wireless Noise-Cancelling Headphones with active noise cancellation and premium sound. Category: Electronics, type: Headphones.",
  "brand": "Acme",
  "category": "Electronics",
  "subcategory": "Headphones",
  "price": 299.99,
  "stock": 0,
  "rating": 2.6,
  "tags": ["wireless", "audio", "noise-cancelling"],
  "available": false,
  "created_at": "2025-08-05",
  "sku": "SKU-ELEC-0001",
  "warranty_months": 12
}
```

## Prerequisites

1. Elasticsearch + Kibana running from `Practical_1`:
   ```powershell
   cd ..\Practical_1
   docker compose up -d
   ```
   Wait until `http://localhost:9200` responds.
2. Python 3.10+ (tested with 3.14).

The client uses `http://127.0.0.1:9200` by default (`ES_URL` is defined in the
notebook setup cell if you need to change it).

## Virtual environment

```powershell
cd "C:\D-Drive\Elastic Search Practicals\Practical_4"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## How to run

```powershell
cd "C:\D-Drive\Elastic Search Practicals\Practical_4"
.\.venv\Scripts\Activate.ps1
python generate_data.py          # writes employees.json + products.json
python -m ipykernel install --user --name p4 --display-name "Python (Practical_4)"
# open practical_4.ipynb and select the "Python (Practical_4)" kernel
```

Or execute headlessly (embeds all outputs):

```powershell
python -m nbconvert --to notebook --execute --inplace `
    --ExecutePreprocessor.kernel_name=p4 practical_4.ipynb
```

The notebook drops and recreates the `employees` and `products` indices at the
start, so it is safe to re-run. **Note:** Practical 4 owns the canonical
`employees` and `products` index names; Practical 2 / 3 recreate their own
copies when their notebooks run.

## Task map

| # | Task | Query / API | Index | Result |
|---|------|-------------|-------|--------|
| 1 | All documents | `match_all` | employees | 120 |
| 2 | Match analyzed text | `match`, `operator: and` | employees, products | 4, 1 |
| 3 | Exact term | `term` (keyword, text negative case, boolean) | employees | 18, 0, 84 |
| 4 | Multiple exact values | `terms` (department, city, tags) | both | 35, 53, 4 |
| 5 | Documents with a field | `exists` (email, bonus, missing field) | employees | 91, 52, 0 |
| 6 | Fetch by ID | `ids` | employees | 2 |
| 7 | Price range | `range` 500-3000 | products | 33 |
| 8 | Salary above threshold | `range` `gte` 100000 | employees | 40 |
| 9 | Date ranges | `range` on `created_at`, `joining_date` | both | 21, 16 |
| 10 | Exact phrase | `match_phrase` | products | 2 |
| 11 | Multiple fields | `multi_match` (`best_fields`) | products | 3 |
| 12 | Lucene expression | `query_string` | employees | 5 |
| 13 | Forgiving user input | `simple_query_string` (`+engineer +(-manager)`) | employees | 21 |
| 14 | Typo tolerance | `fuzzy` (`AUTO`) | both | 4, 1 |
| 15 | Starts with | `prefix` (city, name, SKU) | both | 14, 2, 10 |
| 16 | Wildcards | `wildcard` (`case_insensitive`) | both | 24, 2 |
| 17 | Regular expressions | `regexp` (city, email, SKU) | both | 17, 4, 20 |
| 18 | Sort by price | `sort` asc/desc | products | 60 total, 5 shown |
| 19 | First 10 records | `size: 10` | products | 10 returned |
| 20 | Pagination | `from` + `size` (3 pages of 5) | employees | 15 unique IDs |
| 21 | Source filtering | `source_includes`, `source_excludes`, `source=False` | both | projected |
| 22 | Highlighting | `highlight` | products | `<em>` fragments |

## Assignment query index

All 32 queries are documented in the notebook (requirement, query JSON,
expected output, actual output, explanation). "Matches" is the total number of
matching documents; paged queries return fewer hits.

| Query | Domain | Requirement | Matches |
|-------|--------|-------------|---------|
| A1 | Employee filtering | Active employees in Bengaluru | 9 |
| A2 | Employee filtering | Engineers earning 80000-150000 | 7 |
| A3 | Employee filtering | Active employees who joined after 2023-01-01 | 36 |
| A4 | Employee filtering | Mumbai/Pune/Delhi employees earning below 60000 | 20 |
| A5 | Employee filtering | Senior employees earning at least 90000 | 4 |
| A6 | Employee filtering | Active employees with bonus above 20000 | 14 |
| B1 | Product catalog | Electronics/Home & Kitchen priced 1000-20000 | 11 |
| B2 | Product catalog | Best-rated in-stock products (top 5 by rating) | 20 |
| B3 | Product catalog | Out-of-stock products | 5 |
| B4 | Product catalog | Products tagged wireless or bluetooth | 4 |
| B5 | Product catalog | Books priced under 1000 | 7 |
| B6 | Product catalog | Warranty >= 24 months and price > 5000 | 9 |
| C1 | Full-text search | Product name contains phrase noise cancelling headphones | 1 |
| C2 | Full-text search | bluetooth speaker with both words required | 1 |
| C3 | Full-text search | Electronics/Beauty 1000-10000 with rating >= 4.0 | 3 |
| C4 | Full-text search | simple_query_string `+wireless +headphones` | 1 |
| C5 | Full-text search | 75% of stainless steel water bottle | 1 |
| D1 | Pattern matching | Misspelled brand Nimbuss | 7 |
| D2 | Pattern matching | Misspelled word headphnes | 1 |
| D3 | Pattern matching | SKU prefix SKU-ELEC | 10 |
| D4 | Pattern matching | Name contains Bottle (wildcard) | 2 |
| D5 | Pattern matching | City regexp Mum.* | 17 |
| E1 | Sorting & pagination | Top 3 most expensive products | 60 total, 3 shown |
| E2 | Sorting & pagination | Salary ranking page 2 (11-20) | 120 total, 10 shown |
| E3 | Sorting & pagination | 5 newest products, projected fields | 60 total, 5 shown |
| E4 | Sorting & pagination | 5 earliest hires without email/bonus/salary | 120 total, 5 shown |
| E5 | Sorting & pagination | Highlight wireless in descriptions | 2 |
| F1 | Combined rules | Active Engineering/Finance >= 80000 in metro cities | 6 |
| F2 | Combined rules | Available Electronics/Beauty rated 4.5+, price <= 5000 | 3 |
| F3 | Combined rules | Active managers earning more than 90000 | 27 |
| F4 | Combined rules | In-stock under 500 outside Books/Fashion | 5 |
| F5 | Combined rules | 2024 hires with bonus, active, not HR | 5 |

Two extra **negative tests** (N1, N2) demonstrate the classic `term` mistakes:
a capitalized term on an analyzed `text` field and a lowercase term on a
case-sensitive `keyword` field - both correctly return 0 hits.

## Verification

The committed notebook was executed end-to-end with `nbconvert`:

- 67 cells (32 code, 35 markdown), every code cell has output
- 0 error outputs
- `employees` = 120 documents, `products` = 60 documents
- all 22 task queries plus 32 assignment queries executed
- exact-count assertions passed for every deterministic query
- pagination pages verified contiguous and non-overlapping
- sort order, source projections and highlight fragments asserted in code

## Notes

- `from` is the reserved Python keyword, so the client parameter is `from_`.
- The Elasticsearch 9 Python client exposes source filtering as
  `source_includes` / `source_excludes` (and `source=False`), not `_source`.
- `fuzzy`, `regexp` and leading `wildcard` queries are expensive; prefer
  `prefix`, `match` or n-gram strategies for large indices.
- Deep pagination beyond `index.max_result_window` (10 000) requires
  `search_after`.
- Queries that only filter business constraints use `bool.filter` (no scoring,
  cacheable); full-text clauses stay in `must` so relevance is preserved.
