"""Matching engine package for entity resolution."""

from deduplication.matching.blocking import (
    generate_candidate_pairs,
    get_customer_blocking_keys,
    get_product_blocking_keys,
    soundex,
)
from deduplication.matching.clustering import (
    ClusterResolutionResult,
    resolve_clusters_safely,
)
from deduplication.matching.customer_matcher import CustomerMatcher
from deduplication.matching.models import MatchEvidence
from deduplication.matching.product_matcher import ProductMatcher
from deduplication.matching.similarity import (
    jaro_winkler_similarity,
    numeric_within_percentage,
    string_ratio,
    token_sort_ratio,
)

__all__ = [
    "soundex",
    "get_customer_blocking_keys",
    "get_product_blocking_keys",
    "generate_candidate_pairs",
    "ClusterResolutionResult",
    "resolve_clusters_safely",
    "CustomerMatcher",
    "ProductMatcher",
    "MatchEvidence",
    "string_ratio",
    "token_sort_ratio",
    "jaro_winkler_similarity",
    "numeric_within_percentage",
]
