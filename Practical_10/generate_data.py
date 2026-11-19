"""Generate deterministic synthetic events for the Practical 10 pagination lab.

The notebook imports :func:`build_records` and bulk-loads the result into
Elasticsearch. The script can also write the same records as newline-delimited
JSON for inspection without touching Elasticsearch:

    python generate_data.py --count 100000 --output data/events.ndjson
"""

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_COUNT = 100_000
DEFAULT_SEED = 42
BASE_TIME = datetime(2024, 1, 1, tzinfo=timezone.utc)
REGIONS = ["North", "South", "East", "West", "Central"]
CATEGORIES = ["hardware", "software", "services", "subscription", "training"]
STATUSES = ["completed", "pending", "failed", "refunded"]
EXPORT_FIELDS = [
    "sequence",
    "event_id",
    "created_at",
    "customer_id",
    "region",
    "category",
    "amount",
    "status",
]


def build_records(count=DEFAULT_COUNT, seed=DEFAULT_SEED):
    """Yield exactly ``count`` deterministic event documents."""
    if count < 1:
        raise ValueError("count must be positive")

    rng = random.Random(seed)
    for sequence in range(1, count + 1):
        created_at = BASE_TIME + timedelta(days=(sequence - 1) // 100)
        yield {
            "sequence": sequence,
            "event_id": f"EVT-{sequence:06d}",
            "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "customer_id": f"C-{rng.randint(1, 5000):04d}",
            "region": rng.choice(REGIONS),
            "category": rng.choice(CATEGORIES),
            "amount": rng.randint(100, 250_000),
            "status": rng.choice(STATUSES),
        }


def write_ndjson(path, count=DEFAULT_COUNT, seed=DEFAULT_SEED):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with target.open("w", encoding="utf-8") as handle:
        for record in build_records(count=count, seed=seed):
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")
            written += 1
    return target, written


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--output",
        default="data/events.ndjson",
        help="newline-delimited JSON output path",
    )
    args = parser.parse_args()

    target, written = write_ndjson(args.output, count=args.count, seed=args.seed)
    print(f"wrote {written:,} records to {target}")
    print(f"size: {target.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
