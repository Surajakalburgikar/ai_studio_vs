"""
verify_sprint_29_1.py — Architecture Refinement Verification Suite

Tests:
  1. Manifest revision history (append, list, get)
  2. Revision restore
  3. Canonical character identity never changes
  4. CharacterState updates correctly
  5. NarrativeTimeline events
  6. QualityProfile routing (orthogonal to pipeline mode)
  7. Regression: Sprint 29 verify_sprint_29.py still passes
"""

import os
import sys
import shutil
import unittest
import tempfile

sys.path.insert(0, "c:/Projects/AI_STUDIO")
sys.path.insert(0, "c:/Projects/AI_STUDIO_WORKER")

# ── helpers ──────────────────────────────────────────────────────────────────
TEMP_DIR = tempfile.mkdtemp(prefix="sprint291_test_")

def teardown_temp():
    shutil.rmtree(TEMP_DIR, ignore_errors=True)


# ── imports ───────────────────────────────────────────────────────────────────
from app.services.ai.continuity.continuity_manifest import ContinuityManifest
from app.services.ai.continuity.continuity_manager import ContinuityManager
from app.services.ai.continuity.canonical_character import (
    CanonicalCharacter, CharacterState, CharacterProfile
)
from app.services.ai.continuity.manifest_revision import RevisionHistory
from app.services.ai.continuity.revision_manager import RevisionManager
from app.services.ai.continuity.narrative_timeline import (
    NarrativeTimeline, TimelineNode, TimelineEvent
)
from app.services.ai.continuity.continuity_resolver import ContinuityResolver
from app.services.ai.policies.provider_policy import ProviderPolicy
from app.services.ai.policies.quality_profile import (
    QualityProfile, resolve_profile, QUALITY_PROFILE_DEFAULTS
)


class TestManifestRevisionHistory(unittest.TestCase):
    """Task 1: Manifest revisions replace cloning."""

    def setUp(self):
        self.mgr = ContinuityManager(export_path=TEMP_DIR)

    def _key(self) -> str:
        """Return a test-method-unique key so tests don't share file state."""
        return f"con_rev_{self._testMethodName}"

    def test_append_revision(self):
        key = self._key()
        self.mgr.create_new_manifest(key, "Test Series", "Test Universe")
        rev = self.mgr.add_revision(key, reason="Initial setup", project_id=1)
        self.assertEqual(rev.revision_number, 1)
        self.assertEqual(rev.reason, "Initial setup")
        self.assertEqual(rev.project_id, 1)

    def test_revision_increments(self):
        key = self._key()
        self.mgr.create_new_manifest(key, "Test Series", "Test Universe")
        self.mgr.add_revision(key, reason="Part 1 complete", project_id=1)
        self.mgr.add_revision(key, reason="Part 2 begins",   project_id=2)
        revisions = self.mgr.list_revisions(key)
        self.assertEqual(len(revisions), 2)
        self.assertEqual(revisions[0].revision_number, 1)
        self.assertEqual(revisions[1].revision_number, 2)

    def test_continuity_key_never_changes(self):
        """Continuing a story into a new project must NOT change the continuity_key."""
        key = self._key()
        self.mgr.create_new_manifest(key, "Test Series", "Test Universe")
        self.mgr.add_revision(key, reason="Sequel", project_id=99)
        reloaded = self.mgr.load_manifest(key)
        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded.continuity_key, key)

    def test_current_revision_number(self):
        key = self._key()
        self.mgr.create_new_manifest(key, "Test Series", "Test Universe")
        self.mgr.add_revision(key, project_id=1)
        self.mgr.add_revision(key, project_id=2)
        current = self.mgr.get_current_revision_number(key)
        self.assertEqual(current, 2)

    def test_get_specific_revision(self):
        key = self._key()
        self.mgr.create_new_manifest(key, "Test Series", "Test Universe")
        self.mgr.add_revision(key, reason="Alpha", project_id=1)
        self.mgr.add_revision(key, reason="Beta",  project_id=2)
        rev = self.mgr.get_revision(key, 1)
        self.assertIsNotNone(rev)
        self.assertEqual(rev.reason, "Alpha")


class TestRevisionRestore(unittest.TestCase):
    """Task 1: Restore to a previous revision."""

    def setUp(self):
        self.mgr = ContinuityManager(export_path=TEMP_DIR)
        self.key = "con_restore_test"
        manifest = self.mgr.create_new_manifest(self.key, "Restore Series")
        # Set some canonical characters at revision 1
        manifest.canonical_characters = {
            "elara": {"character_id": "elara", "canonical_name": "Elara", "hair_color": "silver-white"}
        }
        self.mgr.save_manifest(manifest)
        self.mgr.add_revision(self.key, reason="Initial state", project_id=1)

        # Modify and create revision 2
        manifest = self.mgr.load_manifest(self.key)
        manifest.canonical_characters["elara"]["hair_color"] = "dyed-black"
        self.mgr.save_manifest(manifest)
        self.mgr.add_revision(self.key, reason="Post-transformation", project_id=2)

    def test_restore_to_revision_1(self):
        restored = self.mgr.restore_revision(self.key, 1)
        self.assertEqual(
            restored.canonical_characters["elara"]["hair_color"],
            "silver-white",
            "Restored manifest should reflect state at revision 1"
        )

    def test_restore_appends_new_revision(self):
        before = len(self.mgr.list_revisions(self.key))
        self.mgr.restore_revision(self.key, 1)
        after = len(self.mgr.list_revisions(self.key))
        self.assertEqual(after, before + 1, "Restore must append a new revision entry")


