"""Container for quarantined/invalid records preserving full source identity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from typing import Any

from deduplication.schemas.common import EntityType, ValidationErrorDetail


@dataclass(frozen=True)
class QuarantineRecord:
    """Represents an invalid or malformed record isolated for auditing."""
    quarantine_id: str
    run_id: str
    entity_type: EntityType
    source_system: str
    source_record_id: str
    raw_payload: dict[str, Any]
    rejection_reasons: list[ValidationErrorDetail]
    quarantined_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert quarantine record to dictionary for logging and storage."""
        return {
            "quarantine_id": self.quarantine_id,
            "run_id": self.run_id,
            "entity_type": self.entity_type.value,
            "source_system": self.source_system,
            "source_record_id": self.source_record_id,
            "raw_payload": self.raw_payload,
            "rejection_reasons": [r.to_dict() for r in self.rejection_reasons],
            "quarantined_at": self.quarantined_at,
        }

    def raw_payload_json(self) -> str:
        """JSON-serialized raw payload for database storage."""
        return json.dumps(self.raw_payload, sort_keys=True)

    def rejection_reasons_json(self) -> str:
        """JSON-serialized rejection reasons for database storage."""
        return json.dumps([r.to_dict() for r in self.rejection_reasons], sort_keys=True)

