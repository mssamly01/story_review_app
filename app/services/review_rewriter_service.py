"""Deterministic Vietnamese review narration rewriter.

This service updates Beat.review_text only. It does not call AI, create beats,
or generate image prompts.
"""

from __future__ import annotations

import re
from typing import Any

from app.domain.beat import Beat
from app.domain.episode import ReviewEpisode
from app.domain.project import Project
from app.domain.scene import Scene
from app.domain.source_chapter import SourceChapter
from app.infrastructure.ai_gateway import AIGateway


class ReviewRewriterService:
    _allowed_styles = {
        "neutral",
        "mysterious",
        "dramatic",
        "friendly",
        "humorous",
        "fast-paced",
    }
    _allowed_densities = {"full", "balanced", "condensed"}
    _emotion_words = {
        "calm": "bình tĩnh",
        "curious": "tò mò",
        "tense": "căng thẳng",
        "shocked": "bàng hoàng",
        "confused": "bối rối",
        "determined": "quyết tâm",
        "fearful": "sợ hãi",
        "suspicious": "nghi ngờ",
        "sad": "buồn bã",
        "angry": "tức giận",
        "uneasy": "bất an",
        "lonely": "cô đơn",
    }
    _story_function_words = {
        "hook": "mở đầu",
        "setup": "thiết lập tình huống",
        "discovery": "phát hiện",
        "reaction": "phản ứng",
        "decision": "quyết định",
        "conflict": "xung đột",
        "reveal": "hé lộ",
        "transition": "chuyển cảnh",
        "cliffhanger": "đẩy tới nút treo",
        "opening": "mở đầu",
    }

    def __init__(
        self,
        ai_gateway: AIGateway | None = None,
        use_ai: bool = False,
    ) -> None:
        self.ai_gateway = ai_gateway
        self.use_ai = use_ai

    def rewrite_beat(
        self,
        project: Project,
        beat_id: str,
        narration_style: str | None = None,
        retelling_density: str | None = None,
    ) -> Beat:
        episode, scene, beat = self._find_beat_context(project, beat_id)
        style = narration_style or episode.tone
        density = retelling_density or episode.density
        self._validate_style(style)
        self._validate_density(density)

        if self.use_ai:
            beat.review_text = self._rewrite_beat_with_ai(
                project=project,
                episode=episode,
                scene=scene,
                beat=beat,
                narration_style=style,
                retelling_density=density,
            )
        else:
            beat.review_text = self._compose_review_text(
                project=project,
                episode=episode,
                scene=scene,
                beat=beat,
                narration_style=style,
                retelling_density=density,
            )
        return beat

    def rewrite_scene(
        self,
        project: Project,
        scene_id: str,
        narration_style: str | None = None,
        retelling_density: str | None = None,
    ) -> list[Beat]:
        episode, scene = self._find_scene_context(project, scene_id)
        style = narration_style or episode.tone
        density = retelling_density or episode.density
        self._validate_style(style)
        self._validate_density(density)

        rewritten_beats: list[Beat] = []
        for beat in scene.ordered_beats():
            if self.use_ai:
                beat.review_text = self._rewrite_beat_with_ai(
                    project=project,
                    episode=episode,
                    scene=scene,
                    beat=beat,
                    narration_style=style,
                    retelling_density=density,
                )
            else:
                beat.review_text = self._compose_review_text(
                    project=project,
                    episode=episode,
                    scene=scene,
                    beat=beat,
                    narration_style=style,
                    retelling_density=density,
                )
            rewritten_beats.append(beat)
        return rewritten_beats

    def rewrite_episode(
        self,
        project: Project,
        episode_id: str,
        narration_style: str | None = None,
        retelling_density: str | None = None,
    ) -> list[Beat]:
        episode = self._find_episode(project, episode_id)
        style = narration_style or episode.tone
        density = retelling_density or episode.density
        self._validate_style(style)
        self._validate_density(density)

        rewritten_beats: list[Beat] = []
        for scene in episode.scenes:
            for beat in scene.ordered_beats():
                if self.use_ai:
                    beat.review_text = self._rewrite_beat_with_ai(
                        project=project,
                        episode=episode,
                        scene=scene,
                        beat=beat,
                        narration_style=style,
                        retelling_density=density,
                    )
                else:
                    beat.review_text = self._compose_review_text(
                        project=project,
                        episode=episode,
                        scene=scene,
                        beat=beat,
                        narration_style=style,
                        retelling_density=density,
                    )
                rewritten_beats.append(beat)
        return rewritten_beats

    def _rewrite_beat_with_ai(
        self,
        *,
        project: Project,
        episode: ReviewEpisode,
        scene: Scene,
        beat: Beat,
        narration_style: str,
        retelling_density: str,
    ) -> str:
        gateway = self._require_ai_gateway()
        response = gateway.generate_json(
            "review_rewriter",
            {
                "episode": episode.to_dict(),
                "scene": scene.to_dict(),
                "beat": beat.to_dict(),
                "beat_id": beat.beat_id,
                "source_chapter_context": [
                    chapter.to_dict()
                    for chapter in self._source_chapters_for_episode(
                        project, episode
                    )
                ],
                "narration_style": narration_style,
                "retelling_density": retelling_density,
            },
        )
        return self._review_text_from_ai_response(response, beat.beat_id)

    def _review_text_from_ai_response(
        self, response: dict[str, Any], beat_id: str
    ) -> str:
        if not isinstance(response, dict):
            raise ValueError("review_rewriter AI response must be a dict.")

        rewritten_beats = response.get("rewritten_beats", [])
        if not isinstance(rewritten_beats, list) or not rewritten_beats:
            raise ValueError(
                "review_rewriter AI response field 'rewritten_beats' must be a non-empty list."
            )

        selected_item = rewritten_beats[0]
        for item in rewritten_beats:
            if isinstance(item, dict) and item.get("beat_id") == beat_id:
                selected_item = item
                break

        if not isinstance(selected_item, dict):
            raise ValueError("review_rewriter AI rewritten beat items must be dicts.")
        review_text = selected_item.get("review_text")
        if not isinstance(review_text, str) or not review_text.strip():
            raise ValueError("review_rewriter AI review_text must be a non-empty string.")
        return review_text

    def _compose_review_text(
        self,
        *,
        project: Project,
        episode: ReviewEpisode,
        scene: Scene,
        beat: Beat,
        narration_style: str,
        retelling_density: str,
    ) -> str:
        style_key = narration_style
        if style_key not in self._allowed_styles:
            style_key = "neutral"
        if style_key == "humorous":
            style_key = "friendly"
        
        context_sentence = self._context_sentence(scene)
        action_sentence = self._action_sentence(beat)
        emotion_sentence = self._emotion_sentence(scene, beat)
        visual_sentence = self._visual_sentence(beat)
        continuity_sentence = self._continuity_sentence(project, episode, beat)

        base_sentences = [
            self._style_opening(style_key, scene, beat),
            context_sentence,
            action_sentence,
            emotion_sentence,
        ]
        if retelling_density in {"full", "balanced"}:
            base_sentences.append(visual_sentence)
        if retelling_density == "full":
            base_sentences.append(continuity_sentence)
            base_sentences.append(self._style_closing(style_key, beat))
        elif retelling_density == "balanced":
            base_sentences.append(self._balanced_closing(style_key, beat))

        return self._join_sentences(base_sentences)

    def _style_opening(self, style: str, scene: Scene, beat: Beat) -> str:
        location = scene.location or beat.location or "khung cảnh này"
        if style == "mysterious":
            return (
                f"Lúc này, tại {location}, câu chuyện bắt đầu chậm lại như "
                "đang giấu một điều bất thường."
            )
        if style == "dramatic":
            return (
                f"Ngay trong khoảnh khắc ở {location}, tình thế được đẩy lên "
                "một nấc căng hơn."
            )
        if style == "friendly":
            return (
                f"Ở đoạn này, người xem theo chân nhân vật tại {location} "
                "để nắm rõ diễn biến tiếp theo."
            )
        if style == "fast-paced":
            return f"Tại {location}, diễn biến chuyển nhanh sang điểm chính."
        return f"Tại {location}, cảnh này tiếp tục triển khai mạch truyện."

    def _context_sentence(self, scene: Scene) -> str:
        characters = self._human_list(scene.characters, fallback="nhân vật chính")
        mood = scene.mood or "ổn định"
        scene_summary = self._clean_text(scene.summary or scene.title)
        return (
            f"{characters} đang ở trong cảnh '{scene.title}', với không khí "
            f"{mood}; chi tiết nền là {scene_summary}."
        )

    def _action_sentence(self, beat: Beat) -> str:
        action = self._clean_action(beat.action or beat.visual_description)
        story_function = self._story_function_words.get(
            beat.story_function,
            beat.story_function or "diễn biến",
        )
        return (
            f"Beat này giữ vai trò {story_function}: {action}. "
            "Nó được kể như một khoảnh khắc riêng, không gộp chung thành "
            "một câu tóm tắt qua loa."
        )

    def _emotion_sentence(self, scene: Scene, beat: Beat) -> str:
        emotion = self._emotion_words.get(beat.emotion, beat.emotion or "chú ý")
        characters = self._human_list(beat.characters or scene.characters)
        return (
            f"Cảm xúc chính là {emotion}, nên nhịp kể tập trung vào phản ứng "
            f"của {characters} trước điều đang xảy ra."
        )

    def _visual_sentence(self, beat: Beat) -> str:
        visual = self._clean_text(beat.visual_description)
        if not visual:
            visual = (
                f"góc máy {beat.shot_type or 'medium shot'} nhấn vào hành động "
                f"{self._clean_action(beat.action)}"
            )
        return (
            f"Về mặt hình ảnh, cảnh nên hiện lên qua {beat.shot_type or 'medium shot'}, "
            f"nhấn vào {visual}."
        )

    def _continuity_sentence(
        self, project: Project, episode: ReviewEpisode, beat: Beat
    ) -> str:
        source_labels = self._source_labels(project, episode, beat)
        continuity = ", ".join(beat.continuity_tags[:4]) or "mạch truyện hiện tại"
        return (
            f"Phần kể này vẫn bám theo {source_labels}, giữ các dấu mốc liên tục "
            f"như {continuity}, để người xem không bị hụt khỏi dòng sự kiện."
        )

    def _style_closing(self, style: str, beat: Beat) -> str:
        if style == "mysterious":
            return (
                "Vì vậy, đoạn kể nên khép lại bằng cảm giác còn điều gì đó "
                "đang chờ được hé lộ."
            )
        if style == "dramatic":
            return (
                "Điểm này cần được nhấn mạnh như một bước ngoặt nhỏ, khiến "
                "căng thẳng tiếp tục tăng lên."
            )
        if style == "friendly":
            return (
                "Cách kể nên rõ ràng, dễ nghe, để người xem theo được từng "
                "thay đổi của nhân vật."
            )
        if style == "fast-paced":
            return "Câu kể kết nhanh, gọn, rồi chuyển ngay sang beat tiếp theo."
        if beat.story_function == "cliffhanger":
            return "Đây là điểm giữ lại sự chờ đợi cho phần tiếp theo."
        return "Nhờ vậy, beat này nối mạch tự nhiên sang diễn biến kế tiếp."

    def _balanced_closing(self, style: str, beat: Beat) -> str:
        if style == "mysterious":
            return "Chi tiết này được giữ lại để tạo cảm giác nghi vấn cho cảnh."
        if style == "dramatic":
            return "Nó giúp nhịp truyện có thêm lực trước diễn biến kế tiếp."
        if style == "friendly":
            return "Câu kể nên mềm và rõ để người xem dễ theo dõi."
        if style == "fast-paced":
            return "Nhịp kể dứt khoát và chuyển nhanh sang beat sau."
        return "Beat này giữ mạch kể rõ ràng trước khi sang đoạn tiếp theo."

    def _source_labels(
        self, project: Project, episode: ReviewEpisode, beat: Beat
    ) -> str:
        chapter_ids = beat.source_refs or episode.source_chapter_ids
        chapter_titles = {
            chapter.chapter_id: chapter.title for chapter in project.source_chapters
        }
        labels = [
            f"{chapter_id} ({chapter_titles.get(chapter_id, 'source chapter')})"
            for chapter_id in chapter_ids
        ]
        return ", ".join(labels) if labels else "nguồn truyện gốc"

    def _find_beat_context(
        self, project: Project, beat_id: str
    ) -> tuple[ReviewEpisode, Scene, Beat]:
        for episode in project.review_episodes:
            for scene in episode.scenes:
                for beat in scene.beats:
                    if beat.beat_id == beat_id:
                        return episode, scene, beat
        raise LookupError(f"Beat not found: {beat_id}")

    def _find_scene_context(
        self, project: Project, scene_id: str
    ) -> tuple[ReviewEpisode, Scene]:
        for episode in project.review_episodes:
            for scene in episode.scenes:
                if scene.scene_id == scene_id:
                    return episode, scene
        raise LookupError(f"Scene not found: {scene_id}")

    def _find_episode(self, project: Project, episode_id: str) -> ReviewEpisode:
        for episode in project.review_episodes:
            if episode.episode_id == episode_id:
                return episode
        raise LookupError(f"ReviewEpisode not found: {episode_id}")

    def _human_list(self, values: list[str], fallback: str = "nhân vật") -> str:
        if not values:
            return fallback
        if len(values) == 1:
            return values[0]
        return ", ".join(values[:-1]) + " và " + values[-1]

    def _clean_action(self, value: str) -> str:
        cleaned = self._clean_text(value)
        cleaned = re.sub(r"^[a-z_ -]+:\s*focus on\s+", "", cleaned, flags=re.I)
        cleaned = re.sub(r"^[a-z_ -]+:\s*", "", cleaned, flags=re.I)
        return cleaned or "một hành động quan trọng trong beat"

    def _clean_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def _join_sentences(self, sentences: list[str]) -> str:
        return " ".join(sentence for sentence in sentences if sentence).strip()

    def _source_chapters_for_episode(
        self, project: Project, episode: ReviewEpisode
    ) -> list[SourceChapter]:
        chapters_by_id = {
            chapter.chapter_id: chapter for chapter in project.source_chapters
        }
        return [
            chapters_by_id[chapter_id]
            for chapter_id in episode.source_chapter_ids
            if chapter_id in chapters_by_id
        ]

    def _require_ai_gateway(self) -> AIGateway:
        if self.ai_gateway is None:
            raise ValueError("use_ai=True requires an ai_gateway.")
        return self.ai_gateway

    def _validate_style(self, narration_style: str) -> None:
        if narration_style not in self._allowed_styles:
            raise ValueError(
                f"Unknown narration_style '{narration_style}'. "
                f"Allowed: {sorted(self._allowed_styles)}"
            )

    def _validate_density(self, retelling_density: str) -> None:
        if retelling_density not in self._allowed_densities:
            raise ValueError(
                f"Unknown retelling_density '{retelling_density}'. "
                f"Allowed: {sorted(self._allowed_densities)}"
            )
