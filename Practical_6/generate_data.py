"""Generate a reproducible real-estate dataset for Practical 6 (analysis).

Writes projects.json next to this script:

    projects.json   50 project records with fields for every text-analysis task

Everything is deterministic (seed 42), so the notebook can assert counts and
search-result sets instead of hard-coding random values.

The vocabulary is intentional: descriptions use apartment/flat,
builder/developer and residence/residency so the synonym analyzer has
something to match, and several names share prefixes/substrings for the
autocomplete and partial-search tasks.
"""

import datetime as dt
import json
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 42
PROJECT_COUNT = 50

LOCALITIES = {
    "Navi Mumbai": [
        "New Panvel", "Kharghar", "Kamothe", "Ulwe", "Vashi", "Nerul",
        "Belapur", "Airoli", "Taloja",
    ],
    "Mumbai": ["Andheri", "Borivali", "Dahisar", "Chembur", "Mulund"],
    "Thane": ["Ghodbunder Road", "Majiwada", "Kolshet"],
    "Pune": ["Hinjewadi", "Wakad", "Baner", "Kharadi"],
}

BUILDERS = [
    "Greenfield Developers",
    "Skyline Builders",
    "Palm Estates",
    "Delta Realtors",
    "Sunrise Developers",
    "Emerald Infra",
    "Horizon Builders",
    "Metro Developers",
    "Crescent Realty",
    "Urban Nest Builders",
]

# property_type -> (name suffixes, description nouns, typical BHK options)
PROPERTY_TYPES = {
    "Apartment": (
        ["Heights", "Apartments", "Towers", "Enclave", "Greens"],
        ["apartment", "apartments", "flat", "flats"],
        [["1 BHK", "2 BHK"], ["2 BHK", "3 BHK"], ["2 BHK", "3 BHK", "4 BHK"]],
    ),
    "Residence": (
        ["Residences", "Residency", "Greens", "Court"],
        ["residence", "residence", "residency", "residences"],
        [["2 BHK", "3 BHK"], ["3 BHK", "4 BHK"]],
    ),
    "Villa": (
        ["Villas", "Villa Park", "Meadows"],
        ["villa", "villas"],
        [["4 BHK"], ["4 BHK", "5 BHK"]],
    ),
    "Row House": (
        ["Row Houses", "Township", "Enclave"],
        ["row house", "row houses"],
        [["3 BHK", "4 BHK"]],
    ),
    "Plot": (
        ["Plots", "Landmark"],
        ["plot", "plots"],
        [[]],
    ),
}

PREFIXES = [
    "Green", "Skyline", "Palm", "Sunrise", "Royal", "Crescent", "Emerald",
    "Silver", "Golden", "Lake", "River", "Hill", "Orchid", "Lotus", "Maple",
    "Cedar", "Horizon", "Prime", "Urban", "Metro", "Grand", "Elite", "Blue",
    "Pearl",
]

AMENITIES = [
    "clubhouse", "gym", "swimming pool", "children's play area", "jogging track",
    "landscaped garden", "indoor games", "24x7 security", "power backup",
    "covered parking", "amphitheatre", "sports court",
]

STATUSES = ["Ready to Move", "Under Construction", "New Launch"]

