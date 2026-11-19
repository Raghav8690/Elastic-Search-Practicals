"""Generate reproducible datasets for Practical 8 (aggregations).

Writes two files next to this script:

    employees.json   120 records (Practical 2/4 schema)
    products.json     72 records across 12 categories with nested reviews

Everything is deterministic (seed 42), so the notebook can assert exact counts.
Products are spread over 30 of the 36 months in 2023-2025 so the monthly
date_histogram always contains six empty buckets.
"""

import calendar
import datetime as dt
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 42

# ---------------------------------------------------------------------------
# Employees (same generator as Practical 5, so results stay familiar)
# ---------------------------------------------------------------------------

EMPLOYEE_COUNT = 120
EMPLOYEE_START_ID = 101

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


def salary_for(designation, rng):
    if "Manager" in designation or "Lead" in designation:
        low, high = 90000, 160000
    elif "Senior" in designation:
        low, high = 70000, 125000
    else:
        low, high = 35000, 80000
    return int(round(rng.randint(low, high) / 500.0) * 500)


def random_date(rng, start=START_DATE, end=END_DATE):
    span = (end - start).days
    return (start + dt.timedelta(days=rng.randint(0, span))).isoformat()


def build_employees(count=EMPLOYEE_COUNT, start_id=EMPLOYEE_START_ID):
    rng = random.Random(SEED)
    departments = list(DEPARTMENTS)
    employees = []

    for offset in range(count):
        employee_id = start_id + offset
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        department = departments[offset % len(departments)]
        options = DEPARTMENTS[department]
        designation = options[(offset // len(departments)) % len(options)]

        record = {
            "employee_id": employee_id,
            "name": f"{first} {last}",
            "department": department,
            "designation": designation,
            "salary": salary_for(designation, rng),
            "city": rng.choice(CITIES),
            "joining_date": random_date(rng),
            "active": rng.random() < 0.7,
        }

        if rng.random() < 0.8:
            record["email"] = f"{first}.{last}{employee_id}@example.com".lower()

        if rng.random() < 0.5:
            record["bonus"] = float(rng.choice([5000, 10000, 15000, 25000, 40000]))

        employees.append(record)

    return employees


# ---------------------------------------------------------------------------
# Products -- 12 categories x 6 products = 72 documents
# ---------------------------------------------------------------------------

BRANDS = [
    "Acme", "Nimbus", "Zenith", "Vertex", "Lumina", "Orbit",
    "Pinnacle", "Globex", "Northwind", "Apex", "Quantum", "Terra",
]

# category -> (code, [ (name, subcategory, price) ... ])
CATALOGUE = {
    "Electronics": ("ELEC", [
        ("Wireless Noise-Cancelling Headphones", "Headphones", 299.99),
        ("Ultra Slim Laptop 14 inch", "Laptops", 78999.0),
        ("Smart LED TV 43 inch", "Televisions", 32999.0),
        ("Bluetooth Speaker Mini", "Speakers", 59.99),
        ("Compact Digital Camera", "Cameras", 24999.0),
        ("Wireless Charging Pad", "Accessories", 1499.0),
    ]),
    "Home & Kitchen": ("HOME", [
        ("Ceramic Coffee Mug", "Mugs", 9.5),
        ("Non-Stick Cookware Set", "Cookware", 3499.0),
        ("Ergonomic Office Chair", "Furniture", 12999.0),
        ("High-Speed Blender 600W", "Blenders", 2799.0),
        ("Bamboo Cutting Board", "Kitchen Tools", 499.0),
        ("Luxury Bed Sheet Set", "Bedding", 2499.0),
    ]),
    "Fashion": ("FASH", [
        ("Classic Cotton Shirt", "Shirts", 1299.0),
        ("Slim Fit Denim Jeans", "Jeans", 1899.0),
        ("Leather Bomber Jacket", "Jackets", 5999.0),
        ("Urban Sneakers", "Sneakers", 2999.0),
        ("Minimalist Wrist Watch", "Watches", 7499.0),
        ("Aviator Sunglasses", "Eyewear", 1799.0),
    ]),
    "Books": ("BOOK", [
        ("The Silent Horizon", "Fiction", 499.0),
        ("Data Structures Explained", "Textbooks", 899.0),
        ("World History Compendium", "Non-Fiction", 1299.0),
        ("Galactic Adventures Comic", "Comics", 349.0),
        ("Startup Playbook", "Business", 999.0),
        ("Machine Learning Basics", "Textbooks", 1499.0),
    ]),
    "Beauty": ("BEAU", [
        ("Vitamin C Face Serum", "Skincare", 899.0),
        ("Herbal Shampoo", "Haircare", 449.0),
        ("Matte Lipstick Set", "Makeup", 1299.0),
        ("Luxury Perfume 100ml", "Fragrance", 4999.0),
        ("Beard Trimmer Pro", "Grooming", 1799.0),
        ("Sunscreen SPF 50", "Skincare", 649.0),
    ]),
    "Sports": ("SPOR", [
        ("Pro Yoga Mat", "Yoga Mats", 1499.0),
        ("Adjustable Dumbbell Set", "Dumbbells", 4999.0),
        ("Mountain Bike 21-Speed", "Cycles", 18999.0),
        ("Running Shoes Air", "Shoes", 3999.0),
        ("Carbon Tennis Racket", "Rackets", 6999.0),
        ("Foldable Treadmill", "Fitness Equipment", 34999.0),
    ]),
    "Toys": ("TOYS", [
        ("Building Blocks 500 Pieces", "Building Sets", 2499.0),
        ("Remote Control Car", "Vehicles", 1799.0),
        ("Wooden Puzzle Set", "Puzzles", 699.0),
        ("Plush Teddy Bear", "Soft Toys", 899.0),
        ("Board Game Strategy", "Board Games", 1499.0),
        ("Kids Art Kit", "Art & Craft", 599.0),
    ]),
    "Grocery": ("GROC", [
        ("Organic Basmati Rice 5kg", "Staples", 899.0),
        ("Cold Pressed Olive Oil 1L", "Oils", 1299.0),
        ("Almonds Premium 500g", "Dry Fruits", 749.0),
        ("Green Tea 100 Bags", "Beverages", 449.0),
        ("Dark Chocolate Pack", "Snacks", 299.0),
        ("Whole Wheat Flour 10kg", "Staples", 499.0),
    ]),
    "Automotive": ("AUTO", [
        ("Car Phone Mount", "Accessories", 499.0),
        ("Engine Oil 5L", "Lubricants", 2499.0),
        ("Dash Camera Full HD", "Electronics", 4499.0),
        ("Car Vacuum Cleaner", "Cleaning", 1899.0),
        ("All-Weather Floor Mats", "Interior", 2999.0),
        ("Portable Tire Inflator", "Tools", 2199.0),
    ]),
    "Garden": ("GARD", [
        ("Garden Tool Set", "Tools", 1499.0),
        ("Solar Garden Lights Pack", "Lighting", 1799.0),
        ("Indoor Plant Pot Set", "Planters", 899.0),
        ("Watering Can 5L", "Watering", 399.0),
        ("Hedge Trimmer Electric", "Power Tools", 6499.0),
        ("Outdoor Patio Chair", "Furniture", 8999.0),
    ]),
    "Office": ("OFFI", [
        ("Ergonomic Wireless Mouse", "Computer Accessories", 1299.0),
        ("A4 Printer Paper 500 Sheets", "Paper", 349.0),
        ("Standing Desk Converter", "Furniture", 11999.0),
        ("Noise-Cancelling Headset", "Audio", 4999.0),
        ("Desk Organizer Set", "Organization", 799.0),
        ("Laser Printer Compact", "Printers", 18999.0),
    ]),
    "Pet Supplies": ("PETS", [
        ("Dog Food Premium 10kg", "Food", 2499.0),
        ("Cat Scratching Post", "Furniture", 1899.0),
        ("Pet Grooming Kit", "Grooming", 1299.0),
        ("Chew Toy Pack", "Toys", 499.0),
        ("Pet Bed Large", "Beds", 2299.0),
        ("Aquarium Starter Kit", "Aquarium", 4499.0),
    ]),
}

PRODUCT_START = dt.date(2023, 1, 1)
PRODUCT_END = dt.date(2025, 12, 31)

# Six deliberately empty months so the date_histogram has zero buckets.
EMPTY_MONTHS = {
    (2023, 2), (2023, 7), (2024, 1), (2024, 8), (2025, 3), (2025, 9),
}

# Six deliberately out-of-stock products.
STOCK_ZERO_OFFSETS = {2, 13, 27, 40, 55, 68}

REVIEW_AUTHORS = [
    "alice", "bob", "carol", "dave", "erin", "frank", "grace", "heidi",
    "ivan", "judy", "mallory", "niaj", "olivia", "peggy", "rupert",
    "sybil", "trent", "uma", "victor", "wendy",
]

REVIEW_COMMENTS = [
    "excellent quality and fast delivery",
    "good value for the price",
    "works as expected",
    "average quality, nothing special",
    "would buy again",
    "poor packaging but the product is fine",
    "loved it, highly recommended",
    "not great, expected better",
    "exceeded my expectations",
    "decent product for everyday use",
]

SUPPLIERS = [
    ("AcmeSupply", "IN", 7),
    ("GlobexTrade", "US", 14),
    ("NimbusLogistics", "CN", 21),
    ("ZenithDistributors", "DE", 10),
    ("VertexGlobal", "JP", 12),
    ("OrbitExports", "GB", 18),
]

ALL_MONTHS = [
    (year, month)
    for year in (2023, 2024, 2025)
    for month in range(1, 13)
]
ACTIVE_MONTHS = [m for m in ALL_MONTHS if m not in EMPTY_MONTHS]


def date_in_month(rng, year, month):
    day = rng.randint(1, 28)
    return dt.date(year, month, day).isoformat()


def build_reviews(rng, created_at):
    count = rng.randint(1, 4)
    created = dt.date.fromisoformat(created_at)
    span = (PRODUCT_END - created).days
    reviews = []

    for _ in range(count):
        review_date = created + dt.timedelta(days=rng.randint(0, span))
        reviews.append({
            "author": rng.choice(REVIEW_AUTHORS),
            "rating": rng.randint(1, 5),
            "comment": rng.choice(REVIEW_COMMENTS),
            "date": review_date.isoformat(),
        })

    return reviews


def build_products():
    rng = random.Random(SEED + 1)
    products = []
    offset = 0

    for category, (code, items) in CATALOGUE.items():
        for name, subcategory, price in items:
            index = offset + 1
            year, month = ACTIVE_MONTHS[offset % len(ACTIVE_MONTHS)]
            created_at = date_in_month(rng, year, month)
            stock = 0 if offset in STOCK_ZERO_OFFSETS else rng.randint(5, 200)
            brand = BRANDS[offset % len(BRANDS)]
            supplier_name, supplier_country, lead_time = SUPPLIERS[offset % len(SUPPLIERS)]
            slug = category.lower().replace(" & ", "-").replace(" ", "-")
            tags = [subcategory.lower(), slug, "sale" if offset % 3 == 0 else "featured"]
            reviews = build_reviews(rng, created_at)

            products.append({
                "product_id": f"P{index:03d}",
                "name": name,
                "description": (
                    f"{brand} {name}. {subcategory} product in {category}."
                    f" Tags: {', '.join(tags)}."
                ),
                "brand": brand,
                "category": category,
                "subcategory": subcategory,
                "price": price,
                "stock": stock,
                "rating": round(rng.uniform(2.5, 5.0), 1),
                "tags": tags,
                "available": stock > 0,
                "created_at": created_at,
                "sku": f"SKU-{code}-{index:04d}",
                "warranty_months": rng.choice([0, 6, 12, 12, 12, 24, 24, 36]),
                "supplier": {
                    "name": supplier_name,
                    "country": supplier_country,
                    "lead_time_days": lead_time,
                },
                "reviews": reviews,
            })
            offset += 1

    return products


def main():
    employees = build_employees()
    products = build_products()

    with open(os.path.join(HERE, "employees.json"), "w", encoding="utf-8") as handle:
        json.dump(employees, handle, indent=2)

    with open(os.path.join(HERE, "products.json"), "w", encoding="utf-8") as handle:
        json.dump(products, handle, indent=2)

    review_total = sum(len(p["reviews"]) for p in products)
    review_ratings = [r["rating"] for p in products for r in p["reviews"]]

    print(f"employees: {len(employees)} -> employees.json")
    print("  active:", sum(1 for e in employees if e["active"]))
    print("  departments:", len({e["department"] for e in employees}))
    print("  cities:", len({e["city"] for e in employees}))
    print("  bonus present:", sum(1 for e in employees if "bonus" in e))
    print(f"products: {len(products)} -> products.json")
    print("  categories:", len({p["category"] for p in products}))
    print("  per category:", sorted({p["category"]: 0 for p in products}))
    print("  out of stock:", sum(1 for p in products if p["stock"] == 0))
    print("  inventory:", sum(p["stock"] for p in products))
    print("  price sum:", round(sum(p["price"] for p in products), 2))
    print("  months covered:", len({p["created_at"][:7] for p in products}))
    print("  reviews:", review_total,
          "avg rating:", round(sum(review_ratings) / len(review_ratings), 4))


if __name__ == "__main__":
    main()
