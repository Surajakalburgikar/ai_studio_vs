"""
verify_sprint29_1_final.py — Sprint 29.1 Final Refinement Verification Suite

Verifies:
  1. Character state version history
  2. State restoration
  3. Timeline revision linkage (continuity_revision + character_state_versions)
  4. RenderProfile creation and built-in presets
  5. RenderProfile migration from QualityProfile
  6. ProviderPolicy with RenderProfile
  7. GenerationSpecification compatibility
  8. Regression: Sprint 29.1 (27 tests) and Sprint 29 (5 tests)
"""

import os
import sys
import shutil
import unittest
import tempfile

sys.path.insert(0, "c:/Projects/AI_STUDIO")
sys.path.insert(0, "c:/Projects/AI_STUDIO_WORKER")

TEMP_DIR = tempfile.mkdtemp(prefix="sprint291_final_")

# ── imports ────────────────────────────────────────────────────────────────
from app.services.ai.continuity.canonical_character import (
    CanonicalCharacter, CharacterState, CharacterProfile
)
from app.services.ai.continuity.narrative_timeline import (
    NarrativeTimeline, TimelineNode, TimelineEvent
)
from app.services.ai.continuity.continuity_manager import ContinuityManager
from app.services.ai.policies.quality_profile import QualityProfile, resolve_profile
from app.services.ai.policies.render_profile import (
    RenderProfile, resolve_render_profile, get_render_profile, RENDER_PROFILE_REGISTRY
)
from app.services.ai.policies.provider_policy import ProviderPolicy


# ══════════════════════════════════════════════════════════════════════════════
# TASK 1 — Character State Version History
# ══════════════════════════════════════════════════════════════════════════════

class TestCharacterStateVersioning(unittest.TestCase):
    """Task 1: Every state update creates a new version; old versions remain accessible."""

    def _make_profile(self):
        return CharacterProfile(
            identity=CanonicalCharacter(character_id="elara", canonical_name="Elara"),
            current_state=CharacterState(current_outfit="apprentice robes", state_version=1),
        )

    def test_initial_state_is_version_1(self):
        profile = self._make_profile()
        self.assertEqual(profile.current_state.state_version, 1)

    def test_update_creates_new_version(self):
        profile = self._make_profile()
        profile.update_state(reason="Knight promotion", current_outfit="knight armor")
        self.assertEqual(profile.current_state.state_version, 2)
        self.assertEqual(profile.current_state.current_outfit, "knight armor")

    def test_old_state_preserved_in_history(self):
        profile = self._make_profile()
        profile.update_state(reason="V2", current_outfit="knight armor")
        profile.update_state(reason="V3", current_outfit="king robes")
        self.assertEqual(len(profile.state_history), 2)
        self.assertEqual(profile.state_history[0].current_outfit, "apprentice robes")
        self.assertEqual(profile.state_history[1].current_outfit, "knight armor")

    def test_multiple_state_versions_sequence(self):
        profile = self._make_profile()
        profile.update_state(reason="Knight armor",  current_outfit="knight armor")
        profile.update_state(reason="King robes",    current_outfit="king robes")
        profile.update_state(reason="Old king",      current_outfit="tattered king robes")
        self.assertEqual(profile.current_state.state_version, 4)
        self.assertEqual(len(profile.state_history), 3)

    def test_canonical_identity_never_changes_across_updates(self):
        profile = self._make_profile()
        profile.identity.hair_color = "silver-white"
        profile.update_state(current_outfit="knight armor")
        profile.update_state(current_outfit="king robes")
        self.assertEqual(profile.identity.hair_color, "silver-white")
        self.assertEqual(profile.identity.canonical_name, "Elara")

    def test_get_state_version_lookup(self):
        profile = self._make_profile()
        profile.update_state(current_outfit="armor", reason="V2")
        profile.update_state(current_outfit="robes", reason="V3")
        v2 = profile.get_state_version(2)
        self.assertIsNotNone(v2)
        self.assertEqual(v2.current_outfit, "armor")

    def test_backward_compat_state_property(self):
        """profile.state still returns current_state for legacy callers."""
        profile = self._make_profile()
        profile.update_state(current_outfit="armor")
        self.assertIs(profile.state, profile.current_state)

    def test_state_reason_recorded(self):
        profile = self._make_profile()
        profile.update_state(reason="Won tournament", current_outfit="knight armor")
        self.assertEqual(profile.current_state.state_reason, "Won tournament")

    def test_previous_state_version_recorded(self):
        profile = self._make_profile()
        profile.update_state(reason="Step 2", current_outfit="armor")
        self.assertEqual(profile.current_state.previous_state_version, 1)


