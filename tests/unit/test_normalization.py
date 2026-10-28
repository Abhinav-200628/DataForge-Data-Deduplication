"""Unit tests for text, phone, email, address, SKU, and UPC normalizers."""

from deduplication.normalization.text_cleaners import (
    calculate_gtin_check_digit,
    clean_text,
    normalize_email,
    normalize_phone,
    normalize_postal_code,
    normalize_sku,
    normalize_street_address,
    normalize_tax_id,
    normalize_upc_ean,
)


class TestTextCleaners:
    def test_clean_text_null_representations(self):
        assert clean_text(None) is None
        assert clean_text("") is None
        assert clean_text("   ") is None
        assert clean_text("NULL") is None
        assert clean_text("None") is None
        assert clean_text("NaN") is None
        assert clean_text("  N/A  ") is None
        assert clean_text("  Hello   World  ") == "Hello World"

    def test_normalize_email(self):
        assert normalize_email(None) is None
        assert normalize_email("  ALICE@EXAMPLE.COM  ") == "alice@example.com"
        assert normalize_email("bob.smith+tag@gmail.com") == "bob.smith+tag@gmail.com"

    def test_normalize_phone(self):
        assert normalize_phone(None) is None
        assert normalize_phone("(555) 123-4567") == "5551234567"
        assert normalize_phone("+1-555-123-4567") == "5551234567"
        assert normalize_phone("1-555-123-4567") == "5551234567"
        assert normalize_phone("555.123.4567") == "5551234567"

    def test_normalize_postal_code(self):
        assert normalize_postal_code(None) is None
        assert normalize_postal_code("62701-1234") == "62701"
        assert normalize_postal_code(" 62701 ") == "62701"

    def test_normalize_tax_id(self):
        assert normalize_tax_id(None) is None
        assert normalize_tax_id("123456789") == "123-45-6789"
        assert normalize_tax_id("123-45-6789") == "123-45-6789"
        assert normalize_tax_id(" 123 45 6789 ") == "123-45-6789"

    def test_normalize_street_address(self):
        assert normalize_street_address("123 Main St.") == "123 main street"
        assert normalize_street_address("456 Oak Blvd, Apt 4B") == "456 oak boulevard apartment 4b"
        assert normalize_street_address("789 Highland Ave.") == "789 highland avenue"

    def test_normalize_sku(self):
        assert normalize_sku("wh-1000xm5 / blk") == "WH-1000XM5BLK"
        assert normalize_sku("  mbp_16  ") == "MBP16"

    def test_gtin_check_digit_and_upc_normalize(self):
        # GTIN-12 for UPC: '01234567890' -> check digit 5
        assert calculate_gtin_check_digit("01234567890") == 5
        assert normalize_upc_ean("0-12345-67890-5") == "012345678905"
        assert normalize_upc_ean("027242923456") == "027242923456"
