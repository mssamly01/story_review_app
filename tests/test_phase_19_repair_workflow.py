import unittest

from app.services.repair_suggestion_service import RepairSuggestionService
from tests.test_production_readiness_service import build_ready_project
from tests.test_repair_suggestion_service import first_action


class PhaseNineteenRepairWorkflowTests(unittest.TestCase):
    def test_medium_risk_repair_can_apply_when_allowed(self) -> None:
        project, _beat = build_ready_project()
        scene = project.review_episodes[0].scenes[0]
        scene.beats.clear()
        service = RepairSuggestionService()
        actions = service.suggest_repairs_for_episode(project, "ep_001")
        action = first_action(actions, "generate_missing_beats")

        result = service.apply_repair_action(
            project,
            action.action_id,
            actions,
            allow_medium_risk=True,
        )

        self.assertTrue(result.applied)
        self.assertTrue(scene.beats)

    def test_product_direction_guards_still_pass(self) -> None:
        project, beat = build_ready_project()
        beat.image_prompt = ""

        actions = RepairSuggestionService().suggest_repairs_for_episode(
            project,
            "ep_001",
        )

        self.assertTrue(actions)


if __name__ == "__main__":
    unittest.main()
