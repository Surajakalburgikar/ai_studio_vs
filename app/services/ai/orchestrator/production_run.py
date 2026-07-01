from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
from datetime import datetime
from .production_checkpoint import ProductionCheckpoint

@dataclass
class ProductionRun:
    run_id: str
    continuity_key: str
    project_id: int
    status: str = "active"  # 'active', 'paused', 'completed', 'failed'
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    checkpoint: Optional[ProductionCheckpoint] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.checkpoint:
            d["checkpoint"] = self.checkpoint.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductionRun":
        chk_data = data.get("checkpoint")
        checkpoint = ProductionCheckpoint.from_dict(chk_data) if chk_data else None
        return cls(
            run_id=data["run_id"],
            continuity_key=data["continuity_key"],
            project_id=data["project_id"],
            status=data.get("status", "active"),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            checkpoint=checkpoint,
            metadata=data.get("metadata", {})
        )
