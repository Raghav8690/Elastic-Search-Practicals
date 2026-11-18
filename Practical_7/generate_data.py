"""Generate a reproducible real-estate dataset for Practical 7 (relevance).

Writes projects.json next to this script: 60 project records with the fields
needed for BM25 scoring, field boosting, function_score and the assignment.

Everything is deterministic (seed 42). A small set of hand-written fixtures
creates a controlled "palm beach" signal cluster:

    exact name      PJ011  Palm Beach
    partial name    PJ012  Palm Beach Residences
    partial name    PJ013  Palm Beach Enclave
    location only   PJ014  Royal Palm Grove (Palm Beach Road)
    builder only    PJ015  Crescent Bay (Palm Beach Developers)

"Palm Beach Road" and "Palm Beach Developers" are reserved for these fixtures,
and no generated project is named Skyline, so the field-importance experiment
(name-only PJ016 vs builder-only PJ018) stays deterministic.
"""

import datetime as dt
import json
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 42
PROJECT_COUNT = 60

LOCALITIES = {
    "Navi Mumbai": [
        "New Panvel", "Kharghar", "Kamothe", "Ulwe", "Vashi", "Nerul",
        "Belapur", "Airoli", "Taloja",
    ],
    "Mumbai": ["Andheri", "Borivali", "Chembur", "Mulund"],
    "Thane": ["Ghodbunder Road", "Majiwada", "Kolshet"],
    "Pune": ["Hinjewadi", "Wakad", "Baner", "Kharadi"],
}

# Generated builders exclude the fixture-only "Palm Beach Developers" and
# "Skyline Builders" so builder-only hits for those queries stay controlled.
BUILDERS = [
    "Greenfield Developers",
    "Palm Estates",
    "Delta Realtors",
    "Sunrise Developers",
    "Emerald Infra",
    "Horizon Builders",
    "Metro Developers",
    "Crescent Realty",
    "Urban Nest Builders",
]

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

# "Skyline" is reserved for the field-importance fixtures.
PREFIXES = [
    "Green", "Palm", "Sunrise", "Royal", "Crescent", "Emerald", "Silver",
    "Golden", "Lake", "River", "Hill", "Orchid", "Lotus", "Maple", "Cedar",
    "Horizon", "Prime", "Urban", "Metro", "Grand", "Elite", "Blue", "Pearl",
]

AMENITIES = [
    "clubhouse", "gym", "swimming pool", "children's play area",
    "jogging track", "landscaped garden", "indoor games", "24x7 security",
    "power backup", "covered parking", "amphitheatre", "sports court",
]

