"""Golden master record models for customers and products."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class MasterCustomer:
    """Consolidated golden customer entity."""
    master_id: str
    last_name: str
    updated_at: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    first_name: Optional[str] = None
    primary_email: Optional[str] = None
    secondary_emails: list[str] = field(default_factory=list)
    primary_phone: Optional[str] = None
    secondary_phones: list[str] = field(default_factory=list)
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "US"
    tax_id: Optional[str] = None
    date_of_birth: Optional[str] = None
    record_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert master customer to dictionary."""
        return {
            "master_id": self.master_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "primary_email": self.primary_email,
            "secondary_emails": self.secondary_emails,
            "primary_phone": self.primary_phone,
            "secondary_phones": self.secondary_phones,
            "street_address": self.street_address,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "tax_id": self.tax_id,
            "date_of_birth": self.date_of_birth,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "record_version": self.record_version,
        }


@dataclass
class MasterProduct:
    """Consolidated golden product entity."""
    master_id: str
    product_name: str
    brand: str
    updated_at: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    primary_sku: Optional[str] = None
    secondary_skus: list[str] = field(default_factory=list)
    primary_upc_ean: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[float] = None
    currency: str = "USD"
    record_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert master product to dictionary."""
        return {
            "master_id": self.master_id,
            "product_name": self.product_name,
            "brand": self.brand,
            "primary_sku": self.primary_sku,
            "secondary_skus": self.secondary_skus,
            "primary_upc_ean": self.primary_upc_ean,
            "category": self.category,
            "unit_price": self.unit_price,
            "currency": self.currency,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "record_version": self.record_version,
        }

