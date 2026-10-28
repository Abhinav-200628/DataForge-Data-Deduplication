"""
Deterministic field-level survivorship and stable Master ID generation.

Resolves conflicting fields across merged source records using configurable
source priority, update recency, completeness, and stable tie-breaking.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Sequence
import uuid

from deduplication.normalization.customer_normalizer import NormalizedCustomer
from deduplication.normalization.product_normalizer import NormalizedProduct
from deduplication.schemas.common import EntityType, MatchDecision
from deduplication.survivorship.models import MasterCustomer, MasterProduct

# Default source system priorities (higher weight = higher priority)
DEFAULT_CUSTOMER_SOURCE_PRIORITY: dict[str, int] = {
    "ERP": 100,
    "BILLING": 90,
    "CRM": 80,
    "WEB": 60,
    "MARKETING": 40,
    "UNKNOWN": 10,
}

DEFAULT_PRODUCT_SOURCE_PRIORITY: dict[str, int] = {
    "PIM": 100,
    "SAP": 90,
    "SHOPIFY": 80,
    "AMAZON": 70,
    "SCRAPED": 30,
    "UNKNOWN": 10,
}


def generate_stable_master_id(
    entity_type: EntityType, source_system: str, source_record_id: str
) -> str:
    """
    Generate a deterministic, immutable Master ID (UUIDv5) based on an anchor record.
    """
    seed = f"{entity_type.value}:{source_system.upper().strip()}:{source_record_id.strip()}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))


class SurvivorshipEngine:
    """Consolidates clusters of source records into golden master records."""

    def __init__(
        self,
        customer_priorities: Optional[dict[str, int]] = None,
        product_priorities: Optional[dict[str, int]] = None,
    ) -> None:
        self.cust_priorities = customer_priorities or DEFAULT_CUSTOMER_SOURCE_PRIORITY
        self.prod_priorities = product_priorities or DEFAULT_PRODUCT_SOURCE_PRIORITY

    def _resolve_scalar_field(
        self,
        candidates: list[tuple[Any, str, str, str]],  # (value, system, updated_at, source_id)
        priority_map: dict[str, int],
    ) -> Optional[Any]:
        """
        Deterministically resolve a single field across multiple source records.
        Sort key:
            1. Non-null validity (True beats False)
            2. Source system priority weight (higher wins)
            3. Recency / updated_at ISO string (later timestamp wins)
            4. Deterministic tie-breaker: source_record_id (lowest lexicographical wins)
        """
        valid_candidates = [c for c in candidates if c[0] is not None and str(c[0]).strip() != ""]
        if not valid_candidates:
            return None

        def sort_key(item: tuple[Any, str, str, str]) -> tuple[int, str, str]:
            val, system, updated_at, src_id = item
            weight = priority_map.get(system.upper().strip(), 10)
            # We want highest weight first, latest updated_at first, lowest src_id first
            return (weight, updated_at, str(src_id))

        # Sort with custom comparator
        # For descending weight and timestamp, we sort candidates
        sorted_candidates = sorted(
            valid_candidates,
            key=lambda c: (
                priority_map.get(c[1].upper().strip(), 10),
                c[2],
            ),
            reverse=True,
        )

        # Check if top candidates tie on weight and updated_at
        top_weight = priority_map.get(sorted_candidates[0][1].upper().strip(), 10)
        top_time = sorted_candidates[0][2]
        tied = [
            c for c in sorted_candidates
            if priority_map.get(c[1].upper().strip(), 10) == top_weight and c[2] == top_time
        ]

        if len(tied) > 1:
            # Deterministic tie-breaker: sort alphabetically by source_record_id
            tied.sort(key=lambda c: str(c[3]))
            return tied[0][0]

        return sorted_candidates[0][0]

    def consolidate_customers(
        self, cluster: Sequence[NormalizedCustomer]
    ) -> MasterCustomer:
        """Consolidate a cluster of 1 or more customer records into a MasterCustomer."""
        assert len(cluster) > 0, "Cannot consolidate an empty customer cluster"

        # Determine anchor record for stable master ID
        # Anchor is highest priority source system, latest timestamp, lowest source_record_id
        sorted_cluster = sorted(
            cluster,
            key=lambda c: (
                self.cust_priorities.get(c.source_system, 10),
                c.updated_at,
            ),
            reverse=True,
        )
        anchor = sorted_cluster[0]
        master_id = generate_stable_master_id(
            EntityType.CUSTOMER, anchor.source_system, anchor.source_record_id
        )

        # Resolve scalar fields
        first_names = [(c.raw.first_name, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        last_names = [(c.raw.last_name, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        addresses = [(c.raw.street_address, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        cities = [(c.raw.city, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        states = [(c.raw.state, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        zips = [(c.raw.postal_code, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        countries = [(c.raw.country, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        tax_ids = [(c.raw.tax_id, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        dobs = [(c.raw.date_of_birth, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        timestamps = [(c.updated_at, c.source_system, c.updated_at, c.source_record_id) for c in cluster]

        best_first = self._resolve_scalar_field(first_names, self.cust_priorities)
        best_last = self._resolve_scalar_field(last_names, self.cust_priorities) or "UNKNOWN"
        best_addr = self._resolve_scalar_field(addresses, self.cust_priorities)
        best_city = self._resolve_scalar_field(cities, self.cust_priorities)
        best_state = self._resolve_scalar_field(states, self.cust_priorities)
        best_zip = self._resolve_scalar_field(zips, self.cust_priorities)
        best_country = self._resolve_scalar_field(countries, self.cust_priorities) or "US"
        best_tax = self._resolve_scalar_field(tax_ids, self.cust_priorities)
        best_dob = self._resolve_scalar_field(dobs, self.cust_priorities)
        latest_update = max(c.updated_at for c in cluster)

        # Collect emails and phones with primary vs secondary
        email_candidates = [(c.raw.email, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        primary_email = self._resolve_scalar_field(email_candidates, self.cust_priorities)
        all_emails = {
            c.raw.email.strip().lower()
            for c in cluster
            if c.raw.email and str(c.raw.email).strip()
        }
        secondary_emails = sorted(
            [e for e in all_emails if primary_email and e != primary_email.strip().lower()]
        )

        phone_candidates = [(c.raw.phone, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        primary_phone = self._resolve_scalar_field(phone_candidates, self.cust_priorities)
        all_phones = {
            c.raw.phone.strip()
            for c in cluster
            if c.raw.phone and str(c.raw.phone).strip()
        }
        secondary_phones = sorted(
            [p for p in all_phones if primary_phone and p != primary_phone.strip()]
        )

        return MasterCustomer(
            master_id=master_id,
            first_name=best_first,
            last_name=best_last,
            primary_email=primary_email,
            secondary_emails=secondary_emails,
            primary_phone=primary_phone,
            secondary_phones=secondary_phones,
            street_address=best_addr,
            city=best_city,
            state=best_state,
            postal_code=best_zip,
            country=best_country,
            tax_id=best_tax,
            date_of_birth=best_dob,
            updated_at=latest_update,
        )

    def consolidate_products(
        self, cluster: Sequence[NormalizedProduct]
    ) -> MasterProduct:
        """Consolidate a cluster of 1 or more product records into a MasterProduct."""
        assert len(cluster) > 0, "Cannot consolidate an empty product cluster"

        sorted_cluster = sorted(
            cluster,
            key=lambda c: (
                self.prod_priorities.get(c.source_system, 10),
                c.updated_at,
            ),
            reverse=True,
        )
        anchor = sorted_cluster[0]
        master_id = generate_stable_master_id(
            EntityType.PRODUCT, anchor.source_system, anchor.source_record_id
        )

        names = [(c.raw.product_name, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        brands = [(c.raw.brand, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        upcs = [(c.raw.upc_ean, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        categories = [(c.raw.category, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        prices = [(c.raw.unit_price, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        currencies = [(c.raw.currency, c.source_system, c.updated_at, c.source_record_id) for c in cluster]

        best_name = self._resolve_scalar_field(names, self.prod_priorities) or "UNKNOWN PRODUCT"
        best_brand = self._resolve_scalar_field(brands, self.prod_priorities) or "GENERIC"
        best_upc = self._resolve_scalar_field(upcs, self.prod_priorities)
        best_cat = self._resolve_scalar_field(categories, self.prod_priorities)
        best_price = self._resolve_scalar_field(prices, self.prod_priorities)
        best_curr = self._resolve_scalar_field(currencies, self.prod_priorities) or "USD"
        latest_update = max(c.updated_at for c in cluster)

        sku_candidates = [(c.raw.sku, c.source_system, c.updated_at, c.source_record_id) for c in cluster]
        primary_sku = self._resolve_scalar_field(sku_candidates, self.prod_priorities)
        all_skus = {
            c.raw.sku.strip()
            for c in cluster
            if c.raw.sku and str(c.raw.sku).strip()
        }
        secondary_skus = sorted(
            [s for s in all_skus if primary_sku and s != primary_sku.strip()]
        )

        return MasterProduct(
            master_id=master_id,
            product_name=best_name,
            brand=best_brand,
            primary_sku=primary_sku,
            secondary_skus=secondary_skus,
            primary_upc_ean=best_upc,
            category=best_cat,
            unit_price=best_price,
            currency=best_curr,
            updated_at=latest_update,
        )

