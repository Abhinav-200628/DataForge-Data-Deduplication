"""Performance and reconciliation assertions tests."""

from pathlib import Path

from deduplication.generator.synthetic_data import generate_customer_dataset
from deduplication.orchestration import DeduplicationPipeline
from deduplication.reporting.validation_report import ReportGenerator
from deduplication.schemas.common import EntityType


def test_reconciliation_and_report_generation(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_file = tmp_path / "recon.db"

    # Generate 200 records with fixed seed
    generate_customer_dataset(count=200, seed=42, output_dir=data_dir)
    csv_file = data_dir / "customers_200.csv"
    gt_file = data_dir / "customers_200_ground_truth.json"

    pipeline = DeduplicationPipeline(
        entity_type=EntityType.CUSTOMER,
        db_path=db_file,
    )

    metrics = pipeline.run(input_path=csv_file)

    # Conservation Law Assertions
    assert metrics.input_count == 200
    assert metrics.input_count == metrics.valid_count + metrics.quarantined_count
    assert metrics.master_records_created > 0
    assert metrics.status.value == "COMPLETED"

    # Test report generation and precision/recall evaluation
    reporter = ReportGenerator(db_path=db_file)
    report_data = reporter.generate_run_report(metrics.run_id, ground_truth_path=gt_file)

    assert report_data["reconciliation"]["is_balanced"] is True
    assert "ground_truth_evaluation" in report_data

    gt_eval = report_data["ground_truth_evaluation"]
    # Check that precision is high (low false positives)
    assert gt_eval["precision"] >= 0.85

    md = reporter.format_markdown_report(report_data)
    assert "Reconciliation Conservation Check" in md
    assert "PASSED" in md

