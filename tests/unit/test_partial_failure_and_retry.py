"""Unit tests for transaction atomicity, partial failure isolation, and retry execution."""

from pathlib import Path
import pytest

from deduplication.ingestion.loader import EmptyInputError, SchemaMismatchError
from deduplication.orchestration import DeduplicationPipeline
from deduplication.schemas.common import EntityType, RunStatus
from deduplication.storage.repository import SQLiteRepository


def test_partial_failure_rolls_back_and_marks_run_failed(tmp_path: Path):
    """
    Verify that an unrecoverable failure during ingestion or schema validation
    records a FAILED run in the audit table and leaves no corrupted records in master tables.
    """
    db_file = tmp_path / "rollback_test.db"
    bad_csv = tmp_path / "corrupted_header.csv"

    # CSV missing mandatory 'last_name' header
    bad_csv.write_text(
        "source_system,source_record_id,first_name\n"
        "CRM,BAD-1,Alice\n",
        encoding="utf-8",
    )

    pipeline = DeduplicationPipeline(
        entity_type=EntityType.CUSTOMER,
        db_path=db_file,
    )

    with pytest.raises(SchemaMismatchError):
        pipeline.run(input_path=bad_csv, run_id="FAIL-RUN-1")

    repo = SQLiteRepository(db_file)

    # Master and Lineage tables must remain completely empty (No partial / orphan records)
    assert repo.get_master_count(EntityType.CUSTOMER) == 0
    assert repo.get_lineage_count(EntityType.CUSTOMER) == 0

    # Pipeline audit table must record the failure with error summary
    with repo._get_connection() as conn:
        cursor = conn.execute("SELECT status, error_summary FROM pipeline_runs WHERE run_id = 'FAIL-RUN-1'")
        row = cursor.fetchone()
        assert row is not None
        assert row["status"] == RunStatus.FAILED.value
        assert "Missing mandatory header column" in row["error_summary"]


def test_retry_after_failure_succeeds(tmp_path: Path):
    """
    Verify that after fixing a broken input file, a retry run executes cleanly
    and successfully populates master records and lineage.
    """
    db_file = tmp_path / "retry_test.db"
    fixed_csv = tmp_path / "fixed.csv"

    # Write corrected CSV
    fixed_csv.write_text(
        "source_system,source_record_id,first_name,last_name,updated_at\n"
        "CRM,OK-1,Bruce,Wayne,2026-01-01T00:00:00Z\n",
        encoding="utf-8",
    )

    pipeline = DeduplicationPipeline(
        entity_type=EntityType.CUSTOMER,
        db_path=db_file,
    )

    metrics = pipeline.run(input_path=fixed_csv, run_id="RETRY-RUN-2")

    assert metrics.status == RunStatus.COMPLETED
    assert metrics.valid_count == 1
    assert metrics.master_records_created == 1

    repo = SQLiteRepository(db_file)
    assert repo.get_master_count(EntityType.CUSTOMER) == 1
    assert repo.get_lineage_count(EntityType.CUSTOMER) == 1

