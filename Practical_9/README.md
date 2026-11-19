# Practical 9 - Data Ingestion, Validation, and Pipelines

Hands-on Elasticsearch practical covering raw-data inspection, cleaning, explicit
mappings, the Bulk API, failed-document handling, delete-and-restore with
`_reindex`, ingest pipelines, and a reusable ingestion CLI.

**Environment**

- Elasticsearch 9.2.0 at `http://127.0.0.1:9200`
- Kibana 9.2.0 at `http://127.0.0.1:5601`
- Python client `elasticsearch 9.5.1`, pandas 3.1.1, kernel `es`

## Files

| File | Purpose |
|---|---|
| `download_data.py` | Downloads UCI Adult and creates CSV/JSON samples plus invalid rows |
| `data/adult.csv` | Raw dataset, 32,561 records, original whitespace and `?` markers preserved |
| `data/adult_sample.csv` | First 1,000 records for quick CLI runs |
| `data/adult_sample.json` | First 1,000 records as a JSON array |
| `data/adult_invalid.csv` | 6 records with 2 deliberately invalid values |
| `mapping.json` | 21-property strict mapping for `adult_people` |
| `ingest.py` | Reusable CSV/JSON/JSONL ingestion CLI with validation and stats |
| `practical_9.ipynb` | Executed notebook for Tasks 1-14 plus the advanced assignment |
| `artifacts/` | Benchmark, validation report, failed records, logs, stats, rejects |
| `README.md` | This summary |

## Setup

```powershell
cd "C:\D-Drive\Elastic Search Practicals\Practical_9"
..\.venv\Scripts\python.exe download_data.py
..\.venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace `
  --ExecutePreprocessor.kernel_name=es --ExecutePreprocessor.timeout=300 practical_9.ipynb
```

The notebook recreates its demo indices on every run, so it is idempotent.

## Dataset

Source:
`https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data`

| Property | Value |
|---|---:|
| Raw records | 32,561 |
| Columns | 15 |
| Missing cells (`?`) | 4,262 |
| Missing `workclass` | 1,836 |
| Missing `occupation` | 1,843 |
| Missing `native_country` | 583 |
| Exact duplicate rows | 24 |
| Clean records | 32,537 |
| Income `<=50K` / `>50K` | 24,720 / 7,841 |

After dropping duplicates: `<=50k` = 24,698, `>50k` = 7,839. `native_country`
has 582 `Unknown` values after deduplication because one missing-country row is
an exact duplicate.

## Cleaning rules

- Trim every string field, then convert `?` to missing.
- Drop exact duplicate rows.
- Fill missing `workclass`, `occupation`, and `native_country` with `Unknown`.
- Convert `age`, `fnlwgt`, `education_num`, `capital_gain`, `capital_loss`, and
  `hours_per_week` to integers.
- Enforce `age` 17-90, `hours_per_week` 1-99, and `education_num` 1-16.
- Lowercase `sex` and `income`.
- Replace hyphens in `native_country` with spaces.
- Derive `net_capital`, `is_high_income`, `age_band`, and `hours_band`.
- Assign stable `record_id` (`AD-000001`, ...) and preserve `source_row`.

The mapping sets `dynamic: strict`, so an unexpected field is rejected rather
than silently added:

```json
{
  "settings": {"number_of_shards": 1, "number_of_replicas": 0},
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "record_id": {"type": "keyword"},
      "age": {"type": "integer"},
      "sex": {"type": "keyword"},
      "income": {"type": "keyword"},
      "net_capital": {"type": "integer"},
      "is_high_income": {"type": "boolean"},
      "age_band": {"type": "keyword"},
      "hours_band": {"type": "keyword"}
    }
  }
}
```

## Task results

### 1. Download with Python

`download_data.py` uses `requests`, validates 32,561 downloaded records, writes
`adult.csv`, and builds the sample and invalid files.

### 2. Read and inspect

The raw CSV loads as **32,561 rows x 15 columns**. Every field is read as text
first so invalid numeric values can be detected instead of coerced to null.

### 3. Detect missing values and duplicates

- **4,262** missing cells across three fields.
- **24** exact duplicate rows.
- Rows with at least one missing value: **2,399**.

### 4. Clean and derive

**32,537** clean documents remain. Average age is **38.5855**.
Sex counts: `male` 21,775, `female` 10,762.
Unknown counts: `workclass` 1,836, `occupation` 1,843, `native_country` 582.

### 5. Mapping

`adult_people` has **21 properties** and `dynamic: strict`. Numeric fields are
`integer`/`long`, categorical fields are `keyword`, and `is_high_income` is
`boolean`.

### 6. Single-document indexing

A fixed 500-document sample indexed one request at a time:

- **53.527 s** total
- **107.1 ms** per document

### 7. Bulk indexing

The same 500 documents through `helpers.bulk` with chunk size 250:

- **0.237 s**

The full 32,537-document load into `adult_people`:

- **4.300 s**
- **7,567 docs/s**

### 8. Strategy comparison

| Strategy | Documents | Time | Result |
|---|---:|---:|---|
| Individual `index` calls | 500 | 53.527 s | Baseline |
| Bulk API | 500 | 0.237 s | **226x faster** |

Bulk indexing amortizes HTTP and per-request overhead across many actions.

### 9. Failed-document handling

A batch with two valid and two invalid documents produced:

| Outcome | Count |
|---|---:|
| Indexed | 2 |
| Rejected | 2 |
| Final count after repairs | 4 |

Errors were HTTP 400 `document_parsing_exception` for `age = "not-a-number"`
and `hours_per_week = "many"`. Details are stored in
`artifacts/failed_records.json`; the two documents were repaired and retried.

### 10. Delete by query

`adult_backup` was created from `adult_people` with `_reindex`:

- Backup: **32,537** documents in **1.685 s**
- Deleted `age < 25`: **5,562**
- Remaining: **26,975**
- Documents younger than 25 remaining: **0**

### 11. Restore with `_reindex`

Only the affected subset was copied back from the backup:

- Restored: **5,562**
- Failures: **0**
- Final `adult_people` count: **32,537**

### 12. Ingest pipeline

`adult_normalize_pipeline` contains **28 processors**:

- 15 `trim` processors
- 2 `lowercase` processors (`sex`, `income`)
- 1 `gsub` processor (`native_country`)
- 6 `convert` processors (five `integer`, one `long`)
- 1 Painless `script` deriving capital, income, age-band, and hours-band fields
- 2 `set` processors for pipeline metadata
- 1 `remove` processor for `temp_note`

### 13. Simulate and apply the pipeline

Simulation on a raw row changed leading-space strings into typed values:

| Field | Before | After |
|---|---|---|
| `age` | `"39"` | `39` (integer) |
| `sex` | `" Male"` | `"male"` |
| `income` | `" <=50K"` | `"<=50k"` |
| `native_country` | `" United-States"` | `"United States"` |
| `net_capital` | absent | `2174` |
| `temp_note` | present | removed |

A further **100 raw documents** were indexed through the pipeline into
`adult_pipeline_demo`; all 100 succeeded.

### 14. Validation

Elasticsearch results match pandas exactly:

| Check | Result |
|---|---|
| `adult_people` count | 32,537 |
| Income buckets | `<=50k`: 24,698; `>50k`: 7,839 |
| Average age | 38.5855 (pandas 38.5855) |
| Unknown `workclass` | 1,836 |
| Unknown `occupation` | 1,843 |
| Unknown `native_country` | 582 |
| `sex` buckets | male 21,775; female 10,762 |
| Mapping | `dynamic: strict`, 21 properties |
| Failed demo | 4 documents after repair |

`artifacts/validation_report.json` stores the full machine-readable report.

## Advanced assignment - reusable ingestion CLI

`ingest.py` supports CSV, JSON, and JSONL input, explicit mappings, batching,
optional pipelines, deduplication, validation, reject files, stats, and logging.

```powershell
..\.venv\Scripts\python.exe ingest.py `
  --input data/adult.csv --index adult_ingest_csv --recreate `
  --batch-size 1000 `
  --stats-file artifacts/ingestion_stats_csv.json `
  --reject-file artifacts/rejected_csv.jsonl `
  --log-file artifacts/ingestion_csv.log
```

