"""
Reusable text and field-specific normalization utilities.

Provides deterministic cleaning for whitespace, phone numbers, emails,
addresses, tax IDs, SKUs, and UPC/EAN check digits.
"""

from __future__ import annotations

import re
from typing import Optional

# Pre-compiled regex patterns for performance
_WHITESPACE_REGEX = re.compile(r"\s+")
_NON_DIGIT_REGEX = re.compile(r"\D")
_NON_ALPHANUM_REGEX = re.compile(r"[^A-Za-z0-9]")
_STREET_SUFFIX_MAP = {
    "st": "street",
    "st.": "street",
    "ave": "avenue",
    "ave.": "avenue",
    "rd": "road",
    "rd.": "road",
    "blvd": "boulevard",
    "blvd.": "boulevard",
    "dr": "drive",
    "dr.": "drive",
    "ln": "lane",
    "ln.": "lane",
    "ct": "court",
    "ct.": "court",
    "pl": "place",
    "pl.": "place",
    "apt": "apartment",
    "apt.": "apartment",
    "ste": "suite",
    "ste.": "suite",
}


def clean_text(value: Optional[str]) -> Optional[str]:
    """Strip whitespace, collapse internal spaces, and handle null-like representations."""
    if value is None:
        return None
    val = _WHITESPACE_REGEX.sub(" ", str(value)).strip()
    if not val or val.lower() in {"none", "null", "nan", "na", "n/a", "undefined"}:
        return None
    return val


def normalize_email(email: Optional[str]) -> Optional[str]:
    """Lowercase and strip whitespace from email addresses."""
    cleaned = clean_text(email)
    if not cleaned:
        return None
    return cleaned.lower()


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    """
    Standardize phone numbers to digits-only.
    Converts 10-digit US numbers or 11-digit starting with 1 to a standard 10-digit format.
    """
    cleaned = clean_text(phone)
    if not cleaned:
        return None
    digits = _NON_DIGIT_REGEX.sub("", cleaned)
    if not digits:
        return None

    # Standardize US numbers: if 11 digits starting with 1, strip country code
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    return digits


def normalize_postal_code(zip_code: Optional[str]) -> Optional[str]:
    """Normalize US postal code to 5-digit standard."""
    cleaned = clean_text(zip_code)
    if not cleaned:
        return None
    digits = _NON_DIGIT_REGEX.sub("", cleaned)
    if len(digits) >= 5:
        return digits[:5]
    return cleaned.upper()


def normalize_tax_id(tax_id: Optional[str]) -> Optional[str]:
    """Normalize SSN/Tax ID to standard 9-digit format (XXX-XX-XXXX)."""
    cleaned = clean_text(tax_id)
    if not cleaned:
        return None
    digits = _NON_DIGIT_REGEX.sub("", cleaned)
    if len(digits) == 9:
        return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
    return cleaned


def normalize_street_address(address: Optional[str]) -> Optional[str]:
    """Standardize street address abbreviations and lowercase for similarity comparisons."""
    cleaned = clean_text(address)
    if not cleaned:
        return None

    tokens = cleaned.lower().replace(",", "").replace(".", "").split()
    standardized = [_STREET_SUFFIX_MAP.get(tok, tok) for tok in tokens]
    return " ".join(standardized)


def normalize_sku(sku: Optional[str]) -> Optional[str]:
    """Uppercase and strip punctuation/spaces for SKU comparison."""
    cleaned = clean_text(sku)
    if not cleaned:
        return None
    # Preserve alphanumeric characters and hyphens, uppercase
    return re.sub(r"[^A-Za-z0-9\-]", "", cleaned).upper()


def calculate_gtin_check_digit(digits_str: str) -> int:
    """Calculate the standard GTIN/UPC/EAN check digit using the modulo-10 algorithm."""
    # Reverse digits and multiply alternately by 3 and 1
    total = 0
    reversed_digits = digits_str[::-1]
    for idx, char in enumerate(reversed_digits):
        multiplier = 3 if idx % 2 == 0 else 1
        total += int(char) * multiplier
    return (10 - (total % 10)) % 10


def normalize_upc_ean(code: Optional[str]) -> Optional[str]:
    """
    Standardize UPC/EAN to digits-only.
    Validates check digit for 12-digit (UPC-A) and 13-digit (EAN-13) codes.
    """
    cleaned = clean_text(code)
    if not cleaned:
        return None
    digits = _NON_DIGIT_REGEX.sub("", cleaned)
    if len(digits) not in {8, 12, 13, 14}:
        # Return cleaned digits even if non-standard length
        return digits if digits else None

    # Validate check digit if 12 or 13 digits
    if len(digits) in {12, 13}:
        payload = digits[:-1]
        expected_check = calculate_gtin_check_digit(payload)
        actual_check = int(digits[-1])
        if expected_check != actual_check:
            # Check digit mismatch - still return digits but preserve identity
            return digits

    return digits
