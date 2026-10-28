"""Unit tests for late-arriving records, update recency, and historical survivorship."""

from pathlib import Path
import pytest

from deduplication.normalization.customer_normalizer import NormalizedCustomer
from deduplication.orchestration import DeduplicationPipeline
from deduplication.schemas.common import EntityType
from deduplication.schemas.customer import CustomerSourceRecord
from deduplication.storage.repository import SQLiteRepository
from deduplication.survivorship.engine import SurvivorshipEngine


def test_late_arriving_older_record_does_not_overwrite_newer_record():
    """
    Scenario:
    A newer record (updated in March) was already recorded.
    A late-arriving record (updated in January) arrives later from another source.
    Survivorship must preserve the newer record's values while recording the late-arriving record.
    """
    engine = SurvivorshipEngine()

    newer_rec = NormalizedCustomer.from_source(
        CustomerSourceRecord(
            source_system="CRM",
            source_record_id="CRM-RECENT",
            first_name="Alice",
            last_name="Johnson",
            street_address="456 New Road",
            phone="555-9999",
            updated_at="2026-03-15T12:00:00Z",  # March (Newer)
        )
    )

    late_arriving_older_rec = NormalizedCustomer.from_source(
        CustomerSourceRecord(
            source_system="CRM",
            source_record_id="CRM-LATE-OLD",
            first_name="Alice",
            last_name="Johnson",
            street_address="123 Old Street",  # Obsolete address
            phone="555-1111",
            updated_at="2026-01-10T08:00:00Z",  # January (Older)
        )
    )

    # Process cluster containing both
    master = engine.consolidate_customers([newer_rec, late_arriving_older_rec])

    # The newer address and phone must win
    assert master.street_address == "456 New Road"
    assert master.primary_phone == "555-9999"
    assert "555-1111" in master.secondary_phones
    assert master.updated_at == "2026-03-15T12:00:00Z"


def test_late_arriving_batch_in_pipeline(tmp_path: Path):
    """
    Scenario:
    Batch 1 is processed.
    Batch 2 arrives with an updated version of a customer record.
    Idempotent pipeline updates the record in SQLite without duplicating lineage or masters.
    """
    db_file = tmp_path / "late_pipeline.db"
    csv_batch1 = tmp_path / "batch1.csv"
    csv_batch2 = tmp_path / "batch2.csv"

    csv_batch1.write_text(
        "source_system,source_record_id,first_name,last_name,email,updated_at\n"
        "CRM,C-501,Diana,Prince,diana@example.com,2026-01-01T00:00:00Z\n",
        encoding="utf-8",
    )

    csv_batch2.write_text(
        "source_system,source_record_id,first_name,last_name,email,updated_at\n"
        "CRM,C-501,Diana,Prince-Wayne,diana.wayne@example.com,2026-02-01T00:00:00Z\n",
        encoding="utf-8",
    )

    pipeline = DeduplicationPipeline(
        entity_type=EntityType.CUSTOMER,
        db_path=db_file,
    )

    # Run Batch 1
    m1 = pipeline.run(input_path=csv_batch1, run_id="BATCH-1")
    assert m1.valid_count == 1
    assert m1.master_records_created == 1

    repo = SQLiteRepository(db_file)
    assert repo.get_master_count(EntityType.CUSTOMER) == 1
    assert repo.get_lineage_count(EntityType.CUSTOMER) == 1

    # Run Batch 2 (Late-arriving updated record)
    m2 = pipeline.run(input_path=csv_batch2, run_id="BATCH-2")
    assert m2.valid_count == 1

    # Idempotency and update check
    assert repo.get_master_count(EntityType.CUSTOMER) == 1
    assert repo.get_lineage_count(EntityType.CUSTOMER) == 1

    with repo._get_connection() as conn:
        cursor = conn.execute("SELECT last_name, primary_email FROM master_customers WHERE master_id = ?",
                              (list(conn.execute("SELECT master_id FROM master_customers"))[0][0],))
        row = cursor.fetchone()
        assert row["last_name"] == "Prince-Wayne"
        assert row["primary_email"] == "diana.wayne@example.com"

