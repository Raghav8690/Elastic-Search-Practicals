"""Generate reproducible datasets for Practical 5 (compound queries + filtering).

Writes two files next to this script:

    employees.json   120 records (Practical 2/4 schema)
    products.json     60 records with nested reviews and a supplier object

Everything is deterministic (seed 42), so the notebook can assert exact counts.
"""

import datetime as dt
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 42

# ---------------------------------------------------------------------------
# Employees
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
# Products
# ---------------------------------------------------------------------------

CATEGORY_CODES = {
    "Electronics": "ELEC",
    "Home & Kitchen": "HOME",
    "Sports": "SPOR",
    "Books": "BOOK",
    "Fashion": "FASH",
    "Beauty": "BEAU",
}

# (name, brand, category, subcategory, price, tags)
CATALOGUE = [
    ("Wireless Noise-Cancelling Headphones", "Acme", "Electronics", "Headphones", 299.99,
     ["wireless", "audio", "noise-cancelling"]),
    ("Bluetooth Speaker Mini", "Nimbus", "Electronics", "Speakers", 59.99,
     ["bluetooth", "audio", "portable"]),
    ("Smart LED TV 43 inch", "Zenith", "Electronics", "Televisions", 32999.0,
     ["tv", "smart", "4k"]),
    ("Ultra Slim Laptop 14 inch", "Vertex", "Electronics", "Laptops", 78999.0,
     ["laptop", "portable", "office"]),
    ("Compact Digital Camera", "Lumina", "Electronics", "Cameras", 24999.0,
     ["camera", "photography"]),
    ("Wireless Charging Pad", "Orbit", "Electronics", "Accessories", 1499.0,
     ["wireless", "charging", "mobile"]),
    ("Wireless Noise-Cancelling Earbuds", "Acme", "Electronics", "Headphones", 7999.0,
     ["audio", "wireless", "earbuds"]),
    ("Smartphone Pro Max", "Pinnacle", "Electronics", "Smartphones", 129999.0,
     ["mobile", "smart", "camera"]),
    ("Portable Power Bank 20000mAh", "Nimbus", "Electronics", "Accessories", 1999.0,
     ["powerbank", "portable"]),
    ("4K Action Camera", "Lumina", "Electronics", "Cameras", 18999.0,
     ["camera", "action", "4k"]),

    ("Ceramic Coffee Mug", "Globex", "Home & Kitchen", "Mugs", 9.5,
     ["ceramic", "kitchen", "drinkware"]),
    ("Stainless Steel Water Bottle", "Globex", "Home & Kitchen", "Bottles", 799.0,
     ["steel", "bottle", "eco"]),
    ("Non-Stick Cookware Set", "Pinnacle", "Home & Kitchen", "Cookware", 3499.0,
     ["cookware", "kitchen", "nonstick"]),
    ("Ergonomic Office Chair", "Vertex", "Home & Kitchen", "Furniture", 12999.0,
     ["furniture", "office", "ergonomic"]),
    ("High-Speed Blender 600W", "Zenith", "Home & Kitchen", "Blenders", 2799.0,
     ["blender", "kitchen", "appliance"]),
    ("Classic Electric Kettle", "Orbit", "Home & Kitchen", "Appliances", 1199.0,
     ["kettle", "kitchen", "electric"]),
    ("Bamboo Cutting Board", "Lumina", "Home & Kitchen", "Kitchen Tools", 499.0,
     ["bamboo", "eco", "kitchen"]),
    ("Luxury Bed Sheet Set", "Acme", "Home & Kitchen", "Bedding", 2499.0,
     ["bedding", "cotton", "home"]),
    ("Vacuum Insulated Water Bottle", "Nimbus", "Home & Kitchen", "Bottles", 1299.0,
     ["flask", "insulated", "travel"]),
    ("Dinner Plate Set of 6", "Globex", "Home & Kitchen", "Dinnerware", 1899.0,
     ["ceramic", "dinnerware", "kitchen"]),

    ("Pro Yoga Mat", "Zenith", "Sports", "Yoga Mats", 1499.0,
     ["yoga", "fitness", "mat"]),
    ("Adjustable Dumbbell Set", "Vertex", "Sports", "Dumbbells", 4999.0,
     ["dumbbell", "fitness", "strength"]),
    ("Mountain Bike 21-Speed", "Pinnacle", "Sports", "Cycles", 18999.0,
     ["cycle", "outdoor", "sports"]),
    ("Running Shoes Air", "Lumina", "Sports", "Shoes", 3999.0,
     ["shoes", "running", "sports"]),
    ("Carbon Tennis Racket", "Acme", "Sports", "Rackets", 6999.0,
     ["tennis", "racket", "sports"]),
    ("Resistance Band Kit", "Orbit", "Sports", "Fitness Accessories", 899.0,
     ["fitness", "bands", "home"]),
    ("Steel Football", "Nimbus", "Sports", "Football", 1299.0,
     ["football", "outdoor", "sports"]),
    ("Badminton Racket Combo", "Globex", "Sports", "Rackets", 2199.0,
     ["badminton", "racket", "combo"]),
    ("Cricket Bat Kashmir Willow", "Vertex", "Sports", "Cricket", 3299.0,
     ["cricket", "bat", "sports"]),
    ("Foldable Treadmill", "Pinnacle", "Sports", "Fitness Equipment", 34999.0,
     ["treadmill", "fitness", "home"]),

    ("The Silent Horizon", "Lumina", "Books", "Fiction", 499.0,
     ["fiction", "novel", "bestseller"]),
    ("Data Structures Explained", "Vertex", "Books", "Textbooks", 899.0,
     ["education", "computers", "textbook"]),
    ("World History Compendium", "Acme", "Books", "Non-Fiction", 1299.0,
     ["history", "nonfiction"]),
    ("The Art of Cooking", "Globex", "Books", "Non-Fiction", 799.0,
     ["cooking", "nonfiction", "lifestyle"]),
    ("Galactic Adventures Comic", "Orbit", "Books", "Comics", 349.0,
     ["comic", "scifi", "graphic"]),
    ("Startup Playbook", "Pinnacle", "Books", "Business", 999.0,
     ["business", "startup", "nonfiction"]),
    ("Poems for Rainy Days", "Zenith", "Books", "Poetry", 399.0,
     ["poetry", "literature"]),
    ("Machine Learning Basics", "Nimbus", "Books", "Textbooks", 1499.0,
     ["education", "ai", "textbook"]),
    ("The Last Detective", "Lumina", "Books", "Fiction", 599.0,
     ["fiction", "thriller", "mystery"]),
    ("Biography of Innovators", "Vertex", "Books", "Biographies", 1099.0,
     ["biography", "history"]),

    ("Classic Cotton Shirt", "Acme", "Fashion", "Shirts", 1299.0,
     ["shirt", "cotton", "formal"]),
    ("Slim Fit Denim Jeans", "Globex", "Fashion", "Jeans", 1899.0,
     ["jeans", "denim", "casual"]),
    ("Leather Bomber Jacket", "Zenith", "Fashion", "Jackets", 5999.0,
     ["jacket", "leather", "winter"]),
    ("Urban Sneakers", "Nimbus", "Fashion", "Sneakers", 2999.0,
     ["sneakers", "casual", "shoes"]),
    ("Minimalist Wrist Watch", "Lumina", "Fashion", "Watches", 7499.0,
     ["watch", "accessory", "minimal"]),
    ("Silk Scarf", "Orbit", "Fashion", "Accessories", 1499.0,
     ["scarf", "silk", "accessory"]),
    ("Formal Blazer", "Vertex", "Fashion", "Blazers", 4999.0,
     ["blazer", "formal", "office"]),
    ("Sports Cap", "Pinnacle", "Fashion", "Accessories", 599.0,
     ["cap", "sports", "accessory"]),
    ("Woolen Sweater", "Acme", "Fashion", "Sweaters", 2199.0,
     ["sweater", "wool", "winter"]),
    ("Aviator Sunglasses", "Globex", "Fashion", "Eyewear", 1799.0,
     ["sunglasses", "eyewear", "summer"]),

    ("Vitamin C Face Serum", "Lumina", "Beauty", "Skincare", 899.0,
     ["skincare", "serum", "vitamin"]),
    ("Herbal Shampoo", "Orbit", "Beauty", "Haircare", 449.0,
     ["haircare", "herbal", "shampoo"]),
    ("Matte Lipstick Set", "Zenith", "Beauty", "Makeup", 1299.0,
     ["makeup", "lipstick", "matte"]),
    ("Luxury Perfume 100ml", "Pinnacle", "Beauty", "Fragrance", 4999.0,
     ["perfume", "fragrance", "luxury"]),
    ("Makeup Brush Kit", "Nimbus", "Beauty", "Tools", 999.0,
     ["makeup", "brush", "tools"]),
    ("Sunscreen SPF 50", "Vertex", "Beauty", "Skincare", 649.0,
     ["sunscreen", "skincare", "spf"]),
    ("Beard Trimmer Pro", "Acme", "Beauty", "Grooming", 1799.0,
     ["grooming", "trimmer", "beauty"]),
    ("Aloe Vera Gel", "Globex", "Beauty", "Skincare", 299.0,
     ["skincare", "aloe", "natural"]),
    ("Hair Dryer 1800W", "Zenith", "Beauty", "Styling", 1599.0,
     ["hair", "dryer", "styling"]),
    ("Nail Polish Combo", "Orbit", "Beauty", "Makeup", 549.0,
     ["makeup", "nails", "combo"]),
]

