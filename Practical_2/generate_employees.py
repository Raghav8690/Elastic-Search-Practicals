"""Generate a reproducible employee dataset for the Elasticsearch practical.

Creates ``employees.json`` next to this script containing at least 100 records
with the fields required by the assignment:

    employee_id, name, department, designation, salary, city, joining_date, active
"""

import datetime as dt
import json
import os
import random

RECORD_COUNT = 120
START_ID = 101
SEED = 42

FIRST_NAMES = [
    "Rahul", "Priya", "Amit", "Sneha", "Vikram", "Anjali", "Rohan", "Neha",
    "Arjun", "Kavya", "Suresh", "Divya", "Manish", "Pooja", "Karan", "Ritu",
    "Sanjay", "Meera", "Ajay", "Shreya", "Nikhil", "Ananya", "Deepak", "Isha",
    "Vishal", "Tanvi", "Rajesh", "Sakshi", "Gaurav", "Nandini",
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Gupta", "Singh", "Reddy", "Nair", "Iyer",
    "Mehta", "Joshi", "Desai", "Rao", "Pillai", "Chowdhury", "Banerjee",
    "Kulkarni", "Malhotra", "Kapoor", "Agarwal", "Menon",
]

CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Pune", "Chennai", "Hyderabad",
    "Kolkata", "Ahmedabad",
]

DEPARTMENTS = {
    "Engineering": [
        "Software Engineer", "Senior Software Engineer", "DevOps Engineer",
        "QA Engineer", "Engineering Manager",
    ],
    "Sales": [
        "Sales Executive", "Account Manager", "Sales Manager",
        "Business Development Executive",
    ],
    "HR": ["HR Executive", "HR Manager", "Recruiter"],
    "Finance": ["Accountant", "Financial Analyst", "Finance Manager"],
    "Marketing": [
        "Marketing Executive", "Content Strategist", "Marketing Manager",
        "SEO Specialist",
    ],
    "Support": [
        "Support Engineer", "Customer Success Manager", "Support Lead",
    ],
    "Operations": [
        "Operations Executive", "Operations Manager", "Logistics Coordinator",
    ],
}

START_DATE = dt.date(2018, 1, 1)
END_DATE = dt.date(2025, 12, 31)


def salary_for(designation: str, rng: random.Random) -> int:
    if "Manager" in designation or "Lead" in designation:
        low, high = 90000, 160000
    elif "Senior" in designation:
        low, high = 70000, 125000
    else:
        low, high = 35000, 80000
    base = rng.randint(low, high)
    return int(round(base / 500.0) * 500)


def random_date(rng: random.Random) -> str:
    span = (END_DATE - START_DATE).days
    return (START_DATE + dt.timedelta(days=rng.randint(0, span))).isoformat()


def build_dataset(count: int = RECORD_COUNT, start_id: int = START_ID) -> list:
    rng = random.Random(SEED)
    records = []
    for offset in range(count):
        department = rng.choice(list(DEPARTMENTS))
        designation = rng.choice(DEPARTMENTS[department])
        records.append(
            {
                "employee_id": start_id + offset,
                "name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                "department": department,
                "designation": designation,
                "salary": salary_for(designation, rng),
                "city": rng.choice(CITIES),
                "joining_date": random_date(rng),
                "active": rng.random() > 0.15,
            }
        )
    return records


def main() -> None:
    records = build_dataset()
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "employees.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2)
        handle.write("\n")
    print(f"Wrote {len(records)} employee records to {out_path}")


if __name__ == "__main__":
    main()
