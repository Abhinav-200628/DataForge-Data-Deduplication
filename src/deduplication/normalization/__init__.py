"""Normalization package for field cleaning and entity standardization."""

from deduplication.normalization.customer_normalizer import NormalizedCustomer
from deduplication.normalization.product_normalizer import NormalizedProduct
from deduplication.normalization.text_cleaners import (
    clean_text,
    normalize_email,
    normalize_phone,
    normalize_postal_code,
    normalize_sku,
    normalize_street_address,
    normalize_tax_id,
    normalize_upc_ean,
)

__all__ = [
    "clean_text",
    "normalize_email",
    "normalize_phone",
    "normalize_postal_code",
    "normalize_sku",
    "normalize_street_address",
    "normalize_tax_id",
    "normalize_upc_ean",
    "NormalizedCustomer",
    "NormalizedProduct",
]
