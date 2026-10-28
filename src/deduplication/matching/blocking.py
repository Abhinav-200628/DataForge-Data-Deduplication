"""
Candidate pair generation via multi-pass blocking.

Avoids O(N^2) pairwise comparison explosions by grouping records into blocks
sharing phonetic or structural keys, then taking the union of candidate pairs.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, Sequence, TypeVar

from deduplication.normalization.customer_normalizer import NormalizedCustomer
from deduplication.normalization.product_normalizer import NormalizedProduct

T = TypeVar("T")

# Soundex mapping table
_SOUNDEX_MAP = {
    "B": "1", "F": "1", "P": "1", "V": "1",
    "C": "2", "G": "2", "J": "2", "K": "2", "Q": "2", "S": "2", "X": "2", "Z": "2",
    "D": "3", "T": "3",
    "L": "4",
    "M": "5", "N": "5",
    "R": "6",
}


def soundex(name: str) -> str:
    """Compute 4-character American Soundex phonetic code for a name."""
    if not name:
        return "0000"
    cleaned = "".join([c.upper() for c in name if c.isalpha()])
    if not cleaned:
        return "0000"

    first_char = cleaned[0]
    encoded = [first_char]
    prev_code = _SOUNDEX_MAP.get(first_char, "0")

    for char in cleaned[1:]:
        code = _SOUNDEX_MAP.get(char, "0")
        if code != "0" and code != prev_code:
            encoded.append(code)
            prev_code = code
        elif code == "0":
            prev_code = "0"
        if len(encoded) == 4:
            break

    # Pad with zeros if less than 4 chars
    while len(encoded) < 4:
        encoded.append("0")

    return "".join(encoded)


def get_customer_blocking_keys(record: NormalizedCustomer) -> list[str]:
    """Generate multi-pass blocking keys for customer records."""
    keys: list[str] = []

    # Pass 1: Phonetic Soundex of last name + 3-digit zip prefix
    if record.norm_last_name:
        snd = soundex(record.norm_last_name)
        zip_prefix = (record.norm_postal_code or "000")[:3]
        keys.append(f"CUST_SND_ZIP:{snd}_{zip_prefix}")

    # Pass 2: Exact phone number (or last 7 digits)
    if record.norm_phone:
        phone_suffix = record.norm_phone[-7:] if len(record.norm_phone) >= 7 else record.norm_phone
        keys.append(f"CUST_PHONE:{phone_suffix}")

    # Pass 3: Email domain + initial of last name
    if record.norm_email and "@" in record.norm_email:
        domain = record.norm_email.split("@")[-1].lower()
        last_initial = record.norm_last_name[:1].upper() if record.norm_last_name else "X"
        keys.append(f"CUST_EMAIL_DOMAIN:{domain}_{last_initial}")

    # Pass 4: Tax ID (SSN)
    if record.norm_tax_id:
        keys.append(f"CUST_TAX:{record.norm_tax_id}")

    return keys


def get_product_blocking_keys(record: NormalizedProduct) -> list[str]:
    """Generate multi-pass blocking keys for product records."""
    keys: list[str] = []

    # Pass 1: Brand + Category
    if record.norm_brand:
        cat = record.norm_category or "GENERIC"
        keys.append(f"PROD_BRAND_CAT:{record.norm_brand}_{cat}")

    # Pass 2: UPC prefix (first 6 digits)
    if record.norm_upc_ean:
        upc_prefix = record.norm_upc_ean[:6] if len(record.norm_upc_ean) >= 6 else record.norm_upc_ean
        keys.append(f"PROD_UPC_PREFIX:{upc_prefix}")

    # Pass 3: SKU prefix (first 4 alphanumeric characters)
    if record.norm_sku:
        sku_clean = record.norm_sku.replace("-", "")[:4]
        keys.append(f"PROD_SKU_PREFIX:{sku_clean}")

    return keys


def generate_candidate_pairs(
    records: Sequence[T],
    key_extractor: Callable[[T], list[str]],
    force_full_pairwise: bool = False,
) -> set[tuple[int, int]]:
    """
    Generate candidate index pairs (i, j) where i < j that share at least one blocking key.

    Args:
        records: List of normalized records.
        key_extractor: Function that extracts a list of blocking keys from a record.
        force_full_pairwise: If True (e.g. for small tests), compares all pairs without blocking.

    Returns:
        Set of unique candidate index tuples (i, j).
    """
    n = len(records)
    if n < 2:
        return set()

    # If small test or explicitly forced, do full pairwise
    if force_full_pairwise or n <= 25:
        pairs = set()
        for i in range(n):
            for j in range(i + 1, n):
                pairs.add((i, j))
        return pairs

    # Inverted index: key -> list of record indices
    index: dict[str, list[int]] = defaultdict(list)
    for idx, rec in enumerate(records):
        for key in key_extractor(rec):
            index[key].append(idx)

    # Union of pairs within each block
    candidate_pairs: set[tuple[int, int]] = set()
    for key, indices in index.items():
        # Avoid massive blocks (e.g. if key is too generic and matches > 2000 records)
        if len(indices) > 2500:
            continue
        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                idx_a, idx_b = indices[i], indices[j]
                if idx_a > idx_b:
                    idx_a, idx_b = idx_b, idx_a
                candidate_pairs.add((idx_a, idx_b))

    return candidate_pairs
