# Practical 10 - Deep Pagination, PIT, Scroll and Export

A hands-on Elasticsearch pagination lab against a local single-node cluster.
It compares offset pagination, `search_after`, point-in-time (PIT) cursors,
scroll, and the Python `scan` helper, then exports all 100,000 records to CSV.

**Environment**

- Elasticsearch 9.2.0 at `http://127.0.0.1:9200`
- Kibana 9.2.0 at `http://127.0.0.1:5601`
- Python client `elasticsearch 9.5.1`, kernel `es`

## Files

| File | Purpose |
|---|---|
| `generate_data.py` | Deterministic generator for 100,000 synthetic events |
| `mapping.json` | Strict one-shard mapping for `pagination_events` |
| `export_records.py` | Standalone streaming scan-to-CSV application |
| `practical_10.ipynb` | Executed Tasks 1-10 plus the assignment |
| `artifacts/benchmark.json` | Retrieval-method measurements |
| `artifacts/pagination_report.json` | Page checks, PIT/scroll results, assignment summary |
| `artifacts/export_summary.json` | Export row count, timing, size, and sequence range |
| `artifacts/export_100000.csv` | Generated CSV output, 100,001 lines including header |
| `README.md` | This summary |

The raw 100,000-record NDJSON file is optional and is not required by the
notebook:

```powershell
..\.venv\Scripts\python.exe generate_data.py --output data/events.ndjson
```

## Dataset and mapping

`pagination_events` contains exactly **100,000** deterministic documents from
`generate_data.py` (seed 42). It uses one shard and zero replicas.

| Field | Type | Notes |
|---|---|---|
| `sequence` | `integer` | Unique 1-100,000; stable pagination tie-breaker |
| `event_id` | `keyword` | `EVT-000001` ... `EVT-100000` |
| `created_at` | `date` | 100 events share each day |
| `customer_id` | `keyword` | Synthetic customer |
| `region` | `keyword` | North, South, East, West, Central |
| `category` | `keyword` | hardware, software, services, subscription, training |
| `amount` | `integer` | 100-250,000 |
| `status` | `keyword` | completed, pending, failed, refunded |

The global sort used by the page-number and `search_after` examples is:

```json
[{"created_at": "asc"}, {"sequence": "asc"}]
```

`created_at` repeats across a day, so the unique `sequence` tie-breaker is what
makes the order deterministic. The PIT automatically adds `_shard_doc` as an
additional implicit tie-breaker.

The index explicitly sets `index.max_result_window` to **10,000** so the deep
pagination boundary is visible in the mapping.

## Setup

```powershell
cd "C:\D-Drive\Elastic Search Practicals\Practical_10"
..\.venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace `
  --ExecutePreprocessor.kernel_name=es --ExecutePreprocessor.timeout=300 practical_10.ipynb
```

The notebook deletes and recreates `pagination_events`, bulk-loads 100,000
records, and then runs every task. Indexing took **36.176 s** in this run.

For just the standalone export, after the index exists:

```powershell
..\.venv\Scripts\python.exe export_records.py `
  --index pagination_events `
  --output artifacts/export_100000.csv `
  --limit 100000
```

## Task results

### 1. First 10 records

Sorted by `created_at, sequence`, `size=10` returns sequences **1-10**.

### 2. Next 10 records

`from_=10, size=10` returns sequences **11-20**. The two pages are disjoint.

### 3. `from` and `size` pagination

Pages at offsets 0, 10, and 20 returned sequences **1-10, 11-20, 21-30**.
The index reports 100,000 total hits.

`from` is a reserved Python keyword, so the Python client parameter is
`from_`.

### 4. Deep-pagination limitation

| Request | Result |
|---|---|
| `from_=9,990, size=10` | 10 hits (last legal window) |
| `from_=10,000, size=10` | HTTP 400 |

The rejected request tried to address `10,010` hits:

```text
Result window is too large, from + size must be less than or equal to:
[10000] but was [10010]
```

Raising `index.max_result_window` would move the boundary, but each shard still
has to collect and sort every skipped hit. That increases memory pressure and
latency, so deep pagination should use `search_after` instead.

### 5. `search_after`

The first page returns sequences **1-10**. Its last hit's sort values become the
next cursor:

```text
["2024-01-01T00:00:00.000Z", 10]
```

The second request with `search_after` returns **11-20**. The query and sort must
remain identical across pages.

### 6. `search_after` with PIT

A PIT was opened for 2 minutes and used for ten pages:

