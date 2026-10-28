"""
Cluster resolver that prevents unsafe transitive merges.

Uses connected components with full cluster conflict auditing:
if any two members in a transitive cluster have a hard conflict,
the cluster is safely partitioned and routed to the manual review queue.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence, TypeVar, Union

from deduplication.matching.models import MatchEvidence
from deduplication.normalization.customer_normalizer import NormalizedCustomer
from deduplication.normalization.product_normalizer import NormalizedProduct
from deduplication.schemas.common import MatchDecision

T = TypeVar("T", NormalizedCustomer, NormalizedProduct)


class ClusterResolutionResult:
    """Output of cluster resolution containing safe clusters and review items."""

    def __init__(
        self,
        safe_clusters: list[list[int]],
        manual_reviews: list[MatchEvidence],
        singleton_indices: list[int],
    ) -> None:
        self.safe_clusters = safe_clusters
        self.manual_reviews = manual_reviews
        self.singleton_indices = singleton_indices


def resolve_clusters_safely(
    records: Sequence[Union[NormalizedCustomer, NormalizedProduct]],
    pairwise_evidence: list[MatchEvidence],
    pair_index_map: dict[tuple[int, int], MatchEvidence],
) -> ClusterResolutionResult:
    """
    Cluster records based on exact and probable matches while strictly
    vetoing unsafe transitive merges that contain internal hard conflicts.

    Args:
        records: List of normalized records.
        pairwise_evidence: All evaluated pair evidence.
        pair_index_map: Map from (idx_a, idx_b) to MatchEvidence.

    Returns:
        ClusterResolutionResult containing safe clusters and manual review items.
    """
    n = len(records)
    manual_reviews: list[MatchEvidence] = [
        ev for ev in pairwise_evidence if ev.decision == MatchDecision.MANUAL_REVIEW
    ]

    # Build adjacency graph of auto-mergeable pairs (EXACT_MATCH or PROBABLE_MATCH)
    adj: dict[int, set[int]] = defaultdict(set)
    for (i, j), ev in pair_index_map.items():
        if ev.decision in {MatchDecision.EXACT_MATCH, MatchDecision.PROBABLE_MATCH}:
            adj[i].add(j)
            adj[j].add(i)

    # Find connected components (candidate clusters)
    visited: set[int] = set()
    candidate_clusters: list[list[int]] = []

    for i in range(n):
        if i not in visited:
            cluster: list[int] = []
            queue = [i]
            visited.add(i)
            while queue:
                curr = queue.pop(0)
                cluster.append(curr)
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            candidate_clusters.append(sorted(cluster))

    safe_clusters: list[list[int]] = []
    singleton_indices: list[int] = []

    for cluster in candidate_clusters:
        if len(cluster) == 1:
            singleton_indices.append(cluster[0])
            continue

        # Audit cluster for internal hard conflicts across all pairs in the cluster
        has_transitive_conflict = False
        conflict_pair: tuple[int, int] = (-1, -1)
        conflict_reason = ""

        for idx_x in range(len(cluster)):
            for idx_y in range(idx_x + 1, len(cluster)):
                i, j = cluster[idx_x], cluster[idx_y]
                rec_a, rec_b = records[i], records[j]

                # Customer conflict check
                if isinstance(rec_a, NormalizedCustomer) and isinstance(rec_b, NormalizedCustomer):
                    if rec_a.norm_tax_id and rec_b.norm_tax_id and rec_a.norm_tax_id != rec_b.norm_tax_id:
                        has_transitive_conflict = True
                        conflict_pair = (i, j)
                        conflict_reason = (
                            f"Transitive merge blocked: '{rec_a.source_record_id}' (Tax ID: {rec_a.norm_tax_id}) "
                            f"conflicts with '{rec_b.source_record_id}' (Tax ID: {rec_b.norm_tax_id})"
                        )
                        break
                    if (
                        rec_a.norm_date_of_birth
                        and rec_b.norm_date_of_birth
                        and rec_a.norm_date_of_birth != rec_b.norm_date_of_birth
                    ):
                        has_transitive_conflict = True
                        conflict_pair = (i, j)
                        conflict_reason = (
                            f"Transitive merge blocked: '{rec_a.source_record_id}' (DOB: {rec_a.norm_date_of_birth}) "
                            f"conflicts with '{rec_b.source_record_id}' (DOB: {rec_b.norm_date_of_birth})"
                        )
                        break

                # Product conflict check
                elif isinstance(rec_a, NormalizedProduct) and isinstance(rec_b, NormalizedProduct):
                    if rec_a.norm_upc_ean and rec_b.norm_upc_ean and rec_a.norm_upc_ean != rec_b.norm_upc_ean:
                        has_transitive_conflict = True
                        conflict_pair = (i, j)
                        conflict_reason = (
                            f"Transitive merge blocked: '{rec_a.source_record_id}' (UPC: {rec_a.norm_upc_ean}) "
                            f"conflicts with '{rec_b.source_record_id}' (UPC: {rec_b.norm_upc_ean})"
                        )
                        break
                    if rec_a.norm_brand and rec_b.norm_brand and rec_a.norm_brand != rec_b.norm_brand:
                        has_transitive_conflict = True
                        conflict_pair = (i, j)
                        conflict_reason = (
                            f"Transitive merge blocked: '{rec_a.source_record_id}' (Brand: {rec_a.norm_brand}) "
                            f"conflicts with '{rec_b.source_record_id}' (Brand: {rec_b.norm_brand})"
                        )
                        break

            if has_transitive_conflict:
                break

        if has_transitive_conflict:
            # Veto the entire transitive merge! Break into singletons and route conflict to review
            i, j = conflict_pair
            rec_a, rec_b = records[i], records[j]
            review_ev = MatchEvidence(
                record_id_a=rec_a.source_record_id,
                record_id_b=rec_b.source_record_id,
                system_a=rec_a.source_system,
                system_b=rec_b.source_system,
                decision=MatchDecision.MANUAL_REVIEW,
                overall_score=0.50,
                rule_id="RULE_TRANSITIVE_CONFLICT_VETO",
                reasons=[conflict_reason],
                hard_conflicts=[conflict_reason],
            )
            manual_reviews.append(review_ev)
            # Add all members of conflicting cluster as distinct singletons to avoid false merges
            for member in cluster:
                singleton_indices.append(member)
        else:
            safe_clusters.append(cluster)

    return ClusterResolutionResult(
        safe_clusters=safe_clusters,
        manual_reviews=manual_reviews,
        singleton_indices=singleton_indices,
    )