PRODUCT_START = dt.date(2023, 1, 1)
PRODUCT_END = dt.date(2025, 12, 31)

# Offsets that are deliberately out of stock (indices 3, 11, 23, 35, 47).
STOCK_ZERO_OFFSETS = {2, 10, 22, 34, 46}

REVIEW_AUTHORS = ["alice", "bob", "carol", "dave", "erin"]

REVIEW_COMMENTS = [
    "excellent quality and fast delivery",
    "good value for the price",
    "works as expected",
    "average quality, nothing special",
    "would buy again",
    "poor packaging but the product is fine",
    "loved it, highly recommended",
    "not great, expected better",
]

SUPPLIERS = [
    ("AcmeSupply", "IN", 7),
    ("GlobexTrade", "US", 14),
    ("NimbusLogistics", "CN", 21),
    ("ZenithDistributors", "DE", 10),
]


def build_reviews(offset, rng):
    if offset == 0:
        return [
            {"author": "alice", "rating": 5,
             "comment": "excellent quality and sound",
             "date": "2024-03-12"},
            {"author": "bob", "rating": 4,
             "comment": "good value for the price",
             "date": "2024-07-08"},
        ]

    if offset == 1:
        # Negative fixture for nested vs object: no single review satisfies
        # alice AND rating >= 4.
        return [
            {"author": "alice", "rating": 2,
             "comment": "not great, expected better",
             "date": "2024-02-20"},
            {"author": "bob", "rating": 5,
             "comment": "loved it, highly recommended",
             "date": "2024-09-15"},
        ]

    count = rng.randint(2, 3)
    reviews = []
    for _ in range(count):
        reviews.append({
            "author": rng.choice(REVIEW_AUTHORS),
            "rating": rng.randint(1, 5),
            "comment": rng.choice(REVIEW_COMMENTS),
            "date": random_date(rng, PRODUCT_START, PRODUCT_END),
        })
    return reviews


