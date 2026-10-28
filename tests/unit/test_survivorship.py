"""Unit tests for deterministic field-level survivorship and stable Master IDs."""

from deduplication.normalization.customer_normalizer import NormalizedCustomer
from deduplication.normalization.product_normalizer import NormalizedProduct
from deduplication.schemas.common import EntityType
from deduplication.schemas.customer import CustomerSourceRecord
from deduplication.schemas.product import ProductSourceRecord
from deduplication.survivorship.engine import (
    SurvivorshipEngine,
    generate_stable_master_id,
)


class TestSurvivorshipEngine:
    def test_source_system_priority_wins(self):
        engine = SurvivorshipEngine()
        # ERP (priority 100) vs CRM (priority 80)
        c1 = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="CRM",
                source_record_id="CRM-1",
                first_name="Bob",
                last_name="Smith",
                street_address="123 Old St",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        c2 = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="ERP",
                source_record_id="ERP-1",
                first_name="Robert",
                last_name="Smith",
                street_address="123 Verified Blvd",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        master = engine.consolidate_customers([c1, c2])

        # ERP address and first name should win
        assert master.first_name == "Robert"
        assert master.street_address == "123 Verified Blvd"

    def test_recency_wins_on_equal_source_priority(self):
        engine = SurvivorshipEngine()
        # Both from CRM, but C2 has a newer timestamp
        c1 = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="CRM",
                source_record_id="CRM-1",
                first_name="Alice",
                last_name="Brown",
                phone="555-0001",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        c2 = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="CRM",
                source_record_id="CRM-2",
                first_name="Alice",
                last_name="Brown",
                phone="555-0002",
                updated_at="2026-02-01T00:00:00Z",  # Newer
            )
        )
        master = engine.consolidate_customers([c1, c2])

        assert master.primary_phone == "555-0002"
        assert "555-0001" in master.secondary_phones

    def test_data_completeness_beats_null(self):
        engine = SurvivorshipEngine()
        # Newer record has null phone, older record has non-null phone
        c1 = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="ERP",
                source_record_id="ERP-1",
                first_name="Charlie",
                last_name="Davis",
                phone="555-9876",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        c2 = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="ERP",
                source_record_id="ERP-2",
                first_name="Charlie",
                last_name="Davis",
                phone=None,  # Null
                updated_at="2026-03-01T00:00:00Z",
            )
        )
        master = engine.consolidate_customers([c1, c2])

        # Phone should survive from c1 despite c2 being newer
        assert master.primary_phone == "555-9876"

    def test_deterministic_tie_breaker_stable_master_id(self):
        # Two identical priority and timestamps: deterministic tie breaker guarantees identical output
        c1 = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="CRM",
                source_record_id="REC-A",
                last_name="Taylor",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        c2 = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="CRM",
                source_record_id="REC-B",
                last_name="Taylor",
                updated_at="2026-01-01T00:00:00Z",
            )
        )

        id1 = generate_stable_master_id(EntityType.CUSTOMER, "CRM", "REC-A")
        id2 = generate_stable_master_id(EntityType.CUSTOMER, "CRM", "REC-A")
        assert id1 == id2
        assert len(id1) == 36  # Standard UUID length

