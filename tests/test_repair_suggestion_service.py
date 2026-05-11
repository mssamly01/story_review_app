import unittest

from app.services.quality.readiness import ProductionReadinessService
from app.services.quality.repair import RepairSuggestionService
from tests.test_production_readiness_service import build_ready_project


class RepairSuggestionServiceTests(unittest.TestCase):
    def test_suggest_repairs_does_not_modify_project(self) -> None:
        project, beat = build_ready_project()
        beat.review_text = ""
        beat.image_prompt = ""
        before = project.to_dict()

        RepairSuggestionService().suggest_repairs_for_episode(project, "ep_001")

        self.assertEqual(project.to_dict(), before)

    def test_missing_review_text_suggests_rewrite_action(self) -> None:
        project, beat = build_ready_project()
        beat.review_text = ""

        actions = RepairSuggestionService().suggest_repairs_for_episode(project, "ep_001")

        self.assertIn("rewrite_review_text", action_types(actions))

    def test_missing_image_prompt_suggests_rebuild_prompt_action(self) -> None:
        project, beat = build_ready_project()
        beat.image_prompt = ""

        actions = RepairSuggestionService().suggest_repairs_for_episode(project, "ep_001")

        self.assertIn("rebuild_image_prompt", action_types(actions))

    def test_missing_negative_prompt_suggests_negative_prompt_fix(self) -> None:
        project, beat = build_ready_project()
        beat.negative_prompt = ""

        actions = RepairSuggestionService().suggest_repairs_for_episode(project, "ep_001")

        self.assertIn("add_negative_prompt", action_types(actions))

    def test_missing_character_visual_base_suggests_bible_update(self) -> None:
        project, _beat = build_ready_project()
        project.characters[0].visual_prompt_base = ""

        actions = RepairSuggestionService().suggest_repairs_for_episode(project, "ep_001")
        action = first_action(actions, "update_character_bible")

        self.assertTrue(action.requires_user_review)
        self.assertEqual(action.risk_level, "medium")

    def test_missing_location_visual_base_suggests_bible_update(self) -> None:
        project, _beat = build_ready_project()
        project.locations[0].visual_prompt_base = ""

        actions = RepairSuggestionService().suggest_repairs_for_episode(project, "ep_001")
        action = first_action(actions, "update_location_bible")

        self.assertTrue(action.requires_user_review)
        self.assertEqual(action.risk_level, "medium")

    def test_missing_style_suggests_create_default_style_presets(self) -> None:
        project, _beat = build_ready_project()
        project.style_presets.clear()

        actions = RepairSuggestionService().suggest_repairs_for_episode(project, "ep_001")

        self.assertIn("create_default_style_presets", action_types(actions))

    def test_scene_without_beats_suggests_generate_missing_beats(self) -> None:
        project, _beat = build_ready_project()
        project.review_episodes[0].scenes[0].beats.clear()

        actions = RepairSuggestionService().suggest_repairs_for_episode(project, "ep_001")
        action = first_action(actions, "generate_missing_beats")

        self.assertEqual(action.risk_level, "medium")
        self.assertTrue(action.requires_user_review)

    def test_broken_reference_suggests_no_safe_auto_fix_or_high_risk_fix(self) -> None:
        project, _beat = build_ready_project()
        project.review_episodes[0].source_chapter_ids.append("missing_chapter")

        actions = RepairSuggestionService().suggest_repairs_for_episode(project, "ep_001")
        risky_actions = [
            action
            for action in actions
            if action.action_type in {"no_safe_auto_fix", "fix_broken_reference"}
        ]

        self.assertTrue(risky_actions)
        self.assertTrue(any(action.risk_level == "high" for action in risky_actions))

    def test_apply_rebuild_prompt_action_updates_only_prompt_fields(self) -> None:
        project, beat = build_ready_project()
        beat.image_prompt = ""
        beat.negative_prompt = ""
        original_review = beat.review_text
        original_raw_text = project.source_chapters[0].raw_text
        actions = RepairSuggestionService().suggest_repairs_for_episode(project, "ep_001")
        action = first_action(actions, "rebuild_image_prompt")

        result = RepairSuggestionService().apply_repair_action(
            project,
            action.action_id,
            actions,
        )

        self.assertTrue(result.applied)
        self.assertTrue(beat.image_prompt)
        self.assertTrue(beat.negative_prompt)
        self.assertEqual(beat.review_text, original_review)
        self.assertEqual(project.source_chapters[0].raw_text, original_raw_text)

    def test_apply_rewrite_missing_review_updates_only_review_text(self) -> None:
        project, beat = build_ready_project()
        beat.review_text = ""
        original_image_prompt = beat.image_prompt
        original_negative_prompt = beat.negative_prompt
        original_raw_text = project.source_chapters[0].raw_text
        service = RepairSuggestionService()
        actions = service.suggest_repairs_for_episode(project, "ep_001")
        action = first_action(actions, "rewrite_review_text")

        result = service.apply_repair_action(project, action.action_id, actions)

        self.assertTrue(result.applied)
        self.assertTrue(beat.review_text)
        self.assertEqual(beat.image_prompt, original_image_prompt)
        self.assertEqual(beat.negative_prompt, original_negative_prompt)
        self.assertEqual(project.source_chapters[0].raw_text, original_raw_text)

    def test_apply_create_default_style_presets(self) -> None:
        project, _beat = build_ready_project()
        project.style_presets.clear()
        service = RepairSuggestionService()
        actions = service.suggest_repairs_for_episode(project, "ep_001")
        action = first_action(actions, "create_default_style_presets")

        result = service.apply_repair_action(project, action.action_id, actions)

        self.assertTrue(result.applied)
        self.assertTrue(project.style_presets)

    def test_apply_low_risk_repairs_does_not_apply_medium_high_risk(self) -> None:
        project, _beat = build_ready_project()
        project.style_presets.clear()
        project.review_episodes[0].scenes[0].beats.clear()
        project.review_episodes[0].source_chapter_ids.append("missing_chapter")
        service = RepairSuggestionService()
        actions = service.suggest_repairs_for_episode(project, "ep_001")

        results = service.apply_low_risk_repairs(project, actions)

        self.assertTrue(any(result.applied for result in results))
        self.assertTrue(project.style_presets)
        self.assertFalse(project.review_episodes[0].scenes[0].beats)

    def test_apply_repair_requires_permission_for_medium_risk(self) -> None:
        project, _beat = build_ready_project()
        project.review_episodes[0].scenes[0].beats.clear()
        service = RepairSuggestionService()
        actions = service.suggest_repairs_for_episode(project, "ep_001")
        action = first_action(actions, "generate_missing_beats")

        result = service.apply_repair_action(project, action.action_id, actions)

        self.assertFalse(result.applied)
        self.assertIn("Medium-risk", result.message)

    def test_repair_workflow_improves_readiness(self) -> None:
        project, beat = build_ready_project()
        beat.review_text = ""
        beat.image_prompt = ""
        beat.negative_prompt = ""
        readiness = ProductionReadinessService()
        before = readiness.build_episode_report(project, "ep_001")
        service = RepairSuggestionService()
        actions = service.suggest_repairs_for_episode(project, "ep_001")

        service.apply_low_risk_repairs(project, actions)
        after = readiness.build_episode_report(project, "ep_001")

        self.assertGreaterEqual(after.overall_score, before.overall_score)
        self.assertLessEqual(len(after.blocked_reasons), len(before.blocked_reasons))


def action_types(actions) -> set[str]:
    return {action.action_type for action in actions}


def first_action(actions, action_type: str):
    for action in actions:
        if action.action_type == action_type:
            return action
    raise AssertionError(f"Missing action type: {action_type}")


if __name__ == "__main__":
    unittest.main()
