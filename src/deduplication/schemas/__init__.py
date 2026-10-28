"""Data contracts and schemas for customers, products, and quarantine records."""

from deduplication.schemas.common import (
    EntityType,
    MatchDecision,
    RejectionCode,
    RunStatus,
    ValidationErrorDetail,
)
from deduplication.schemas.customer import CustomerSourceRecord
from deduplication.schemas.product import ProductSourceRecord
from deduplication.schemas.quarantine import QuarantineRecord

__all__ = [
    "EntityType",
    "MatchDecision",
    "RejectionCode",
    "RunStatus",
    "ValidationErrorDetail",
    "CustomerSourceRecord",
    "ProductSourceRecord",
    "QuarantineRecord",
]

