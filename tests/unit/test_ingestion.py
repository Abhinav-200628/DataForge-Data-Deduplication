"""Unit tests for CSV ingestion, schema validation, and edge case handling."""

from pathlib import Path
import pytest

from deduplication.ingestion.loader import (
    CSVLoader,
    EmptyInputError,
    IngestionIOError,
    SchemaMismatchError,
)
from deduplication.schemas.common import EntityType, RejectionCode


@pytest.fixture
def temp_csv_dir(tmp_path: Path) -> Path:
    csv_dir = tmp_path / "csv_fixtures"
    csv_dir.mkdir(parents=True, exist_ok=True)
    return csv_dir


class TestCSVLoaderCustomer:
    def test_valid_customer_csv(self, temp_csv_dir: Path):
        csv_path = temp_csv_dir / "valid_customers.csv"
        csv_path.write_text(
            "source_system,source_record_id,first_name,last_name,email,phone,updated_at\n"
            "CRM,C-1,Alice,Smith,alice@example.com,555-0101,2026-01-01T10:00:00Z\n"
            "ERP,C-2,Bob,Jones,bob@example.com,555-0102,2026-01-02T10:00:00Z\n",
            encoding="utf-8",
        )

        loader = CSVLoader(entity_type=EntityType.CUSTOMER)
        result = loader.load_from_path(csv_path)

        assert result.total_rows_read == 2
        assert result.valid_count == 2
        assert result.quarantined_count == 0
        assert result.valid_records[0].source_record_id == "C-1"
        assert result.valid_records[1].source_record_id == "C-2"

    def test_empty_input_file(self, temp_csv_dir: Path):
        empty_path = temp_csv_dir / "empty.csv"
        empty_path.write_text("", encoding="utf-8")

        loader = CSVLoader(entity_type=EntityType.CUSTOMER)
        with pytest.raises(EmptyInputError) as exc_info:
            loader.load_from_path(empty_path)

        assert "empty (0 bytes)" in str(exc_info.value)

    def test_header_only_file(self, temp_csv_dir: Path):
        header_only_path = temp_csv_dir / "headers_only.csv"
        header_only_path.write_text(
            "source_system,source_record_id,first_name,last_name,updated_at\n",
            encoding="utf-8",
        )

        loader = CSVLoader(entity_type=EntityType.CUSTOMER)
        result = loader.load_from_path(header_only_path)

        assert result.total_rows_read == 0
        assert result.valid_count == 0
        assert result.quarantined_count == 0

    def test_missing_mandatory_header_columns(self):
        # Missing 'last_name' and 'updated_at'
        csv_content = (
            "source_system,source_record_id,first_name\n"
            "CRM,C-1,Alice\n"
        )
        loader = CSVLoader(entity_type=EntityType.CUSTOMER)

        with pytest.raises(SchemaMismatchError) as exc_info:
            loader.load_from_string(csv_content)

        assert "Missing mandatory header column(s)" in str(exc_info.value)
        assert "last_name" in str(exc_info.value)
        assert "updated_at" in str(exc_info.value)

    def test_unexpected_schema_changes_strict_mode(self):
        # Contains unknown column 'internal_cost_center'
        csv_content = (
            "source_system,source_record_id,last_name,updated_at,internal_cost_center\n"
            "CRM,C-1,Smith,2026-01-01T00:00:00Z,CC-999\n"
        )
        loader = CSVLoader(entity_type=EntityType.CUSTOMER, allow_unknown_columns=False)

        with pytest.raises(SchemaMismatchError) as exc_info:
            loader.load_from_string(csv_content)

        assert "Unexpected schema drift detected" in str(exc_info.value)
        assert "internal_cost_center" in str(exc_info.value)

    def test_unexpected_schema_changes_relaxed_mode(self):
        csv_content = (
            "source_system,source_record_id,last_name,updated_at,internal_cost_center\n"
            "CRM,C-1,Smith,2026-01-01T00:00:00Z,CC-999\n"
        )
        loader = CSVLoader(entity_type=EntityType.CUSTOMER, allow_unknown_columns=True)
        result = loader.load_from_string(csv_content)

        assert result.valid_count == 1
        assert result.valid_records[0].last_name == "Smith"

    def test_malformed_rows_unequal_column_count(self):
        csv_content = (
            "source_system,source_record_id,first_name,last_name,updated_at\n"
            "CRM,C-1,Alice,Smith,2026-01-01T00:00:00Z\n"
            "CRM,C-2,Bob\n"  # Too few columns
            "CRM,C-3,Charlie,Brown,2026-01-01T00:00:00Z,EXTRA_COL_VAL\n"  # Too many columns
        )
        loader = CSVLoader(entity_type=EntityType.CUSTOMER)
        result = loader.load_from_string(csv_content)

        assert result.total_rows_read == 3
        assert result.valid_count == 1
        assert result.quarantined_count == 2
        for q in result.quarantined_records:
            assert any(r.code == RejectionCode.MALFORMED_ROW for r in q.rejection_reasons)

    def test_duplicate_source_keys_in_batch(self):
        csv_content = (
            "source_system,source_record_id,first_name,last_name,updated_at\n"
            "CRM,C-100,Alice,Smith,2026-01-01T00:00:00Z\n"
            "CRM,C-100,Alice,Smith Duplicate,2026-01-02T00:00:00Z\n"
        )
        loader = CSVLoader(entity_type=EntityType.CUSTOMER)
        result = loader.load_from_string(csv_content)

        assert result.total_rows_read == 2
        assert result.valid_count == 1
        assert result.quarantined_count == 1
        dup_quarantine = result.quarantined_records[0]
        assert dup_quarantine.source_record_id == "C-100"
        assert any(r.code == RejectionCode.DUPLICATE_SOURCE_KEY for r in dup_quarantine.rejection_reasons)

    def test_missing_file_raises_io_error(self):
        loader = CSVLoader(entity_type=EntityType.CUSTOMER)
        with pytest.raises(IngestionIOError):
            loader.load_from_path(Path("non_existent_file.csv"))


