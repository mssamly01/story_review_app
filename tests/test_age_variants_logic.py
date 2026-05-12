import unittest
import json
from app.domain.project import Project
from app.services.manual_ai_bible_style_service import ManualAIBibleStyleService
from app.services.manual_ai_episode_planner_service import ManualAIEpisodePlannerService
from app.services.prompt_builder_service import PromptBuilderService
from app.services.project_service import ProjectService
from app.domain.character import Character, CharacterVariant, CharacterOutfit
from app.domain.beat import Beat
from app.domain.scene import Scene
from app.domain.episode import ReviewEpisode

class AgeVariantsLogicTests(unittest.TestCase):
    def setUp(self):
        self.project_service = ProjectService()
        self.bible_service = ManualAIBibleStyleService()
        self.planner_service = ManualAIEpisodePlannerService(self.project_service)
        self.prompt_builder = PromptBuilderService()
        self.project = self.project_service.create_project("Test Project")
        # Add a dummy chapter
        self.chapter = self.project_service.add_source_chapter(self.project, title="C1", chapter_number=1, raw_text="text")

    def test_bible_style_prompt_variants_only_for_age_forms(self):
        prompt = self.bible_service.build_bible_style_analysis_prompt(self.project, [self.chapter.chapter_id])
        self.assertIn("Only create variants when the character has a major age/age-form difference", prompt)
        self.assertIn("Do NOT create separate variants for temporary states, emotions, injuries, or poses", prompt)
        self.assertIn("angry, injured, crying, battle pose", prompt)

    def test_bible_style_prompt_outfits_still_separate(self):
        prompt = self.bible_service.build_bible_style_analysis_prompt(self.project, [self.chapter.chapter_id])
        self.assertIn("Every distinct outfit should be a separate outfit object", prompt)
        self.assertIn("character_outfits", prompt)

    def test_apply_bible_style_creates_age_variants(self):
        result_json = {
            "characters": [
                {"character_id": "char_001", "name": "Co Than"}
            ],
            "character_variants": [
                {
                    "variant_id": "char_001_young",
                    "character_id": "char_001",
                    "display_name": "Co Than - young",
                    "age_stage": "child",
                    "visual_prompt_base": "young boy"
                },
                {
                    "variant_id": "char_001_old",
                    "character_id": "char_001",
                    "display_name": "Co Than - old",
                    "age_stage": "old",
                    "visual_prompt_base": "old man"
                }
            ],
            "character_outfits": []
        }
        self.bible_service.apply_bible_style_analysis_result(self.project, result_json)
        
        char = self.project.characters[0]
        self.assertEqual(len(char.variants), 2)
        self.assertEqual(char.variants[0].age_stage, "child")
        self.assertEqual(char.variants[1].age_stage, "old")

    def test_no_variant_created_for_temporary_state_rule_documented(self):
        prompt = self.bible_service.build_bible_style_analysis_prompt(self.project, [self.chapter.chapter_id])
        self.assertIn("Store temporary states as beat/storyboard fields later in Episode Planner", prompt)

    def test_episode_planner_prompt_uses_age_variant_and_outfit_refs(self):
        # Setup character with variants
        char = self.project_service.add_character(self.project, character_id="char_001", name="Co Than")
        char.variants = [
            CharacterVariant(variant_id="char_001_young", character_id="char_001", age_stage="child")
        ]
        
        prompt = self.planner_service.build_episode_plan_with_review_prompt(self.project, [self.chapter.chapter_id])
        self.assertIn("choose the correct character age variant", prompt)
        self.assertIn("character_variants", prompt)
        self.assertIn("character_outfits", prompt)
        self.assertIn("emotion, posture, expression, body_language, character_state", prompt)

    def test_prompt_builder_uses_age_variant_plus_beat_state(self):
        char = self.project_service.add_character(
            self.project, 
            character_id="char_001", 
            name="Co Than",
            gender="male"
        )
        char.variants = [
            CharacterVariant(
                variant_id="char_001_old", 
                character_id="char_001", 
                display_name="Co Than - 500 tuoi",
                age_stage="old",
                age_description="over 500 years old",
                hair="white hair",
                visual_prompt_base="old cultivator with white hair"
            )
        ]
        
        scene = Scene(episode_id="e1", scene_id="s1", title="Scene 1", location="loc1")
        beat = Beat(
            beat_id="b1",
            scene_id="s1",
            order_index=1,
            characters=["char_001"],
            character_variants={"char_001": "char_001_old"},
            character_state="soul-burning final attack",
            expression="furious",
            posture="standing unsteadily"
        )
        
        prompt = self.prompt_builder._build_image_prompt(
            project=self.project,
            scene=scene,
            beat=beat,
            style_preset=None
        )
        
        self.assertIn("Co Than - 500 tuoi", prompt)
        self.assertIn("white hair", prompt)
        self.assertIn("Current state: soul-burning final attack", prompt)
        self.assertIn("Expression: furious", prompt)
        self.assertIn("Posture: standing unsteadily", prompt)

    def test_prompt_builder_uses_outfit_separately(self):
        char = self.project_service.add_character(self.project, character_id="char_001", name="Co Than")
        outfit = CharacterOutfit(
            outfit_id="outfit_1",
            character_id="char_001",
            display_name="Battle Robe",
            description="heavy armored ancient robes"
        )
        char.outfits = [outfit]
        
        scene = Scene(episode_id="e1", scene_id="s1", title="Scene 1", location="loc1")
        beat = Beat(
            beat_id="b1",
            scene_id="s1",
            order_index=1,
            characters=["char_001"],
            character_outfits={"char_001": "outfit_1"}
        )
        
        prompt = self.prompt_builder._build_image_prompt(
            project=self.project,
            scene=scene,
            beat=beat,
            style_preset=None
        )
        
        self.assertIn("Outfit: heavy armored ancient robes", prompt)

    def test_product_direction_guards_still_pass(self):
        # Assert no actual image generation is implemented in PromptBuilderService
        # (It only builds strings)
        self.assertFalse(hasattr(self.prompt_builder, "generate_image"))
        
        # Verify deterministic builder doesn't call AI
        ep = self.project_service.add_review_episode(self.project, title="E1", source_chapter_ids=[self.chapter.chapter_id])
        sc = self.project_service.add_scene(self.project, episode_id=ep.episode_id, title="S1", location="loc1")
        b = self.project_service.add_beat(self.project, episode_id=ep.episode_id, scene_id=sc.scene_id, beat_id="b1", order_index=1)
        
        # Ensure it doesn't crash or try to network
        self.prompt_builder.build_prompt_for_beat(self.project, "b1")

if __name__ == "__main__":
    unittest.main()
