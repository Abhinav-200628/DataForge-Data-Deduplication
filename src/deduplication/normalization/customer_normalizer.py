"""Customer record normalization and preparation for matching."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from deduplication.normalization.text_cleaners import (
    clean_text,
    normalize_email,
    normalize_phone,
    normalize_postal_code,
    normalize_street_address,
    normalize_tax_id,
)
from deduplication.schemas.customer import CustomerSourceRecord


@dataclass(frozen=True)
class NormalizedCustomer:
    """Customer record with normalized attributes and blocking keys."""
    raw: CustomerSourceRecord
    source_system: str
    source_record_id: str
    norm_first_name: Optional[str]
    norm_last_name: str
    norm_full_name: str
    norm_email: Optional[str]
    norm_phone: Optional[str]
    norm_street_address: Optional[str]
    norm_city: Optional[str]
    norm_state: Optional[str]
    norm_postal_code: Optional[str]
    norm_country: str
    norm_tax_id: Optional[str]
    norm_date_of_birth: Optional[str]
    updated_at: str

    @classmethod
    def from_source(cls, record: CustomerSourceRecord) -> NormalizedCustomer:
        first = clean_text(record.first_name)
        last = clean_text(record.last_name) or ""
        norm_first = first.lower() if first else None
        norm_last = last.lower()

        full_name_parts = [p for p in (norm_first, norm_last) if p]
        norm_full_name = " ".join(full_name_parts)

        city = clean_text(record.city)
        state = clean_text(record.state)

        return cls(
            raw=record,
            source_system=record.source_system.strip().upper(),
            source_record_id=record.source_record_id.strip(),
            norm_first_name=norm_first,
            norm_last_name=norm_last,
            norm_full_name=norm_full_name,
            norm_email=normalize_email(record.email),
            norm_phone=normalize_phone(record.phone),
            norm_street_address=normalize_street_address(record.street_address),
            norm_city=city.lower() if city else None,
            norm_state=state.upper() if state else None,
            norm_postal_code=normalize_postal_code(record.postal_code),
            norm_country=(clean_text(record.country) or "US").upper(),
            norm_tax_id=normalize_tax_id(record.tax_id),
            norm_date_of_birth=clean_text(record.date_of_birth),
            updated_at=record.updated_at,
        )