STATUSES = ["Ready to Move", "Under Construction", "New Launch"]

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
        "created_at": "2024-06-15",
        "rera_approved": True,
        "rating": 4.5,
        "reviews_count": 120,
        "views": 45000,
        "featured": True,
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
        "created_at": "2025-02-10",
        "rera_approved": True,
        "rating": 4.2,
        "reviews_count": 88,
        "views": 30000,
        "featured": False,
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
        "created_at": "2023-03-12",
        "rera_approved": True,
        "rating": 4.4,
        "reviews_count": 75,
        "views": 21000,
        "featured": False,
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
        "created_at": "2025-07-01",
        "rera_approved": False,
        "rating": 4.0,
        "reviews_count": 32,
        "views": 8000,
        "featured": False,
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
        "created_at": "2022-05-18",
        "rera_approved": True,
        "rating": 4.6,
        "reviews_count": 60,
        "views": 15000,
        "featured": True,
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
        "created_at": "2024-10-05",
        "rera_approved": True,
        "rating": 4.3,
        "reviews_count": 54,
        "views": 13000,
        "featured": False,
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
        "created_at": "2023-08-22",
        "rera_approved": True,
        "rating": 4.1,
        "reviews_count": 47,
        "views": 17000,
        "featured": False,
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
        "created_at": "2024-01-30",
        "rera_approved": True,
        "rating": 4.0,
        "reviews_count": 38,
        "views": 9500,
        "featured": False,
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
        "created_at": "2022-09-14",
        "rera_approved": True,
        "rating": 4.2,
        "reviews_count": 66,
        "views": 12000,
        "featured": False,
        "type_word": "residency",
    },
    {
        "project_id": "PJ010",
        "name": "Palm Springs",
        "locality": "Kamothe",
        "city": "Navi Mumbai",
        "builder": "Palm Estates",
        "property_type": "Apartment",
        "status": "Ready to Move",
        "price_min": 7000000,
        "price_max": 9800000,
        "bhk": ["2 BHK", "3 BHK"],
        "amenities": ["gym", "swimming pool", "covered parking"],
        "possession_date": "2024-02-28",
        "created_at": "2023-05-06",
        "rera_approved": True,
        "rating": 4.2,
        "reviews_count": 43,
        "views": 11000,
        "featured": False,
        "type_word": "apartment",
    },
    # --- assignment signal cluster (query: "palm beach") -------------------
    {
        "project_id": "PJ011",
        "name": "Palm Beach",
        "locality": "Palm Beach Road",
        "city": "Navi Mumbai",
        "builder": "Palm Beach Developers",
        "property_type": "Apartment",
        "status": "Ready to Move",
        "price_min": 11000000,
        "price_max": 16000000,
        "bhk": ["2 BHK", "3 BHK"],
        "amenities": ["clubhouse", "swimming pool", "24x7 security"],
        "possession_date": "2024-08-31",
        "created_at": "2024-04-10",
        "rera_approved": True,
        "rating": 4.8,
        "reviews_count": 210,
        "views": 52000,
        "featured": True,
        "type_word": "apartment",
    },
    {
        "project_id": "PJ012",
        "name": "Palm Beach Residences",
        "locality": "Palm Beach Road",
        "city": "Navi Mumbai",
        "builder": "Palm Beach Developers",
        "property_type": "Apartment",
        "status": "Under Construction",
        "price_min": 9800000,
        "price_max": 14000000,
        "bhk": ["2 BHK", "3 BHK"],
        "amenities": ["gym", "landscaped garden", "covered parking"],
        "possession_date": "2026-03-31",
        "created_at": "2025-01-20",
        "rera_approved": True,
        "rating": 4.5,
        "reviews_count": 95,
        "views": 24000,
        "featured": False,
        "type_word": "residences",
    },
    {
        "project_id": "PJ013",
        "name": "Palm Beach Enclave",
        "locality": "Palm Beach Road",
        "city": "Navi Mumbai",
        "builder": "Skyline Builders",
        "property_type": "Apartment",
        "status": "Ready to Move",
        "price_min": 10500000,
        "price_max": 15000000,
        "bhk": ["3 BHK", "4 BHK"],
        "amenities": ["clubhouse", "indoor games", "power backup"],
        "possession_date": "2023-11-05",
        "created_at": "2023-11-05",
        "rera_approved": True,
        "rating": 4.4,
        "reviews_count": 70,
        "views": 18000,
        "featured": False,
        "type_word": "apartments",
    },
    {
        "project_id": "PJ014",
        "name": "Royal Palm Grove",
        "locality": "Palm Beach Road",
        "city": "Navi Mumbai",
        "builder": "Palm Estates",
        "property_type": "Residence",
        "status": "Ready to Move",
        "price_min": 13500000,
        "price_max": 19000000,
        "bhk": ["3 BHK", "4 BHK"],
        "amenities": ["swimming pool", "sports court", "24x7 security"],
        "possession_date": "2024-09-01",
        "created_at": "2024-09-01",
        "rera_approved": True,
        "rating": 4.9,
        "reviews_count": 160,
        "views": 120000,
        "featured": True,
        "type_word": "residence",
    },
    {
        "project_id": "PJ015",
        "name": "Crescent Bay",
        "locality": "Nerul",
        "city": "Navi Mumbai",
        "builder": "Palm Beach Developers",
        "property_type": "Apartment",
        "status": "Under Construction",
        "price_min": 8500000,
        "price_max": 12000000,
        "bhk": ["2 BHK", "3 BHK"],
        "amenities": ["gym", "jogging track", "children's play area"],
        "possession_date": "2025-06-30",
        "created_at": "2025-06-01",
        "rera_approved": False,
        "rating": 4.0,
        "reviews_count": 40,
        "views": 9000,
        "featured": False,
        "type_word": "apartment",
    },
    # --- field-importance fixtures (query: "skyline") ----------------------
    {
        "project_id": "PJ016",
        "name": "Skyline",
        "locality": "Kharghar",
        "city": "Navi Mumbai",
        "builder": "Palm Estates",
        "property_type": "Apartment",
        "status": "Ready to Move",
        "price_min": 7600000,
        "price_max": 10500000,
        "bhk": ["2 BHK", "3 BHK"],
        "amenities": ["clubhouse", "gym", "covered parking"],
        "possession_date": "2024-01-31",
        "created_at": "2024-02-01",
        "rera_approved": True,
        "rating": 4.7,
        "reviews_count": 150,
        "views": 40000,
        "featured": True,
        "type_word": "apartment",
    },
    {
        "project_id": "PJ017",
        "name": "Skyline Grand",
        "locality": "Kharghar",
        "city": "Navi Mumbai",
        "builder": "Skyline Builders",
        "property_type": "Apartment",
        "status": "Under Construction",
        "price_min": 8200000,
        "price_max": 12500000,
        "bhk": ["2 BHK", "3 BHK"],
        "amenities": ["gym", "amphitheatre", "power backup"],
        "possession_date": "2026-09-30",
        "created_at": "2025-03-15",
        "rera_approved": True,
        "rating": 4.3,
        "reviews_count": 58,
        "views": 16000,
        "featured": False,
        "type_word": "apartments",
    },
    {
        "project_id": "PJ018",
        "name": "Crescent Bay Vista",
        "locality": "Nerul",
        "city": "Navi Mumbai",
        "builder": "Skyline Builders",
        "property_type": "Apartment",
        "status": "Ready to Move",
        "price_min": 9100000,
        "price_max": 12800000,
        "bhk": ["3 BHK"],
        "amenities": ["clubhouse", "swimming pool", "24x7 security"],
        "possession_date": "2023-07-31",
        "created_at": "2023-07-31",
        "rera_approved": True,
        "rating": 4.4,
        "reviews_count": 81,
        "views": 19000,
        "featured": False,
        "type_word": "apartment",
    },
]


