"""Generate deterministic synthetic events for the Practical 13 security lab."""

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_PUBLIC_COUNT = 1_000
DEFAULT_PRIVATE_COUNT = 500
DEFAULT_SEED = 42
BASE_TIME = datetime(2024, 1, 1, tzinfo=timezone.utc)
SERVICES = ["billing", "catalog", "identity", "search", "notifications"]
LEVELS = ["info", "warn", "error"]
EVENT_FIELDS = [
    "event_id",
    "created_at",
    "service",
    "level",
    "amount",
    "message",
    "visibility",
]


def build_events(count, visibility, seed=DEFAULT_SEED):
    """Yield deterministic events with a public/private visibility label."""
    if count < 1:
        raise ValueError("count must be positive")
    if visibility not in {"public", "private"}:
        raise ValueError("visibility must be public or private")

    rng = random.Random(seed + (0 if visibility == "public" else 10_000))
    prefix = "PUB" if visibility == "public" else "PRV"
    for sequence in range(1, count + 1):
        level = rng.choice(LEVELS)
        service = rng.choice(SERVICES)
        created_at = BASE_TIME + timedelta(days=(sequence - 1) // 50)
        yield {
            "event_id": f"{prefix}-{sequence:06d}",
            "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "service": service,
            "level": level,
            "amount": rng.randint(100, 250_000),
            "message": f"{level} event from {service} number {sequence}",
            "visibility": visibility,
        }


def build_public_events(count=DEFAULT_PUBLIC_COUNT, seed=DEFAULT_SEED):
    return build_events(count=count, visibility="public", seed=seed)


def build_private_events(count=DEFAULT_PRIVATE_COUNT, seed=DEFAULT_SEED):
    return build_events(count=count, visibility="private", seed=seed)


def write_ndjson(path, records):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with target.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")
            written += 1
    return target, written


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-count", type=int, default=DEFAULT_PUBLIC_COUNT)
    parser.add_argument("--private-count", type=int, default=DEFAULT_PRIVATE_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", default="data/public.ndjson")
    parser.add_argument("--private-output", default="data/private.ndjson")
    args = parser.parse_args()

    public_target, public_written = write_ndjson(
        args.output,
        build_public_events(count=args.public_count, seed=args.seed),
    )
    private_target, private_written = write_ndjson(
        args.private_output,
        build_private_events(count=args.private_count, seed=args.seed),
    )
    print(f"wrote {public_written:,} public events to {public_target}")
    print(f"wrote {private_written:,} private events to {private_target}")


if __name__ == "__main__":
    main()
