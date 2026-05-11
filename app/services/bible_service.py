"""Management helpers for character, location, and style bible data."""

from __future__ import annotations

import re

from app.domain.character import Character
from app.domain.location import Location
from app.domain.project import Project
from app.domain.style_preset import StylePreset


class BibleService:
    DEFAULT_FORBIDDEN_TERMS = [
        "text",
        "watermark",
        "logo",
        "subtitles",
        "captions",
        "speech bubbles",
    ]

    def add_or_update_character(
        self,
        project: Project,
        character: Character,
    ) -> Character:
        for index, existing in enumerate(project.characters):
            if existing.character_id == character.character_id:
                project.characters[index] = character
                project.touch()
                return character
        project.characters.append(character)
        project.touch()
        return character

    def add_or_update_location(
        self,
        project: Project,
        location: Location,
    ) -> Location:
        for index, existing in enumerate(project.locations):
            if existing.location_id == location.location_id:
                project.locations[index] = location
                project.touch()
                return location
        project.locations.append(location)
        project.touch()
        return location

    def add_or_update_style_preset(
        self,
        project: Project,
        style: StylePreset,
    ) -> StylePreset:
        for index, existing in enumerate(project.style_presets):
            if existing.style_id == style.style_id:
                project.style_presets[index] = style
                project.touch()
                return style
        project.style_presets.append(style)
        project.touch()
        return style

    def find_character_by_name_or_alias(
        self,
        project: Project,
        name: str,
    ) -> Character | None:
        key = self._normalise(name)
        for character in project.characters:
            values = [character.character_id, character.name, *character.aliases]
            if key in {self._normalise(value) for value in values}:
                return character
        return None

    def find_location_by_name_or_alias(
        self,
        project: Project,
        name: str,
    ) -> Location | None:
        key = self._normalise(name)
        for location in project.locations:
            values = [location.location_id, location.name, *location.aliases]
            if key in {self._normalise(value) for value in values}:
                return location
        return None

    def get_default_style_preset(self, project: Project) -> StylePreset | None:
        if not project.style_presets:
            return None

        preferred = self._normalise(project.default_art_style)
        for style in project.style_presets:
            if self._normalise(style.style_id) == preferred:
                return style
            if self._normalise(style.name) == preferred:
                return style

        return project.style_presets[0]

    def create_default_style_presets(self, project: Project) -> list[StylePreset]:
        presets = self._default_presets()
        for preset in presets:
            self.add_or_update_style_preset(project, preset)
        return presets

    def _default_presets(self) -> list[StylePreset]:
        return [
            StylePreset(
                style_id="dark_fantasy_webtoon",
                name="Dark Fantasy Webtoon",
                description="Moody fantasy review illustration style.",
                positive_prompt=(
                    "dark fantasy webtoon style, cinematic shadows, "
                    "detailed backgrounds, dramatic rim light, high quality illustration"
                ),
                negative_prompt="flat lighting, washed out colors, low detail background",
                genre="dark fantasy",
                line_style="clean ink line art with sharp silhouettes",
                color_palette="deep blues, muted crimson, cold moonlight",
                lighting_style="moonlight, rim light, deep shadows",
                rendering_style="polished digital webtoon rendering",
                character_design_rules="expressive eyes, consistent outfit, dramatic poses",
                background_detail_level="high",
                camera_style="cinematic close-ups and wide establishing views",
                mood_keywords=["mysterious", "tense", "ominous"],
                forbidden_terms=list(self.DEFAULT_FORBIDDEN_TERMS),
            ),
            StylePreset(
                style_id="korean_romance_webtoon",
                name="Korean Romance Webtoon",
                positive_prompt=(
                    "korean romance webtoon style, soft clean line art, "
                    "glowing skin tones, elegant outfits, high quality illustration"
                ),
                negative_prompt="harsh shadows, muddy colors, stiff expressions",
                genre="romance",
                line_style="soft clean line art",
                color_palette="pastel pink, warm ivory, gentle lavender",
                lighting_style="soft window light, gentle glow",
                rendering_style="smooth digital webtoon shading",
                character_design_rules="attractive faces, expressive eyes, refined outfits",
                background_detail_level="medium",
                camera_style="intimate medium shots and emotional close-ups",
                mood_keywords=["romantic", "warm", "bittersweet"],
                forbidden_terms=list(self.DEFAULT_FORBIDDEN_TERMS),
            ),
            StylePreset(
                style_id="modern_school_webtoon",
                name="Modern School Webtoon",
                positive_prompt=(
                    "modern school webtoon style, clean campus backgrounds, "
                    "natural daylight, crisp uniforms, high quality illustration"
                ),
                negative_prompt="messy uniform, empty background, dull lighting",
                genre="school drama",
                line_style="clean youthful webtoon lines",
                color_palette="fresh blues, white, warm classroom sunlight",
                lighting_style="bright daylight, soft indoor light",
                rendering_style="clean digital cel shading",
                character_design_rules="consistent school uniforms, youthful faces",
                background_detail_level="medium",
                camera_style="readable medium shots and classroom details",
                mood_keywords=["youthful", "daily life", "emotional"],
                forbidden_terms=list(self.DEFAULT_FORBIDDEN_TERMS),
            ),
            StylePreset(
                style_id="horror_webtoon",
                name="Horror Webtoon",
                positive_prompt=(
                    "horror webtoon style, oppressive darkness, unsettling composition, "
                    "cold highlights, high quality illustration"
                ),
                negative_prompt="cute expression, bright cheerful colors, comedic tone",
                genre="horror",
                line_style="thin sharp lines and heavy shadow shapes",
                color_palette="black, sickly green, desaturated red",
                lighting_style="low light, flashlight beam, harsh contrast",
                rendering_style="gritty digital webtoon rendering",
                character_design_rules="fearful expressions, consistent clothing damage",
                background_detail_level="high",
                camera_style="claustrophobic close-ups and tilted angles",
                mood_keywords=["fearful", "uneasy", "ominous"],
                forbidden_terms=list(self.DEFAULT_FORBIDDEN_TERMS),
            ),
            StylePreset(
                style_id="action_manhwa",
                name="Action Manhwa",
                positive_prompt=(
                    "action manhwa style, dynamic composition, sharp motion energy, "
                    "bold impact lighting, high quality illustration"
                ),
                negative_prompt="static pose, weak impact, unclear action",
                genre="action",
                line_style="bold angular lines",
                color_palette="electric blue, red accents, smoky gray",
                lighting_style="strong highlights, explosive contrast",
                rendering_style="high energy digital manhwa rendering",
                character_design_rules="athletic poses, readable action silhouettes",
                background_detail_level="medium",
                camera_style="low angle action shots and dramatic close-ups",
                mood_keywords=["intense", "determined", "explosive"],
                forbidden_terms=list(self.DEFAULT_FORBIDDEN_TERMS),
            ),
            StylePreset(
                style_id="historical_fantasy_manhua",
                name="Historical Fantasy Manhua",
                positive_prompt=(
                    "historical fantasy manhua style, flowing robes, ornate architecture, "
                    "elegant magical atmosphere, high quality illustration"
                ),
                negative_prompt="modern clothing, plastic texture, simple background",
                genre="historical fantasy",
                line_style="elegant fine lines",
                color_palette="jade green, antique gold, misty blue",
                lighting_style="misty sunlight, lantern glow, magical highlights",
                rendering_style="ornate digital manhua rendering",
                character_design_rules="period outfits, graceful poses, consistent hair ornaments",
                background_detail_level="high",
                camera_style="wide palace views and graceful medium shots",
                mood_keywords=["elegant", "mythic", "wistful"],
                forbidden_terms=list(self.DEFAULT_FORBIDDEN_TERMS),
            ),
            StylePreset(
                style_id="noir_detective_comic",
                name="Noir Detective Comic",
                positive_prompt=(
                    "noir detective comic style, rain soaked streets, smoky atmosphere, "
                    "hard shadows, high quality illustration"
                ),
                negative_prompt="bright cheerful palette, soft romance lighting, cluttered scene",
                genre="mystery",
                line_style="bold ink shadows and crisp silhouettes",
                color_palette="black, slate gray, amber streetlight",
                lighting_style="venetian blind shadows, streetlamp glow",
                rendering_style="graphic comic rendering with controlled grain",
                character_design_rules="trench coats, sharp profiles, restrained expressions",
                background_detail_level="high",
                camera_style="dramatic close-ups and moody street views",
                mood_keywords=["suspicious", "lonely", "grim"],
                forbidden_terms=list(self.DEFAULT_FORBIDDEN_TERMS),
            ),
            StylePreset(
                style_id="soft_watercolor_webtoon",
                name="Soft Watercolor Webtoon",
                positive_prompt=(
                    "soft watercolor webtoon style, gentle brush texture, airy composition, "
                    "delicate colors, high quality illustration"
                ),
                negative_prompt="harsh contrast, heavy black shadows, muddy paint",
                genre="slice of life",
                line_style="light sketch-like lines",
                color_palette="soft teal, peach, pale sky blue",
                lighting_style="diffused daylight, gentle glow",
                rendering_style="digital watercolor wash",
                character_design_rules="soft expressions, simple consistent outfits",
                background_detail_level="medium",
                camera_style="calm wide shots and tender close-ups",
                mood_keywords=["calm", "nostalgic", "gentle"],
                forbidden_terms=list(self.DEFAULT_FORBIDDEN_TERMS),
            ),
        ]

    def _normalise(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
