"""
Synthetic data generator with deterministic random seeds and ground-truth isolation.

Generates realistic customer and product records with known duplicate clusters,
corroborated variations, hard conflicts, shared contacts, and malformed rows.
Crucially, expected answers/labels are stored in a separate JSON file, never leaked into CSVs.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import random
from typing import Any, Optional
import uuid

from deduplication.schemas.common import EntityType

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
]

STREETS = [
    "Main St", "Highland Ave", "Park Rd", "Maple Dr", "Oak Blvd", "Cedar Ln",
    "Pine St", "Elm Ave", "Washington St", "Lakeview Dr", "Sunset Blvd",
]

CITIES_STATES = [
    ("Springfield", "IL", "62701"),
    ("Austin", "TX", "78701"),
    ("Seattle", "WA", "98101"),
    ("Denver", "CO", "80201"),
    ("Boston", "MA", "02101"),
    ("Atlanta", "GA", "30301"),
    ("Columbus", "OH", "43201"),
]

PRODUCT_BRANDS = [
    ("Sony", ["WH-1000XM5", "Bravia 65-inch OLED", "PlayStation 5 Pro", "Alpha 7 IV Camera"]),
    ("Apple", ["iPhone 16 Pro", "MacBook Pro 16", "iPad Air 11-inch", "AirPods Max"]),
    ("Logitech", ["MX Master 3S Mouse", "MX Mechanical Keyboard", "Brio 4K Webcam", "G Pro X Headset"]),
    ("Dell", ["XPS 15 Laptop", "UltraSharp 32 4K Monitor", "Alienware Aurora R16", "PowerEdge Server"]),
    ("Bose", ["QuietComfort 45", "Smart Soundbar 900", "Ultra Open Earbuds", "SoundLink Flex"]),
]

SOURCE_SYSTEMS_CUSTOMER = ["CRM", "ERP", "BILLING", "WEB", "MARKETING"]
SOURCE_SYSTEMS_PRODUCT = ["PIM", "SAP", "SHOPIFY", "AMAZON", "SCRAPED"]


def generate_customer_dataset(
    count: int = 1000,
    seed: int = 42,
    duplicate_rate: float = 0.20,
    error_rate: float = 0.05,
    output_dir: Optional[Path] = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """
    Generate synthetic customer records with known duplicate groups and isolated ground-truth.

    Returns:
        (records_list, ground_truth_clusters_map)
    """
    rnd = random.Random(seed)
    records: list[dict[str, Any]] = []
    ground_truth: dict[str, list[str]] = {}  # cluster_id -> list of source_record_ids

    cluster_counter = 1
    record_counter = 1000

    target_duplicates = int(count * duplicate_rate)
    target_errors = int(count * error_rate)
    target_singles = count - target_duplicates - target_errors

    # 1. Generate Duplicate Clusters (Groups of 2 or 3 records)
    dupes_created = 0
    while dupes_created < target_duplicates:
        cluster_id = f"CUST-CLUSTER-{cluster_counter:05d}"
        cluster_records: list[str] = []

        first = rnd.choice(FIRST_NAMES)
        last = rnd.choice(LAST_NAMES)
        city, state, zip_code = rnd.choice(CITIES_STATES)
        street = rnd.choice(STREETS)
        phone = f"555{rnd.randint(1000000, 9999999)}"
        email = f"{first.lower()}.{last.lower()}{rnd.randint(10, 99)}@example.com"
        tax_id = f"{rnd.randint(100, 999)}-{rnd.randint(10, 99)}-{rnd.randint(1000, 9999)}"
        dob = f"{rnd.randint(1960, 2004)}-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}"

        cluster_size = min(rnd.choice([2, 2, 3]), target_duplicates - dupes_created + 1)
        systems = rnd.sample(SOURCE_SYSTEMS_CUSTOMER, cluster_size)

        for i in range(cluster_size):
            record_id = f"SRC-CUST-{record_counter:06d}"
            record_counter += 1
            cluster_records.append(record_id)

            rec_phone = phone
            rec_email = email
            rec_street = street
            rec_first = first

            # Add variations to simulate realistic dirty data
            if i == 1:
                # Slight name typo or nickname
                if len(first) > 4:
                    rec_first = first[:3]  # e.g. "Dan" for "Daniel"
                rec_street = street.replace("St", "Street").replace("Ave", "Avenue")
            elif i == 2:
                # Missing phone, slightly different timestamp
                rec_phone = ""

            records.append({
                "source_system": systems[i],
                "source_record_id": record_id,
                "first_name": rec_first,
                "last_name": last,
                "email": rec_email,
                "phone": rec_phone,
                "street_address": rec_street,
                "city": city,
                "state": state,
                "postal_code": zip_code,
                "country": "US",
                "tax_id": tax_id,
                "date_of_birth": dob,
                "updated_at": f"2026-0{rnd.randint(1, 6)}-{rnd.randint(1, 28):02d}T10:00:00Z",
            })

        ground_truth[cluster_id] = cluster_records
        cluster_counter += 1
        dupes_created += cluster_size

    # 2. Generate Single / Distinct Records
    for _ in range(target_singles):
        cluster_id = f"CUST-CLUSTER-{cluster_counter:05d}"
        record_id = f"SRC-CUST-{record_counter:06d}"
        cluster_counter += 1
        record_counter += 1

        first = rnd.choice(FIRST_NAMES)
        last = rnd.choice(LAST_NAMES)
        city, state, zip_code = rnd.choice(CITIES_STATES)
        street = rnd.choice(STREETS)
        phone = f"555{rnd.randint(1000000, 9999999)}"
        email = f"{first.lower()}.{last.lower()}{rnd.randint(100, 999)}@example.com"
        tax_id = f"{rnd.randint(100, 999)}-{rnd.randint(10, 99)}-{rnd.randint(1000, 9999)}"
        dob = f"{rnd.randint(1960, 2004)}-{rnd.randint(1, 12):02d}-{rnd.randint(1, 28):02d}"

        records.append({
            "source_system": rnd.choice(SOURCE_SYSTEMS_CUSTOMER),
            "source_record_id": record_id,
            "first_name": first,
            "last_name": last,
            "email": email,
            "phone": phone,
            "street_address": street,
            "city": city,
            "state": state,
            "postal_code": zip_code,
            "country": "US",
            "tax_id": tax_id,
            "date_of_birth": dob,
            "updated_at": f"2026-0{rnd.randint(1, 6)}-{rnd.randint(1, 28):02d}T12:00:00Z",
        })
        ground_truth[cluster_id] = [record_id]

    # 3. Generate Malformed / Bad Records (Destined for Quarantine)
    for _ in range(target_errors):
        record_id = f"SRC-CUST-ERR-{record_counter:06d}"
        record_counter += 1
        error_type = rnd.choice(["MISSING_LASTNAME", "BAD_EMAIL", "BAD_DATE", "MISSING_SYSTEM"])

        rec = {
            "source_system": "" if error_type == "MISSING_SYSTEM" else "CRM",
            "source_record_id": record_id,
            "first_name": "Test",
            "last_name": "" if error_type == "MISSING_LASTNAME" else "Malformed",
            "email": "not-an-email" if error_type == "BAD_EMAIL" else "valid@example.com",
            "phone": "555-9999",
            "street_address": "123 Error Way",
            "city": "Nowhere",
            "state": "IL",
            "postal_code": "00000",
            "country": "US",
            "tax_id": None,
            "date_of_birth": "invalid-dob" if error_type == "BAD_DATE" else "1990-01-01",
            "updated_at": "2026-01-01T00:00:00Z",
        }
        records.append(rec)
        # Quarantined rows have their own single distinct label
        ground_truth[f"QUARANTINE-{record_id}"] = [record_id]

    # Shuffle records deterministically so duplicates are scattered throughout the file
    rnd.shuffle(records)

    # Save to disk if output_dir is provided
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        csv_file = output_dir / f"customers_{count}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)

        labels_file = output_dir / f"customers_{count}_ground_truth.json"
        with open(labels_file, "w", encoding="utf-8") as f:
            json.dump(ground_truth, f, indent=2)

    return records, ground_truth


def generate_product_dataset(
    count: int = 1000,
    seed: int = 42,
    duplicate_rate: float = 0.20,
    error_rate: float = 0.05,
    output_dir: Optional[Path] = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """
    Generate synthetic product records with known duplicate groups and isolated ground-truth.
    """
    rnd = random.Random(seed)
    records: list[dict[str, Any]] = []
    ground_truth: dict[str, list[str]] = {}

    cluster_counter = 1
    record_counter = 5000

    target_duplicates = int(count * duplicate_rate)
    target_errors = int(count * error_rate)
    target_singles = count - target_duplicates - target_errors

    dupes_created = 0
    while dupes_created < target_duplicates:
        cluster_id = f"PROD-CLUSTER-{cluster_counter:05d}"
        cluster_records: list[str] = []

        brand, models = rnd.choice(PRODUCT_BRANDS)
        base_model = rnd.choice(models)
        upc = f"{rnd.randint(10000000000, 99999999999)}"
        base_sku = f"{brand[:3].upper()}-{rnd.randint(100, 999)}"
        price = round(rnd.uniform(49.99, 1299.99), 2)

        cluster_size = min(rnd.choice([2, 3]), target_duplicates - dupes_created + 1)
        systems = rnd.sample(SOURCE_SYSTEMS_PRODUCT, cluster_size)

        for i in range(cluster_size):
            record_id = f"SRC-PROD-{record_counter:06d}"
            record_counter += 1
            cluster_records.append(record_id)

            prod_name = f"{brand} {base_model}"
            prod_price = price
            prod_sku = base_sku

            if i == 1:
                # Slight word order variation or prefix
                prod_name = f"{base_model} by {brand}"
                prod_price = round(price * rnd.uniform(0.95, 1.05), 2)
            elif i == 2:
                prod_sku = f"{base_sku}-V2"

            records.append({
                "source_system": systems[i],
                "source_record_id": record_id,
                "product_name": prod_name,
                "brand": brand,
                "sku": prod_sku,
                "upc_ean": upc,
                "category": "Electronics",
                "unit_price": prod_price,
                "currency": "USD",
                "updated_at": f"2026-0{rnd.randint(1, 6)}-{rnd.randint(1, 28):02d}T09:00:00Z",
            })

        ground_truth[cluster_id] = cluster_records
        cluster_counter += 1
        dupes_created += cluster_size

    # Single distinct products
    for _ in range(target_singles):
        cluster_id = f"PROD-CLUSTER-{cluster_counter:05d}"
        record_id = f"SRC-PROD-{record_counter:06d}"
        cluster_counter += 1
        record_counter += 1

        brand, models = rnd.choice(PRODUCT_BRANDS)
        base_model = rnd.choice(models)
        prod_name = f"{brand} {base_model} Edition {rnd.randint(1, 99)}"
        upc = f"{rnd.randint(10000000000, 99999999999)}"
        sku = f"{brand[:3].upper()}-{rnd.randint(1000, 9999)}"
        price = round(rnd.uniform(29.99, 1999.99), 2)

        records.append({
            "source_system": rnd.choice(SOURCE_SYSTEMS_PRODUCT),
            "source_record_id": record_id,
            "product_name": prod_name,
            "brand": brand,
            "sku": sku,
            "upc_ean": upc,
            "category": "Electronics",
            "unit_price": price,
            "currency": "USD",
            "updated_at": f"2026-0{rnd.randint(1, 6)}-{rnd.randint(1, 28):02d}T11:00:00Z",
        })
        ground_truth[cluster_id] = [record_id]

    # Malformed products
    for _ in range(target_errors):
        record_id = f"SRC-PROD-ERR-{record_counter:06d}"
        record_counter += 1
        error_type = rnd.choice(["MISSING_BRAND", "NEGATIVE_PRICE", "NON_NUMERIC_PRICE"])

        rec = {
            "source_system": "SHOPIFY",
            "source_record_id": record_id,
            "product_name": "Broken Catalog Item",
            "brand": "" if error_type == "MISSING_BRAND" else "Generic",
            "sku": "BAD-SKU",
            "upc_ean": "000000",
            "category": "Misc",
            "unit_price": -25.00 if error_type == "NEGATIVE_PRICE" else ("FREE" if error_type == "NON_NUMERIC_PRICE" else 10.0),
            "currency": "USD",
            "updated_at": "2026-01-01T00:00:00Z",
        }
        records.append(rec)
        ground_truth[f"QUARANTINE-{record_id}"] = [record_id]

    rnd.shuffle(records)

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        csv_file = output_dir / f"products_{count}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)

        labels_file = output_dir / f"products_{count}_ground_truth.json"
        with open(labels_file, "w", encoding="utf-8") as f:
            json.dump(ground_truth, f, indent=2)

    return records, ground_truth
