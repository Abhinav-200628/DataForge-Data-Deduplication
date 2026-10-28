"""
Customer matching strategy with multi-attribute corroboration and hard-conflict vetoes.
"""

from __future__ import annotations

from typing import Optional

from deduplication.matching.models import MatchEvidence
from deduplication.matching.similarity import (
    jaro_winkler_similarity,
    string_ratio,
    token_sort_ratio,
)
from deduplication.normalization.customer_normalizer import NormalizedCustomer
from deduplication.schemas.common import MatchDecision


class CustomerMatcher:
    """Evaluates candidate pairs of customer records using rule tiers and conflict checks."""

    def __init__(
        self,
        name_exact_threshold: float = 0.95,
        name_fuzzy_threshold: float = 0.88,
        address_fuzzy_threshold: float = 0.85,
        review_lower_threshold: float = 0.72,
    ) -> None:
        self.name_exact_threshold = name_exact_threshold
        self.name_fuzzy_threshold = name_fuzzy_threshold
        self.address_fuzzy_threshold = address_fuzzy_threshold
        self.review_lower_threshold = review_lower_threshold

    def evaluate_pair(
        self, a: NormalizedCustomer, b: NormalizedCustomer
    ) -> MatchEvidence:
        """
        Compare two normalized customer records and return structured match evidence.
        """
        hard_conflicts: list[str] = []
        reasons: list[str] = []
        scores: dict[str, float] = {}

        # 1. Check Hard Conflicts First
        # Conflict A: Distinct Tax IDs
        if a.norm_tax_id and b.norm_tax_id and a.norm_tax_id != b.norm_tax_id:
            hard_conflicts.append(
                f"Conflicting Tax ID: '{a.norm_tax_id}' vs '{b.norm_tax_id}'"
            )

        # Conflict B: Distinct Date of Birth
        if (
            a.norm_date_of_birth
            and b.norm_date_of_birth
            and a.norm_date_of_birth != b.norm_date_of_birth
        ):
            hard_conflicts.append(
                f"Conflicting Date of Birth: '{a.norm_date_of_birth}' vs '{b.norm_date_of_birth}'"
            )

        # Compute attribute similarities
        name_sim = max(
            token_sort_ratio(a.norm_full_name, b.norm_full_name),
            jaro_winkler_similarity(a.norm_full_name, b.norm_full_name),
        )
        scores["name"] = name_sim

        first_name_sim = (
            jaro_winkler_similarity(a.norm_first_name, b.norm_first_name)
            if a.norm_first_name and b.norm_first_name
            else 1.0
        )
        scores["first_name"] = first_name_sim

        last_name_sim = (
            jaro_winkler_similarity(a.norm_last_name, b.norm_last_name)
            if a.norm_last_name and b.norm_last_name
            else 0.0
        )
        scores["last_name"] = last_name_sim

        address_sim = (
            token_sort_ratio(a.norm_street_address, b.norm_street_address)
            if a.norm_street_address and b.norm_street_address
            else 0.0
        )
        scores["address"] = address_sim

        # 2. Shared Contact Guard (Family / Roommate check)
        # If email or phone matches exactly, but first names are conflicting
        shared_contact = False
        if a.norm_email and b.norm_email and a.norm_email == b.norm_email:
            if a.norm_first_name and b.norm_first_name and first_name_sim < 0.50:
                shared_contact = True
                reasons.append(
                    f"Shared email '{a.norm_email}' with conflicting first names "
                    f"('{a.norm_first_name}' vs '{b.norm_first_name}')"
                )

        if a.norm_phone and b.norm_phone and a.norm_phone == b.norm_phone:
            if a.norm_first_name and b.norm_first_name and first_name_sim < 0.50:
                shared_contact = True
                reasons.append(
                    f"Shared phone '{a.norm_phone}' with conflicting first names "
                    f"('{a.norm_first_name}' vs '{b.norm_first_name}')"
                )

        if shared_contact:
            # Shared contact prevents auto-merge; route directly to manual review
            return MatchEvidence(
                record_id_a=a.source_record_id,
                record_id_b=b.source_record_id,
                system_a=a.source_system,
                system_b=b.source_system,
                decision=MatchDecision.MANUAL_REVIEW,
                overall_score=0.75,
                rule_id="RULE_CUST_SHARED_CONTACT_REVIEW",
                reasons=reasons,
                hard_conflicts=hard_conflicts,
                attribute_scores=scores,
            )

        # If hard conflicts exist, auto-merging is strictly vetoed!
        if hard_conflicts:
            # If name or contact looks similar despite conflict, flag for manual review
            if name_sim >= 0.80 or (a.norm_email and a.norm_email == b.norm_email):
                return MatchEvidence(
                    record_id_a=a.source_record_id,
                    record_id_b=b.source_record_id,
                    system_a=a.source_system,
                    system_b=b.source_system,
                    decision=MatchDecision.MANUAL_REVIEW,
                    overall_score=0.60,
                    rule_id="RULE_CUST_HARD_CONFLICT_REVIEW",
                    reasons=["High similarity but blocked by hard conflict veto"],
                    hard_conflicts=hard_conflicts,
                    attribute_scores=scores,
                )
            return MatchEvidence(
                record_id_a=a.source_record_id,
                record_id_b=b.source_record_id,
                system_a=a.source_system,
                system_b=b.source_system,
                decision=MatchDecision.DISTINCT,
                overall_score=0.10,
                rule_id="RULE_CUST_HARD_CONFLICT_DISTINCT",
                reasons=["Vetoed by hard conflict"],
                hard_conflicts=hard_conflicts,
                attribute_scores=scores,
            )

        # 3. Tier 1: Deterministic Exact Matches
        # Exact Tax ID
        if a.norm_tax_id and b.norm_tax_id and a.norm_tax_id == b.norm_tax_id:
            reasons.append(f"Exact Tax ID match: '{a.norm_tax_id}'")
            return MatchEvidence(
                record_id_a=a.source_record_id,
                record_id_b=b.source_record_id,
                system_a=a.source_system,
                system_b=b.source_system,
                decision=MatchDecision.EXACT_MATCH,
                overall_score=1.0,
                rule_id="RULE_CUST_EXACT_TAX_ID",
                reasons=reasons,
                attribute_scores=scores,
            )

        # Exact Email + Last Name Match
        if (
            a.norm_email
            and b.norm_email
            and a.norm_email == b.norm_email
            and last_name_sim >= 0.90
        ):
            reasons.append(f"Exact Email '{a.norm_email}' and matching surname")
            return MatchEvidence(
                record_id_a=a.source_record_id,
                record_id_b=b.source_record_id,
                system_a=a.source_system,
                system_b=b.source_system,
                decision=MatchDecision.EXACT_MATCH,
                overall_score=1.0,
                rule_id="RULE_CUST_EXACT_EMAIL_LASTNAME",
                reasons=reasons,
                attribute_scores=scores,
            )

        # Exact Phone + Surname + Zip
        if (
            a.norm_phone
            and b.norm_phone
            and a.norm_phone == b.norm_phone
            and last_name_sim >= 0.90
            and a.norm_postal_code
            and a.norm_postal_code == b.norm_postal_code
        ):
            reasons.append(f"Exact Phone '{a.norm_phone}', surname, and zip '{a.norm_postal_code}'")
            return MatchEvidence(
                record_id_a=a.source_record_id,
                record_id_b=b.source_record_id,
                system_a=a.source_system,
                system_b=b.source_system,
                decision=MatchDecision.EXACT_MATCH,
                overall_score=0.98,
                rule_id="RULE_CUST_EXACT_PHONE_LASTNAME_ZIP",
                reasons=reasons,
                attribute_scores=scores,
            )

        # 4. Tier 2: Corroborated Probable Matches
        # Name + Phone
        if (
            name_sim >= self.name_fuzzy_threshold
            and a.norm_phone
            and b.norm_phone
            and a.norm_phone == b.norm_phone
        ):
            reasons.append(
                f"High name similarity ({name_sim:.2f}) corroborated by exact phone '{a.norm_phone}'"
            )
            return MatchEvidence(
                record_id_a=a.source_record_id,
                record_id_b=b.source_record_id,
                system_a=a.source_system,
                system_b=b.source_system,
                decision=MatchDecision.PROBABLE_MATCH,
                overall_score=0.92,
                rule_id="RULE_CUST_CORROBORATED_NAME_PHONE",
                reasons=reasons,
                attribute_scores=scores,
            )

        # Name + Address + Postal Code
        if (
            name_sim >= self.name_fuzzy_threshold
            and address_sim >= self.address_fuzzy_threshold
            and a.norm_postal_code
            and a.norm_postal_code == b.norm_postal_code
        ):
            reasons.append(
                f"High name similarity ({name_sim:.2f}) corroborated by address "
                f"({address_sim:.2f}) and zip '{a.norm_postal_code}'"
            )
            return MatchEvidence(
                record_id_a=a.source_record_id,
                record_id_b=b.source_record_id,
                system_a=a.source_system,
                system_b=b.source_system,
                decision=MatchDecision.PROBABLE_MATCH,
                overall_score=0.90,
                rule_id="RULE_CUST_CORROBORATED_NAME_ADDRESS",
                reasons=reasons,
                attribute_scores=scores,
            )

        # 5. Tier 3: Ambiguous / Manual Review
        # Same name in same city/zip, but missing phone and email (cannot auto-merge safely)
        if (
            name_sim >= 0.88
            and a.norm_postal_code
            and a.norm_postal_code == b.norm_postal_code
            and not (a.norm_email or b.norm_email or a.norm_phone or b.norm_phone)
        ):
            reasons.append("Matching name and zip, but lacking contact channels to corroborate")
            return MatchEvidence(
                record_id_a=a.source_record_id,
                record_id_b=b.source_record_id,
                system_a=a.source_system,
                system_b=b.source_system,
                decision=MatchDecision.MANUAL_REVIEW,
                overall_score=0.76,
                rule_id="RULE_CUST_MISSING_CORROBORATION_REVIEW",
                reasons=reasons,
                attribute_scores=scores,
            )

        # Borderline name similarity with matching zip code AND similar street address
        if (
            self.review_lower_threshold <= name_sim < self.name_fuzzy_threshold
            and a.norm_postal_code
            and a.norm_postal_code == b.norm_postal_code
            and address_sim >= 0.70
        ):
            reasons.append(
                f"Borderline name similarity ({name_sim:.2f}) with same zip code and similar address ({address_sim:.2f})"
            )
            return MatchEvidence(
                record_id_a=a.source_record_id,
                record_id_b=b.source_record_id,
                system_a=a.source_system,
                system_b=b.source_system,
                decision=MatchDecision.MANUAL_REVIEW,
                overall_score=name_sim,
                rule_id="RULE_CUST_BORDERLINE_SCORE_REVIEW",
                reasons=reasons,
                attribute_scores=scores,
            )

        # 6. Tier 4: Distinct Records
        return MatchEvidence(
            record_id_a=a.source_record_id,
            record_id_b=b.source_record_id,
            system_a=a.source_system,
            system_b=b.source_system,
            decision=MatchDecision.DISTINCT,
            overall_score=max(name_sim, address_sim),
            rule_id="RULE_CUST_DISTINCT",
            reasons=["Insufficient evidence to link records"],
            attribute_scores=scores,
        )

