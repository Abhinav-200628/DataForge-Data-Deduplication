"""
Product matching strategy with SKU/UPC validation, brand checking, and price tolerance.
"""

from __future__ import annotations

from typing import Optional

from deduplication.matching.models import MatchEvidence
from deduplication.matching.similarity import (
    numeric_within_percentage,
    string_ratio,
    token_sort_ratio,
)
from deduplication.normalization.product_normalizer import NormalizedProduct
from deduplication.schemas.common import MatchDecision


class ProductMatcher:
    """Evaluates candidate pairs of product records using catalog rules and conflict checks."""

    def __init__(
        self,
        title_fuzzy_threshold: float = 0.90,
        price_tolerance: float = 0.15,
        review_lower_threshold: float = 0.75,
    ) -> None:
        self.title_fuzzy_threshold = title_fuzzy_threshold
        self.price_tolerance = price_tolerance
        self.review_lower_threshold = review_lower_threshold

    def evaluate_pair(
        self, a: NormalizedProduct, b: NormalizedProduct
    ) -> MatchEvidence:
        """
        Compare two normalized product records and return structured match evidence.
        """
        hard_conflicts: list[str] = []
        reasons: list[str] = []
        scores: dict[str, float] = {}

        # 1. Hard Conflicts
        # Conflict A: Conflicting UPC/EAN
        if a.norm_upc_ean and b.norm_upc_ean and a.norm_upc_ean != b.norm_upc_ean:
            hard_conflicts.append(
                f"Conflicting UPC/EAN: '{a.norm_upc_ean}' vs '{b.norm_upc_ean}'"
            )

        # Conflict B: Distinct Brands
        brand_match = a.norm_brand == b.norm_brand
        if a.norm_brand and b.norm_brand and not brand_match:
            # Check for identical SKU across different brands (vendor collision)
            if a.norm_sku and b.norm_sku and a.norm_sku == b.norm_sku:
                return MatchEvidence(
                    record_id_a=a.source_record_id,
                    record_id_b=b.source_record_id,
                    system_a=a.source_system,
                    system_b=b.source_system,
                    decision=MatchDecision.MANUAL_REVIEW,
                    overall_score=0.70,
                    rule_id="RULE_PROD_SKU_COLLISION_REVIEW",
                    reasons=[
                        f"Identical SKU '{a.norm_sku}' across different brands "
                        f"('{a.norm_brand}' vs '{b.norm_brand}')"
                    ],
                    hard_conflicts=[f"Conflicting brands: '{a.norm_brand}' vs '{b.norm_brand}'"],
                    attribute_scores={"sku": 1.0, "brand": 0.0},
                )
            hard_conflicts.append(
                f"Conflicting Brand: '{a.norm_brand}' vs '{b.norm_brand}'"
            )

        title_sim = token_sort_ratio(a.norm_product_name, b.norm_product_name)
        scores["title"] = title_sim
        scores["brand"] = 1.0 if brand_match else 0.0

        if hard_conflicts:
            return MatchEvidence(
                record_id_a=a.source_record_id,
                record_id_b=b.source_record_id,
                system_a=a.source_system,
                system_b=b.source_system,
                decision=MatchDecision.DISTINCT,
                overall_score=0.0,
                rule_id="RULE_PROD_HARD_CONFLICT_DISTINCT",
                reasons=["Vetoed by hard conflict"],
                hard_conflicts=hard_conflicts,
                attribute_scores=scores,
            )

        # 2. Tier 1: Deterministic Exact Matches
        # Exact UPC
        if a.norm_upc_ean and b.norm_upc_ean and a.norm_upc_ean == b.norm_upc_ean:
            reasons.append(f"Exact UPC/EAN match: '{a.norm_upc_ean}'")
            return MatchEvidence(
                record_id_a=a.source_record_id,
                record_id_b=b.source_record_id,
                system_a=a.source_system,
                system_b=b.source_system,
                decision=MatchDecision.EXACT_MATCH,
                overall_score=1.0,
                rule_id="RULE_PROD_EXACT_UPC",
                reasons=reasons,
                attribute_scores=scores,
            )

        # Exact SKU + Brand
        if a.norm_sku and b.norm_sku and a.norm_sku == b.norm_sku and brand_match:
            reasons.append(f"Exact SKU '{a.norm_sku}' and Brand '{a.norm_brand}'")
            return MatchEvidence(
                record_id_a=a.source_record_id,
                record_id_b=b.source_record_id,
                system_a=a.source_system,
                system_b=b.source_system,
                decision=MatchDecision.EXACT_MATCH,
                overall_score=1.0,
                rule_id="RULE_PROD_EXACT_SKU_BRAND",
                reasons=reasons,
                attribute_scores=scores,
            )

        # 3. Tier 2: Corroborated Probable Matches
        # Brand + High Title Similarity + Compatible Price
        price_compatible = (
            numeric_within_percentage(a.unit_price, b.unit_price, self.price_tolerance)
            if (a.unit_price is not None and b.unit_price is not None)
            else True  # If price is missing on one side, do not block
        )

        if brand_match and title_sim >= self.title_fuzzy_threshold and price_compatible:
            reasons.append(
                f"Same brand '{a.norm_brand}', title similarity {title_sim:.2f}, "
                f"and compatible pricing"
            )
            return MatchEvidence(
                record_id_a=a.source_record_id,
                record_id_b=b.source_record_id,
                system_a=a.source_system,
                system_b=b.source_system,
                decision=MatchDecision.PROBABLE_MATCH,
                overall_score=0.92,
                rule_id="RULE_PROD_TITLE_BRAND_PRICE",
                reasons=reasons,
                attribute_scores=scores,
            )

        # 4. Tier 3: Manual Review
        # Same brand and high title match, but price differs significantly (> 30%)
        if (
            brand_match
            and title_sim >= self.title_fuzzy_threshold
            and (a.unit_price is not None and b.unit_price is not None)
            and not numeric_within_percentage(a.unit_price, b.unit_price, 0.30)
        ):
            reasons.append(
                f"Same brand and high title similarity ({title_sim:.2f}), but significant "
                f"price divergence (${a.unit_price} vs ${b.unit_price})"
            )
            return MatchEvidence(
                record_id_a=a.source_record_id,
                record_id_b=b.source_record_id,
                system_a=a.source_system,
                system_b=b.source_system,
                decision=MatchDecision.MANUAL_REVIEW,
                overall_score=0.78,
                rule_id="RULE_PROD_PRICE_DISCREPANCY_REVIEW",
                reasons=reasons,
                attribute_scores=scores,
            )

        # Borderline title similarity with same brand
        if brand_match and (self.review_lower_threshold <= title_sim < self.title_fuzzy_threshold):
            reasons.append(f"Borderline title similarity ({title_sim:.2f}) under same brand")
            return MatchEvidence(
                record_id_a=a.source_record_id,
                record_id_b=b.source_record_id,
                system_a=a.source_system,
                system_b=b.source_system,
                decision=MatchDecision.MANUAL_REVIEW,
                overall_score=title_sim,
                rule_id="RULE_PROD_BORDERLINE_REVIEW",
                reasons=reasons,
                attribute_scores=scores,
            )

        # 5. Tier 4: Distinct Records
        return MatchEvidence(
            record_id_a=a.source_record_id,
            record_id_b=b.source_record_id,
            system_a=a.source_system,
            system_b=b.source_system,
            decision=MatchDecision.DISTINCT,
            overall_score=title_sim,
            rule_id="RULE_PROD_DISTINCT",
            reasons=["Low title similarity or differing brands"],
            attribute_scores=scores,
        )
