import os
import json
from typing import Dict, Any, Optional, List
from app.core.config import settings
from .production_run import ProductionRun
from .production_checkpoint import ProductionCheckpoint

class ProductionStateManager:
    """Manages persistence and states for ProductionRuns and ProductionCheckpoints."""

    def __init__(self, export_path: Optional[str] = None) -> None:
        self.export_path = export_path or settings.CONTINUITY_EXPORT_PATH
        self.runs_path = os.path.join(self.export_path, "runs")
        self.checkpoints_path = os.path.join(self.export_path, "checkpoints")
        os.makedirs(self.runs_path, exist_ok=True)
        os.makedirs(self.checkpoints_path, exist_ok=True)

    def save_run(self, run: ProductionRun) -> None:
        file_path = os.path.join(self.runs_path, f"{run.run_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(run.to_dict(), f, indent=2, ensure_ascii=False)
        
        mapping_path = os.path.join(self.runs_path, f"mapping_{run.continuity_key}.json")
        with open(mapping_path, "w", encoding="utf-8") as f:
            json.dump({"run_id": run.run_id}, f)

    def load_run(self, run_id: str) -> Optional[ProductionRun]:
        file_path = os.path.join(self.runs_path, f"{run_id}.json")
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ProductionRun.from_dict(data)
        except Exception:
            return None

    def load_run_by_continuity_key(self, continuity_key: str) -> Optional[ProductionRun]:
        mapping_path = os.path.join(self.runs_path, f"mapping_{continuity_key}.json")
        if not os.path.exists(mapping_path):
            return None
        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping = json.load(f)
            return self.load_run(mapping["run_id"])
        except Exception:
            return None

    def save_checkpoint(self, checkpoint: ProductionCheckpoint) -> None:
        file_path = os.path.join(self.checkpoints_path, f"{checkpoint.continuity_key}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, indent=2, ensure_ascii=False)

    def load_checkpoint(self, continuity_key: str) -> Optional[ProductionCheckpoint]:
        file_path = os.path.join(self.checkpoints_path, f"{continuity_key}.json")
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ProductionCheckpoint.from_dict(data)
        except Exception:
            return None

    def list_runs(self) -> List[ProductionRun]:
        runs = []
        for filename in os.listdir(self.runs_path):
            if filename.endswith(".json") and not filename.startswith("mapping_"):
                run_id = filename[:-5]
                run = self.load_run(run_id)
                if run:
                    runs.append(run)
        return runs
