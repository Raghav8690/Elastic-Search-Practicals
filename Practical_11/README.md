# Practical 11 - Templates, Aliases, Lifecycle and Optimization

A hands-on Elasticsearch index-management lab against the local single-node
cluster. It creates reusable templates, moves a read alias atomically, reindexes
100,000 documents, compares shard and refresh settings, profiles a slow query,
demonstrates ILM/rollover/data streams, and finishes with a baseline-versus-
optimized index assignment.

**Environment**

- Elasticsearch 9.2.0 at `http://127.0.0.1:9200`
- Kibana 9.2.0 at `http://127.0.0.1:5601`
- Python client `elasticsearch 9.5.1`, kernel `es`
- Dataset: 100,000 deterministic synthetic events generated with seed 42

## Files

| File | Purpose |
|---|---|
| `generate_data.py` | Deterministic generator for 100,000 events, including a text `description` |
| `mapping.json` | Explicit strict mapping and one-shard optimized settings |
| `practical_11.ipynb` | Executed Tasks 1-12 plus the optimization assignment |
| `artifacts/index_report.json` | Templates, aliases, reindex, shards, refresh, ILM, rollover, data stream, slow query |
| `artifacts/optimization_report.json` | Baseline versus optimized index measurements |
| `artifacts/benchmark.json` | Indexing, shard, query, and slow-query measurements |
| `artifacts/stats.json` | Final index and node statistics |
| `README.md` | This summary |

The generated dataset is not stored as a raw file; the notebook builds it
directly from `generate_data.py`. It can also be written to NDJSON:

```powershell
..\.venv\Scripts\python.exe generate_data.py --output data/events.ndjson
```

## Dataset and mappings

Every document contains nine fields:

| Field | Type | Notes |
|---|---|---|
| `sequence` | `integer` | Unique 1-100,000 |
| `event_id` | `keyword` | `EVT-000001` ... `EVT-100000` |
| `created_at` | `date` | 100 events share each day |
| `customer_id` | `keyword` | Synthetic customer |
| `region` | `keyword` | North, South, East, West, Central |
| `category` | `keyword` | hardware, software, services, subscription, training |
| `amount` | `integer` | 100-250,000 |
| `status` | `keyword` | completed, pending, failed, refunded |
| `description` | `text` | Synthetic sentence with a varying verb and event details |

The baseline deliberately uses **dynamic mapping** with five primary shards.
The optimized index uses the explicit strict mapping in `mapping.json`, one
shard, zero replicas, `best_compression`, and refresh disabled during loading.

## Setup

```powershell
cd "C:\D-Drive\Elastic Search Practicals\Practical_11"
..\.venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace `
  --ExecutePreprocessor.kernel_name=es --ExecutePreprocessor.timeout=600 practical_11.ipynb
