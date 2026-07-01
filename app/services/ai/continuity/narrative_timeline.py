from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional


@dataclass
class TimelineEvent:
    """A single narrative event placed both in story-time and production-time.

    Keeps chronological order separate from production order, supporting
    flashbacks, time-skips, parallel timelines, and dream sequences.

    Sprint 29.1 Final: extended with continuity_revision and character_state_versions
    so every event knows exactly which universe state and character versions were active
    when it was recorded.
    """
    event_id: str
    event_type: str = "scene"          # scene, flashback, dream, timeskip, parallel
    story_time: str = ""               # Narrative timestamp, e.g. "Year 3042, Spring"
    production_time: str = ""          # Production sequence ref, e.g. "E01S03"
    arc: str = ""                      # Story arc label
    chapter: str = ""
    description: str = ""
    characters_present: List[str] = field(default_factory=list)
    location: str = ""

    # ── revision linkage (Sprint 29.1 Final) ──────────────────────────────
    continuity_revision: Optional[int] = None
    """The manifest revision number that was active when this event was created.
    Enables timeline restoration and continuity rollback without ambiguity."""

    character_state_versions: Dict[str, int] = field(default_factory=dict)
    """Maps character_name → state_version for every character present in this event.
    Allows precise replay: which costume/equipment/expression each character had."""

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimelineEvent":
        return cls(
            event_id=data["event_id"],
            event_type=data.get("event_type", "scene"),
            story_time=data.get("story_time", ""),
            production_time=data.get("production_time", ""),
            arc=data.get("arc", ""),
            chapter=data.get("chapter", ""),
            description=data.get("description", ""),
            characters_present=data.get("characters_present", []),
            location=data.get("location", ""),
            continuity_revision=data.get("continuity_revision"),
            character_state_versions=data.get("character_state_versions", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TimelineNode:
    """A logical grouping of timeline events — e.g. a single scene or story branch."""
    node_id: str
    node_type: str = "scene"          # scene, arc, episode, branch
    label: str = ""
    story_time_start: str = ""
    story_time_end: str = ""
    arc: str = ""
    events: List[TimelineEvent] = field(default_factory=list)
    parent_node_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["events"] = [e.to_dict() for e in self.events]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimelineNode":
        events = [TimelineEvent.from_dict(e) for e in data.get("events", [])]
        return cls(
            node_id=data["node_id"],
            node_type=data.get("node_type", "scene"),
            label=data.get("label", ""),
            story_time_start=data.get("story_time_start", ""),
            story_time_end=data.get("story_time_end", ""),
            arc=data.get("arc", ""),
            events=events,
            parent_node_id=data.get("parent_node_id"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class NarrativeTimeline:
    """The full chronological model of a story universe.

    Separates *story time* (narrative chronology) from *production time* (scene/shot order),
    enabling flashbacks, time-skips, parallel timelines, and future arcs without disrupting
    the production schedule.
    """
    continuity_key: str
    nodes: List[TimelineNode] = field(default_factory=list)
    arcs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: TimelineNode) -> None:
        self.nodes.append(node)

    def get_node(self, node_id: str) -> Optional[TimelineNode]:
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def get_nodes_by_arc(self, arc: str) -> List[TimelineNode]:
        return [n for n in self.nodes if n.arc == arc]

    def get_events_by_revision(self, revision: int) -> List[TimelineEvent]:
        """Return all events that were linked to a specific continuity revision."""
        result = []
        for node in self.nodes:
            for evt in node.events:
                if evt.continuity_revision == revision:
                    result.append(evt)
        return result

    def get_events_by_character_state(self, character_name: str, state_version: int) -> List[TimelineEvent]:
        """Return all events where a character was at a specific state version."""
        result = []
        for node in self.nodes:
            for evt in node.events:
                if evt.character_state_versions.get(character_name) == state_version:
                    result.append(evt)
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "continuity_key": self.continuity_key,
            "nodes": [n.to_dict() for n in self.nodes],
            "arcs": self.arcs,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NarrativeTimeline":
        nodes = [TimelineNode.from_dict(n) for n in data.get("nodes", [])]
        return cls(
            continuity_key=data["continuity_key"],
            nodes=nodes,
            arcs=data.get("arcs", []),
            metadata=data.get("metadata", {}),
        )