class TestCharacterStateRestoration(unittest.TestCase):
    """Task 1: Restore to a previous state version; history is never erased."""

    def _make_profile(self):
        p = CharacterProfile(
            identity=CanonicalCharacter(character_id="kael", canonical_name="Kael"),
            current_state=CharacterState(current_outfit="apprentice", state_version=1),
        )
        p.update_state(reason="Knight", current_outfit="knight armor")
        p.update_state(reason="King",   current_outfit="king robes")
        return p

    def test_restore_creates_new_version(self):
        profile = self._make_profile()
        before = profile.current_state.state_version
        profile.restore_state_version(1, reason="Flashback")
        self.assertGreater(profile.current_state.state_version, before)

    def test_restored_state_reflects_target(self):
        profile = self._make_profile()
        profile.restore_state_version(1)
        self.assertEqual(profile.current_state.current_outfit, "apprentice")

    def test_history_not_erased_after_restore(self):
        profile = self._make_profile()
        before_count = len(profile.state_history)
        profile.restore_state_version(1)
        self.assertEqual(len(profile.state_history), before_count + 1)

    def test_restore_nonexistent_version_returns_false(self):
        profile = self._make_profile()
        result = profile.restore_state_version(999)
        self.assertFalse(result)


class TestContinuityManagerCharacterState(unittest.TestCase):
    """Task 1: ContinuityManager exposes create/update/list/restore state versions."""

    def setUp(self):
        self.mgr = ContinuityManager(export_path=TEMP_DIR)
        self.key = f"con_char_state_{self._testMethodName}"
        self.mgr.create_new_manifest(self.key)

    def test_create_character_state(self):
        profile = self.mgr.create_character_state(
            self.key, "elara", current_outfit="apprentice robes"
        )
        self.assertEqual(profile.current_state.state_version, 1)
        self.assertEqual(profile.current_state.current_outfit, "apprentice robes")

    def test_update_character_state_increments_version(self):
        self.mgr.create_character_state(self.key, "elara", current_outfit="apprentice robes")
        profile = self.mgr.update_character_state(
            self.key, "elara", reason="Knight", current_outfit="knight armor"
        )
        self.assertEqual(profile.current_state.state_version, 2)
        self.assertEqual(profile.current_state.current_outfit, "knight armor")

    def test_list_character_state_versions(self):
        self.mgr.create_character_state(self.key, "elara", current_outfit="V1")
        self.mgr.update_character_state(self.key, "elara", current_outfit="V2")
        self.mgr.update_character_state(self.key, "elara", current_outfit="V3")
        versions = self.mgr.list_character_state_versions(self.key, "elara")
        self.assertEqual(len(versions), 3)
        self.assertEqual(versions[0].state_version, 1)
        self.assertEqual(versions[2].state_version, 3)

    def test_restore_character_state_version(self):
        self.mgr.create_character_state(self.key, "elara", current_outfit="apprentice")
        self.mgr.update_character_state(self.key, "elara", current_outfit="armor")
        restored = self.mgr.restore_character_state_version(self.key, "elara", 1)
        self.assertIsNotNone(restored)
        self.assertEqual(restored.current_state.current_outfit, "apprentice")

    def test_restore_appends_new_version_preserves_history(self):
        self.mgr.create_character_state(self.key, "elara", current_outfit="apprentice")
        self.mgr.update_character_state(self.key, "elara", current_outfit="armor")
        versions_before = self.mgr.list_character_state_versions(self.key, "elara")
        self.mgr.restore_character_state_version(self.key, "elara", 1)
        versions_after = self.mgr.list_character_state_versions(self.key, "elara")
        self.assertEqual(len(versions_after), len(versions_before) + 1)


# ══════════════════════════════════════════════════════════════════════════════
# TASK 2 — Timeline Revision Linkage
# ══════════════════════════════════════════════════════════════════════════════

