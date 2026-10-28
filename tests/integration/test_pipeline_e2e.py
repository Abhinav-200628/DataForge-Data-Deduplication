"""End-to-end pipeline integration tests for Customers and Products."""

from pathlib import Path
import pytest

from deduplication.ingestion.loader import SchemaMismatchError
from deduplication.orchestration import DeduplicationPipeline
from deduplication.schemas.common import EntityType, MatchDecision


def test_customer_pipeline_e2e(tmp_path: Path):
    db_file = tmp_path / "e2e_cust.db"
    out_dir = tmp_path / "e2e_cust_out"
    csv_file = tmp_path / "cust_input.csv"

    # 1 exact duplicate pair, 1 probable duplicate pair, 1 distinct, 1 invalid row
    csv_file.write_text(
        "source_system,source_record_id,first_name,last_name,email,phone,street_address,city,state,postal_code,tax_id,updated_at\n"
        "CRM,C-1,Alice,Smith,alice@example.com,555-1111,123 Main St,Springfield,IL,62701,111-11-1111,2026-01-01T00:00:00Z\n"
        "ERP,C-2,Alice,Smith,alice@example.com,555-1111,123 Main Street,Springfield,IL,62701,111-11-1111,2026-01-02T00:00:00Z\n"
        "CRM,C-3,Robert,Johnson,rob.j@test.com,555-2222,456 Oak Ave,Austin,TX,78701,,2026-01-01T00:00:00Z\n"
        "WEB,C-4,Bob,Johnson,rob.j@test.com,555-2222,456 Oak Avenue,Austin,TX,78701,,2026-01-03T00:00:00Z\n"
        "CRM,C-5,Unique,Person,unique@test.com,555-3333,789 Pine Rd,Seattle,WA,98101,,2026-01-01T00:00:00Z\n"
        "CRM,C-ERR,Bad,Row,not-an-email,555-4444,000 Nowhere,None,IL,00000,,2026-01-01T00:00:00Z\n",
        encoding="utf-8",
    )

    pipeline = DeduplicationPipeline(
        entity_type=EntityType.CUSTOMER,
        db_path=db_file,
        output_dir=out_dir,
    )

    metrics = pipeline.run(input_path=csv_file)

    assert metrics.input_count == 6
    assert metrics.valid_count == 5
    assert metrics.quarantined_count == 1
    # 5 valid records -> 3 master records (Alice merged, Robert merged, Unique distinct)
    assert metrics.master_records_created == 3

    # Check exported CSV and JSON files
    assert (out_dir / "customer_masters.csv").exists()
    assert (out_dir / "customer_masters.json").exists()
    assert (out_dir / "customer_lineage.csv").exists()
    assert (out_dir / "customer_quarantine.csv").exists()


def test_product_pipeline_e2e(tmp_path: Path):
    db_file = tmp_path / "e2e_prod.db"
    out_dir = tmp_path / "e2e_prod_out"
    csv_file = tmp_path / "prod_input.csv"

    csv_file.write_text(
        "source_system,source_record_id,product_name,brand,sku,upc_ean,unit_price,currency,updated_at\n"
        "SAP,P-1,Sony WH-1000XM5 Black,Sony,WH1000XM5,027242923456,399.99,USD,2026-01-01T00:00:00Z\n"
        "SHOPIFY,P-2,Wireless Noise Canceling Headphones Sony,Sony,WH1000XM5,027242923456,389.99,USD,2026-01-02T00:00:00Z\n"
        "SAP,P-3,Apple MacBook Pro 16,Apple,MBP-16,194253123456,2499.00,USD,2026-01-01T00:00:00Z\n",
        encoding="utf-8",
    )

    pipeline = DeduplicationPipeline(
        entity_type=EntityType.PRODUCT,
        db_path=db_file,
        output_dir=out_dir,
    )

    metrics = pipeline.run(input_path=csv_file)

    assert metrics.input_count == 3
    assert metrics.valid_count == 3
    assert metrics.quarantined_count == 0
    # 3 valid records -> 2 master records (Sony merged, Apple distinct)
    assert metrics.master_records_created == 2

    assert (out_dir / "product_masters.csv").exists()
    assert (out_dir / "product_masters.json").exists()


def test_cross_entity_schema_isolation(tmp_path: Path):
    """Ensure customer pipeline strictly rejects product schema and vice versa."""
    csv_file = tmp_path / "products.csv"
    csv_file.write_text(
        "source_system,source_record_id,product_name,brand,updated_at\n"
        "SAP,P-1,Laptop,Apple,2026-01-01T00:00:00Z\n",
        encoding="utf-8",
    )

    # Attempting to load product CSV into Customer pipeline MUST raise SchemaMismatchError
    pipeline = DeduplicationPipeline(
        entity_type=EntityType.CUSTOMER,
        db_path=tmp_path / "fail.db",
    )

    with pytest.raises(SchemaMismatchError) as exc_info:
        pipeline.run(input_path=csv_file)

    assert "Missing mandatory header column(s)" in str(exc_info.value)
    assert "last_name" in str(exc_info.value)