# Hand-written fixtures that the notebook refers to by name.
FIXTURES = [
    {
        "project_id": "PJ001",
        "name": "Green Valley Residency",
        "locality": "New Panvel",
        "city": "Navi Mumbai",
        "builder": "Greenfield Developers",
        "property_type": "Apartment",
        "status": "Ready to Move",
        "price_min": 6500000,
        "price_max": 9500000,
        "bhk": ["2 BHK", "3 BHK"],
        "amenities": ["clubhouse", "gym", "swimming pool"],
        "possession_date": "2024-12-15",
        "rera_approved": True,
        "rating": 4.5,
        "type_word": "apartment",
    },
    {
        "project_id": "PJ002",
        "name": "Skyline Heights",
        "locality": "Kharghar",
        "city": "Navi Mumbai",
        "builder": "Skyline Builders",
        "property_type": "Apartment",
        "status": "Under Construction",
        "price_min": 7200000,
        "price_max": 11000000,
        "bhk": ["2 BHK", "3 BHK"],
        "amenities": ["gym", "jogging track", "covered parking"],
        "possession_date": "2026-06-30",
        "rera_approved": True,
        "rating": 4.2,
        "type_word": "apartments",
    },
    {
        "project_id": "PJ003",
        "name": "Palm Grove Residences",
        "locality": "Kamothe",
        "city": "Navi Mumbai",
        "builder": "Palm Estates",
        "property_type": "Residence",
        "status": "Ready to Move",
        "price_min": 9500000,
        "price_max": 14500000,
        "bhk": ["3 BHK", "4 BHK"],
        "amenities": ["clubhouse", "landscaped garden", "indoor games"],
        "possession_date": "2023-09-20",
        "rera_approved": True,
        "rating": 4.4,
        "type_word": "residence",
    },
    {
        "project_id": "PJ004",
        "name": "Sunrise Residency",
        "locality": "Panvel",
        "city": "Navi Mumbai",
        "builder": "Sunrise Developers",
        "property_type": "Apartment",
        "status": "New Launch",
        "price_min": 4200000,
        "price_max": 6800000,
        "bhk": ["1 BHK", "2 BHK"],
        "amenities": ["gym", "children's play area", "power backup"],
        "possession_date": "2027-03-31",
        "rera_approved": False,
        "rating": 4.0,
        "type_word": "flats",
    },
    {
        "project_id": "PJ005",
        "name": "Green Meadows Villas",
        "locality": "New Panvel",
        "city": "Navi Mumbai",
        "builder": "Greenfield Developers",
        "property_type": "Villa",
        "status": "Ready to Move",
        "price_min": 18000000,
        "price_max": 24000000,
        "bhk": ["4 BHK"],
        "amenities": ["swimming pool", "landscaped garden", "24x7 security"],
        "possession_date": "2022-11-10",
        "rera_approved": True,
        "rating": 4.6,
        "type_word": "villas",
    },
    {
        "project_id": "PJ006",
        "name": "Royal Palms",
        "locality": "Ulwe",
        "city": "Navi Mumbai",
        "builder": "Delta Realtors",
        "property_type": "Row House",
        "status": "Under Construction",
        "price_min": 12000000,
        "price_max": 16000000,
        "bhk": ["3 BHK", "4 BHK"],
        "amenities": ["clubhouse", "sports court", "covered parking"],
        "possession_date": "2026-12-01",
        "rera_approved": True,
        "rating": 4.3,
        "type_word": "row houses",
    },
    {
        "project_id": "PJ007",
        "name": "Sea Breeze Apartments",
        "locality": "Vashi",
        "city": "Navi Mumbai",
        "builder": "Emerald Infra",
        "property_type": "Apartment",
        "status": "Ready to Move",
        "price_min": 8800000,
        "price_max": 13000000,
        "bhk": ["2 BHK", "3 BHK"],
        "amenities": ["swimming pool", "amphitheatre", "24x7 security"],
        "possession_date": "2024-05-15",
        "rera_approved": True,
        "rating": 4.1,
        "type_word": "apartment",
    },
    {
        "project_id": "PJ008",
        "name": "Delta Residency",
        "locality": "Nerul",
        "city": "Navi Mumbai",
        "builder": "Delta Realtors",
        "property_type": "Apartment",
        "status": "Under Construction",
        "price_min": 5500000,
        "price_max": 8200000,
        "bhk": ["1 BHK", "2 BHK"],
        "amenities": ["gym", "jogging track", "power backup"],
        "possession_date": "2025-10-31",
        "rera_approved": True,
        "rating": 4.0,
        "type_word": "flat",
    },
    {
        "project_id": "PJ009",
        "name": "Horizon Residency",
        "locality": "Belapur",
        "city": "Navi Mumbai",
        "builder": "Horizon Builders",
        "property_type": "Residence",
        "status": "Ready to Move",
        "price_min": 9000000,
        "price_max": 13500000,
        "bhk": ["2 BHK", "3 BHK"],
        "amenities": ["clubhouse", "landscaped garden", "covered parking"],
        "possession_date": "2023-04-18",
        "rera_approved": True,
        "rating": 4.2,
        "type_word": "residency",
    },
    {
        "project_id": "PJ010",
        "name": "Palm Beach Residences",
        "locality": "Taloja",
        "city": "Navi Mumbai",
        "builder": "Palm Estates",
        "property_type": "Residence",
        "status": "New Launch",
        "price_min": 6100000,
        "price_max": 8900000,
        "bhk": ["2 BHK", "3 BHK"],
        "amenities": ["swimming pool", "children's play area", "sports court"],
        "possession_date": "2027-08-15",
        "rera_approved": False,
        "rating": 3.9,
        "type_word": "residences",
    },
]


