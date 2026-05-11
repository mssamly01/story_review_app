import unittest

from app.services.quality.readiness import ProductionReadinessService
from tests.test_production_readiness_service import build_ready_project


class ProductionReadinessWorkflowTests(unittest.TestCase):
    def test_batch_report_markdown_contains_episode_rows(self) -> None:
        project, _beat = build_ready_project()

        markdown = ProductionReadinessService(
            generated_at_factory=lambda: "fixed",
        ).export_batch_report_markdown(project, ["ep_001"])

        self.assertIn("Batch Production Readiness Report", markdown)
        self.assertIn("Episode 1", markdown)
        self.assertIn("ready", markdown)

    def test_product_direction_guards_still_pass(self) -> None:
        project, _beat = build_ready_project()

        report = ProductionReadinessService(
            generated_at_factory=lambda: "fixed",
        ).build_episode_report(project, "ep_001")

        self.assertEqual(report.episode_id, "ep_001")
        self.assertGreaterEqual(report.total_beats, 1)


if __name__ == "__main__":
    unittest.main()
