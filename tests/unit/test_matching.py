"""Unit tests for entity matching, corroboration rules, hard conflicts, and transitive safety."""

import pytest

from deduplication.matching.blocking import (
    generate_candidate_pairs,
    get_customer_blocking_keys,
    soundex,
)
from deduplication.matching.clustering import resolve_clusters_safely
from deduplication.matching.customer_matcher import CustomerMatcher
from deduplication.matching.models import MatchEvidence
from deduplication.matching.product_matcher import ProductMatcher
from deduplication.normalization.customer_normalizer import NormalizedCustomer
from deduplication.normalization.product_normalizer import NormalizedProduct
from deduplication.schemas.common import MatchDecision
from deduplication.schemas.customer import CustomerSourceRecord
from deduplication.schemas.product import ProductSourceRecord


class TestBlockingAndSoundex:
    def test_soundex(self):
        assert soundex("Smith") == "S530"
        assert soundex("Smythe") == "S530"
        assert soundex("Johnson") == "J525"
        assert soundex("") == "0000"

    def test_customer_blocking_keys(self):
        raw = CustomerSourceRecord(
            source_system="CRM",
            source_record_id="C-1",
            last_name="Smith",
            postal_code="62701",
            phone="555-1234567",
            email="john.smith@gmail.com",
            tax_id="123-45-6789",
            updated_at="2026-01-01T00:00:00Z",
        )
        norm = NormalizedCustomer.from_source(raw)
        keys = get_customer_blocking_keys(norm)

        assert any("S530_627" in k for k in keys)
        assert any("1234567" in k for k in keys)
        assert any("gmail.com_S" in k for k in keys)
        assert any("123-45-6789" in k for k in keys)


class TestCustomerMatcher:
    @pytest.fixture
    def matcher(self) -> CustomerMatcher:
        return CustomerMatcher()

    def test_exact_tax_id_match(self, matcher: CustomerMatcher):
        rec_a = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="CRM",
                source_record_id="A-1",
                first_name="Alice",
                last_name="Smith",
                tax_id="999-88-7777",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        rec_b = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="ERP",
                source_record_id="B-1",
                first_name="A.",
                last_name="Smith",
                tax_id="999-88-7777",
                updated_at="2026-01-02T00:00:00Z",
            )
        )
        ev = matcher.evaluate_pair(rec_a, rec_b)

        assert ev.decision == MatchDecision.EXACT_MATCH
        assert ev.overall_score == 1.0
        assert ev.rule_id == "RULE_CUST_EXACT_TAX_ID"

    def test_hard_conflict_different_tax_ids(self, matcher: CustomerMatcher):
        # Same exact name and address, but DIFFERENT Tax IDs
        rec_a = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="CRM",
                source_record_id="A-2",
                first_name="David",
                last_name="Miller",
                street_address="100 Main St",
                postal_code="98101",
                tax_id="111-22-3333",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        rec_b = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="ERP",
                source_record_id="B-2",
                first_name="David",
                last_name="Miller",
                street_address="100 Main St",
                postal_code="98101",
                tax_id="999-88-7777",  # CONFLICT
                updated_at="2026-01-02T00:00:00Z",
            )
        )
        ev = matcher.evaluate_pair(rec_a, rec_b)

        assert ev.decision in {MatchDecision.MANUAL_REVIEW, MatchDecision.DISTINCT}
        assert len(ev.hard_conflicts) > 0
        assert "Conflicting Tax ID" in ev.hard_conflicts[0]

    def test_shared_contact_guard_family_roommates(self, matcher: CustomerMatcher):
        # Same email and phone, but "John Smith" vs "Mary Smith" (Family members sharing email)
        rec_a = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="WEB",
                source_record_id="A-3",
                first_name="John",
                last_name="Smith",
                email="thesmiths@example.com",
                phone="555-0199",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        rec_b = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="CRM",
                source_record_id="B-3",
                first_name="Mary",
                last_name="Smith",
                email="thesmiths@example.com",
                phone="555-0199",
                updated_at="2026-01-02T00:00:00Z",
            )
        )
        ev = matcher.evaluate_pair(rec_a, rec_b)

        # Must NOT auto-merge! Should route to manual review
        assert ev.decision == MatchDecision.MANUAL_REVIEW
        assert ev.rule_id == "RULE_CUST_SHARED_CONTACT_REVIEW"
        assert any("Shared email" in r for r in ev.reasons)

    def test_corroborated_probable_match_name_and_phone(self, matcher: CustomerMatcher):
        # Slight name typo ("Jonathon" vs "Jonathan"), same phone
        rec_a = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="CRM",
                source_record_id="A-4",
                first_name="Jonathan",
                last_name="Taylor",
                phone="555-4321098",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        rec_b = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="WEB",
                source_record_id="B-4",
                first_name="Jonathon",
                last_name="Taylor",
                phone="555-4321098",
                updated_at="2026-01-02T00:00:00Z",
            )
        )
        ev = matcher.evaluate_pair(rec_a, rec_b)

        assert ev.decision == MatchDecision.PROBABLE_MATCH
        assert ev.rule_id == "RULE_CUST_CORROBORATED_NAME_PHONE"
        assert ev.overall_score >= 0.90


