"""Product record normalization and preparation for matching."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from deduplication.normalization.text_cleaners import (
    clean_text,
    normalize_sku,
    normalize_upc_ean,
)
from deduplication.schemas.product import ProductSourceRecord


@dataclass(frozen=True)
class NormalizedProduct:
    """Product record with normalized attributes and blocking keys."""
    raw: ProductSourceRecord
    source_system: str
    source_record_id: str
    norm_product_name: str
    norm_brand: str
    norm_sku: Optional[str]
    norm_upc_ean: Optional[str]
    norm_category: Optional[str]
    unit_price: Optional[float]
    currency: str
    updated_at: str

    @classmethod
    def from_source(cls, record: ProductSourceRecord) -> NormalizedProduct:
        p_name = clean_text(record.product_name) or ""
        brand = clean_text(record.brand) or ""
        cat = clean_text(record.category)
        curr = clean_text(record.currency) or "USD"

        return cls(
            raw=record,
            source_system=record.source_system.strip().upper(),
            source_record_id=record.source_record_id.strip(),
            norm_product_name=p_name.lower(),
            norm_brand=brand.upper(),
            norm_sku=normalize_sku(record.sku),
            norm_upc_ean=normalize_upc_ean(record.upc_ean),
            norm_category=cat.lower() if cat else None,
            unit_price=record.unit_price,
            currency=curr.upper(),
            updated_at=record.updated_at,
        )