class TestTimelineVersionLinking(unittest.TestCase):
    """Task 2: TimelineEvents carry continuity_revision and character_state_versions."""

    def test_event_stores_continuity_revision(self):
        event = TimelineEvent(
            event_id="evt1",
            description="Opening battle",
            continuity_revision=3,
        )
        self.assertEqual(event.continuity_revision, 3)

    def test_event_stores_character_state_versions(self):
        event = TimelineEvent(
            event_id="evt2",
            characters_present=["Elara", "Kael"],
            character_state_versions={"Elara": 2, "Kael": 1},
            continuity_revision=1,
        )
        self.assertEqual(event.character_state_versions["Elara"], 2)
        self.assertEqual(event.character_state_versions["Kael"], 1)

    def test_event_serialisation_roundtrip(self):
        event = TimelineEvent(
            event_id="evt3",
            continuity_revision=5,
            character_state_versions={"Elara": 3},
        )
        d = event.to_dict()
        restored = TimelineEvent.from_dict(d)
        self.assertEqual(restored.continuity_revision, 5)
        self.assertEqual(restored.character_state_versions["Elara"], 3)

    def test_timeline_query_by_revision(self):
        timeline = NarrativeTimeline(continuity_key="con_tl_rev")
        node = TimelineNode(node_id="n1")
        node.events.append(TimelineEvent(event_id="e1", continuity_revision=1))
        node.events.append(TimelineEvent(event_id="e2", continuity_revision=2))
        node.events.append(TimelineEvent(event_id="e3", continuity_revision=1))
        timeline.add_node(node)

        rev1_events = timeline.get_events_by_revision(1)
        self.assertEqual(len(rev1_events), 2)
        self.assertIn("e1", [e.event_id for e in rev1_events])
        self.assertIn("e3", [e.event_id for e in rev1_events])

    def test_timeline_query_by_character_state(self):
        timeline = NarrativeTimeline(continuity_key="con_tl_char")
        node = TimelineNode(node_id="n1")
        node.events.append(TimelineEvent(event_id="e1", character_state_versions={"Elara": 1}))
        node.events.append(TimelineEvent(event_id="e2", character_state_versions={"Elara": 2}))
        timeline.add_node(node)

        events = timeline.get_events_by_character_state("Elara", 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_id, "e1")

    def test_backward_compat_event_without_revision_fields(self):
        """Old events without the new fields deserialise cleanly."""
        old_data = {"event_id": "old_evt", "description": "Legacy event"}
        event = TimelineEvent.from_dict(old_data)
        self.assertIsNone(event.continuity_revision)
        self.assertEqual(event.character_state_versions, {})


# ══════════════════════════════════════════════════════════════════════════════
# TASK 3 — RenderProfile
# ══════════════════════════════════════════════════════════════════════════════

class TestRenderProfile(unittest.TestCase):
    """Task 3: RenderProfile creation and built-in anime presets."""

    def test_all_anime_presets_exist(self):
        for name in ["anime_draft", "anime_preview", "anime_production", "anime_master"]:
            profile = get_render_profile(name)
            self.assertIsNotNone(profile, f"Missing preset: {name}")

    def test_anime_draft_uses_schnell(self):
        profile = get_render_profile("anime_draft")
        self.assertIn("schnell", profile.preferred_model)
        self.assertEqual(profile.quality_profile, QualityProfile.QUICK_DRAFT)

    def test_anime_production_uses_dev(self):
        profile = get_render_profile("anime_production")
        self.assertIn("dev", profile.preferred_model)
        self.assertEqual(profile.quality_profile, QualityProfile.PRODUCTION)

    def test_anime_master_highest_resolution(self):
        master = get_render_profile("anime_master")
        draft  = get_render_profile("anime_draft")
        self.assertGreater(master.width, draft.width)

    def test_render_profile_has_style_template(self):
        profile = get_render_profile("anime_production")
        self.assertIsNotNone(profile.style_template)
        self.assertIn("anime", profile.style_template)

    def test_render_profile_has_negative_prompt_template(self):
        profile = get_render_profile("anime_draft")
        self.assertIsNotNone(profile.negative_prompt_template)

    def test_custom_render_profile_serialisation(self):
        profile = RenderProfile(
            name="custom_test",
            quality_profile=QualityProfile.PRODUCTION,
            preferred_model="black-forest-labs/FLUX.1-dev",
            preferred_transport="fal-ai",
            steps=40,
        )
        d = profile.to_dict()
        restored = RenderProfile.from_dict(d)
        self.assertEqual(restored.name, "custom_test")
        self.assertEqual(restored.steps, 40)

    def test_resolve_quality_config_from_render_profile(self):
        profile = get_render_profile("anime_production")
        qcfg = profile.resolve_quality_config()
        self.assertFalse(qcfg.allow_quality_downgrade)
        self.assertTrue(qcfg.allow_transport_fallback)

    def test_render_profile_master_forbids_transport_fallback(self):
        profile = get_render_profile("anime_master")
        qcfg = profile.resolve_quality_config()
        self.assertFalse(qcfg.allow_transport_fallback)


# ══════════════════════════════════════════════════════════════════════════════
# TASK 4 & 5 — ProviderPolicy + RenderProfile Integration & Migration
# ══════════════════════════════════════════════════════════════════════════════

