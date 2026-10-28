"""Common enumerations and validation containers across the deduplication pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class EntityType(str, Enum):
    """Supported entity domains to strictly prevent unsafe cross-entity matching."""
    CUSTOMER = "CUSTOMER"
    PRODUCT = "PRODUCT"


class MatchDecision(str, Enum):
    """The four operational outcomes of entity resolution."""
    EXACT_MATCH = "EXACT_MATCH"        # Deterministic match (e.g. Tax ID, UPC)
    PROBABLE_MATCH = "PROBABLE_MATCH"  # Corroborated multi-attribute match
    MANUAL_REVIEW = "MANUAL_REVIEW"    # Contradictory or borderline case
    DISTINCT = "DISTINCT"              # No match; warrants a new master record


class RunStatus(str, Enum):
    """Lifecycle status of a pipeline run."""
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class RejectionCode(str, Enum):
    """Explicit error codes for quarantined records."""
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_DATA_TYPE = "INVALID_DATA_TYPE"
    MALFORMED_ROW = "MALFORMED_ROW"
    DUPLICATE_SOURCE_KEY = "DUPLICATE_SOURCE_KEY"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    EMPTY_INPUT = "EMPTY_INPUT"
    MALFORMED_DATE = "MALFORMED_DATE"
    MALFORMED_NUMERIC = "MALFORMED_NUMERIC"
    UNKNOWN_SOURCE_SYSTEM = "UNKNOWN_SOURCE_SYSTEM"


@dataclass(frozen=True)
class ValidationErrorDetail:
    """Structured detail of a single schema or validation failure."""
    field: str
    code: RejectionCode
    message: str
    invalid_value: Optional[Any] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert validation error to a serializable dictionary."""
        return {
            "field": self.field,
            "code": self.code.value,
            "message": self.message,
            "invalid_value": str(self.invalid_value) if self.invalid_value is not None else None,
        }

