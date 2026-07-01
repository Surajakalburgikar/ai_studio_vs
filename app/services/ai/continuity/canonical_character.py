from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CanonicalCharacter:
    """The permanent, immutable identity of a character across the entire story universe.

    These values describe WHO the character is — species, appearance, core features.
    They should rarely (if ever) change. Never overwrite from runtime story state.
    """
    character_id: str
    canonical_name: str
    species: str = "human"
    gender: str = ""
    face_description: str = ""
    hair_style: str = ""
    hair_color: str = ""
    eye_color: str = ""
    skin_tone: str = ""
    body_type: str = ""
    age_group: str = ""
    reference_prompt: str = ""
    negative_prompt: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CanonicalCharacter":
        return cls(
            character_id=data.get("character_id", data.get("name", "")),
            canonical_name=data.get("canonical_name", data.get("name", "")),
            species=data.get("species", "human"),
            gender=data.get("gender", ""),
            face_description=data.get("face_description", ""),
            hair_style=data.get("hair_style", ""),
            hair_color=data.get("hair_color", ""),
            eye_color=data.get("eye_color", ""),
            skin_tone=data.get("skin_tone", ""),
            body_type=data.get("body_type", ""),
            age_group=data.get("age_group", ""),
            reference_prompt=data.get("reference_prompt", ""),
            negative_prompt=data.get("negative_prompt", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CharacterState:
    """The mutable runtime state of a character at a specific point in the story.

    Each update creates a new version. Old versions are never overwritten.
    They change freely throughout the narrative without affecting canonical identity.
    """
    # ── story state fields ──────────────────────────────────────────────────
    current_outfit: str = ""
    current_weapon: str = ""
    current_expression: str = "neutral"
    current_pose: str = ""
    injuries: List[str] = field(default_factory=list)
    accessories: List[str] = field(default_factory=list)
    magic_level: str = ""
    temporary_effects: List[str] = field(default_factory=list)
    relationship_status: Dict[str, str] = field(default_factory=dict)
    current_location: str = ""

    # ── version tracking fields (Sprint 29.1 Final) ─────────────────────────
    state_version: int = 1
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    previous_state_version: Optional[int] = None
    state_reason: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CharacterState":
        return cls(
            current_outfit=data.get("current_outfit", data.get("clothing", "")),
            current_weapon=data.get("current_weapon", ""),
            current_expression=data.get("current_expression", "neutral"),
            current_pose=data.get("current_pose", ""),
            injuries=data.get("injuries", []),
            accessories=data.get("accessories", []),
            magic_level=data.get("magic_level", ""),
            temporary_effects=data.get("temporary_effects", []),
            relationship_status=data.get("relationship_status", {}),
            current_location=data.get("current_location", ""),
            state_version=data.get("state_version", 1),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
            previous_state_version=data.get("previous_state_version"),
            state_reason=data.get("state_reason"),
            metadata=data.get("metadata", {}),
        )

    def bump_version(self, reason: Optional[str] = None) -> "CharacterState":
        """Return a NEW CharacterState with version incremented. Old state is unchanged."""
        import copy
        new_state = copy.deepcopy(self)
        new_state.previous_state_version = self.state_version
        new_state.state_version = self.state_version + 1
        new_state.updated_at = _now_iso()
        new_state.state_reason = reason
        return new_state


@dataclass
class CharacterProfile:
    """Backward-compatible combined profile = CanonicalCharacter + versioned CharacterState.

    identity      → permanent (CanonicalCharacter)
    current_state → latest version (CharacterState)
    state_history → all previous versions, oldest first
    """
    identity: CanonicalCharacter
    current_state: CharacterState = field(default_factory=CharacterState)
    state_history: List[CharacterState] = field(default_factory=list)

    # ── backward-compat shim: `profile.state` still works ────────────────────
    @property
    def state(self) -> CharacterState:
        return self.current_state

    @property
    def name(self) -> str:
        return self.identity.canonical_name

    @property
    def character_id(self) -> str:
        return self.identity.character_id

    def to_dict(self) -> Dict[str, Any]:
        d = self.identity.to_dict()
        d["state"] = self.current_state.to_dict()
        d["current_state"] = self.current_state.to_dict()
        d["state_history"] = [s.to_dict() for s in self.state_history]
        # Flatten legacy key
        d["clothing"] = self.current_state.current_outfit
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CharacterProfile":
        identity = CanonicalCharacter.from_dict(data)

        # Prefer explicit current_state, then legacy state, then flat format
        state_data = data.get("current_state") or data.get("state") or {}
        if not state_data:
            state_data = {
                "current_outfit": data.get("clothing", data.get("current_outfit", "")),
                "current_weapon": data.get("current_weapon", ""),
                "current_expression": data.get("current_expression", "neutral"),
                "current_location": data.get("current_location", ""),
            }
        current_state = CharacterState.from_dict(state_data)
        history = [CharacterState.from_dict(s) for s in data.get("state_history", [])]
        return cls(identity=identity, current_state=current_state, state_history=history)

    def update_state(self, reason: Optional[str] = None, **kwargs) -> None:
        """Create a new state version, push old state to history. Canonical identity untouched."""
        new_state = self.current_state.bump_version(reason=reason)
        for k, v in kwargs.items():
            if hasattr(new_state, k):
                setattr(new_state, k, v)
        self.state_history.append(self.current_state)
        self.current_state = new_state

    def get_state_version(self, version: int) -> Optional[CharacterState]:
        """Retrieve a historical state by version number."""
        if self.current_state.state_version == version:
            return self.current_state
        for s in self.state_history:
            if s.state_version == version:
                return s
        return None

    def restore_state_version(self, version: int, reason: Optional[str] = None) -> bool:
        """Restore a historical state version as the new current_state.

        The restored state gets a new version number; history is never erased.
        Returns True if found and restored, False otherwise.
        """
        target = self.get_state_version(version)
        if target is None:
            return False
        import copy
        restored = copy.deepcopy(target)
        restored.previous_state_version = self.current_state.state_version
        restored.state_version = self.current_state.state_version + 1
        restored.updated_at = _now_iso()
        restored.state_reason = reason or f"Restored from version {version}"
        self.state_history.append(self.current_state)
        self.current_state = restored
        return True
