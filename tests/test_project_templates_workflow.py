import unittest

from app.domain.project_template import ProjectTemplate
from app.services.project_template_service import ProjectTemplateService


class ProjectTemplatesWorkflowTests(unittest.TestCase):
    def test_template_roundtrip_dict(self) -> None:
        template = ProjectTemplateService().get_template("dark_fantasy_webtoon")

        reloaded = ProjectTemplate.from_dict(template.to_dict())

        self.assertEqual(reloaded.template_id, template.template_id)
        self.assertEqual(reloaded.default_art_style, template.default_art_style)
        self.assertTrue(reloaded.default_style_presets)

    def test_product_direction_guards_still_pass(self) -> None:
        template = ProjectTemplateService().get_template("action_manhwa")

        self.assertIn("beat", " ".join(template.prompt_guidelines).lower())
        self.assertTrue(template.review_guidelines)


if __name__ == "__main__":
    unittest.main()
