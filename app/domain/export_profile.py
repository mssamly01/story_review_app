"""Named export profile model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ExportProfile:
    profile_id: str
    name: str
    description: str = ""
    target_use: str = ""
    formats: list[str] = field(default_factory=list)
    include_review_text: bool = True
    include_image_prompts: bool = True
    include_negative_prompts: bool = True
    include_metadata: bool = True
    include_quality_scores: bool = False
    include_readiness_summary: bool = False
    include_character_bible: bool = False
    include_location_bible: bool = False
    file_naming_pattern: str = "episode_{episode_number}_{profile}"
    output_subdir: str = ""
    markdown_template: str = "default"
    csv_columns: list[str] = field(default_factory=list)
    txt_mode: str = ""
    json_include_full_project_context: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "description": self.description,
            "target_use": self.target_use,
            "formats": list(self.formats),
            "include_review_text": self.include_review_text,
            "include_image_prompts": self.include_image_prompts,
            "include_negative_prompts": self.include_negative_prompts,
            "include_metadata": self.include_metadata,
            "include_quality_scores": self.include_quality_scores,
            "include_readiness_summary": self.include_readiness_summary,
            "include_character_bible": self.include_character_bible,
            "include_location_bible": self.include_location_bible,
            "file_naming_pattern": self.file_naming_pattern,
            "output_subdir": self.output_subdir,
            "markdown_template": self.markdown_template,
            "csv_columns": list(self.csv_columns),
            "txt_mode": self.txt_mode,
            "json_include_full_project_context": self.json_include_full_project_context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExportProfile":
        return cls(
            profile_id=data["profile_id"],
            name=data["name"],
            description=data.get("description", ""),
            target_use=data.get("target_use", ""),
            formats=list(data.get("formats", [])),
            include_review_text=bool(data.get("include_review_text", True)),
            include_image_prompts=bool(data.get("include_image_prompts", True)),
            include_negative_prompts=bool(data.get("include_negative_prompts", True)),
            include_metadata=bool(data.get("include_metadata", True)),
            include_quality_scores=bool(data.get("include_quality_scores", False)),
            include_readiness_summary=bool(data.get("include_readiness_summary", False)),
            include_character_bible=bool(data.get("include_character_bible", False)),
            include_location_bible=bool(data.get("include_location_bible", False)),
            file_naming_pattern=data.get(
                "file_naming_pattern",
                "episode_{episode_number}_{profile}",
            ),
            output_subdir=data.get("output_subdir", ""),
            markdown_template=data.get("markdown_template", "default"),
            csv_columns=list(data.get("csv_columns", [])),
            txt_mode=data.get("txt_mode", ""),
            json_include_full_project_context=bool(
                data.get("json_include_full_project_context", False)
            ),
        )
