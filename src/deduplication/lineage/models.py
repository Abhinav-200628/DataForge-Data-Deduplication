"""Audit lineage and manual review data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from typing import Any, Optional

from deduplication.schemas.common import EntityType, MatchDecision


@dataclass(frozen=True)
class RecordLineage:
    """Immutable audit trail linking an ingested source record to a master entity."""
    lineage_id: str
    run_id: str
    entity_type: EntityType
    source_system: str
    source_record_id: str
    master_id: str
    decision: MatchDecision
    match_rule_id: str
    confidence_score: float
    merge_reasons: list[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert lineage entry to serializable dictionary."""
        return {
            "lineage_id": self.lineage_id,
            "run_id": self.run_id,
            "entity_type": self.entity_type.value,
            "source_system": self.source_system,
            "source_record_id": self.source_record_id,
            "master_id": self.master_id,
            "decision": self.decision.value,
            "match_rule_id": self.match_rule_id,
            "confidence_score": round(self.confidence_score, 4),
            "merge_reasons": self.merge_reasons,
            "created_at": self.created_at,
        }

    def merge_reasons_json(self) -> str:
        """JSON-serialized merge reasons for database insertion."""
        return json.dumps(self.merge_reasons, sort_keys=True)


@dataclass(frozen=True)
class ManualReviewItem:
    """Ambiguous or conflicting candidate pair flagged for human triage."""
    review_id: str
    run_id: str
    entity_type: EntityType
    source_system: str
    source_record_id: str
    candidate_master_id: Optional[str]
    similarity_score: float
    reasons: list[str]
    hard_conflicts: list[str] = field(default_factory=list)
    status: str = "PENDING"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert review item to dictionary."""
        return {
            "review_id": self.review_id,
            "run_id": self.run_id,
            "entity_type": self.entity_type.value,
            "source_system": self.source_system,
            "source_record_id": self.source_record_id,
            "candidate_master_id": self.candidate_master_id,
            "similarity_score": round(self.similarity_score, 4),
            "reasons": self.reasons,
            "hard_conflicts": self.hard_conflicts,
            "status": self.status,
            "created_at": self.created_at,
        }

    def reasons_json(self) -> str:
        """JSON serialized reasons for database storage."""
        return json.dumps(self.reasons, sort_keys=True)
