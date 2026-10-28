"""Integration tests proving rerun idempotency and lack of duplication."""

from pathlib import Path
import pytest

from deduplication.orchestration import DeduplicationPipeline
from deduplication.schemas.common import EntityType
from deduplication.storage.repository import SQLiteRepository


def test_rerun_idempotency(tmp_path: Path):
    db_file = tmp_path / "idempotent.db"
    out_dir = tmp_path / "idempotent_out"
    csv_file = tmp_path / "customers.csv"

    # Create dataset with 1 exact duplicate pair and 1 distinct record
    csv_file.write_text(
        "source_system,source_record_id,first_name,last_name,email,phone,updated_at\n"
        "CRM,C-101,Alice,Smith,alice.smith@example.com,555-0101,2026-01-01T00:00:00Z\n"
        "ERP,E-101,Alice,Smith,alice.smith@example.com,555-0101,2026-01-02T00:00:00Z\n"
        "CRM,C-102,Bob,Jones,bob.jones@example.com,555-0102,2026-01-01T00:00:00Z\n",
        encoding="utf-8",
    )

    pipeline = DeduplicationPipeline(
        entity_type=EntityType.CUSTOMER,
        db_path=db_file,
        output_dir=out_dir,
    )

    # First Run
    run1_metrics = pipeline.run(input_path=csv_file, run_id="RUN-1")
    assert run1_metrics.valid_count == 3
    assert run1_metrics.master_records_created == 2  # (C-101 + E-101 merged, C-102 distinct)

    repo = SQLiteRepository(db_file)
    masters_run1 = repo.get_master_count(EntityType.CUSTOMER)
    lineage_run1 = repo.get_lineage_count(EntityType.CUSTOMER)

    assert masters_run1 == 2
    assert lineage_run1 == 3

    # Query master IDs from Run 1
    with repo._get_connection() as conn:
        cursor = conn.execute("SELECT master_id, last_name, primary_email FROM master_customers ORDER BY master_id")
        rows_run1 = cursor.fetchall()

    # Second Run (Rerun with the identical input file!)
    run2_metrics = pipeline.run(input_path=csv_file, run_id="RUN-2")
    assert run2_metrics.valid_count == 3
    assert run2_metrics.master_records_created == 2

    masters_run2 = repo.get_master_count(EntityType.CUSTOMER)
    lineage_run2 = repo.get_lineage_count(EntityType.CUSTOMER)

    # CRITICAL IDEMPOTENCY ASSERTIONS:
    # 1. Total master count has NOT increased
    assert masters_run2 == masters_run1, "Rerunning the pipeline created duplicate master records!"

    # 2. Total lineage count has NOT increased
    assert lineage_run2 == lineage_run1, "Rerunning the pipeline created duplicate lineage rows!"

    # 3. Master IDs and field values are 100% stable
    with repo._get_connection() as conn:
        cursor = conn.execute("SELECT master_id, last_name, primary_email FROM master_customers ORDER BY master_id")
        rows_run2 = cursor.fetchall()

    assert rows_run1 == rows_run2, "Master IDs changed across identical runs!"
