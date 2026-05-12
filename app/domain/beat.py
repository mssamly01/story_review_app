"""Narrative beat domain model.

A beat is the smallest production unit in the app: one narratable moment and
one image-promptable visual idea. After the prompt is rendered externally
(Midjourney / Stable Diffusion / ComfyUI / DALL-E), one or more
``BeatImageVariant`` entries can be attached to the beat to close the feedback
loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.dialogue import Dialogue


def _parse_mapping(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): str(item)
        for key, item in value.items()
        if str(key).strip() and str(item).strip()
    }


def _mapping_from_character_states(value: Any, target_key: str) -> dict[str, str]:
    if not isinstance(value, list):
        return {}
    resolved: dict[str, str] = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        character_id = str(item.get("character_id", "")).strip()
        mapped_value = str(item.get(target_key, "")).strip()
        if character_id and mapped_value:
            resolved[character_id] = mapped_value
    return resolved


@dataclass(slots=True)
class BeatImageVariant:
    """A single rendered image artifact attached to a Beat.

    The app never generates these — they are produced by an external image
    model and imported back via ``BeatImageService`` / ``story-review
    import-image``. Storing them on the Beat closes the feedback loop so a
    project knows which beats have visuals and which variant is selected.
    """

    image_id: str
    image_path: str
    model: str = ""
    seed: str = ""
    generated_at: str = ""
    selected: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_id": self.image_id,
            "image_path": self.image_path,
            "model": self.model,
            "seed": self.seed,
            "generated_at": self.generated_at,
            "selected": self.selected,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BeatImageVariant":
        return cls(
            image_id=str(data["image_id"]),
            image_path=str(data["image_path"]),
            model=str(data.get("model", "")),
            seed=str(data.get("seed", "")),
            generated_at=str(data.get("generated_at", "")),
            selected=bool(data.get("selected", False)),
            notes=str(data.get("notes", "")),
        )


@dataclass(slots=True)
class Beat:
    beat_id: str
    scene_id: str
    order_index: int
    story_function: str = ""
    characters: list[str] = field(default_factory=list)
    character_variants: dict[str, str] = field(default_factory=dict)
    character_outfits: dict[str, str] = field(default_factory=dict)
    character_states: dict[str, dict[str, str]] = field(default_factory=dict)
    location: str = ""
    action: str = ""
    emotion: str = ""
    camera: str = ""
    shot_type: str = ""
    timeOfDay: str = ""
    lighting: str = ""
    atmosphere: str = ""
    location_cues: str = ""
    asmr_visuals: str = ""
    composition: str = ""
    posture: str = ""
    expression: str = ""
    body_language: str = ""
    review_text: str = ""
    visual_description: str = ""
    image_prompt: str = ""
    negative_prompt: str = ""
    continuity_tags: list[str] = field(default_factory=list)
    props: list[str] = field(default_factory=list)
    wardrobe_notes: str = ""
    character_state: str = ""
    location_state: str = ""
    transition_note: str = ""
    source_refs: list[str] = field(default_factory=list)
    status: str = "planned"
    images: list[BeatImageVariant] = field(default_factory=list)
    dialogues: list[Dialogue] = field(default_factory=list)

    @property
    def selected_image(self) -> BeatImageVariant | None:
        for image in self.images:
            if image.selected:
                return image
        return None

    @property
    def image_path(self) -> str:
        """Convenience accessor for the selected image's local path."""
        selected = self.selected_image
        return selected.image_path if selected else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "beat_id": self.beat_id,
            "scene_id": self.scene_id,
            "order_index": self.order_index,
            "source_refs": list(self.source_refs),
            "story_function": self.story_function,
            "characters": list(self.characters),
            "character_variants": dict(self.character_variants),
            "character_outfits": dict(self.character_outfits),
            "character_states": {k: dict(v) for k, v in self.character_states.items()},
            "location": self.location,
            "action": self.action,
            "emotion": self.emotion,
            "camera": self.camera,
            "shot_type": self.shot_type,
            "timeOfDay": self.timeOfDay,
            "lighting": self.lighting,
            "atmosphere": self.atmosphere,
            "location_cues": self.location_cues,
            "asmr_visuals": self.asmr_visuals,
            "composition": self.composition,
            "posture": self.posture,
            "expression": self.expression,
            "body_language": self.body_language,
            "review_text": self.review_text,
            "visual_description": self.visual_description,
            "image_prompt": self.image_prompt,
            "negative_prompt": self.negative_prompt,
            "continuity_tags": list(self.continuity_tags),
            "props": list(self.props),
            "wardrobe_notes": self.wardrobe_notes,
            "character_state": self.character_state,
            "location_state": self.location_state,
            "transition_note": self.transition_note,
            "status": self.status,
            "images": [image.to_dict() for image in self.images],
            "dialogues": [dialogue.to_dict() for dialogue in self.dialogues],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Beat":
        variants = _parse_mapping(data.get("character_variants"))
        outfits = _parse_mapping(data.get("character_outfits"))
        states_mapping = data.get("character_states")
        if not isinstance(states_mapping, dict):
            states_mapping = {}
        else:
            # Deep copy and ensure types
            states_mapping = {
                str(k): {str(sub_k): str(sub_v) for sub_k, sub_v in v.items()}
                for k, v in states_mapping.items()
                if isinstance(v, dict)
            }

        if not variants and not outfits:
            legacy_states = data.get("character_states")
            if isinstance(legacy_states, list):
                variants = _mapping_from_character_states(legacy_states, "variant_id")
                outfits = _mapping_from_character_states(legacy_states, "outfit_id")

        return cls(
            beat_id=data["beat_id"],
            scene_id=data["scene_id"],
            order_index=int(data.get("order_index", 0)),
            source_refs=list(data.get("source_refs", [])),
            story_function=data.get("story_function", ""),
            characters=list(data.get("characters", [])),
            character_variants=variants,
            character_outfits=outfits,
            character_states=states_mapping,
            location=data.get("location", ""),
            action=data.get("action", ""),
            emotion=data.get("emotion", ""),
            camera=data.get("camera", ""),
            shot_type=data.get("shot_type", ""),
            timeOfDay=data.get("timeOfDay", data.get("time_of_day", "")),
            lighting=data.get("lighting", ""),
            atmosphere=data.get("atmosphere", ""),
            location_cues=data.get("location_cues", ""),
            asmr_visuals=data.get("asmr_visuals", ""),
            composition=data.get("composition", ""),
            posture=data.get("posture", ""),
            expression=data.get("expression", ""),
            body_language=data.get("body_language", ""),
            review_text=data.get("review_text", ""),
            visual_description=data.get("visual_description", ""),
            image_prompt=data.get("image_prompt", ""),
            negative_prompt=data.get("negative_prompt", ""),
            continuity_tags=list(data.get("continuity_tags", [])),
            props=list(data.get("props", [])),
            wardrobe_notes=data.get("wardrobe_notes", ""),
            character_state=data.get("character_state", ""),
            location_state=data.get("location_state", ""),
            transition_note=data.get("transition_note", ""),
            status=data.get("status", "planned"),
            images=[BeatImageVariant.from_dict(img) for img in data.get("images", [])],
            dialogues=[Dialogue.from_dict(d) for d in data.get("dialogues", [])],
        )