def build_products():
    rng = random.Random(SEED + 1)
    products = []

    for offset, (name, brand, category, subcategory, price, tags) in enumerate(CATALOGUE):
        index = offset + 1
        product_id = f"P{index:03d}"
        category_code = CATEGORY_CODES[category]

        stock = 0 if offset in STOCK_ZERO_OFFSETS else rng.randint(5, 150)
        rating = round(rng.uniform(2.5, 5.0), 1)
        warranty = rng.choice([0, 6, 12, 12, 12, 24, 24, 36])
        created_at = random_date(rng, PRODUCT_START, PRODUCT_END)
        supplier_name, supplier_country, lead_time = SUPPLIERS[offset % len(SUPPLIERS)]

        if "Headphones" in subcategory:
            description = (
                f"{brand} {name} with active noise cancellation and premium sound."
                f" Category: {category}, type: {subcategory}."
            )
        else:
            description = (
                f"{brand} {name}. {subcategory} product in {category}."
                f" Tags: {', '.join(tags)}."
            )

        reviews = build_reviews(offset, rng)

        products.append({
            "product_id": product_id,
            "name": name,
            "description": description,
            "brand": brand,
            "category": category,
            "subcategory": subcategory,
            "price": price,
            "stock": stock,
            "rating": rating,
            "tags": tags,
            "available": stock > 0,
            "created_at": created_at,
            "sku": f"SKU-{category_code}-{index:04d}",
            "warranty_months": warranty,
            "supplier": {
                "name": supplier_name,
                "country": supplier_country,
                "lead_time_days": lead_time,
            },
            "reviews": reviews,
            "reviews_flat": reviews,
        })

    return products


def main():
    employees = build_employees()
    products = build_products()

    with open(os.path.join(HERE, "employees.json"), "w", encoding="utf-8") as handle:
        json.dump(employees, handle, indent=2)

    with open(os.path.join(HERE, "products.json"), "w", encoding="utf-8") as handle:
        json.dump(products, handle, indent=2)

    print(f"employees: {len(employees)} -> employees.json")
    print("  active:", sum(1 for e in employees if e["active"]))
    print("  in Mumbai & active:",
          sum(1 for e in employees if e["active"] and e["city"] == "Mumbai"))
    print(f"products: {len(products)} -> products.json")
    print("  out of stock:", sum(1 for p in products if p["stock"] == 0))
    print("  electronics available:",
          sum(1 for p in products if p["category"] == "Electronics" and p["available"]))
    print("  reviews per product:", min(len(p["reviews"]) for p in products),
          "-", max(len(p["reviews"]) for p in products))
    print("  alice & rating>=4 products:",
          sum(1 for p in products
              if any(r["author"] == "alice" and r["rating"] >= 4 for r in p["reviews"])))
    print("  'set' products:",
          sum(1 for p in products if "set" in name_tokens(p["name"])))


def name_tokens(text):
    return [token.strip(".,") for token in text.lower().split()]


if __name__ == "__main__":
    main()
