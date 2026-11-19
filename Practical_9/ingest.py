"""Reusable ingestion CLI for the UCI Adult Census dataset.

Supports CSV, JSON and JSON Lines input with validation, cleaning, bulk
indexing, failure handling, logging and ingestion statistics.

Examples:

    python ingest.py --input data/adult.csv --index adult_ingest \
        --recreate --batch-size 1000

    python ingest.py --input data/adult_sample.json --index adult_json \
        --recreate --limit 500

    python ingest.py --input data/adult_invalid.csv --index adult_invalid \
        --recreate --reject-file artifacts/rejected_records.jsonl
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from elasticsearch import Elasticsearch, helpers

HERE = Path(__file__).resolve().parent
DEFAULT_MAPPING = HERE / "mapping.json"

COLUMNS = [
    "age", "workclass", "fnlwgt", "education", "education_num",
    "marital_status", "occupation", "relationship", "race", "sex",
    "capital_gain", "capital_loss", "hours_per_week", "native_country",
    "income",
]

OPTIONAL_FIELDS = ("workclass", "occupation", "native_country")
INCOME_VALUES = {"<=50k", ">50k"}
SEX_VALUES = {"male", "female"}

SUMMARY_FIELDS = (
    "read", "duplicates_removed", "valid", "invalid", "indexed", "failed",
    "elapsed_seconds", "docs_per_second", "batches",
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="CSV, JSON or JSONL file")
    parser.add_argument("--index", required=True, help="target Elasticsearch index")
    parser.add_argument("--mapping", default=str(DEFAULT_MAPPING), help="index mapping JSON")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--limit", type=int, default=None, help="only process the first N records")
    parser.add_argument("--recreate", action="store_true", help="drop and recreate the index")
    parser.add_argument("--keep-duplicates", action="store_true")
    parser.add_argument("--pipeline", default=None, help="optional ingest pipeline id")
    parser.add_argument("--dry-run", action="store_true", help="clean and validate only")
    parser.add_argument("--reject-file", default="artifacts/rejected_records.jsonl")
    parser.add_argument("--stats-file", default="artifacts/ingestion_stats.json")
    parser.add_argument("--log-file", default="logs/ingestion.log")
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--encoding", default="utf-8")
    parser.add_argument("--es-url", default="http://127.0.0.1:9200")
    return parser.parse_args(argv)


def setup_logging(log_file):
    path = Path(log_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ingest")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def load_input(path, delimiter=",", encoding="utf-8"):
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(
            path,
            dtype=str,
            keep_default_na=False,
            na_filter=False,
            delimiter=delimiter,
            encoding=encoding,
        )
        return frame.to_dict(orient="records")

    if suffix in {".json", ".jsonl", ".ndjson"}:
        text = Path(path).read_text(encoding=encoding)
        if suffix == ".json":
            data = json.loads(text)
            if not isinstance(data, list):
                raise ValueError("JSON input must be an array of objects")
            return data
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    raise ValueError(f"unsupported input type: {suffix}")


def numeric(raw, field, minimum=None, maximum=None):
    value = int(float(str(raw[field]).strip()))
    if minimum is not None and value < minimum:
        raise ValueError(f"{field} below {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{field} above {maximum}")
    return value


def age_band(age):
    if age < 25:
        return "17-24"
    if age < 35:
        return "25-34"
    if age < 45:
        return "35-44"
    if age < 55:
        return "45-54"
    if age < 65:
        return "55-64"
    return "65+"


def hours_band(hours):
    if hours < 35:
        return "part-time"
    if hours <= 40:
        return "full-time"
    return "overtime"


def clean_record(raw, source_row):
    missing = [field for field in COLUMNS if field not in raw]
    if missing:
        raise ValueError(f"missing columns: {', '.join(missing)}")

    clean = {}
    problems = []

    for field in COLUMNS:
        value = raw[field]
        if isinstance(value, str):
            value = value.strip()
        if value in (None, "", "?"):
            value = None

        if field in OPTIONAL_FIELDS and value is None:
            value = "Unknown"
        elif value is None:
            problems.append(f"{field} is required")

        clean[field] = value

    if problems:
        raise ValueError("; ".join(problems))

    clean["age"] = numeric(clean, "age", 17, 90)
    clean["fnlwgt"] = numeric(clean, "fnlwgt", 1)
    clean["education_num"] = numeric(clean, "education_num", 1, 16)
    clean["capital_gain"] = numeric(clean, "capital_gain", 0)
    clean["capital_loss"] = numeric(clean, "capital_loss", 0)
    clean["hours_per_week"] = numeric(clean, "hours_per_week", 1, 99)

    clean["sex"] = str(clean["sex"]).lower()
    if clean["sex"] not in SEX_VALUES:
        raise ValueError("sex must be male or female")

    clean["income"] = str(clean["income"]).strip().rstrip(".").lower()
    if clean["income"] not in INCOME_VALUES:
        raise ValueError("income must be <=50k or >50k")

    clean["native_country"] = str(clean["native_country"]).replace("-", " ").strip()
    clean["record_id"] = str(raw.get("record_id") or f"AD-{source_row:06d}")
    clean["source_row"] = source_row
    clean["net_capital"] = clean["capital_gain"] - clean["capital_loss"]
    clean["is_high_income"] = clean["income"] == ">50k"
    clean["age_band"] = age_band(clean["age"])
    clean["hours_band"] = hours_band(clean["hours_per_week"])
    return clean


def prepare(records, keep_duplicates=False):
    cleaned = []
    invalid = []
    duplicates = 0
    seen = set()

    for row_number, raw in enumerate(records, 1):
        if not isinstance(raw, dict):
            invalid.append({"row": row_number, "reasons": ["record is not an object"]})
            continue

        signature = tuple(str(raw.get(field, "")).strip() for field in COLUMNS)
        if not keep_duplicates:
            if signature in seen:
                duplicates += 1
                continue
            seen.add(signature)

        try:
            cleaned.append(clean_record(raw, row_number))
        except (TypeError, ValueError) as exc:
            invalid.append({
                "row": row_number,
                "record_id": raw.get("record_id"),
                "reasons": [str(exc)],
                "record": raw,
            })

    return cleaned, invalid, duplicates


def ensure_index(es, index, mapping, recreate):
    if es.indices.exists(index=index):
        if not recreate:
            return
        es.indices.delete(index=index)
    es.indices.create(index=index, **mapping)


def write_rejects(path, items):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, default=str) + "\n")


def bulk_index(es, index, documents, batch_size, pipeline, logger):
    by_id = {doc["record_id"]: doc for doc in documents}
    failed = []
    indexed = 0
    batches = 0
    started = time.perf_counter()

    def actions():
        for doc in documents:
            yield {"_index": index, "_id": doc["record_id"], "_source": doc}

    kwargs = {
        "chunk_size": batch_size,
        "raise_on_error": False,
        "max_retries": 2,
        "initial_backoff": 1,
    }
    if pipeline:
        kwargs["pipeline"] = pipeline

    for ok, item in helpers.streaming_bulk(es, actions(), **kwargs):
        if ok:
            indexed += 1
        else:
            operation = next(iter(item.values()))
            record_id = operation.get("_id")
            failed.append({
                "type": "bulk",
                "record_id": record_id,
                "status": operation.get("status"),
                "error": operation.get("error"),
                "record": by_id.get(record_id),
            })

        processed = indexed + len(failed)
        while processed >= (batches + 1) * batch_size:
            batches += 1
            logger.info("progress: %s indexed, %s failed (batch %s)",
                        indexed, len(failed), batches)

    elapsed = time.perf_counter() - started
    return indexed, failed, batches, elapsed


def write_stats(path, payload):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def main(argv=None):
    args = parse_args(argv)
    started = time.perf_counter()
    logger = setup_logging(args.log_file)
    logger.info("input=%s index=%s batch_size=%s pipeline=%s dry_run=%s",
                args.input, args.index, args.batch_size, args.pipeline, args.dry_run)

    records = load_input(args.input, delimiter=args.delimiter, encoding=args.encoding)
    if args.limit:
        records = records[:args.limit]
    logger.info("read %s records", len(records))

    documents, invalid, duplicates = prepare(records, keep_duplicates=args.keep_duplicates)
    logger.info("valid=%s invalid=%s duplicates_removed=%s",
                len(documents), len(invalid), duplicates)

    es = Elasticsearch(args.es_url, request_timeout=60)
    indexed = 0
    failed = []
    batches = 0
    bulk_elapsed = 0.0

    if not args.dry_run:
        mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
        ensure_index(es, args.index, mapping, args.recreate)
        indexed, failed, batches, bulk_elapsed = bulk_index(
            es, args.index, documents, args.batch_size, args.pipeline, logger
        )
        es.indices.refresh(index=args.index)
        count = es.count(index=args.index)["count"]
        logger.info("indexed=%s failed=%s index_count=%s elapsed=%.2fs",
                    indexed, len(failed), count, bulk_elapsed)

    rejects = invalid + failed
    write_rejects(args.reject_file, rejects)

    elapsed = time.perf_counter() - started
    stats = {
        "source": str(args.input),
        "index": args.index,
        "pipeline": args.pipeline,
        "dry_run": args.dry_run,
        "read": len(records),
        "duplicates_removed": duplicates,
        "valid": len(documents),
        "invalid": len(invalid),
        "indexed": indexed,
        "failed": len(failed),
        "rejected_total": len(rejects),
        "batches": batches,
        "elapsed_seconds": round(elapsed, 3),
        "bulk_seconds": round(bulk_elapsed, 3),
        "docs_per_second": round(indexed / elapsed, 1) if elapsed else 0.0,
        "started_at": datetime.fromtimestamp(
            time.time() - elapsed, tz=timezone.utc
        ).isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    write_stats(args.stats_file, stats)

    logger.info("summary: %s", json.dumps(
        {key: stats[key] for key in SUMMARY_FIELDS}, sort_keys=True
    ))
    print(json.dumps(stats, indent=2))
    return stats


if __name__ == "__main__":
    main()
