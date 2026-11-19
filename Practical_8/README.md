# Practical 8 — Aggregations and the Analytics Report

Hands-on Elasticsearch practical covering bucket aggregations, metric aggregations,
nested data, filtered aggregations and a 42-row analytics report.

**Environment**

- Elasticsearch 9.2.0 at `http://127.0.0.1:9200`
- Kibana 9.2.0 at `http://127.0.0.1:5601`
- Python client `elasticsearch 9.5.1`, kernel `es`

## Files

| File | Purpose |
|---|---|
| `generate_data.py` | Deterministic dataset generator (seed 42) |
| `products.json` | 72 products across 12 categories, with nested reviews |
| `employees.json` | 120 employees across 7 departments and 8 cities |
| `practical_8.ipynb` | Executed notebook for Tasks 1–10 plus the assignment |
| `aggregation_report.json` | Machine-readable analytics report (42 aggregations) |
| `README.md` | This summary |

## Setup

```powershell
cd "C:\D-Drive\Elastic Search Practicals\Practical_8"
..\.venv\Scripts\python.exe generate_data.py
..\.venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace `
  --ExecutePreprocessor.kernel_name=es --ExecutePreprocessor.timeout=180 practical_8.ipynb
```

The notebook drops and recreates the `products` and `employees` indices, bulk-indexes both
files, and writes `aggregation_report.json` as a reproducible artefact.

## Dataset

| Dataset | Count | Details |
|---|---:|---|
| Products | 72 | 12 categories × 6 products, 12 brands, prices 9.50–78,999.00, stock 0–200 |
| Reviews | 181 | 1–4 nested reviews per product, 20 authors, ratings 1–5 |
| Employees | 120 | 7 departments, 8 cities, salary 35,000–160,000, 52 with `bonus` |

Products are spread over 30 of the 36 months in 2023–2025, leaving six deliberately empty
months (`2023-02`, `2023-07`, `2024-01`, `2024-08`, `2025-03`, `2025-09`).

`reviews` is mapped as `nested`:

```json
"reviews": {
  "type": "nested",
  "properties": {
    "author": {"type": "keyword"},
    "rating": {"type": "float"},
    "comment": {"type": "text"},
    "date": {"type": "date"}
  }
}
```

All aggregation fields (`category`, `brand`, `city`, `department`, `author`, ...) are mapped
as `keyword`, numeric fields as `float`/`integer`, and dates as `date`.

## Task results

### 1. Count products by category

`terms` on `category`, `size: 20`.

| Category | Products |
|---|---:|
| Automotive | 6 |
| Beauty | 6 |
| Books | 6 |
| Electronics | 6 |
| Fashion | 6 |
| Garden | 6 |
| Grocery | 6 |
| Home & Kitchen | 6 |
| Office | 6 |
| Pet Supplies | 6 |
| Sports | 6 |
| Toys | 6 |
| **Total** | **72** |

### 2. Average product price

`avg` on `price` = **5,112.5067** (matches the Python mean).

### 3. Maximum and minimum price

| Metric | Value |
|---|---:|
| `min` price | 9.50 |
| `max` price | 78,999.00 |
| `stats.count` | 72 |
| `stats.avg` | 5,112.5067 |

### 4. Total inventory

`sum` on `stock` = **5,753 units** across 72 products (66 in stock, 6 out of stock).

### 5. Top 10 product categories

`terms` with `size: 10`. All 12 categories contain 6 products, so the default tie-break
(`doc_count` descending, then key ascending) returns the first ten names alphabetically:

| Rank | Category | Products |
|---:|---|---:|
| 1 | Automotive | 6 |
| 2 | Beauty | 6 |
| 3 | Books | 6 |
| 4 | Electronics | 6 |
| 5 | Fashion | 6 |
| 6 | Garden | 6 |
| 7 | Grocery | 6 |
| 8 | Home & Kitchen | 6 |
| 9 | Office | 6 |
| 10 | Pet Supplies | 6 |

`sum_other_doc_count` = **12** (Sports and Toys are outside the top ten).

### 6. Products created each month

`date_histogram` with `calendar_interval: month`, `format: yyyy-MM`,
`min_doc_count: 0` and `extended_bounds` from `2023-01` to `2025-12`.

- 36 monthly buckets, 72 documents total.
- Six zero buckets: `2023-02`, `2023-07`, `2024-01`, `2024-08`, `2025-03`, `2025-09`.
- The sub-aggregation `avg_price` reports the monthly average price per bucket.

### 7. Average salary by employee department

| Department | Employees | Average salary |
|---|---:|---:|
| Engineering | 18 | 83,138.89 |
| Finance | 17 | 73,382.35 |
| HR | 17 | 76,147.06 |
| Marketing | 17 | 67,705.88 |
| Operations | 17 | 79,147.06 |
| Sales | 17 | 90,235.29 |
| Support | 17 | 103,029.41 |

### 8. Unique employees by city

`cardinality` on `employee_id` with `precision_threshold: 1000`.

| City | Employees | Unique (`cardinality`) |
|---|---:|---:|
| Pune | 22 | 22 |
| Kolkata | 18 | 18 |
| Mumbai | 17 | 17 |
| Ahmedabad | 14 | 14 |
| Bengaluru | 14 | 14 |
| Delhi | 14 | 14 |
| Chennai | 12 | 12 |
| Hyderabad | 9 | 9 |

Cardinality equals `doc_count` because `employee_id` is unique per document; cardinality is
approximate in general and becomes exact at this scale with the raised threshold.

### 9. Nested aggregations

| Metric | Value |
|---|---:|
| Nested review documents | 181 |
| Average review rating | 2.9392 |
| Maximum review rating | 5.0 |
| Parent products (`reverse_nested`) | 72 |

The `authors` terms aggregation returns 20 authors whose review counts sum to 181;
`products_with_author` uses `reverse_nested` to count parent products per author (for example
`dave`: 19 reviews from 19 products; `trent`: 12 reviews from 11 products).

### 10. Aggregations with filters

**Single `filter` bucket**

| Metric | Value |
|---|---:|
| Available products | 66 |
| Average available price | 4,903.13 |
| Total stock (available) | 5,753 |

**`filters` buckets**

| Tier | Price range | Products | Avg rating |
|---|---|---:|---:|
| budget | < 1,000 | 25 | 3.65 |
| mid | 1,000–9,999.99 | 39 | 3.72 |
| premium | ≥ 10,000 | 8 | 3.62 |
| **Total** | | **72** | |

**`global` comparison:** global average price 5,112.51 vs available-only 4,903.13
(difference 209.38).

## Assignment — analytics report

`aggregation_report.json` contains **42 aggregation instances** across **19 distinct
aggregation types**: `terms`, `avg`, `sum`, `min`, `max`, `stats`, `extended_stats`,
`value_count`, `cardinality`, `percentiles`, `date_histogram`, `histogram`, `range`,
`filters`, `filter`, `global`, `missing`, `nested`, `reverse_nested`.

| # | Aggregation | Index | Kind | Type | Value |
|---:|---|---|---|---|---|
| 1 | `categories` | products | bucket | `terms` | 12 buckets / 72 docs / top Automotive=6 |
| 2 | `top_categories` | products | bucket | `terms` | 10 buckets / 60 docs / top Automotive=6 |
| 3 | `average_price` | products | metric | `avg` | 5,112.5067 |
| 4 | `minimum_price` | products | metric | `min` | 9.5000 |
| 5 | `maximum_price` | products | metric | `max` | 78,999.0000 |
| 6 | `price_stats` | products | metric | `stats` | avg 5,112.51, min 9.50, max 78,999.00 |
| 7 | `price_percentiles` | products | metric | `percentiles` | p25 786.5, p50 1,649, p75 4,124, p90 11,699, p95 21,699 |
| 8 | `total_inventory` | products | metric | `sum` | 5,753 |
| 9 | `product_count` | products | metric | `value_count` | 72 |
| 10 | `monthly_created` | products | bucket | `date_histogram` | 36 buckets / 72 docs |
| 11 | `brands` | products | bucket | `terms` | 12 buckets / 72 docs / top Acme=6 |
| 12 | `price_histogram` | products | bucket | `histogram` | 16 buckets / 72 docs |
| 13 | `price_ranges` | products | bucket | `range` | 3 buckets / 72 docs |
| 14 | `price_tiers` | products | bucket | `filters` | 3 buckets / 72 docs |
| 15 | `rating_extended` | products | metric | `extended_stats` | avg 3.69, min 2.50, max 5.00 |
| 16 | `available_only` | products | bucket | `filter` | 66 docs |
| 17 | `available_avg_price` | products | metric | `avg` | 4,903.1285 |
| 18 | `stock_zero` | products | bucket | `filter` | 6 docs |
| 19 | `global_all` | products | bucket | `global` | 72 docs |
| 20 | `global_avg_price` | products | metric | `avg` | 5,112.5067 |
| 21 | `supplier_countries` | products | bucket | `terms` | 6 buckets / 72 docs / top CN=12 |
| 22 | `price_by_category` | products | bucket | `terms` | 12 buckets / 72 docs |
| 23 | `reviews_nested` | products | bucket | `nested` | 181 docs |
| 24 | `review_parent_products` | products | bucket | `reverse_nested` | 72 docs |
| 25 | `avg_review_rating` | products | metric | `avg` | 2.9392 |
| 26 | `review_authors` | products | bucket | `terms` | 20 buckets / 181 docs / top dave=19 |
| 27 | `salary_by_department` | employees | bucket | `terms` | 7 buckets / 120 docs |
| 28 | `avg_salary_engineering` | employees | metric | `avg` | 83,138.8889 |
| 29 | `avg_salary_finance` | employees | metric | `avg` | 73,382.3529 |
| 30 | `avg_salary_hr` | employees | metric | `avg` | 76,147.0588 |
| 31 | `avg_salary_marketing` | employees | metric | `avg` | 67,705.8824 |
| 32 | `avg_salary_operations` | employees | metric | `avg` | 79,147.0588 |
| 33 | `avg_salary_sales` | employees | metric | `avg` | 90,235.2941 |
| 34 | `avg_salary_support` | employees | metric | `avg` | 103,029.4118 |
| 35 | `unique_by_city` | employees | bucket | `terms` | 8 buckets / 120 docs / top Pune=22 |
| 36 | `unique_employee_total` | employees | metric | `cardinality` | 120 |
| 37 | `missing_bonus` | employees | bucket | `missing` | 68 docs |
| 38 | `active_only` | employees | bucket | `filter` | 84 docs |
| 39 | `active_avg_salary` | employees | metric | `avg` | 83,297.6190 |
| 40 | `designations` | employees | bucket | `terms` | 25 buckets / 120 docs |
| 41 | `salary_percentiles` | employees | metric | `percentiles` | p25 49,250, p50 73,000, p75 115,625, p90 137,300, p95 147,575 |
| 42 | `employee_count` | employees | metric | `value_count` | 120 |

## Bucket vs metric aggregations

### Bucket aggregations group documents

A bucket aggregation returns `buckets`. Each bucket has a `doc_count` and can contain
sub-aggregations. It answers **"which groups exist and how many documents are in each?"**

Examples: `terms`, `range`, `date_histogram`, `histogram`, `filters`, `filter`, `missing`,
`nested`, `reverse_nested`, `global`.

- `filters` creates several named buckets from several filters.
- `filter` creates exactly one bucket with the matching documents.
- `global` ignores the query context and creates one bucket over the whole index.
- Bucket aggregations can contain other bucket aggregations and metric aggregations, which is
  how `category -> stats(price)` produces one stats result per category.

### Metric aggregations calculate numbers

A metric aggregation returns `value` (or a small set of values) and has no buckets. It answers
**"what is the average/minimum/maximum/count/sum?"**

Examples: `avg`, `sum`, `min`, `max` (single-value); `stats`, `extended_stats`,
`percentiles` (multi-value); `value_count`; `cardinality` (approximate distinct count).

Metric aggregations can sit at the top level (one value for the whole query) or inside a
bucket (one value per bucket). A metric cannot contain a sub-aggregation, because it produces
a value, not a group.

### One-line rule

- **Bucket** = "split into groups" → returns `buckets`.
- **Metric** = "calculate a number" → returns `value`.

## Verification

The notebook asserts every task against a Python calculation from the source JSON:

- 72 products / 120 employees / 181 nested reviews indexed.
- Category counts sum to 72 across 12 buckets.
- Average, min, max, stock sum and percentile values match Python.
- The date histogram returns 36 buckets with exactly six empty months and 72 documents.
- Department averages, city cardinalities, nested review totals and filtered tier counts
  match the raw data.
- The report has at least 15 aggregations (42 rows, 19 types) and both kinds.

Execution result: **31 cells (15 code, 16 markdown), 0 errors, all outputs stored.**
