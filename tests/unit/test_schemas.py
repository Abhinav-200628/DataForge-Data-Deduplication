"""Unit tests for Customer and Product schema validation and error reporting."""

import pytest

from deduplication.schemas.common import RejectionCode
from deduplication.schemas.customer import CustomerSourceRecord
from deduplication.schemas.product import ProductSourceRecord


class TestCustomerSchema:
    def test_valid_customer_creation(self):
        row = {
            "source_system": "CRM",
            "source_record_id": "C-1001",
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice.smith@example.com",
            "phone": "+1-555-0100",
            "street_address": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701",
            "country": "US",
            "tax_id": "987-65-4321",
            "date_of_birth": "1990-05-15",
            "updated_at": "2026-01-15T08:30:00Z",
        }
        record, errors = CustomerSourceRecord.from_row(row)

        assert errors == []
        assert record is not None
        assert record.source_system == "CRM"
        assert record.source_record_id == "C-1001"
        assert record.first_name == "Alice"
        assert record.last_name == "Smith"
        assert record.email == "alice.smith@example.com"
        assert record.phone == "+1-555-0100"
        assert record.updated_at == "2026-01-15T08:30:00Z"

    def test_missing_required_fields(self):
        # Missing last_name, source_system, updated_at
        row = {
            "source_record_id": "C-1002",
            "first_name": "Bob",
        }
        record, errors = CustomerSourceRecord.from_row(row)

        assert record is None
        error_fields = {e.field for e in errors}
        assert "source_system" in error_fields
        assert "last_name" in error_fields
        assert "updated_at" in error_fields
        for err in errors:
            assert err.code == RejectionCode.MISSING_REQUIRED_FIELD

    def test_invalid_email_format(self):
        row = {
            "source_system": "CRM",
            "source_record_id": "C-1003",
            "last_name": "Jones",
            "email": "not-a-valid-email",
            "updated_at": "2026-01-15T09:00:00Z",
        }
        record, errors = CustomerSourceRecord.from_row(row)

        assert record is None
        assert len(errors) == 1
        assert errors[0].field == "email"
        assert errors[0].code == RejectionCode.INVALID_DATA_TYPE

    def test_future_date_of_birth(self):
        row = {
            "source_system": "CRM",
            "source_record_id": "C-1004",
            "last_name": "Doe",
            "date_of_birth": "2099-01-01",
            "updated_at": "2026-01-15T09:00:00Z",
        }
        record, errors = CustomerSourceRecord.from_row(row)

        assert record is None
        assert any(e.field == "date_of_birth" and e.code == RejectionCode.MALFORMED_DATE for e in errors)

    def test_malformed_updated_at_timestamp(self):
        row = {
            "source_system": "CRM",
            "source_record_id": "C-1005",
            "last_name": "Brown",
            "updated_at": "invalid-timestamp",
        }
        record, errors = CustomerSourceRecord.from_row(row)

        assert record is None
        assert any(e.field == "updated_at" and e.code == RejectionCode.MALFORMED_DATE for e in errors)


class TestProductSchema:
    def test_valid_product_creation(self):
        row = {
            "source_system": "SAP",
            "source_record_id": "P-9001",
            "product_name": "Wireless Noise Cancelling Headphones",
            "brand": "Sony",
            "sku": "WH-1000XM5-BLK",
            "upc_ean": "027242923456",
            "category": "Electronics > Audio",
            "unit_price": "399.99",
            "currency": "USD",
            "updated_at": "2026-02-01T10:00:00Z",
        }
        record, errors = ProductSourceRecord.from_row(row)

        assert errors == []
        assert record is not None
        assert record.product_name == "Wireless Noise Cancelling Headphones"
        assert record.brand == "Sony"
        assert record.unit_price == 399.99
        assert record.currency == "USD"

    def test_missing_product_name_and_brand(self):
        row = {
            "source_system": "SAP",
            "source_record_id": "P-9002",
            "updated_at": "2026-02-01T10:00:00Z",
        }
        record, errors = ProductSourceRecord.from_row(row)

        assert record is None
        error_fields = {e.field for e in errors}
        assert "product_name" in error_fields
        assert "brand" in error_fields

    def test_negative_unit_price(self):
        row = {
            "source_system": "SHOPIFY",
            "source_record_id": "P-9003",
            "product_name": "Mechanical Keyboard",
            "brand": "Keychron",
            "unit_price": "-89.99",
            "updated_at": "2026-02-01T10:00:00Z",
        }
        record, errors = ProductSourceRecord.from_row(row)

        assert record is None
        assert any(e.field == "unit_price" and e.code == RejectionCode.MALFORMED_NUMERIC for e in errors)

    def test_non_numeric_unit_price(self):
        row = {
            "source_system": "SHOPIFY",
            "source_record_id": "P-9004",
            "product_name": "Mechanical Keyboard",
            "brand": "Keychron",
            "unit_price": "FREE_GIFT",
            "updated_at": "2026-02-01T10:00:00Z",
        }
        record, errors = ProductSourceRecord.from_row(row)

        assert record is None
        assert any(e.field == "unit_price" and e.code == RejectionCode.INVALID_DATA_TYPE for e in errors)