The notebook runs the CLI three times:

| Input | Read | Duplicates removed | Invalid | Indexed | Target |
|---|---:|---:|---:|---:|---|
| `data/adult.csv` | 32,561 | 24 | 0 | 32,537 | `adult_ingest_csv` |
| `data/adult_sample.json` | 1,000 | 0 | 0 | 1,000 | `adult_ingest_json` |
| `data/adult_invalid.csv` | 6 | 0 | 2 | 4 | `adult_ingest_invalid` |

The invalid run writes two rejected records to
`artifacts/rejected_invalid.jsonl`. Every run writes a stats JSON file and a log.
Useful options: `--limit`, `--keep-duplicates`, `--pipeline`, `--dry-run`,
`--delimiter`, `--encoding`, and `--es-url`.

## Indices left in the cluster

| Index | Documents | Purpose |
|---|---:|---|
| `adult_people` | 32,537 | Canonical cleaned dataset |
| `adult_backup` | 32,537 | Backup before delete-by-query |
| `adult_pipeline_demo` | 100 | Raw documents normalized by the pipeline |
| `adult_individual_bench` | 500 | Per-document benchmark |
| `adult_bulk_bench` | 500 | Bulk benchmark |
| `adult_failed_demo` | 4 | Repaired failure demo |
| `adult_ingest_csv` | 32,537 | CLI full-CSV run |
| `adult_ingest_json` | 1,000 | CLI JSON run |
| `adult_ingest_invalid` | 4 | CLI invalid-row run |

## Verification

The notebook asserts every expected count against pandas or the source data:
raw rows, missing values, duplicates, clean rows, mapping properties, benchmark
counts, failed and repaired documents, deleted and restored counts, pipeline
output, aggregation buckets, and CLI statistics.

Execution result: **34 cells (17 code, 17 markdown), 0 errors, all outputs stored.**
