"""
Pipeline Stage Abstract Base Class.
"""

from abc import ABC, abstractmethod
from app.services.ai.pipeline_context import PipelineContext


class PipelineStage(ABC):
    """Abstract base class representing a single processing stage in the project pipeline."""

    @abstractmethod
    def run(self, context: PipelineContext) -> PipelineContext:
        """Run the logic of this pipeline stage.

        Args:
            context: The shared PipelineContext object.

        Returns:
            The updated PipelineContext object.
        """
        pass