def description_for(project):
    bhk = project["bhk"]
    home = " and ".join(bhk) + " homes" if bhk else "residential plots"
    amenities = ", ".join(project["amenities"][:3])
    rera = "RERA approved" if project["rera_approved"] else "RERA registration pending"
    return (
        f"{project['name']} in {project['locality']}, {project['city']} is a "
        f"{home} {project['type_word']} project by {project['builder']}. "
        f"Amenities include {amenities}. Possession by "
        f"{project['possession_date'][:7]}. {rera}. "
        f"Rated {project['rating']} from {project['reviews_count']} reviews."
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
        ["Apartment"] * 26
        + ["Residence"] * 9
        + ["Villa"] * 4
        + ["Row House"] * 2
        + ["Plot"] * 1
    )
    rng.shuffle(type_cycle)

    start = dt.date(2022, 1, 1)
    end = dt.date(2025, 12, 31)
    span = (end - start).days

    index = 0
    while len(projects) < PROJECT_COUNT:
        property_type = type_cycle[index % len(type_cycle)]
        suffixes, nouns, bhk_options = PROPERTY_TYPES[property_type]
        prefix = PREFIXES[(index * 5 + 2) % len(PREFIXES)]
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
        created = start + dt.timedelta(days=rng.randrange(span))
        possession = created + dt.timedelta(days=rng.randrange(180, 1200))
        price_min = rng.randrange(3000000, 20000000, 100000)
        price_max = price_min + rng.randrange(1000000, 9000000, 100000)

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
            "created_at": created.isoformat(),
            "rera_approved": rng.random() < 0.8,
            "rating": round(rng.uniform(3.5, 4.8), 1),
            "reviews_count": rng.randrange(5, 250, 5),
            "views": rng.randrange(500, 60000, 500),
            "featured": rng.random() < 0.1,
            "type_word": rng.choice(nouns),
        }
        project["description"] = description_for(project)
        del project["type_word"]
        projects.append(project)

    return projects


def words(text):
    return re.findall(r"[a-z0-9]+", str(text).lower())


def main():
    projects = build_projects()

    with open(os.path.join(HERE, "projects.json"), "w", encoding="utf-8") as handle:
        json.dump(projects, handle, indent=2)

    types = {}
    for project in projects:
        types[project["property_type"]] = types.get(project["property_type"], 0) + 1

    print(f"projects: {len(projects)} -> projects.json")
    print("  by type:", types)
    print("  featured:", sum(1 for p in projects if p["featured"]))
    print("  'palm' in name:", sum(1 for p in projects if "palm" in words(p["name"])))
    print("  'palm beach' phrase docs:", sum(
        1 for p in projects
        if "palm beach" in " ".join(words(p["name"]))
        or "palm beach" in " ".join(words(p["builder"]))
        or "palm beach" in " ".join(words(p["locality"]))
    ))
    print("  Skyline names:", [p["project_id"] for p in projects
                               if "skyline" in words(p["name"])])
    print("  Skyline builders:", [p["project_id"] for p in projects
                                  if "skyline" in words(p["builder"])])
    print("  Palm Beach Road docs:", [p["project_id"] for p in projects
                                      if p["locality"] == "Palm Beach Road"])
    print("  max views:", max(p["views"] for p in projects),
          "| rating range:", min(p["rating"] for p in projects),
          "-", max(p["rating"] for p in projects))


if __name__ == "__main__":
    main()
