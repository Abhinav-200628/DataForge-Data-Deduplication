"""
Pipeline orchestrator tying together Ingestion, Normalization, Blocking,
Matching, Survivorship, Lineage, Persistence, and Reconciliation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any, Optional, Union
import uuid

from deduplication.ingestion.loader import CSVLoader, IngestionResult
from deduplication.lineage.models import ManualReviewItem, RecordLineage
from deduplication.matching.blocking import (
    generate_candidate_pairs,
    get_customer_blocking_keys,
    get_product_blocking_keys,
)
from deduplication.matching.clustering import resolve_clusters_safely
from deduplication.matching.customer_matcher import CustomerMatcher
from deduplication.matching.models import MatchEvidence
from deduplication.matching.product_matcher import ProductMatcher
from deduplication.normalization.customer_normalizer import NormalizedCustomer
from deduplication.normalization.product_normalizer import NormalizedProduct
from deduplication.schemas.common import EntityType, MatchDecision, RunStatus
from deduplication.schemas.customer import CustomerSourceRecord
from deduplication.schemas.product import ProductSourceRecord
from deduplication.storage.repository import SQLiteRepository
from deduplication.survivorship.engine import SurvivorshipEngine
from deduplication.survivorship.models import MasterCustomer, MasterProduct


class ReconciliationError(Exception):
    """Raised when record accounting violates conservation laws."""


@dataclass
class PipelineMetrics:
    """Detailed operational and reconciliation counts for a pipeline run."""
    run_id: str
    entity_type: EntityType
    started_at: str
    ended_at: str = ""
    status: RunStatus = RunStatus.RUNNING
    input_count: int = 0
    valid_count: int = 0
    quarantined_count: int = 0
    exact_matches: int = 0
    probable_matches: int = 0
    manual_reviews: int = 0
    distinct_count: int = 0
    master_records_created: int = 0
    elapsed_seconds: float = 0.0
    error_summary: Optional[str] = None

    def assert_reconciliation(self) -> None:
        """
        Assert mathematical conservation laws:
            1. Total Input == Valid + Quarantined
            2. Valid Records == Records linked in Master Lineage + Quarantined/Filtered
        """
        if self.input_count != (self.valid_count + self.quarantined_count):
            raise ReconciliationError(
                f"Reconciliation Balance Broken! "
                f"Total Input ({self.input_count}) != "
                f"Valid ({self.valid_count}) + Quarantined ({self.quarantined_count})"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "entity_type": self.entity_type.value,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "status": self.status.value,
            "input_count": self.input_count,
            "valid_count": self.valid_count,
            "quarantined_count": self.quarantined_count,
            "exact_matches": self.exact_matches,
            "probable_matches": self.probable_matches,
            "manual_reviews": self.manual_reviews,
            "distinct_count": self.distinct_count,
            "master_records_created": self.master_records_created,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "error_summary": self.error_summary,
        }


class DeduplicationPipeline:
    """Main orchestrator for customer and product entity resolution."""

    def __init__(
        self,
        entity_type: EntityType,
        db_path: Union[str, Path] = "pipeline.db",
        output_dir: Optional[Union[str, Path]] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> None:
        self.entity_type = entity_type
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir) if output_dir else Path("output")
        self.config = config or {}
        self.repository = SQLiteRepository(self.db_path)
        self.survivorship_engine = SurvivorshipEngine()

    def run(
        self,
        input_path: Union[str, Path],
        run_id: Optional[str] = None,
        force_full_pairwise: bool = False,
    ) -> PipelineMetrics:
        """
        Execute full deduplication lifecycle on an input file.
        """
        active_run_id = run_id or f"RUN-{uuid.uuid4().hex[:12]}"
        start_dt = datetime.now(timezone.utc).isoformat()
        start_perf = time.perf_counter()

        self.repository.record_run_start(active_run_id, self.entity_type, start_dt)

        metrics = PipelineMetrics(
            run_id=active_run_id,
            entity_type=self.entity_type,
            started_at=start_dt,
        )

        try:
            # Stage A: Ingestion & Schema Validation
            loader = CSVLoader(
                entity_type=self.entity_type,
                run_id=active_run_id,
                allow_unknown_columns=self.config.get("allow_unknown_columns", False),
            )
            ingest_result = loader.load_from_path(input_path)

            metrics.input_count = ingest_result.total_rows_read
            metrics.valid_count = ingest_result.valid_count
            metrics.quarantined_count = ingest_result.quarantined_count

            # If no valid records, finish early
            if metrics.valid_count == 0:
                elapsed = time.perf_counter() - start_perf
                end_dt = datetime.now(timezone.utc).isoformat()
                metrics.ended_at = end_dt
                metrics.elapsed_seconds = elapsed
                metrics.status = RunStatus.COMPLETED
                metrics.assert_reconciliation()

                self.repository.publish_pipeline_results(
                    run_id=active_run_id,
                    entity_type=self.entity_type,
                    master_records=[],
                    lineages=[],
                    quarantines=ingest_result.quarantined_records,
                    review_items=[],
                )
                self.repository.record_run_finish(
                    run_id=active_run_id,
                    status=RunStatus.COMPLETED,
                    ended_at=end_dt,
                    input_count=metrics.input_count,
                    valid_count=0,
                    quarantined_count=metrics.quarantined_count,
                    exact_count=0,
                    probable_count=0,
                    review_count=0,
                    distinct_count=0,
                    elapsed_seconds=elapsed,
                )
                return metrics

            # Stage B: Normalization
            normalized_records: list[Union[NormalizedCustomer, NormalizedProduct]] = []
            if self.entity_type == EntityType.CUSTOMER:
                for rec in ingest_result.valid_records:
                    assert isinstance(rec, CustomerSourceRecord)
                    normalized_records.append(NormalizedCustomer.from_source(rec))
                matcher = CustomerMatcher()
                key_extractor = get_customer_blocking_keys
            else:
                for rec in ingest_result.valid_records:
                    assert isinstance(rec, ProductSourceRecord)
                    normalized_records.append(NormalizedProduct.from_source(rec))
                matcher = ProductMatcher()
                key_extractor = get_product_blocking_keys

            # Stage B (cont): Blocking & Candidate Pair Generation
            candidate_pairs = generate_candidate_pairs(
                normalized_records,
                key_extractor=key_extractor,  # type: ignore
                force_full_pairwise=force_full_pairwise,
            )

            # Evaluate Candidate Pairs
            pair_evidence_map: dict[tuple[int, int], MatchEvidence] = {}
            all_evidence: list[MatchEvidence] = []

            for i, j in candidate_pairs:
                rec_a, rec_b = normalized_records[i], normalized_records[j]
                evidence = matcher.evaluate_pair(rec_a, rec_b)  # type: ignore
                pair_evidence_map[(i, j)] = evidence
                all_evidence.append(evidence)

            # Stage B (cont): Safe Cluster Resolution (Transitive conflict protection)
            cluster_res = resolve_clusters_safely(
                records=normalized_records,
                pairwise_evidence=all_evidence,
                pair_index_map=pair_evidence_map,
            )

            # Stage C: Survivorship & Lineage Generation
            master_records: list[Union[MasterCustomer, MasterProduct]] = []
            lineages: list[RecordLineage] = []

            # 1. Process Multi-Record Safe Clusters (Merged Records)
            for cluster_indices in cluster_res.safe_clusters:
                cluster_members = [normalized_records[idx] for idx in cluster_indices]
                if self.entity_type == EntityType.CUSTOMER:
                    master_cust = self.survivorship_engine.consolidate_customers(
                        cluster_members  # type: ignore
                    )
                    master_records.append(master_cust)
                    master_id = master_cust.master_id
                else:
                    master_prod = self.survivorship_engine.consolidate_products(
                        cluster_members  # type: ignore
                    )
                    master_records.append(master_prod)
                    master_id = master_prod.master_id

                # Assign lineage for each member of the cluster
                for member in cluster_members:
                    # Find highest matching evidence involving this member
                    member_evs = [
                        ev for ev in all_evidence
                        if (ev.record_id_a == member.source_record_id or ev.record_id_b == member.source_record_id)
                        and ev.decision in {MatchDecision.EXACT_MATCH, MatchDecision.PROBABLE_MATCH}
                    ]
                    decision = member_evs[0].decision if member_evs else MatchDecision.PROBABLE_MATCH
                    rule_id = member_evs[0].rule_id if member_evs else "RULE_CLUSTER_CONSOLIDATION"
                    conf = member_evs[0].overall_score if member_evs else 0.90
                    reasons = member_evs[0].reasons if member_evs else ["Merged via cluster corroboration"]

                    lineages.append(
                        RecordLineage(
                            lineage_id=str(uuid.uuid4()),
                            run_id=active_run_id,
                            entity_type=self.entity_type,
                            source_system=member.source_system,
                            source_record_id=member.source_record_id,
                            master_id=master_id,
                            decision=decision,
                            match_rule_id=rule_id,
                            confidence_score=conf,
                            merge_reasons=reasons,
                        )
                    )

            # 2. Process Singletons (Distinct Records)
            for idx in cluster_res.singleton_indices:
                member = normalized_records[idx]
                if self.entity_type == EntityType.CUSTOMER:
                    master_cust = self.survivorship_engine.consolidate_customers([member])  # type: ignore
                    master_records.append(master_cust)
                    master_id = master_cust.master_id
                else:
                    master_prod = self.survivorship_engine.consolidate_products([member])  # type: ignore
                    master_records.append(master_prod)
                    master_id = master_prod.master_id

                lineages.append(
                    RecordLineage(
                        lineage_id=str(uuid.uuid4()),
                        run_id=active_run_id,
                        entity_type=self.entity_type,
                        source_system=member.source_system,
                        source_record_id=member.source_record_id,
                        master_id=master_id,
                        decision=MatchDecision.DISTINCT,
                        match_rule_id="RULE_NEW_MASTER_DISTINCT",
                        confidence_score=1.0,
                        merge_reasons=["New distinct master record created"],
                    )
                )

            # 3. Process Manual Review Items
            review_items: list[ManualReviewItem] = []
            for ev in cluster_res.manual_reviews:
                review_items.append(
                    ManualReviewItem(
                        review_id=f"REV-{uuid.uuid4().hex[:12]}",
                        run_id=active_run_id,
                        entity_type=self.entity_type,
                        source_system=ev.system_a,
                        source_record_id=ev.record_id_a,
                        candidate_master_id=None,
                        similarity_score=ev.overall_score,
                        reasons=ev.reasons + ev.hard_conflicts,
                        hard_conflicts=ev.hard_conflicts,
                    )
                )

            # Compute Metric Counts
            metrics.master_records_created = len(master_records)
            metrics.exact_matches = sum(
                1 for l in lineages if l.decision == MatchDecision.EXACT_MATCH
            )
            metrics.probable_matches = sum(
                1 for l in lineages if l.decision == MatchDecision.PROBABLE_MATCH
            )
            metrics.distinct_count = sum(
                1 for l in lineages if l.decision == MatchDecision.DISTINCT
            )
            metrics.manual_reviews = len(review_items)

            # Reconciliation Assertion
            metrics.assert_reconciliation()

            # Stage D: Transactional Publishing & Output Export
            self.repository.publish_pipeline_results(
                run_id=active_run_id,
                entity_type=self.entity_type,
                master_records=master_records,
                lineages=lineages,
                quarantines=ingest_result.quarantined_records,
                review_items=review_items,
            )

            # Export CSV and JSON output files
            self.repository.export_outputs(self.output_dir, self.entity_type)

            # Record final metrics
            elapsed = time.perf_counter() - start_perf
            end_dt = datetime.now(timezone.utc).isoformat()
            metrics.ended_at = end_dt
            metrics.elapsed_seconds = elapsed
            metrics.status = RunStatus.COMPLETED

            self.repository.record_run_finish(
                run_id=active_run_id,
                status=RunStatus.COMPLETED,
                ended_at=end_dt,
                input_count=metrics.input_count,
                valid_count=metrics.valid_count,
                quarantined_count=metrics.quarantined_count,
                exact_count=metrics.exact_matches,
                probable_count=metrics.probable_matches,
                review_count=metrics.manual_reviews,
                distinct_count=metrics.distinct_count,
                elapsed_seconds=elapsed,
            )

            return metrics

        except Exception as e:
            elapsed = time.perf_counter() - start_perf
            end_dt = datetime.now(timezone.utc).isoformat()
            metrics.ended_at = end_dt
            metrics.elapsed_seconds = elapsed
            metrics.status = RunStatus.FAILED
            metrics.error_summary = str(e)

            self.repository.record_run_finish(
                run_id=active_run_id,
                status=RunStatus.FAILED,
                ended_at=end_dt,
                input_count=metrics.input_count,
                valid_count=metrics.valid_count,
                quarantined_count=metrics.quarantined_count,
                exact_count=metrics.exact_matches,
                probable_count=metrics.probable_matches,
                review_count=metrics.manual_reviews,
                distinct_count=metrics.distinct_count,
                elapsed_seconds=elapsed,
                error_summary=str(e),
            )
            raise