class TestCSVLoaderProduct:
    def test_valid_product_csv(self, temp_csv_dir: Path):
        csv_path = temp_csv_dir / "valid_products.csv"
        csv_path.write_text(
            "source_system,source_record_id,product_name,brand,sku,unit_price,updated_at\n"
            "SAP,P-1,Laptop Pro 16,Apple,MBP-16,2499.00,2026-01-01T00:00:00Z\n"
            "SAP,P-2,Wireless Mouse,Logitech,MX-3S,99.99,2026-01-01T00:00:00Z\n",
            encoding="utf-8",
        )

        loader = CSVLoader(entity_type=EntityType.PRODUCT)
        result = loader.load_from_path(csv_path)

        assert result.valid_count == 2
        assert result.quarantined_count == 0
        assert result.valid_records[0].product_name == "Laptop Pro 16"
        assert result.valid_records[1].unit_price == 99.99

    def test_invalid_price_and_missing_brand_routed_to_quarantine(self):
        csv_content = (
            "source_system,source_record_id,product_name,brand,unit_price,updated_at\n"
            "SAP,P-1,Good Product,Sony,199.99,2026-01-01T00:00:00Z\n"
            "SAP,P-2,Bad Price Product,Sony,-50.00,2026-01-01T00:00:00Z\n"
            "SAP,P-3,Missing Brand,,49.99,2026-01-01T00:00:00Z\n"
        )
        loader = CSVLoader(entity_type=EntityType.PRODUCT)
        result = loader.load_from_string(csv_content)

        assert result.total_rows_read == 3
        assert result.valid_count == 1
        assert result.quarantined_count == 2

        q_ids = {q.source_record_id: q for q in result.quarantined_records}
        assert "P-2" in q_ids
        assert any(r.code == RejectionCode.MALFORMED_NUMERIC for r in q_ids["P-2"].rejection_reasons)
        assert "P-3" in q_ids
        assert any(r.code == RejectionCode.MISSING_REQUIRED_FIELD for r in q_ids["P-3"].rejection_reasons)

    def test_semicolon_delimited_csv(self):
        csv_content = (
            "source_system;source_record_id;product_name;brand;updated_at\n"
            "SAP;P-10;Monitor 4K;LG;2026-01-01T00:00:00Z\n"
        )
        loader = CSVLoader(entity_type=EntityType.PRODUCT, delimiter=";")
        result = loader.load_from_string(csv_content)

        assert result.valid_count == 1
        assert result.valid_records[0].product_name == "Monitor 4K"

