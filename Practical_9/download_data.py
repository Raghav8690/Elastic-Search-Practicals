"""Download the UCI Adult Census dataset and prepare Practical 9 inputs.

Writes:

    data/adult.csv            32,561 raw records with a header row
    data/adult_sample.csv     first 1,000 records for quick CLI runs
    data/adult_sample.json    first 1,000 records as a JSON array
    data/adult_invalid.csv    6 records, 2 deliberately invalid

The raw CSV preserves the original whitespace and "?" missing markers so the
notebook can demonstrate cleaning. Run with --force to download again.
"""

import argparse
import csv
import json
from pathlib import Path

import requests

URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"
HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
EXPECTED_ROWS = 32_561

COLUMNS = [
    "age", "workclass", "fnlwgt", "education", "education_num",
    "marital_status", "occupation", "relationship", "race", "sex",
    "capital_gain", "capital_loss", "hours_per_week", "native_country",
    "income",
]

MISSING_FIELDS = ("workclass", "occupation", "native_country")
INVALID_AGE = 5
INVALID_HOURS = 200


def download(force=False):
    DATA.mkdir(parents=True, exist_ok=True)
    target = DATA / "adult.csv"
    if target.exists() and not force:
        print("using existing", target)
        return target

    print("downloading", URL)
    response = requests.get(URL, timeout=90)
    response.raise_for_status()
    text = response.text
    lines = [line for line in text.splitlines() if line.strip()]

    if len(lines) != EXPECTED_ROWS:
        raise ValueError(f"expected {EXPECTED_ROWS} rows, got {len(lines)}")

    with target.open("w", encoding="utf-8", newline="") as handle:
        handle.write(",".join(COLUMNS) + "\n")
        for line in lines:
            handle.write(line + "\n")

    print("saved", target, f"({target.stat().st_size:,} bytes)")
    print("rows:", len(lines))
    return target


def read_records(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, skipinitialspace=True)
        return [dict(row) for row in reader]


def write_csv(path, records):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)


def build_samples(raw_path):
    records = read_records(raw_path)
    sample = records[:1000]

    sample_csv = DATA / "adult_sample.csv"
    write_csv(sample_csv, sample)

    sample_json = DATA / "adult_sample.json"
    sample_json.write_text(json.dumps(sample, indent=2), encoding="utf-8")

    invalid = [dict(record) for record in sample[:6]]
    invalid[1]["age"] = str(INVALID_AGE)
    invalid[3]["hours_per_week"] = str(INVALID_HOURS)
    invalid_csv = DATA / "adult_invalid.csv"
    write_csv(invalid_csv, invalid)

    print("sample CSV:", sample_csv, "| records:", len(sample))
    print("sample JSON:", sample_json, "| records:", len(sample))
    print("invalid CSV:", invalid_csv, "| records:", len(invalid),
          "| expected rejects: 2")


def report(raw_path):
    records = read_records(raw_path)
    missing = {
        field: sum(1 for record in records if record[field].strip() == "?")
        for field in MISSING_FIELDS
    }
    duplicates = len(records) - len({tuple(record.values()) for record in records})

    print("rows:", len(records))
    print("missing:", missing, "total:", sum(missing.values()))
    print("exact duplicates:", duplicates)
    print("income:", {
        label: sum(1 for record in records if record["income"].strip() == label)
        for label in ("<=50K", ">50K")
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="download again")
    args = parser.parse_args()

    raw_path = download(force=args.force)
    build_samples(raw_path)
    report(raw_path)


if __name__ == "__main__":
    main()