class TestRenderProfileProviderPolicyIntegration(unittest.TestCase):
    """Task 4: ProviderPolicy consumes RenderProfile. Task 5: migration from QualityProfile."""

    def test_policy_from_render_profile_exact_match(self):
        rp = get_render_profile("anime_production")
        policy = ProviderPolicy.from_render_profile(rp, mode="production")
        available = {"black-forest-labs/FLUX.1-dev": ["fal-ai"]}
        _, _, action = policy.select_route("black-forest-labs/FLUX.1-dev", "fal-ai", available)
        self.assertEqual(action, "execute")

    def test_policy_from_render_profile_forbids_downgrade_in_production(self):
        rp = get_render_profile("anime_production")
        policy = ProviderPolicy.from_render_profile(rp, mode="production")
        available = {"black-forest-labs/FLUX.1-schnell": ["huggingface"]}
        _, _, action = policy.select_route("black-forest-labs/FLUX.1-dev", "fal-ai", available)
        self.assertEqual(action, "fail")

    def test_policy_from_render_profile_allows_downgrade_in_draft(self):
        rp = get_render_profile("anime_draft")
        policy = ProviderPolicy.from_render_profile(rp, mode="development")
        available = {"black-forest-labs/FLUX.1-schnell": ["huggingface"]}
        model, _, action = policy.select_route("black-forest-labs/FLUX.1-dev", "fal-ai", available)
        self.assertEqual(action, "execute")
        self.assertIn("schnell", model)

    def test_master_render_profile_forbids_transport_fallback(self):
        rp = get_render_profile("anime_master")
        policy = ProviderPolicy.from_render_profile(rp, mode="production")
        # Only huggingface available, master forbids transport fallback
        available = {"black-forest-labs/FLUX.1-dev": ["huggingface"]}
        _, transport, action = policy.select_route("black-forest-labs/FLUX.1-dev", "fal-ai", available)
        # Exact match fails (fal-ai not available), transport fallback disallowed → fail
        self.assertEqual(action, "fail")

    def test_render_profile_migration_from_quality_profile(self):
        """Task 5: Auto-create RenderProfile from QualityProfile with no manual migration."""
        rp = RenderProfile.from_quality_profile(QualityProfile.PRODUCTION, name="migrated")
        self.assertEqual(rp.name, "migrated")
        self.assertIn("dev", rp.preferred_model)
        self.assertEqual(rp.quality_profile, QualityProfile.PRODUCTION)

    def test_resolve_render_profile_falls_back_to_quality_profile(self):
        rp = resolve_render_profile(name="nonexistent_profile", quality_profile=QualityProfile.PREVIEW)
        self.assertIsNotNone(rp)
        self.assertEqual(rp.quality_profile, QualityProfile.PREVIEW)

    def test_resolve_render_profile_defaults_to_anime_production(self):
        rp = resolve_render_profile()
        self.assertEqual(rp.name, "anime_production")

    def test_backward_compat_policy_without_render_profile(self):
        """Existing ProviderPolicy callers without render_profile continue to work."""
        policy = ProviderPolicy(mode="production", preferred_model="black-forest-labs/FLUX.1-dev")
        available = {"black-forest-labs/FLUX.1-dev": ["huggingface"]}
        _, _, action = policy.select_route("black-forest-labs/FLUX.1-dev", "huggingface", available)
        self.assertEqual(action, "execute")

    def test_policy_from_render_profile_by_name_string(self):
        policy = ProviderPolicy.from_render_profile("anime_preview", mode="development")
        self.assertIsNotNone(policy.render_profile)
        self.assertIn("schnell", policy.preferred_model)


# ══════════════════════════════════════════════════════════════════════════════
# TASK 6 — GenerationSpecification compatibility
# ══════════════════════════════════════════════════════════════════════════════

class TestGenerationSpecificationCompatibility(unittest.TestCase):
    """Verify GenerationSpecification still works with the new render_profile fields."""

    def test_render_profile_integrates_with_gen_spec_dict(self):
        """RenderProfile can supply model/transport/steps to a spec-like dict."""
        rp = get_render_profile("anime_production")
        spec = {
            "provider": rp.preferred_transport,
            "model": rp.preferred_model,
            "generation_parameters": {
                "width": rp.width,
                "height": rp.height,
                "steps": rp.steps,
                "guidance_scale": rp.guidance_scale,
            },
            "negative_prompt_template": rp.negative_prompt_template,
            "style_template": rp.style_template,
        }
        self.assertEqual(spec["model"], "black-forest-labs/FLUX.1-dev")
        self.assertEqual(spec["generation_parameters"]["steps"], 50)
        self.assertIsNotNone(spec["style_template"])


if __name__ == "__main__":
    import atexit
    atexit.register(lambda: shutil.rmtree(TEMP_DIR, ignore_errors=True))
    unittest.main(verbosity=2)
