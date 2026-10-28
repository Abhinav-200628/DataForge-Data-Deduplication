"""Customer schema definition and row-level type validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any, Optional

from deduplication.schemas.common import RejectionCode, ValidationErrorDetail

# Standard RFC-compliant relaxed email regex
_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class CustomerSourceRecord:
    """Strictly typed customer record as ingested from a source system."""
    source_system: str
    source_record_id: str
    last_name: str
    updated_at: str
    first_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = "US"
    tax_id: Optional[str] = None
    date_of_birth: Optional[str] = None

    @classmethod
    def from_row(
        cls, row: dict[str, Any]
    ) -> tuple[Optional[CustomerSourceRecord], list[ValidationErrorDetail]]:
        """
        Validate and construct a CustomerSourceRecord from an untyped dictionary/row.

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

        last_name = get_clean_str("last_name")
        if not last_name:
            errors.append(
                ValidationErrorDetail(
                    field="last_name",
                    code=RejectionCode.MISSING_REQUIRED_FIELD,
                    message="Field 'last_name' is required for customer records.",
                    invalid_value=row.get("last_name"),
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
            # Validate ISO timestamp or date
            try:
                # Support standard ISO variants (e.g. 2026-01-01T12:00:00Z or 2026-01-01)
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

        # Optional field validations
        first_name = get_clean_str("first_name")
        email = get_clean_str("email")
        if email and not _EMAIL_REGEX.match(email):
            errors.append(
                ValidationErrorDetail(
                    field="email",
                    code=RejectionCode.INVALID_DATA_TYPE,
                    message=f"Field 'email' contains an invalid email address format: '{email}'.",
                    invalid_value=email,
                )
            )

        phone = get_clean_str("phone")
        street_address = get_clean_str("street_address")
        city = get_clean_str("city")
        state = get_clean_str("state")
        postal_code = get_clean_str("postal_code")
        country = get_clean_str("country") or "US"
        tax_id = get_clean_str("tax_id")

        date_of_birth = get_clean_str("date_of_birth")
        if date_of_birth:
            try:
                dob = datetime.fromisoformat(date_of_birth.replace("Z", "+00:00"))
                if dob.year > datetime.now().year:
                    errors.append(
                        ValidationErrorDetail(
                            field="date_of_birth",
                            code=RejectionCode.MALFORMED_DATE,
                            message=f"Date of birth '{date_of_birth}' cannot be in the future.",
                            invalid_value=date_of_birth,
                        )
                    )
            except ValueError:
                errors.append(
                    ValidationErrorDetail(
                        field="date_of_birth",
                        code=RejectionCode.MALFORMED_DATE,
                        message=f"Field 'date_of_birth' must be a valid ISO date (YYYY-MM-DD), got '{date_of_birth}'.",
                        invalid_value=date_of_birth,
                    )
                )

        if errors:
            return None, errors

        # Construct valid instance (safe assertion of non-null required fields)
        assert source_system is not None
        assert source_record_id is not None
        assert last_name is not None
        assert updated_at is not None

        return (
            cls(
                source_system=source_system,
                source_record_id=source_record_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                street_address=street_address,
                city=city,
                state=state,
                postal_code=postal_code,
                country=country,
                tax_id=tax_id,
                date_of_birth=date_of_birth,
                updated_at=updated_at,
            ),
            [],
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "source_system": self.source_system,
            "source_record_id": self.source_record_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "street_address": self.street_address,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "tax_id": self.tax_id,
            "date_of_birth": self.date_of_birth,
            "updated_at": self.updated_at,
        }