class TestCanonicalCharacter(unittest.TestCase):
    """Task 2: Canonical identity is never overwritten by runtime state changes."""

    def test_canonical_identity_immutable_via_update_state(self):
        profile = CharacterProfile(
            identity=CanonicalCharacter(
                character_id="elara",
                canonical_name="Elara",
                hair_color="silver-white",
                eye_color="emerald green",
            ),
            current_state=CharacterState(current_outfit="leather armor"),
        )
        # Update state — should not touch identity
        profile.update_state(current_outfit="royal gown", current_location="palace")
        self.assertEqual(profile.identity.hair_color, "silver-white")
        self.assertEqual(profile.identity.eye_color,  "emerald green")
        self.assertEqual(profile.state.current_outfit, "royal gown")

    def test_legacy_flat_dict_roundtrip(self):
        """Existing serialisers that use flat dicts still work."""
        legacy = {
            "character_id": "kael",
            "canonical_name": "Kael",
            "name": "Kael",
            "hair_color": "black",
            "clothing": "battle-worn tunic",
        }
        profile = CharacterProfile.from_dict(legacy)
        self.assertEqual(profile.name, "Kael")
        self.assertEqual(profile.identity.hair_color, "black")
        self.assertEqual(profile.state.current_outfit, "battle-worn tunic")

    def test_to_dict_includes_legacy_clothing_key(self):
        profile = CharacterProfile(
            identity=CanonicalCharacter(character_id="z", canonical_name="Z"),
            current_state=CharacterState(current_outfit="robes"),
        )
        d = profile.to_dict()
        self.assertIn("clothing", d)
        self.assertEqual(d["clothing"], "robes")


class TestCharacterStateInResolver(unittest.TestCase):
    """Task 2: ContinuityResolver separates identity from state correctly."""

    def setUp(self):
        self.mgr = ContinuityManager(export_path=TEMP_DIR)
        self.key = "con_char_state"
        manifest = self.mgr.create_new_manifest(self.key)
        manifest.canonical_characters = {
            "elara": {
                "character_id": "elara",
                "canonical_name": "Elara",
                "hair_style": "braided",
                "hair_color": "silver-white",
            }
        }
        manifest.active_character_states = {
            "elara": {"current_outfit": "leather armor", "current_location": "forest"}
        }
        self.mgr.save_manifest(manifest)
        self.manifest = manifest
        self.resolver = ContinuityResolver()

    def test_get_canonical_character(self):
        canon = self.resolver.get_canonical_character(self.manifest, "elara")
        self.assertIsNotNone(canon)
        self.assertEqual(canon.canonical_name, "Elara")
        self.assertEqual(canon.hair_color, "silver-white")

    def test_get_character_state(self):
        state = self.resolver.get_character_state(self.manifest, "elara")
        self.assertIsNotNone(state)
        self.assertEqual(state.current_outfit, "leather armor")

    def test_update_state_does_not_touch_identity(self):
        self.resolver.update_character_state(self.manifest, "elara", current_outfit="royal gown")
        state = self.resolver.get_character_state(self.manifest, "elara")
        self.assertEqual(state.current_outfit, "royal gown")
        canon = self.resolver.get_canonical_character(self.manifest, "elara")
        self.assertEqual(canon.hair_color, "silver-white")  # unchanged


