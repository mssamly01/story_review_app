import unittest

from app.infrastructure.prompt_template_loader import PromptTemplateLoader


class PromptTemplateLoaderTests(unittest.TestCase):
    def test_prompt_template_loader_loads_all_required_templates(self) -> None:
        loader = PromptTemplateLoader()

        for prompt_name in PromptTemplateLoader.PROMPT_FILES:
            with self.subTest(prompt_name=prompt_name):
                template = loader.load(prompt_name)

                self.assertNotEqual(template.strip(), "")
                self.assertIn("## Role", template)
                self.assertIn("## Task", template)
                self.assertIn("## Rules", template)
                self.assertIn("## Input schema", template)
                self.assertIn("## Output schema", template)
                self.assertIn("Return JSON only", template)

    def test_prompt_template_loader_missing_template_has_clear_error(self) -> None:
        loader = PromptTemplateLoader()

        with self.assertRaisesRegex(ValueError, "Unknown prompt template"):
            loader.load("unknown_prompt")

        self.assertFalse(loader.exists("unknown_prompt"))


if __name__ == "__main__":
    unittest.main()

