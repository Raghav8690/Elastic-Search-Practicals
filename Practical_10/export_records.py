"""Stream Elasticsearch records into a CSV file.

This application uses ``elasticsearch.helpers.scan`` so the export is bounded in
memory: records are written as the scroll cursor advances instead of loading the
whole index first.

Example:

    python export_records.py --index pagination_events \
        --output artifacts/export_100000.csv --limit 100000
"""

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from elasticsearch import Elasticsearch, helpers

from generate_data import EXPORT_FIELDS

DEFAULT_INDEX = "pagination_events"
DEFAULT_OUTPUT = "artifacts/export_100000.csv"
DEFAULT_SUMMARY = "artifacts/export_summary.json"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", default=DEFAULT_INDEX)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=100_000)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--scroll", default="2m")
    parser.add_argument("--summary-file", default=DEFAULT_SUMMARY)
    parser.add_argument("--es-url", default="http://127.0.0.1:9200")
    return parser.parse_args(argv)


def export_records(es, index, output, limit, batch_size, scroll):
    if limit < 1:
        raise ValueError("limit must be positive")
    if batch_size < 1:
        raise ValueError("batch-size must be positive")

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    rows = 0
    min_sequence = None
    max_sequence = None
    first_row_sequence = None
    last_row_sequence = None

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()

        for hit in helpers.scan(
            es,
            index=index,
            query={"query": {"match_all": {}}},
            size=batch_size,
            scroll=scroll,
            source_includes=EXPORT_FIELDS,
            request_timeout=60,
        ):
            source = hit["_source"]
            writer.writerow(source)
            sequence = source["sequence"]
            rows += 1
            if first_row_sequence is None:
                first_row_sequence = sequence
            last_row_sequence = sequence
            min_sequence = sequence if min_sequence is None else min(min_sequence, sequence)
            max_sequence = sequence if max_sequence is None else max(max_sequence, sequence)
            if rows >= limit:
                break

    elapsed = time.perf_counter() - started
    summary = {
        "index": index,
        "output": str(output_path),
        "requested_limit": limit,
        "rows": rows,
        "first_row_sequence": first_row_sequence,
        "last_row_sequence": last_row_sequence,
        "min_sequence": min_sequence,
        "max_sequence": max_sequence,
        "fields": EXPORT_FIELDS,
        "elapsed_seconds": round(elapsed, 3),
        "rows_per_second": round(rows / elapsed, 1) if elapsed else 0.0,
        "output_bytes": output_path.stat().st_size,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return summary


def main(argv=None):
    args = parse_args(argv)
    es = Elasticsearch(args.es_url, request_timeout=60)
    summary = export_records(
        es,
        index=args.index,
        output=args.output,
        limit=args.limit,
        batch_size=args.batch_size,
        scroll=args.scroll,
    )

    summary_path = Path(args.summary_file)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()
