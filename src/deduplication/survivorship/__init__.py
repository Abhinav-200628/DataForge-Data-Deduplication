"""Survivorship and golden record consolidation package."""

from deduplication.survivorship.engine import (
    DEFAULT_CUSTOMER_SOURCE_PRIORITY,
    DEFAULT_PRODUCT_SOURCE_PRIORITY,
    SurvivorshipEngine,
    generate_stable_master_id,
)
from deduplication.survivorship.models import MasterCustomer, MasterProduct

__all__ = [
    "MasterCustomer",
    "MasterProduct",
    "SurvivorshipEngine",
    "generate_stable_master_id",
    "DEFAULT_CUSTOMER_SOURCE_PRIORITY",
    "DEFAULT_PRODUCT_SOURCE_PRIORITY",
]

