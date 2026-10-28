"""Unit tests for missing optional values and multi-tier hard conflict detection."""

import pytest

from deduplication.matching.customer_matcher import CustomerMatcher
from deduplication.matching.product_matcher import ProductMatcher
from deduplication.normalization.customer_normalizer import NormalizedCustomer
from deduplication.normalization.product_normalizer import NormalizedProduct
from deduplication.schemas.common import MatchDecision
from deduplication.schemas.customer import CustomerSourceRecord
from deduplication.schemas.product import ProductSourceRecord


class TestMissingValuesHandling:
    def test_missing_optional_customer_fields_does_not_crash(self):
        matcher = CustomerMatcher()
        # Records with only required fields (no phone, no email, no address, no tax id, no dob)
        c1 = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="CRM",
                source_record_id="C-MIN-1",
                last_name="Johnson",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        c2 = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="ERP",
                source_record_id="C-MIN-2",
                last_name="Johnson",
                updated_at="2026-01-02T00:00:00Z",
            )
        )
        # Should evaluate cleanly without null pointer or missing key errors
        ev = matcher.evaluate_pair(c1, c2)
        assert ev.decision in {MatchDecision.DISTINCT, MatchDecision.MANUAL_REVIEW}
        assert ev.overall_score >= 0.0

    def test_missing_optional_product_fields_does_not_crash(self):
        matcher = ProductMatcher()
        p1 = NormalizedProduct.from_source(
            ProductSourceRecord(
                source_system="SAP",
                source_record_id="P-MIN-1",
                product_name="Generic Widget",
                brand="Acme",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        p2 = NormalizedProduct.from_source(
            ProductSourceRecord(
                source_system="SHOPIFY",
                source_record_id="P-MIN-2",
                product_name="Generic Widget",
                brand="Acme",
                updated_at="2026-01-02T00:00:00Z",
            )
        )
        ev = matcher.evaluate_pair(p1, p2)
        assert ev.decision in {MatchDecision.EXACT_MATCH, MatchDecision.PROBABLE_MATCH}


class TestHardConflictSafeguards:
    def test_conflicting_dob_blocks_customer_merge(self):
        matcher = CustomerMatcher()
        # Same exact name, address, and phone, but confirmed differing dates of birth
        c1 = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="CRM",
                source_record_id="DOB-1",
                first_name="Michael",
                last_name="Scott",
                street_address="1725 Slough Ave",
                phone="555-1234",
                date_of_birth="1965-03-15",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        c2 = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="ERP",
                source_record_id="DOB-2",
                first_name="Michael",
                last_name="Scott",
                street_address="1725 Slough Ave",
                phone="555-1234",
                date_of_birth="1982-10-25",  # Conflicting DOB!
                updated_at="2026-01-02T00:00:00Z",
            )
        )
        ev = matcher.evaluate_pair(c1, c2)

        # Must NOT be EXACT_MATCH or PROBABLE_MATCH! Auto-merging is strictly vetoed
        assert ev.decision != MatchDecision.EXACT_MATCH
        assert ev.decision != MatchDecision.PROBABLE_MATCH
        assert len(ev.hard_conflicts) > 0
        assert "Conflicting Date of Birth" in ev.hard_conflicts[0]

    def test_conflicting_upc_blocks_product_merge(self):
        matcher = ProductMatcher()
        # Same exact title and brand, but differing UPC codes
        p1 = NormalizedProduct.from_source(
            ProductSourceRecord(
                source_system="PIM",
                source_record_id="UPC-1",
                product_name="Ultra 4K Smart TV 55 Inch",
                brand="Samsung",
                upc_ean="887276123456",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        p2 = NormalizedProduct.from_source(
            ProductSourceRecord(
                source_system="SAP",
                source_record_id="UPC-2",
                product_name="Ultra 4K Smart TV 55 Inch",
                brand="Samsung",
                upc_ean="887276999999",  # Conflicting UPC!
                updated_at="2026-01-02T00:00:00Z",
            )
        )
        ev = matcher.evaluate_pair(p1, p2)

        assert ev.decision == MatchDecision.DISTINCT
        assert len(ev.hard_conflicts) > 0
        assert "Conflicting UPC/EAN" in ev.hard_conflicts[0]

    def test_conflicting_brand_blocks_product_merge(self):
        matcher = ProductMatcher()
        # Same exact product title, but differing brands
        p1 = NormalizedProduct.from_source(
            ProductSourceRecord(
                source_system="PIM",
                source_record_id="B-1",
                product_name="Noise Cancelling Wireless Headphones",
                brand="Sony",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        p2 = NormalizedProduct.from_source(
            ProductSourceRecord(
                source_system="SAP",
                source_record_id="B-2",
                product_name="Noise Cancelling Wireless Headphones",
                brand="Bose",  # Different brand!
                updated_at="2026-01-02T00:00:00Z",
            )
        )
        ev = matcher.evaluate_pair(p1, p2)

        assert ev.decision == MatchDecision.DISTINCT
        assert len(ev.hard_conflicts) > 0

