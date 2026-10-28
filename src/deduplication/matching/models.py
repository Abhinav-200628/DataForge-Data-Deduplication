"""Data models for entity matching results and audit evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from deduplication.schemas.common import MatchDecision


@dataclass(frozen=True)
class MatchEvidence:
    """Detailed audit evidence explaining an entity resolution decision."""
    record_id_a: str
    record_id_b: str
    system_a: str
    system_b: str
    decision: MatchDecision
    overall_score: float
    rule_id: str
    reasons: list[str] = field(default_factory=list)
    hard_conflicts: list[str] = field(default_factory=list)
    attribute_scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert evidence to a serializable dictionary."""
        return {
            "record_id_a": self.record_id_a,
            "record_id_b": self.record_id_b,
            "system_a": self.system_a,
            "system_b": self.system_b,
            "decision": self.decision.value,
            "overall_score": round(self.overall_score, 4),
            "rule_id": self.rule_id,
            "reasons": self.reasons,
            "hard_conflicts": self.hard_conflicts,
            "attribute_scores": {k: round(v, 4) for k, v in self.attribute_scores.items()},
        }
