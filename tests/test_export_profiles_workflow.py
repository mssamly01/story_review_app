import unittest

from app.domain.export_profile import ExportProfile
from app.services.export_profile_service import ExportProfileService


class ExportProfilesWorkflowTests(unittest.TestCase):
    def test_export_profile_roundtrip_dict(self) -> None:
        profile = ExportProfileService().get_profile("full_json_handoff")

        reloaded = ExportProfile.from_dict(profile.to_dict())

        self.assertEqual(reloaded.profile_id, profile.profile_id)
        self.assertEqual(reloaded.formats, profile.formats)
        self.assertTrue(reloaded.include_quality_scores)

    def test_product_direction_guards_still_pass(self) -> None:
        profile = ExportProfileService().get_profile("image_prompt_csv")

        self.assertIn("prompt", profile.description.lower())
        self.assertTrue(profile.csv_columns)


if __name__ == "__main__":
    unittest.main()
