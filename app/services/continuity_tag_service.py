from __future__ import annotations
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.project import Project

class ContinuityTagService:
    # Suffix mappings for characters and locations
    SUFFIX_MAP = {
        "child": "dạng trẻ",
        "old": "dạng già",
        "injured": "bị thương",
        "bloody_robes": "áo dính máu",
        "divine": "dạng tiên nhân",
        "prime": "thời sung sức",
        "tearful": "rơi lệ",
        "angry": "tức giận",
        "determined": "quyết tâm",
        "morning_light": "ánh sáng ban mai",
        "night": "ban đêm",
        "golden_hour": "giờ vàng (chiều tà)",
        "sunset": "hoàng hôn",
        "sunrise": "bình minh",
        "bedroom": "phòng ngủ",
        "battlefield": "chiến trường",
    }

    # General tags mapping
    GENERAL_MAP = {
        "soul_burning_effect": "Hiệu ứng thiêu đốt nguyên thần",
        "fading_consciousness": "Ý thức tan biến",
        "wooden_door": "Cửa gỗ",
        "door_opening_light": "Ánh sáng khi cửa mở",
        "golden_scroll": "Bí kíp ánh vàng",
        "golden_runes_reflection": "Phản chiếu phù văn vàng",
        "clenched_fists": "Nắm đấm siết chặt",
        "intense_gaze": "Ánh mắt mãnh liệt",
        "ancient_soul_eyes": "Ánh mắt linh hồn cổ xưa",
        "tears_of_joy": "Nước mắt vui mừng",
        "natural_lighting": "Ánh sáng tự nhiên",
        "bloody_robes": "Áo dính máu",
        "burning_estate": "Dinh thự bốc cháy",
        "father_son_moment": "Khoảnh khắc cha con",
        "cliffhanger_frame": "Khung hình cliffhanger",
    }

    # Reverse maps for saving
    _REVERSE_SUFFIX_MAP = {v: k for k, v in SUFFIX_MAP.items()}
    _REVERSE_GENERAL_MAP = {v.lower(): k for k, v in GENERAL_MAP.items()}

    def to_display_name(self, project: Project, tag_id: str) -> str:
        if not tag_id:
            return ""

        # 1. Check general map
        if tag_id in self.GENERAL_MAP:
            return self.GENERAL_MAP[tag_id]

        # 2. Check character/location prefixed tags
        # Format: prefix_id_suffix (e.g., char_001_old)
        parts = tag_id.split("_")
        if len(parts) >= 3:
            prefix = parts[0]
            if prefix in ("char", "loc"):
                base_id = f"{parts[0]}_{parts[1]}"
                suffix = "_".join(parts[2:])
                
                # Resolve base name
                base_name = ""
                if prefix == "char":
                    for char in project.characters:
                        if char.character_id == base_id:
                            base_name = char.name
                            break
                else: # loc
                    for loc in project.locations:
                        if loc.location_id == base_id:
                            base_name = loc.name
                            break
                
                if not base_name:
                    base_name = base_id
                
                # Resolve suffix
                readable_suffix = self.SUFFIX_MAP.get(suffix, suffix.replace("_", " "))
                return f"{base_name} - {readable_suffix}"

        # 3. Fallback: snake_case to readable text
        return tag_id.replace("_", " ").strip().capitalize()

    def to_display_names(self, project: Project, tag_ids: list[str]) -> list[str]:
        return [self.to_display_name(project, tid) for tid in tag_ids if tid]

    def resolve_display_name(self, project: Project, display_name: str) -> str:
        display_name = display_name.strip()
        if not display_name:
            return ""

        # 1. Check general map reverse
        if display_name.lower() in self._REVERSE_GENERAL_MAP:
            return self._REVERSE_GENERAL_MAP[display_name.lower()]

        # 2. Check "Base Name - Suffix" format
        if " - " in display_name:
            base_part, _, suffix_part = display_name.partition(" - ")
            base_part = base_part.strip()
            suffix_part = suffix_part.strip()

            # Try to find character/location ID
            base_id = ""
            # Check characters
            for char in project.characters:
                if char.name.lower() == base_part.lower():
                    base_id = char.character_id
                    break
            # Check locations
            if not base_id:
                for loc in project.locations:
                    if loc.name.lower() == base_part.lower():
                        base_id = loc.location_id
                        break
            
            # If base not found but looks like an ID, use it
            if not base_id and (base_part.startswith("char_") or base_part.startswith("loc_")):
                base_id = base_part

            if base_id:
                suffix_id = self._REVERSE_SUFFIX_MAP.get(suffix_part, self._slugify(suffix_part))
                return f"{base_id}_{suffix_id}"

        # 3. Check if it's already an ID
        if "_" in display_name and " " not in display_name:
            return display_name

        # 4. Final fallback: slugify to create a new tag ID
        return self._slugify(display_name)

    def resolve_display_names(self, project: Project, display_names_str: str) -> list[str]:
        if not display_names_str:
            return []
        names = [n.strip() for n in display_names_str.split(",") if n.strip()]
        return [self.resolve_display_name(project, name) for name in names]

    def _slugify(self, text: str) -> str:
        # Simple slugify: lowercase, remove accents, replace space with underscore
        text = text.lower().strip()
        # Basic Vietnamese accent removal (could be more comprehensive)
        replacements = {
            'àáạảãâầấậẩẫăằắặẳẵ': 'a', 'èéẹẻẽêềếệểễ': 'e', 'ìíịỉĩ': 'i',
            'òóọỏõôồốộổỗơờớợởỡ': 'o', 'ùúụủũưừứựửữ': 'u', 'ỳýỵỷỹ': 'y', 'đ': 'd'
        }
        for k, v in replacements.items():
            for char in k:
                text = text.replace(char, v)
        text = re.sub(r'[^a-z0-9_]+', '_', text)
        return text.strip('_')