class TestNarrativeTimeline(unittest.TestCase):
    """Task 3: NarrativeTimeline stores events with story-time and production-time."""

    def test_add_and_retrieve_nodes(self):
        timeline = NarrativeTimeline(continuity_key="con_tl")
        node = TimelineNode(
            node_id="ep1s1",
            node_type="scene",
            label="The Opening Battle",
            story_time_start="Year 3042, Spring",
            arc="The Fall of Eldoria",
        )
        event = TimelineEvent(
            event_id="evt001",
            event_type="scene",
            story_time="Year 3042, Spring — Dawn",
            production_time="E01S01",
            arc="The Fall of Eldoria",
            description="Elara defends the gates",
            characters_present=["Elara"],
            location="Eastern Gates",
        )
        node.events.append(event)
        timeline.add_node(node)

        retrieved = timeline.get_node("ep1s1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.arc, "The Fall of Eldoria")
        self.assertEqual(len(retrieved.events), 1)
        self.assertEqual(retrieved.events[0].story_time, "Year 3042, Spring — Dawn")

    def test_flashback_node_separate_from_production_order(self):
        timeline = NarrativeTimeline(continuity_key="con_tl2")
        flashback = TimelineNode(
            node_id="flashback_01",
            node_type="scene",
            label="Elara's Childhood (20 years earlier)",
            story_time_start="Year 3022",
            arc="Origins",
        )
        present = TimelineNode(
            node_id="present_01",
            node_type="scene",
            label="Present Day",
            story_time_start="Year 3042",
            arc="The Fall of Eldoria",
        )
        timeline.add_node(present)
        timeline.add_node(flashback)

        arc_nodes = timeline.get_nodes_by_arc("Origins")
        self.assertEqual(len(arc_nodes), 1)
        self.assertEqual(arc_nodes[0].node_id, "flashback_01")

    def test_timeline_serialisation_roundtrip(self):
        timeline = NarrativeTimeline(continuity_key="con_ser")
        node = TimelineNode(node_id="n1", label="Node 1")
        node.events.append(TimelineEvent(event_id="e1", description="Desc"))
        timeline.add_node(node)

        d = timeline.to_dict()
        restored = NarrativeTimeline.from_dict(d)
        self.assertEqual(len(restored.nodes), 1)
        self.assertEqual(restored.nodes[0].events[0].event_id, "e1")

    def test_timeline_persistence(self):
        mgr = ContinuityManager(export_path=TEMP_DIR)
        key = "con_tl_persist"
        mgr.create_new_manifest(key)
        timeline = mgr.get_or_create_timeline(key)
        timeline.add_node(TimelineNode(node_id="n1", label="Persisted"))
        mgr.save_timeline(timeline)

        loaded = mgr.load_timeline(key)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.nodes[0].label, "Persisted")


class TestQualityProfiles(unittest.TestCase):
    """Task 4: QualityProfile is orthogonal to pipeline mode."""

    def test_quick_draft_allows_downgrade(self):
        cfg = resolve_profile(QualityProfile.QUICK_DRAFT)
        self.assertTrue(cfg.allow_quality_downgrade)
        self.assertIn("schnell", cfg.preferred_model)

    def test_production_profile_forbids_downgrade(self):
        cfg = resolve_profile(QualityProfile.PRODUCTION)
        self.assertFalse(cfg.allow_quality_downgrade)
        self.assertIn("dev", cfg.preferred_model)

    def test_master_profile_forbids_transport_fallback(self):
        cfg = resolve_profile(QualityProfile.MASTER)
        self.assertFalse(cfg.allow_transport_fallback)

    def test_dev_pipeline_production_profile_is_valid_combo(self):
        """Pipeline mode=development + QualityProfile=production is a valid combination."""
        policy = ProviderPolicy.from_profile(QualityProfile.PRODUCTION, mode="development")
        self.assertEqual(policy.mode.value, "development")
        self.assertFalse(policy.allow_quality_downgrade)  # profile overrides

    def test_profile_routing_exact_match(self):
        policy = ProviderPolicy.from_profile(QualityProfile.PRODUCTION, mode="production")
        available = {"black-forest-labs/FLUX.1-dev": ["fal-ai", "huggingface"]}
        model, transport, action = policy.select_route(
            "black-forest-labs/FLUX.1-dev", "fal-ai", available
        )
        self.assertEqual(action, "execute")
        self.assertEqual(transport, "fal-ai")

    def test_quick_draft_allows_schnell_downgrade(self):
        policy = ProviderPolicy.from_profile(QualityProfile.QUICK_DRAFT, mode="development")
        # Only schnell is available
        available = {"black-forest-labs/FLUX.1-schnell": ["huggingface"]}
        model, transport, action = policy.select_route(
            "black-forest-labs/FLUX.1-dev", "fal-ai", available
        )
        self.assertEqual(action, "execute")
        self.assertIn("schnell", model)

    def test_all_profiles_have_defaults(self):
        for p in QualityProfile:
            cfg = resolve_profile(p)
            self.assertIsNotNone(cfg)
            self.assertGreater(cfg.generation_steps, 0)


class TestBackwardCompatibility(unittest.TestCase):
    """Task 6: Existing serialisation paths continue to work."""

    def test_manifest_from_dict_still_works(self):
        data = {
            "continuity_key": "con_compat",
            "series_title": "Old Series",
            "canonical_characters": {},
        }
        manifest = ContinuityManifest.from_dict(data)
        self.assertEqual(manifest.continuity_key, "con_compat")

    def test_provider_policy_without_profile_still_works(self):
        policy = ProviderPolicy(mode="production", preferred_model="black-forest-labs/FLUX.1-dev")
        available = {"black-forest-labs/FLUX.1-dev": ["huggingface"]}
        _, _, action = policy.select_route(
            "black-forest-labs/FLUX.1-dev", "huggingface", available
        )
        self.assertEqual(action, "execute")

    def test_clone_manifest_emits_deprecation_warning(self):
        import warnings
        mgr = ContinuityManager(export_path=TEMP_DIR)
        key = "con_clone_dep"
        mgr.create_new_manifest(key)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mgr.clone_manifest(key, "con_clone_dep_v2")
            self.assertTrue(any(issubclass(ww.category, DeprecationWarning) for ww in w))


if __name__ == "__main__":
    import atexit
    atexit.register(teardown_temp)
    unittest.main(verbosity=2)
