"""Export project and episode data into user-facing formats."""

from __future__ import annotations

from pathlib import Path

from app.domain.beat import Beat
from app.domain.project import Project
from app.services.project_service import ProjectService


class ExportService:
    def __init__(self, project_service: ProjectService | None = None) -> None:
        self.project_service = project_service or ProjectService()

    def export_episode_to_markdown(
        self, project: Project, episode_id: str
    ) -> str:
        episode = self.project_service.find_episode(project, episode_id)
        lines = [
            f"# {episode.title}",
            "",
            f"- Episode ID: `{episode.episode_id}`",
            f"- Tone: {episode.tone}",
            f"- Density: {episode.density}",
            f"- Source chapters: {', '.join(episode.source_chapter_ids)}",
        ]

        if episode.hook:
            lines.extend(["", f"Hook: {episode.hook}"])
        if episode.summary:
            lines.extend(["", f"Summary: {episode.summary}"])

        for scene_index, scene in enumerate(episode.scenes, start=1):
            lines.extend(
                [
                    "",
                    f"## Scene {scene_index} - {scene.title}",
                    "",
                    f"- Scene ID: `{scene.scene_id}`",
                    f"- Mood: {scene.mood}",
                    f"- Location: {scene.location}",
                ]
            )
            if scene.summary:
                lines.extend(["", scene.summary])

            for beat in scene.ordered_beats():
                lines.extend(self._beat_markdown(beat))

        if episode.cliffhanger:
            lines.extend(["", "## Cliffhanger", "", episode.cliffhanger])

        return "\n".join(lines).rstrip() + "\n"

    def save_episode_markdown(
        self, project: Project, episode_id: str, path: str | Path
    ) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            self.export_episode_to_markdown(project, episode_id),
            encoding="utf-8",
        )

    def _beat_markdown(self, beat: Beat) -> list[str]:
        lines = [
            "",
            f"### Beat {beat.order_index} - `{beat.beat_id}`",
            "",
            f"- Story function: {beat.story_function}",
            f"- Characters: {', '.join(beat.characters)}",
            f"- Location: {beat.location}",
            f"- Emotion: {beat.emotion}",
            f"- Shot type: {beat.shot_type}",
        ]

        if beat.action:
            lines.append(f"- Action: {beat.action}")
        if beat.continuity_tags:
            lines.append(
                f"- Continuity tags: {', '.join(beat.continuity_tags)}"
            )

        lines.extend(["", "Review text:", beat.review_text or "_Not written yet._"])

        if beat.visual_description:
            lines.extend(["", "Visual description:", beat.visual_description])

        lines.extend(["", "Image prompt:", beat.image_prompt or "_Not generated yet._"])

        if beat.negative_prompt:
            lines.extend(["", "Negative prompt:", beat.negative_prompt])

        return lines
