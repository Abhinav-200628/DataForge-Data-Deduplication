"""Unit tests for false-positive prevention and shared contact safeguards."""

from deduplication.matching.customer_matcher import CustomerMatcher
from deduplication.normalization.customer_normalizer import NormalizedCustomer
from deduplication.schemas.common import MatchDecision
from deduplication.schemas.customer import CustomerSourceRecord


class TestFalsePositiveSafeguards:
    def test_shared_family_email_prevented_from_auto_merge(self):
        """
        Father (John Miller) and Son (Kevin Miller) sharing the family email 'miller.household@gmail.com'.
        Must NOT auto-merge! Must be routed to manual review.
        """
        matcher = CustomerMatcher()
        rec_father = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="CRM",
                source_record_id="FAM-1",
                first_name="John",
                last_name="Miller",
                email="miller.household@gmail.com",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        rec_son = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="WEB",
                source_record_id="FAM-2",
                first_name="Kevin",
                last_name="Miller",
                email="miller.household@gmail.com",
                updated_at="2026-01-02T00:00:00Z",
            )
        )
        ev = matcher.evaluate_pair(rec_father, rec_son)

        assert ev.decision == MatchDecision.MANUAL_REVIEW
        assert ev.rule_id == "RULE_CUST_SHARED_CONTACT_REVIEW"
        assert any("Shared email" in r for r in ev.reasons)

    def test_shared_roommate_phone_prevented_from_auto_merge(self):
        """
        Two roommates sharing an apartment landline phone.
        Must NOT auto-merge!
        """
        matcher = CustomerMatcher()
        rec_roommate1 = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="BILLING",
                source_record_id="APT-1",
                first_name="David",
                last_name="Clark",
                phone="555-888-1212",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        rec_roommate2 = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="CRM",
                source_record_id="APT-2",
                first_name="Sarah",
                last_name="Adams",
                phone="555-888-1212",
                updated_at="2026-01-02T00:00:00Z",
            )
        )
        ev = matcher.evaluate_pair(rec_roommate1, rec_roommate2)

        assert ev.decision == MatchDecision.MANUAL_REVIEW
        assert ev.rule_id == "RULE_CUST_SHARED_CONTACT_REVIEW"

    def test_same_surname_in_same_zip_with_distinct_first_name_and_address(self):
        """
        Two unrelated people with common last name 'Smith' living in same zip code.
        Different first names, different addresses. Must be DISTINCT.
        """
        matcher = CustomerMatcher()
        c1 = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="CRM",
                source_record_id="CUST-A",
                first_name="Alice",
                last_name="Smith",
                street_address="100 Main St",
                postal_code="62701",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        c2 = NormalizedCustomer.from_source(
            CustomerSourceRecord(
                source_system="CRM",
                source_record_id="CUST-B",
                first_name="Zachary",
                last_name="Smith",
                street_address="999 North Blvd",
                postal_code="62701",
                updated_at="2026-01-01T00:00:00Z",
            )
        )
        ev = matcher.evaluate_pair(c1, c2)

        assert ev.decision == MatchDecision.DISTINCT