class TestProductMatcher:
    @pytest.fixture
    def matcher(self) -> ProductMatcher:
        return ProductMatcher()

    def test_exact_upc_match(self, matcher: ProductMatcher):
        rec_a = NormalizedProduct.from_source(
            ProductSourceRecord(
                source_system="SAP",
                source_record_id="P-1",
                product_name="Sony Headphones WH-1000XM5",
                brand="Sony",
                upc_ean="027242923456",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        rec_b = NormalizedProduct.from_source(
            ProductSourceRecord(
                source_system="SHOPIFY",
                source_record_id="P-2",
                product_name="WH-1000XM5 Wireless Headphones by Sony",
                brand="Sony",
                upc_ean="027242923456",
                updated_at="2026-01-02T00:00:00Z",
            )
        )
        ev = matcher.evaluate_pair(rec_a, rec_b)

        assert ev.decision == MatchDecision.EXACT_MATCH
        assert ev.rule_id == "RULE_PROD_EXACT_UPC"

    def test_conflicting_upc_blocks_merge(self, matcher: ProductMatcher):
        # Similar names, but conflicting UPCs
        rec_a = NormalizedProduct.from_source(
            ProductSourceRecord(
                source_system="SAP",
                source_record_id="P-3",
                product_name="Sony Bravia 65-inch OLED",
                brand="Sony",
                upc_ean="111111111111",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        rec_b = NormalizedProduct.from_source(
            ProductSourceRecord(
                source_system="SHOPIFY",
                source_record_id="P-4",
                product_name="Sony Bravia 65-inch OLED",
                brand="Sony",
                upc_ean="999999999999",  # Conflicting UPC
                updated_at="2026-01-02T00:00:00Z",
            )
        )
        ev = matcher.evaluate_pair(rec_a, rec_b)

        assert ev.decision == MatchDecision.DISTINCT
        assert len(ev.hard_conflicts) > 0

    def test_price_divergence_routes_to_review(self, matcher: ProductMatcher):
        # Same brand and high title match, but price is $100 vs $400 (refurbished/accessory)
        rec_a = NormalizedProduct.from_source(
            ProductSourceRecord(
                source_system="SAP",
                source_record_id="P-5",
                product_name="Logitech MX Master 3S Mouse",
                brand="Logitech",
                unit_price=99.99,
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        rec_b = NormalizedProduct.from_source(
            ProductSourceRecord(
                source_system="AMAZON",
                source_record_id="P-6",
                product_name="Logitech MX Master 3S Mouse",
                brand="Logitech",
                unit_price=249.99,  # Major price difference
                updated_at="2026-01-02T00:00:00Z",
            )
        )
        ev = matcher.evaluate_pair(rec_a, rec_b)

        assert ev.decision == MatchDecision.MANUAL_REVIEW
        assert ev.rule_id == "RULE_PROD_PRICE_DISCREPANCY_REVIEW"


class TestTransitiveMergeProtection:
    def test_transitive_merge_conflict_split(self):
        """
        Scenario:
        - Record A: Tax ID 111-11-1111, Email: family@test.com
        - Record B: Tax ID None,         Email: family@test.com
        - Record C: Tax ID 222-22-2222, Email: family@test.com

        A matches B (email), B matches C (email).
        A and C have CONFLICTING TAX IDs!
        The clustering algorithm MUST detect the transitive conflict,
        veto the merge, and route the conflict to review.
        """
        rec_a = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="CRM",
                source_record_id="A",
                last_name="Johnson",
                email="family@test.com",
                tax_id="111-11-1111",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        rec_b = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="ERP",
                source_record_id="B",
                last_name="Johnson",
                email="family@test.com",
                tax_id=None,
                updated_at="2026-01-02T00:00:00Z",
            )
        )
        rec_c = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="WEB",
                source_record_id="C",
                last_name="Johnson",
                email="family@test.com",
                tax_id="222-22-2222",
                updated_at="2026-01-03T00:00:00Z",
            )
        )

        records = [rec_a, rec_b, rec_c]
        # (A, B) is exact match
        ev_ab = MatchEvidence("A", "B", "CRM", "ERP", MatchDecision.EXACT_MATCH, 1.0, "RULE_EMAIL")
        # (B, C) is exact match
        ev_bc = MatchEvidence("B", "C", "ERP", "WEB", MatchDecision.EXACT_MATCH, 1.0, "RULE_EMAIL")

        pair_map = {(0, 1): ev_ab, (1, 2): ev_bc}
        res = resolve_clusters_safely(records, [ev_ab, ev_bc], pair_map)

        # Unsafe merge of {A, B, C} MUST NOT happen!
        assert len(res.safe_clusters) == 0
        assert len(res.manual_reviews) >= 1
        assert any("Transitive merge blocked" in r for r in res.manual_reviews[0].reasons)
        # All members retained as singletons to protect against false merge
        assert set(res.singleton_indices) == {0, 1, 2}

