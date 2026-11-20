"""Generate deterministic synthetic places for the Practical 12 geo lab.

The notebook imports ``build_places`` and ``build_districts`` and bulk-loads
them into Elasticsearch. The script can also write both datasets as
newline-delimited JSON:

    python generate_data.py --count 10000 --output data/places.ndjson

The generated coordinates are synthetic and clustered within 20 km of central
London. They do not represent real businesses.
"""

import argparse
import json
import math
import random
from pathlib import Path

DEFAULT_COUNT = 10_000
DEFAULT_SEED = 42
CENTER = {"lat": 51.5074, "lon": -0.1278}
MAX_RADIUS_KM = 20.0
KM_PER_DEGREE_LAT = 111.32
CATEGORIES = [
    "cafe",
    "restaurant",
    "pharmacy",
    "grocery",
    "bank",
    "gym",
    "library",
    "hotel",
]
NAME_PREFIXES = [
    "Thames",
    "Camden",
    "Soho",
    "Kensington",
    "Brixton",
    "Shoreditch",
    "Chelsea",
    "Islington",
    "Greenwich",
    "Hackney",
    "Fulham",
    "Ealing",
    "Clapham",
    "Paddington",
    "Southbank",
    "Canary",
    "Hampstead",
    "Battersea",
    "Mayfair",
    "Richmond",
]
PLACE_FIELDS = [
    "place_id",
    "name",
    "category",
    "latitude",
    "longitude",
    "location",
    "rating",
    "capacity",
    "open_now",
]
DISTRICT_FIELDS = ["district_id", "name", "center", "boundary"]


def _rectangle(lon_min, lon_max, lat_min, lat_max):
    """Return a closed counter-clockwise GeoJSON polygon in lon/lat order."""
    ring = [
        [lon_min, lat_min],
        [lon_max, lat_min],
        [lon_max, lat_max],
        [lon_min, lat_max],
        [lon_min, lat_min],
    ]
    return {"type": "polygon", "coordinates": [ring]}


DISTRICTS = [
    {
        "district_id": "district-central",
        "name": "Central",
        "center": {"lat": 51.5100, "lon": -0.1250},
        "boundary": _rectangle(-0.15, -0.10, 51.49, 51.53),
    },
    {
        "district_id": "district-north",
        "name": "North",
        "center": {"lat": 51.5550, "lon": -0.1250},
        "boundary": _rectangle(-0.15, -0.10, 51.53, 51.58),
    },
    {
        "district_id": "district-south",
        "name": "South",
        "center": {"lat": 51.4650, "lon": -0.1250},
        "boundary": _rectangle(-0.15, -0.10, 51.44, 51.49),
    },
    {
        "district_id": "district-east",
        "name": "East",
        "center": {"lat": 51.5100, "lon": -0.0500},
        "boundary": _rectangle(-0.10, -0.00, 51.49, 51.53),
    },
    {
        "district_id": "district-west",
        "name": "West",
        "center": {"lat": 51.5100, "lon": -0.2000},
        "boundary": _rectangle(-0.25, -0.15, 51.49, 51.53),
    },
]


def build_places(count=DEFAULT_COUNT, seed=DEFAULT_SEED):
    """Yield exactly ``count`` deterministic synthetic place documents."""
    if count < 1:
        raise ValueError("count must be positive")

    rng = random.Random(seed)
    lon_scale = KM_PER_DEGREE_LAT * math.cos(math.radians(CENTER["lat"]))
    for sequence in range(1, count + 1):
        radius_km = MAX_RADIUS_KM * math.sqrt(rng.random())
        angle = rng.uniform(0, 2 * math.pi)
        latitude = round(
            CENTER["lat"] + (radius_km * math.sin(angle)) / KM_PER_DEGREE_LAT,
            6,
        )
        longitude = round(
            CENTER["lon"] + (radius_km * math.cos(angle)) / lon_scale,
            6,
        )
        category = rng.choice(CATEGORIES)
        yield {
            "place_id": f"PLC-{sequence:06d}",
            "name": f"{rng.choice(NAME_PREFIXES)} {category.title()} {sequence:05d}",
            "category": category,
            "latitude": latitude,
            "longitude": longitude,
            "location": {"lat": latitude, "lon": longitude},
            "rating": round(rng.uniform(3.0, 5.0), 1),
            "capacity": rng.randint(5, 500),
            "open_now": rng.random() < 0.7,
        }


def build_districts():
    """Yield a fresh copy of the five synthetic district documents."""
    for district in DISTRICTS:
        yield {
            "district_id": district["district_id"],
            "name": district["name"],
            "center": dict(district["center"]),
            "boundary": {
                "type": district["boundary"]["type"],
                "coordinates": [
                    [list(point) for point in ring]
                    for ring in district["boundary"]["coordinates"]
                ],
            },
        }


def write_ndjson(path, count=DEFAULT_COUNT, seed=DEFAULT_SEED):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with target.open("w", encoding="utf-8") as handle:
        for record in build_places(count=count, seed=seed):
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")
            written += 1
    return target, written


def write_districts_ndjson(path):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with target.open("w", encoding="utf-8") as handle:
        for record in build_districts():
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")
            written += 1
    return target, written


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--output",
        default="data/places.ndjson",
        help="newline-delimited JSON output path for places",
    )
    parser.add_argument(
        "--districts-output",
        default="data/districts.ndjson",
        help="newline-delimited JSON output path for districts",
    )
    args = parser.parse_args()

    target, written = write_ndjson(args.output, count=args.count, seed=args.seed)
    print(f"wrote {written:,} places to {target}")
    print(f"size: {target.stat().st_size:,} bytes")

    districts_target, districts_written = write_districts_ndjson(
        args.districts_output
    )
    print(f"wrote {districts_written:,} districts to {districts_target}")


if __name__ == "__main__":
    main()