| Metric | Value |
|---|---:|
| Documents | 100 |
| Requests | 10 |
| Sequences | 1-100 |
| Elapsed | 0.623 s |
| Open PIT/scroll contexts afterward | 0 |

The search omits `index` and sends `pit={"id": ..., "keep_alive": "2m"}`. The
latest `pit_id` is reused on each page, and the PIT is closed in `finally`.

### 7. Scroll API

The Scroll API retrieved the complete index:

| Metric | Value |
|---|---:|
| Documents | 100,000 |
| Unique sequences | 100,000 |
| Scroll batches | 101 |
| HTTP calls including clear | 102 |
| Elapsed | 8.038 s |

The scroll sorts by `_doc` for speed. `clear_scroll` runs in `finally`, so no
search context is left open.

### 8. Python `scan` helper

`helpers.scan` retrieved a 1,000-document sample with `size=100`, then cleared
the scroll automatically. Scan is a scroll wrapper and uses `_doc` order by
default; it does not promise sequence order unless `preserve_order=True`.

### 9. Retrieve all 100,000 records

`helpers.scan` retrieved exactly **100,000** unique documents:

| Metric | Value |
|---|---:|
| Documents | 100,000 |
| Unique sequences | 100,000 |
| Minimum / maximum sequence | 1 / 100,000 |
| Elapsed | 7.894 s |

### 10. Performance comparison

All full-retrieval methods used page size 1,000, the same source projection, and
`track_total_hits=False`. The local single-node timings below are useful for
relative comparison, not as production capacity numbers.

| Method | Documents | Requests | Time | Throughput | Suitability |
|---|---:|---:|---:|---:|---|
| `from` + `size` | 10,000 | 10 | 0.769 s | 13,003.9 docs/s | Shallow page-number UI only |
| `search_after` | 100,000 | 100 | 7.744 s | 12,913.2 docs/s | Deep feeds and infinite scroll |
| PIT + `search_after` | 100,000 | 102 | 7.520 s | 13,297.9 docs/s | Consistent deep pagination |
| Scroll | 100,000 | 102 | 8.038 s | 12,441.3 docs/s | One-off bulk processing |
| `helpers.scan` | 100,000 | 102 | 7.894 s | 12,668.3 docs/s | Python ETL and export |

`from` + `size` is measured only to 10,000 because a deeper offset is rejected.

## Assignment - CSV export

`export_records.py` uses `helpers.scan` and `csv.DictWriter`; it never builds a
100,000-row list in memory.

| Metric | Value |
|---|---:|
| CSV rows | 100,000 |
| CSV lines including header | 100,001 |
| Output size | 7,675,821 bytes |
| Export time | 10.986 s |
| Throughput | 9,102.8 rows/s |
| Sequence range | 1-100,000 |

The header is:

```text
sequence,event_id,created_at,customer_id,region,category,amount,status
```

The export follows scroll `_doc` order, not sequence order. If sorted output is
required, use a sorted `search_after` export or `preserve_order=True` in
`helpers.scan`; both trade some throughput for ordering.

## Choosing an approach

- **`from` + `size`**: page-number UI for shallow pages. Simple and stateless,
  but expensive at depth and capped by `max_result_window`.
- **`search_after`**: deep pagination and infinite scroll. Stateless, efficient,
  and requires a stable unique sort tie-breaker. Live index changes can still
  affect page consistency.
- **PIT + `search_after`**: the recommended choice when a deep pagination
  session must see a stable index snapshot. The PIT must be closed.
- **Scroll**: snapshot cursor for one-off processing and ETL. It is stateful,
  resource-heavy, and not intended for real-time user pagination.
- **`helpers.scan`**: the convenient Python scroll wrapper for full exports and
  batch jobs; it clears its scroll context automatically.

For the assignment, `helpers.scan` is the right tool: it streams all 100,000
records with bounded memory and no page-number limit.

## Verification

The executed notebook asserts:

- The index contains exactly 100,000 documents.
- First and second pages are exactly sequences 1-10 and 11-20.
- The legal window boundary works and the next request raises HTTP 400.
- `search_after` and PIT pages are contiguous and unique.
- Scroll and scan each return all 100,000 unique sequences.
- Every full-retrieval method has the same document count.
- The CSV has 100,001 lines, the correct header, 100,000 rows, and sequences
  1-100,000.
- No PIT or scroll context remains open.

Execution result: **28 cells (14 code, 14 markdown), 0 errors, all outputs stored.**
