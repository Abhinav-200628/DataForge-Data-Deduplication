"""Product schema definition and row-level type validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from deduplication.schemas.common import RejectionCode, ValidationErrorDetail


@dataclass(frozen=True)
class ProductSourceRecord:
    """Strictly typed product record as ingested from an inventory or catalog source."""
    source_system: str
    source_record_id: str
    product_name: str
    brand: str
    updated_at: str
    sku: Optional[str] = None
    upc_ean: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[float] = None
    currency: Optional[str] = "USD"

    @classmethod
    def from_row(
        cls, row: dict[str, Any]
    ) -> tuple[Optional[ProductSourceRecord], list[ValidationErrorDetail]]:
        """
        Validate and construct a ProductSourceRecord from an untyped row dictionary.

        Returns:
            (record, errors): If errors list is non-empty, record will be None.
        """
        errors: list[ValidationErrorDetail] = []

        def get_clean_str(field_name: str) -> Optional[str]:
            val = row.get(field_name)
            if val is None:
                return None
            val_str = str(val).strip()
            return val_str if val_str != "" and val_str.lower() != "nan" and val_str.lower() != "null" else None

        source_system = get_clean_str("source_system")
        if not source_system:
            errors.append(
                ValidationErrorDetail(
                    field="source_system",
                    code=RejectionCode.MISSING_REQUIRED_FIELD,
                    message="Field 'source_system' is required and cannot be blank.",
                    invalid_value=row.get("source_system"),
                )
            )

        source_record_id = get_clean_str("source_record_id")
        if not source_record_id:
            errors.append(
                ValidationErrorDetail(
                    field="source_record_id",
                    code=RejectionCode.MISSING_REQUIRED_FIELD,
                    message="Field 'source_record_id' is required and cannot be blank.",
                    invalid_value=row.get("source_record_id"),
                )
            )

        product_name = get_clean_str("product_name")
        if not product_name:
            errors.append(
                ValidationErrorDetail(
                    field="product_name",
                    code=RejectionCode.MISSING_REQUIRED_FIELD,
                    message="Field 'product_name' is required for product records.",
                    invalid_value=row.get("product_name"),
                )
            )

        brand = get_clean_str("brand")
        if not brand:
            errors.append(
                ValidationErrorDetail(
                    field="brand",
                    code=RejectionCode.MISSING_REQUIRED_FIELD,
                    message="Field 'brand' is required for product records.",
                    invalid_value=row.get("brand"),
                )
            )

        updated_at = get_clean_str("updated_at")
        if not updated_at:
            errors.append(
                ValidationErrorDetail(
                    field="updated_at",
                    code=RejectionCode.MISSING_REQUIRED_FIELD,
                    message="Field 'updated_at' is required for deterministic survivorship.",
                    invalid_value=row.get("updated_at"),
                )
            )
        else:
            try:
                datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except ValueError:
                errors.append(
                    ValidationErrorDetail(
                        field="updated_at",
                        code=RejectionCode.MALFORMED_DATE,
                        message=f"Field 'updated_at' must be a valid ISO 8601 timestamp, got '{updated_at}'.",
                        invalid_value=updated_at,
                    )
                )

        # Optional attributes
        sku = get_clean_str("sku")
        upc_ean = get_clean_str("upc_ean")
        category = get_clean_str("category")
        currency = get_clean_str("currency") or "USD"

        raw_price = row.get("unit_price")
        unit_price: Optional[float] = None
        if raw_price is not None and str(raw_price).strip() != "" and str(raw_price).strip().lower() != "nan":
            try:
                parsed_price = float(raw_price)
                if parsed_price < 0.0:
                    errors.append(
                        ValidationErrorDetail(
                            field="unit_price",
                            code=RejectionCode.MALFORMED_NUMERIC,
                            message=f"Field 'unit_price' cannot be negative, got {parsed_price}.",
                            invalid_value=parsed_price,
                        )
                    )
                else:
                    unit_price = round(parsed_price, 2)
            except (ValueError, TypeError):
                errors.append(
                    ValidationErrorDetail(
                        field="unit_price",
                        code=RejectionCode.INVALID_DATA_TYPE,
                        message=f"Field 'unit_price' must be a valid numeric float, got '{raw_price}'.",
                        invalid_value=raw_price,
                    )
                )

        if errors:
            return None, errors

        assert source_system is not None
        assert source_record_id is not None
        assert product_name is not None
        assert brand is not None
        assert updated_at is not None

        return (
            cls(
                source_system=source_system,
                source_record_id=source_record_id,
                product_name=product_name,
                brand=brand,
                updated_at=updated_at,
                sku=sku,
                upc_ean=upc_ean,
                category=category,
                unit_price=unit_price,
                currency=currency,
            ),
            [],
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "source_system": self.source_system,
            "source_record_id": self.source_record_id,
            "product_name": self.product_name,
            "brand": self.brand,
            "sku": self.sku,
            "upc_ean": self.upc_ean,
            "category": self.category,
            "unit_price": self.unit_price,
            "currency": self.currency,
            "updated_at": self.updated_at,
        }