def description_for(project):
    bhk = project["bhk"]
    if bhk:
        home = " and ".join(bhk) + " homes"
    else:
        home = "residential plots"
    amenities = ", ".join(project["amenities"][:3])
    rera = "RERA approved" if project["rera_approved"] else "RERA registration pending"
    return (
        f"{project['name']} in {project['locality']} is a {home} "
        f"{project['type_word']} project by {project['builder']}. "
        f"It offers {amenities}. Possession by "
        f"{project['possession_date'][:7]}. {rera}."
    )


def build_projects():
    rng = random.Random(SEED)
    projects = []
    used_names = set()

    for fixture in FIXTURES:
        project = dict(fixture)
        project["description"] = description_for(project)
        del project["type_word"]
        projects.append(project)
        used_names.add(project["name"])

    type_cycle = (
        ["Apartment"] * 24
        + ["Residence"] * 8
        + ["Villa"] * 4
        + ["Row House"] * 3
        + ["Plot"] * 1
    )
    rng.shuffle(type_cycle)

    start = dt.date(2022, 1, 1)
    end = dt.date(2028, 6, 30)
    span = (end - start).days

    index = 0
    while len(projects) < PROJECT_COUNT:
        property_type = type_cycle[index % len(type_cycle)]
        suffixes, nouns, bhk_options = PROPERTY_TYPES[property_type]
        prefix = PREFIXES[(index * 7 + 3) % len(PREFIXES)]
        suffix = suffixes[(index * 3 + 1) % len(suffixes)]
        name = f"{prefix} {suffix}"
        index += 1
        if name in used_names:
            continue
        used_names.add(name)

        city = rng.choice(list(LOCALITIES))
        locality = rng.choice(LOCALITIES[city])
        builder = rng.choice(BUILDERS)
        bhk = rng.choice(bhk_options)
        amenities = rng.sample(AMENITIES, 3)
        possession = start + dt.timedelta(days=rng.randrange(span))
        price_min = rng.randrange(3000000, 20000000, 100000)
        price_max = price_min + rng.randrange(1000000, 9000000, 100000)

        type_word = rng.choice(nouns)
        if property_type == "Apartment" and index % 6 == 0:
            type_word = rng.choice(["flat", "flats"])

        project = {
            "project_id": f"PJ{len(projects) + 1:03d}",
            "name": name,
            "locality": locality,
            "city": city,
            "builder": builder,
            "property_type": property_type,
            "status": rng.choice(STATUSES),
            "price_min": price_min,
            "price_max": price_max,
            "bhk": bhk,
            "amenities": amenities,
            "possession_date": possession.isoformat(),
            "rera_approved": rng.random() < 0.8,
            "rating": round(rng.uniform(3.5, 4.8), 1),
            "type_word": type_word,
        }
        project["description"] = description_for(project)
        del project["type_word"]
        projects.append(project)

    return projects


def words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def main():
    projects = build_projects()

    with open(os.path.join(HERE, "projects.json"), "w", encoding="utf-8") as handle:
        json.dump(projects, handle, indent=2)

    types = {}
    for project in projects:
        types[project["property_type"]] = types.get(project["property_type"], 0) + 1

    flat_baseline = sum(1 for p in projects if "flat" in words(p["description"])
                        or "flats" in words(p["description"]))
    apartment_group = sum(
        1 for p in projects
        if {"apartment", "apartments", "flat", "flats"} & set(words(p["description"]))
    )
    builder_group = sum(
        1 for p in projects
        if {"builder", "builders", "developer", "developers"}
        & set(words(p["description"]))
    )
    residence_group = sum(
        1 for p in projects
        if {"residence", "residences", "residency", "residencies"}
        & set(words(p["description"]))
    )

    print(f"projects: {len(projects)} -> projects.json")
    print("  by type:", types)
    print("  localities:", len({p["locality"] for p in projects}))
    print("  New Panvel:", sum(1 for p in projects if p["locality"] == "New Panvel"))
    print("  'flat' baseline:", flat_baseline,
          "| apartment synonym group:", apartment_group)
    print("  builder/developer group:", builder_group)
    print("  residence/residency group:", residence_group)
    print("  names with token prefix 'gre':",
          sum(1 for p in projects if any(w.startswith("gre") for w in words(p["name"]))))
    print("  names with token prefix 'resi':",
          sum(1 for p in projects if any(w.startswith("resi") for w in words(p["name"]))))
    print("  names containing 'alley':",
          sum(1 for p in projects if "alley" in p["name"].lower()))
    print("  'residency' descriptions:",
          sum(1 for p in projects if "residency" in words(p["description"])))


if __name__ == "__main__":
    main()