```

The notebook recreates all Practical 11 indices at the start and is safe to run
again. It leaves the main assignment indices and the lifecycle demonstration
indices in the cluster for inspection.

## Task results

### 1. Component and index templates

Created:

- `p11-events-settings` component template
- `p11-events-mappings` component template
- `p11-events-template` index template for `p11-events-*`

The index template composes both components. Component templates are accessed
through the `cluster` API; the composed index template is accessed through the
`indices` API.

### 2. Index from the template

`p11-events-optimized` resolved to:

- one primary shard
- zero replicas
- `best_compression`
- `dynamic: strict`
- keyword fields for identifiers and categorical values
- `description` as text with norms disabled

### 3. Alias

`p11-events-read` initially pointed at `p11-baseline-events`. Reading through the
alias returned all 100,000 documents.

### 4. Atomic alias switch

A single `_aliases` request removed the alias from the baseline and added it to
the optimized index. The alias never disappeared between the two actions.

### 5. Reindex

`p11-baseline-events` was reindexed into `p11-events-reindexed`:

| Metric | Value |
|---|---:|
| Source documents | 100,000 |
| Destination documents | 100,000 |
| Created documents | 100,000 |
| Failures | 0 |
| Reindex time | 13.047 s |
| Batches | 100 |

### 6. One shard versus three shards

Both experiment indices contain 20,000 documents and use the same explicit
mapping.

| Metric | One shard | Three shards |
|---|---:|---:|
| Indexing time | 1.671 s | 1.503 s |
| Indexing throughput | 11,970.8 docs/s | 13,304.5 docs/s |
| Primary store | 2,610,147 bytes | 2,755,456 bytes |
| Segments | 2 | 6 |
| Query p50 | 51.561 ms | 52.731 ms |
| Query p95 | 58.847 ms | 61.219 ms |

The three-shard load was slightly faster in this run, but it used more storage
and produced more segments. Query latency was slightly better on one shard. On
a single node, three shards do not add hardware parallelism; they add Lucene and
coordination overhead.

### 7. Refresh interval

Both indices contain 20,000 documents.

| Refresh setting | Indexing time | Throughput |
|---|---:|---:|
| `1s` | 3.418 s | 5,851.9 docs/s |
| `-1` during load | 3.142 s | 6,365.3 docs/s |

Disabling refresh during the bulk load was **1.088x** faster in this run. The
gain is smaller than in the full 100,000-document assignment because local
timing noise is a larger fraction of a short 20,000-document load.

### 8. Indexing performance summary

| Index | Documents | Time | Throughput |
|---|---:|---:|---:|
| `p11-baseline-events` | 100,000 | 43.798 s | 2,283.2 docs/s |
| `p11-events-optimized` | 100,000 | 14.660 s | 6,821.3 docs/s |
| `p11-refresh-1s` | 20,000 | 3.418 s | 5,851.9 docs/s |
| `p11-refresh-off` | 20,000 | 3.142 s | 6,365.3 docs/s |

The optimized 100,000-document load was **198.76%** faster than the baseline
load. This combines several changes: one shard instead of five, refresh disabled
during the load, explicit mapping, and compression classes. The separate refresh
experiment isolates part of that effect.

### 9. Slow-query investigation

The script query:

```painless
doc['amount'].value >= params.min
```

returned 60,014 documents. The equivalent range filter returned the same count.

| Query | `took` | Profile query time |
|---|---:|---:|
| Script query | 20 ms | 20,644,752 ns |
| Range filter | 3 ms | 274,446 ns |

The profile shows a `ScriptQuery` inside a constant-score query versus an
`IndexOrDocValuesQuery` for the range. The script runs for candidate documents
and is not filter-cacheable like the range query.

### 10. ILM policy

Created `p11-events-ilm` with:

- hot phase: rollover at 50 MB or 30 days, priority 100
- delete phase after 90 days
- write alias `p11-events-ilm-write`

`explain_lifecycle` shows `p11-events-ilm-demo` as managed, in the `hot` phase,
at the `set_priority` step. Phase transitions are not forced in the lab.

### 11. Rollover and data streams

Regular rollover:

- `p11-rollover-000001` indexed 1,200 documents
- `rollover` with `max_docs: 1000` created `p11-rollover-000002`
- the write alias moved to the new index

Data stream:

- `p11-logs-template` matches `p11-logs*` and declares `data_stream: {}`
- `p11-logs` was created as a data stream
- after a `max_docs: 1` rollover, it had two backing indices:
  `.ds-p11-logs-2026.11.19-000001` and `.ds-p11-logs-2026.11.19-000002`

### 12. Final statistics

| Index | Documents | Primary store | Segments |
|---|---:|---:|---:|
| `p11-baseline-events` | 100,000 | 19,375,515 bytes | 23 |
| `p11-events-optimized` | 100,000 | 8,895,089 bytes | 1 |
| `p11-events-reindexed` | 100,000 | 10,019,210 bytes | 1 |

Node snapshot:

| Metric | Value |
|---|---:|
| Node | `my-node` |
| Heap used / max | 376,832,768 / 536,870,912 bytes |
| CPU | 9% |
| Total documents | 581,885 |
| Total store | 72,409,461 bytes |
| Cluster status | `yellow` |

The cluster is yellow because the local single-node setup has two unassigned
replicas: one on the pre-existing `projects` index and one on
`p11-rollover-000002`. The rollover-created index kept the cluster default of
one replica, so its replica cannot be allocated on a single node. The main
assignment and experiment indices use zero replicas.

## Assignment - Baseline versus optimized index

Both assignment indices contain the same 100,000 documents. The baseline uses
five shards, dynamic mapping, and the default refresh behavior. The optimized
index uses one shard, explicit strict mapping, `best_compression`, disabled
refresh during loading, and was already a single segment after the load
(force-merge was a no-op at 0.005 s).

| Metric | Baseline | Optimized | Change |
|---|---:|---:|---:|
| Load time | 43.798 s | 14.660 s | 66.5% faster |
| Indexing throughput | 2,283.2 docs/s | 6,821.3 docs/s | +198.76% |
| Primary store | 19,375,515 bytes | 8,895,089 bytes | -54.09% |
| Segments | 23 | 1 | -22 |
| Indexing time in stats | 30,480 ms | 5,373 ms | 82.4% lower |

### Query comparison

All query counts match between baseline and optimized. The p50 values are
wall-clock timings and include local HTTP overhead, which creates an approximately
50 ms floor. `mean_took` is the Elasticsearch-reported query time.

| Query | Count | Baseline p50 | Optimized p50 | p50 change | Baseline `took` | Optimized `took` |
|---|---:|---:|---:|---:|---:|---:|
| `status` term | 25,184 | 51.035 ms | 62.925 ms | -23.30% | 2.60 ms | 16.25 ms |
| `region` term | 19,902 | 49.099 ms | 49.212 ms | -0.23% | 3.10 ms | 5.40 ms |
| `amount` range | 23,910 | 47.848 ms | 52.452 ms | -9.62% | 6.95 ms | 8.25 ms |
| `created_at` range | 3,100 | 53.832 ms | 61.152 ms | -13.60% | 3.95 ms | 14.40 ms |
| `description` match | 20,151 | 53.512 ms | 51.920 ms | +2.98% | 4.15 ms | 10.70 ms |
| Combined filters | 15,020 | 54.131 ms | 70.115 ms | -29.53% | 5.00 ms | 15.85 ms |

The optimized index clearly wins on storage, segment count, and indexing
throughput. It does **not** win on these query timings. A five-shard baseline can
parallelize a filter across five Lucene shard searches on this one node, while
the one-shard optimized index executes the query serially. Compression also adds
decompression work. The correct conclusion is workload-dependent: one shard is a
good default for size and ingestion, but query latency must be measured rather
than assumed.

### Reindex assignment

The reindex task independently copied all 100,000 baseline documents into
`p11-events-reindexed` in 13.047 s with zero failures.

## Verification

The executed notebook asserts:

- Both component templates and the composed index template exist.
- The template-created index has one shard, zero replicas, compression, and a
  strict explicit mapping.
- The baseline has five shards and dynamic `.keyword` subfields.
- The read alias points to the baseline, then atomically to the optimized index.
- Reindex creates exactly 100,000 documents with no failures.
- Shard and refresh experiments contain the expected document counts.
- Every baseline query count matches the corresponding optimized query count.
- The script query and range filter return the same count.
- ILM reports the demo index as managed in the hot phase.
- Rollover creates the next index and updates the write alias.
- The data stream has two backing indices after rollover.
- Baseline, optimized, and reindexed indices all contain 100,000 documents.
- All four JSON artifacts are written.

Execution result: **40 cells (21 code, 19 markdown), 0 errors, all outputs stored.**

## Caveats

- All timings are from one local Docker node with zero replicas and shared
  cluster load. They are useful for relative comparison, not production sizing.
- Query p50 includes Python client and HTTP overhead; the `took` column is the
  server-side measurement.
- The baseline's 43.798 s load was slower than earlier runs of the same workload,
  showing that the local Docker host adds significant run-to-run variance.
- `best_compression` reduces storage but can add decompression cost to searches.
- ILM transitions are time- and size-driven; this lab verifies policy attachment
  and explanation rather than waiting for the delete phase.
- Data stream backing index names include the cluster date, so the exact names
  change on a later run.
