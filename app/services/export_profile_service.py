"""Named export profiles for production handoff packages."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import re
from typing import Any

from app.domain.export_profile import ExportProfile
from app.domain.project import Project
from app.services.export_service import ExportService
from app.services.quality.readiness import ProductionReadinessService
from app.services.project_service import ProjectService
from app.services.quality.prompt import PromptQualityService
from app.services.quality.review import ReviewQualityService


class ExportProfileService:
    REQUIRED_PROFILE_IDS = [
        "production_markdown",
        "youtube_review_script",
        "shorts_review_script",
        "image_prompt_csv",
        "prompt_only_txt",
        "review_only_txt",
        "full_json_handoff",
        "batch_package",
        "quality_report_package",
    ]

    PROMPT_CSV_COLUMNS = [
        "beat_id",
        "scene_id",
        "image_prompt",
        "negative_prompt",
        "characters",
        "location",
        "shot_type",
    ]

    def __init__(
        self,
        project_service: ProjectService | None = None,
        export_service: ExportService | None = None,
        prompt_quality_service: PromptQualityService | None = None,
        review_quality_service: ReviewQualityService | None = None,
        readiness_service: ProductionReadinessService | None = None,
    ) -> None:
        self.project_service = project_service or ProjectService()
        self.export_service = export_service or ExportService(self.project_service)
        self.prompt_quality_service = prompt_quality_service or PromptQualityService(
            self.project_service
        )
        self.review_quality_service = review_quality_service or ReviewQualityService(
            self.project_service
        )
        self.readiness_service = readiness_service or ProductionReadinessService(
            self.project_service
        )

    def list_profiles(self) -> list[ExportProfile]:
        return [self.get_profile(profile_id) for profile_id in self.REQUIRED_PROFILE_IDS]

    def get_profile(self, profile_id: str) -> ExportProfile:
        profile = self._profiles_by_id().get(profile_id)
        if profile is None:
            raise LookupError(f"ExportProfile not found: {profile_id}")
        return profile

    def export_episode_with_profile(
        self,
        project: Project,
        episode_id: str,
        profile_id: str,
        output_dir: str | Path,
    ) -> list[Path]:
        profile = self.get_profile(profile_id)
        output_root = self._output_root(output_dir, profile)

        if profile_id == "batch_package":
            return self._export_batch_package_episode(project, episode_id, output_root)
        if profile_id == "quality_report_package":
            return self._export_quality_report_package_episode(project, episode_id, output_root)
        if profile_id == "production_markdown":
            return [
                self._write_text(
                    self.export_service.export_episode_markdown(project, episode_id),
                    output_root / f"{self._episode_stem(project, episode_id)}_production.md",
                )
            ]
        if profile_id == "youtube_review_script":
            return [
                self._write_text(
                    self.export_service.export_review_script_txt(project, episode_id),
                    output_root / f"{self._episode_stem(project, episode_id)}_youtube_review.txt",
                )
            ]
        if profile_id == "shorts_review_script":
            return [
                self._write_text(
                    self._compact_review_script(project, episode_id),
                    output_root / f"{self._episode_stem(project, episode_id)}_shorts_review.txt",
                )
            ]
        if profile_id == "image_prompt_csv":
            return [
                self._write_text(
                    self._prompt_csv(project, episode_id),
                    output_root / f"{self._episode_stem(project, episode_id)}_prompts.csv",
                )
            ]
        if profile_id == "prompt_only_txt":
            return [
                self._write_text(
                    self.export_service.export_image_prompts_txt(project, episode_id),
                    output_root / f"{self._episode_stem(project, episode_id)}_prompts.txt",
                )
            ]
        if profile_id == "review_only_txt":
            return [
                self._write_text(
                    self.export_service.export_review_script_txt(project, episode_id),
                    output_root / f"{self._episode_stem(project, episode_id)}_review.txt",
                )
            ]
        if profile_id == "full_json_handoff":
            return [
                self._write_json(
                    self._full_json_handoff(project, episode_id),
                    output_root / f"{self._episode_stem(project, episode_id)}_handoff.json",
                )
            ]
        raise ValueError(f"Unsupported export profile: {profile_id}")

    def export_batch_with_profile(
        self,
        project: Project,
        episode_ids: list[str],
        profile_id: str,
        output_dir: str | Path,
    ) -> list[Path]:
        paths: list[Path] = []
        for episode_id in episode_ids:
            paths.extend(
                self.export_episode_with_profile(
                    project,
                    episode_id,
                    profile_id,
                    output_dir,
                )
            )
        return paths

    def _export_batch_package_episode(
        self,
        project: Project,
        episode_id: str,
        output_root: Path,
    ) -> list[Path]:
        stem = self._episode_stem(project, episode_id)
        return [
            self._write_text(
                self.export_service.export_episode_markdown(project, episode_id),
                output_root / f"{stem}_production.md",
            ),
            self._write_json(
                self._full_json_handoff(project, episode_id),
                output_root / f"{stem}_handoff.json",
            ),
            self._write_text(
                self.export_service.export_episode_csv(project, episode_id),
                output_root / f"{stem}_beats.csv",
            ),
            self._write_text(
                self.export_service.export_review_script_txt(project, episode_id),
                output_root / f"{stem}_review.txt",
            ),
            self._write_text(
                self.export_service.export_image_prompts_txt(project, episode_id),
                output_root / f"{stem}_prompts.txt",
            ),
        ]

    def _export_quality_report_package_episode(
        self,
        project: Project,
        episode_id: str,
        output_root: Path,
    ) -> list[Path]:
        stem = self._episode_stem(project, episode_id)
        return [
            self._write_text(
                self.prompt_quality_service.export_episode_report_markdown(
                    project,
                    episode_id,
                ),
                output_root / f"{stem}_prompt_quality.md",
            ),
            self._write_text(
                self._review_quality_markdown(project, episode_id),
                output_root / f"{stem}_review_quality.md",
            ),
            self._write_text(
                self.readiness_service.export_episode_report_markdown(
                    project,
                    episode_id,
                ),
                output_root / f"{stem}_readiness.md",
            ),
        ]

    def _full_json_handoff(self, project: Project, episode_id: str) -> dict[str, Any]:
        data = self.export_service.export_episode_json(project, episode_id)
        data["quality"] = {
            "prompt": self.prompt_quality_service.build_episode_report(
                project,
                episode_id,
            ),
            "review": self.review_quality_service.build_episode_report(
                project,
                episode_id,
            ),
        }
        data["readiness"] = self.readiness_service.export_episode_report_json(
            project,
            episode_id,
        )
        return data

    def _prompt_csv(self, project: Project, episode_id: str) -> str:
        episode = self.project_service.find_episode(project, episode_id)
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=self.PROMPT_CSV_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        for scene in episode.scenes:
            for beat in scene.ordered_beats():
                writer.writerow(
                    {
                        "beat_id": beat.beat_id,
                        "scene_id": scene.scene_id,
                        "image_prompt": beat.image_prompt,
                        "negative_prompt": beat.negative_prompt,
                        "characters": "|".join(beat.characters),
                        "location": beat.location,
                        "shot_type": beat.shot_type,
                    }
                )
        return output.getvalue()

    def _compact_review_script(self, project: Project, episode_id: str) -> str:
        episode = self.project_service.find_episode(project, episode_id)
        lines = [episode.title]
        if episode.hook:
            lines.extend(["", episode.hook])
        for scene in episode.scenes:
            lines.extend(["", scene.title])
            for beat in scene.ordered_beats():
                if beat.review_text:
                    lines.append(f"- {beat.review_text}")
        if episode.cliffhanger:
            lines.extend(["", episode.cliffhanger])
        return "\n".join(lines).rstrip() + "\n"

    def _review_quality_markdown(self, project: Project, episode_id: str) -> str:
        report = self.review_quality_service.build_episode_report(project, episode_id)
        lines = [
            f"# Review Quality Report - {report['episode_title']}",
            "",
            f"- Episode ID: `{report['episode_id']}`",
            f"- Average score: {report['average_score']}",
            f"- Ready: {report['ready_count']}",
            f"- Not ready: {report['not_ready_count']}",
            "",
            "## Beat Results",
            "",
            "| Beat ID | Score | Grade | Ready | Top Issues |",
            "|---|---:|:---:|:---:|---|",
        ]
        for result in report["results"]:
            top_issues = ", ".join(
                issue["category"] for issue in result["issues"][:3]
            ) or "None"
            ready = "yes" if result["is_ready"] else "no"
            lines.append(
                f"| `{result['beat_id']}` | {result['score']} | "
                f"{result['grade']} | {ready} | {top_issues} |"
            )
        return "\n".join(lines).rstrip() + "\n"

    def _write_text(self, content: str, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _write_json(self, data: dict[str, Any], path: Path) -> Path:
        return self._write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            path,
        )

    def _output_root(self, output_dir: str | Path, profile: ExportProfile) -> Path:
        root = Path(output_dir)
        if profile.output_subdir:
            root = root / profile.output_subdir
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _episode_stem(self, project: Project, episode_id: str) -> str:
        episode = self.project_service.find_episode(project, episode_id)
        match = re.search(r"(\d+)$", episode.episode_id)
        if match:
            return f"episode_{int(match.group(1)):03d}"
        return self._safe_slug(episode.episode_id or episode.title or "episode")

    def _safe_slug(self, value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
        return slug or "episode"

    def _profiles_by_id(self) -> dict[str, ExportProfile]:
        prompt_columns = list(self.PROMPT_CSV_COLUMNS)
        profiles = [
            ExportProfile(
                profile_id="production_markdown",
                name="Production Markdown",
                description="Full human-readable episode export with narration and prompts.",
                target_use="production handoff",
                formats=["markdown"],
                output_subdir="",
            ),
            ExportProfile(
                profile_id="youtube_review_script",
                name="YouTube Review Script",
                description="Review script without image prompt sections.",
                target_use="long-form narration script",
                formats=["txt"],
                include_image_prompts=False,
                include_negative_prompts=False,
                txt_mode="review",
            ),
            ExportProfile(
                profile_id="shorts_review_script",
                name="Shorts Review Script",
                description="Compact review script for brief narration workflows.",
                target_use="compact narration script",
                formats=["txt"],
                include_image_prompts=False,
                include_negative_prompts=False,
                txt_mode="compact_review",
            ),
            ExportProfile(
                profile_id="image_prompt_csv",
                name="Image Prompt CSV",
                description="Spreadsheet-friendly prompt table by beat.",
                target_use="prompt table handoff",
                formats=["csv"],
                include_review_text=False,
                csv_columns=prompt_columns,
            ),
            ExportProfile(
                profile_id="prompt_only_txt",
                name="Prompt Only TXT",
                description="Text file with beat IDs, image prompts, and negative prompts.",
                target_use="prompt list handoff",
                formats=["txt"],
                include_review_text=False,
                txt_mode="prompts",
            ),
            ExportProfile(
                profile_id="review_only_txt",
                name="Review Only TXT",
                description="Narration-only text file.",
                target_use="review narration handoff",
                formats=["txt"],
                include_image_prompts=False,
                include_negative_prompts=False,
                txt_mode="review",
            ),
            ExportProfile(
                profile_id="full_json_handoff",
                name="Full JSON Handoff",
                description="Structured episode JSON with quality and readiness summaries.",
                target_use="structured data handoff",
                formats=["json"],
                include_quality_scores=True,
                include_readiness_summary=True,
                include_character_bible=True,
                include_location_bible=True,
                json_include_full_project_context=True,
            ),
            ExportProfile(
                profile_id="batch_package",
                name="Batch Package",
                description="Production bundle of markdown, JSON, CSV, review TXT, and prompt TXT.",
                target_use="multi-format episode package",
                formats=["markdown", "json", "csv", "review-txt", "prompts-txt"],
                include_quality_scores=True,
                include_readiness_summary=True,
            ),
            ExportProfile(
                profile_id="quality_report_package",
                name="Quality Report Package",
                description="Prompt quality, review quality, and readiness report markdown files.",
                target_use="quality review handoff",
                formats=["markdown"],
                include_review_text=False,
                include_image_prompts=False,
                include_negative_prompts=False,
                include_quality_scores=True,
                include_readiness_summary=True,
                output_subdir="quality_reports",
            ),
        ]
        return {profile.profile_id: profile for profile in profiles}
