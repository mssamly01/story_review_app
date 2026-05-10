# PLAN.md — Kế hoạch triển khai chi tiết

## 1. Mục tiêu sản phẩm

Ứng dụng này dùng để chuyển tiểu thuyết, truyện chữ, truyện tranh hoặc nội dung truyện dài tập thành:

- Review text kể lại gần đầy đủ câu chuyện
- Scene breakdown
- Beat / panel-like units
- Image prompts cho từng beat
- Character bible
- Location/world bible
- Continuity notes
- Export dạng Markdown / JSON / CSV / TXT

Ứng dụng **không phải video editor**, **không phải app dựng phim**, và **không phải công cụ tóm tắt ngắn**.

Tư duy sản phẩm:

```text
Truyện gốc
→ Episode
→ Scene
→ Beat
→ Review text kể lại gần đầy đủ
→ Image prompt cho từng beat
```

---

## 2. Định nghĩa sản phẩm

Tên tạm thời:

- StoryReview Studio
- Novel2Review
- ReviewToon Generator
- PanelReview AI
- StoryBeat Studio

Mô tả ngắn:

> Một ứng dụng giúp người dùng biến truyện dài tập thành kịch bản review kiểu kể lại, được chia theo cấu trúc episode → scene → beat, kèm prompt ảnh minh họa nhất quán cho từng beat như quy trình sản xuất truyện tranh.

---

## 3. Input chính

Ứng dụng nhận:

- Text truyện gốc
- Chương tiểu thuyết
- Nội dung truyện tranh được mô tả lại
- Outline truyện
- Tóm tắt nhiều chương
- Ghi chú nhân vật / bối cảnh

---

## 4. Output chính

Ứng dụng xuất:

- Review script kể lại gần đầy đủ
- Danh sách episode
- Danh sách scene
- Danh sách beat/panel-like unit
- Prompt ảnh cho từng beat
- Character bible
- Location bible
- Continuity tags
- Export Markdown / JSON / CSV / TXT

---

## 5. Nguyên tắc sản phẩm

### 5.1. Không tóm tắt quá mức

Ứng dụng không sinh kiểu:

```text
Chương này nói về việc nam chính phát hiện bí mật gia đình.
```

Mà phải sinh kiểu:

```text
Sau khi trở về căn nhà cũ của gia đình, nam chính bắt đầu cảm thấy nơi này có điều gì đó không bình thường. Ngay trong đêm đầu tiên, anh nghe thấy tiếng động phát ra từ căn phòng bị khóa ở cuối hành lang. Ban đầu anh nghĩ đó chỉ là tiếng gió, nhưng khi cánh cửa tự rung lên, anh bắt đầu nhận ra mọi chuyện không đơn giản.
```

### 5.2. Cấu trúc giống sản xuất truyện tranh

Nội dung phải được chia thành:

```text
Series
 └── Arc
      └── Source Chapter
           └── Review Episode
                └── Scene
                     └── Beat
```

### 5.3. Beat là đơn vị cốt lõi

Mỗi beat tương đương một “panel kể chuyện”, gồm:

- Review text
- Nhân vật
- Địa điểm
- Hành động
- Cảm xúc
- Shot type
- Visual description
- Image prompt
- Continuity tags

### 5.4. Prompt ảnh phải nhất quán

Prompt không được sinh rời rạc. Nó phải dựa trên:

- Character bible
- Location bible
- World style
- Episode mood
- Beat action
- Camera/shot type

### 5.5. Tôn trọng bản quyền

Ứng dụng nên khuyến khích viết lại bằng lời mới, không sao chép nguyên văn dài từ nội dung gốc nếu người dùng không có quyền sử dụng.

---

## 6. MVP tổng thể

## MVP 1 — Project & Source Import

Mục tiêu:

- Tạo project truyện
- Nhập nội dung chương
- Lưu source chapter
- Quản lý danh sách chương

Tính năng:

- Create Project
- Add Source Chapter
- Edit Source Text
- Store metadata: title, chapter number, word count

Output:

```json
{
  "project_id": "project_001",
  "title": "Tên truyện",
  "source_chapters": [
    {
      "chapter_id": "ch_001",
      "title": "Chương 1",
      "raw_text": "...",
      "word_count": 3500
    }
  ]
}
```

---

## MVP 2 — Story Parser

Mục tiêu:

- Phân tích chương truyện
- Nhận diện nhân vật, địa điểm, sự kiện chính
- Chia truyện thành scene

Tính năng:

- Extract characters
- Extract locations
- Extract important events
- Split into scenes
- Detect mood and conflict

Output:

```json
{
  "chapter_id": "ch_001",
  "detected_characters": ["Lâm Vũ", "Ông nội"],
  "detected_locations": ["căn nhà cũ", "hành lang", "căn phòng khóa"],
  "scenes": [
    {
      "scene_id": "sc_001",
      "summary": "Lâm Vũ trở về căn nhà cũ.",
      "mood": "mysterious",
      "characters": ["Lâm Vũ"],
      "location": "căn nhà cũ"
    }
  ]
}
```

---

## MVP 3 — Character & Location Bible

Mục tiêu:

- Tạo hồ sơ nhân vật
- Tạo hồ sơ địa điểm
- Dùng lại trong các episode sau

Tính năng:

- Create/Edit Character
- Create/Edit Location
- Auto-suggest bible from source
- Store visual prompt base

Character example:

```json
{
  "character_id": "lam_vu",
  "name": "Lâm Vũ",
  "appearance": "young man, messy black hair, gray eyes, slim build",
  "default_outfit": "black jacket, white shirt",
  "personality": "calm, cautious, observant",
  "visual_prompt_base": "young man, messy black hair, gray eyes, slim build, black jacket, white shirt, webtoon style"
}
```

Location example:

```json
{
  "location_id": "old_house_hallway",
  "name": "Hành lang nhà cũ",
  "visual_prompt_base": "old narrow hallway, wooden floor, dusty walls, dim moonlight, eerie atmosphere",
  "mood": "dark, silent, mysterious"
}
```

---

## MVP 4 — Episode Planner

Mục tiêu:

- Gom một hoặc nhiều source chapter thành review episode
- Tạo episode outline
- Chia episode thành scene
- Chia scene thành beat

Tính năng:

- Create Review Episode
- Select source chapters
- Choose retelling density: Full / Balanced / Condensed
- Choose narration style: dramatic / mysterious / neutral / humorous / fast-paced
- Generate scene list
- Generate beat list

Output:

```json
{
  "episode_id": "ep_001",
  "title": "Căn nhà cũ của ông nội",
  "source_chapter_ids": ["ch_001"],
  "retelling_density": "full",
  "narration_style": "mysterious",
  "scenes": ["sc_001", "sc_002"],
  "estimated_beats": 48
}
```

---

## MVP 5 — Beat Rewriter

Mục tiêu:

- Viết lại từng beat thành review text tự nhiên
- Không copy nguyên văn dài
- Giữ mạch truyện gần đầy đủ

Tính năng:

- Generate review text per beat
- Rewrite selected beat
- Change tone
- Expand / shorten beat
- Add cliffhanger line

Beat example:

```json
{
  "beat_id": "b_001",
  "scene_id": "sc_001",
  "review_text": "Sau nhiều năm xa cách, Lâm Vũ cuối cùng cũng quay trở lại căn nhà cũ mà ông nội để lại cho mình.",
  "story_function": "opening",
  "characters": ["lam_vu"],
  "location": "old_house",
  "emotion": "lonely",
  "importance": "medium"
}
```

---

## MVP 6 — Prompt Builder

Mục tiêu:

- Tạo prompt ảnh minh họa cho từng beat
- Đảm bảo nhân vật, địa điểm, style nhất quán

Tính năng:

- Generate image prompt
- Generate negative prompt
- Regenerate prompt only
- Apply style preset
- Use character/location bible

Prompt structure:

```text
[art style] + [character base] + [location base] + [action] + [emotion] + [camera shot] + [lighting] + [composition]
```

Example:

```json
{
  "beat_id": "b_001",
  "image_prompt": "dark fantasy webtoon style, young man with messy black hair and gray eyes, wearing a black jacket and white shirt, standing in front of an old countryside house at dusk, lonely atmosphere, cinematic lighting, medium wide shot",
  "negative_prompt": "low quality, blurry, inconsistent face, wrong outfit, extra fingers, distorted anatomy, watermark, text"
}
```

---

## MVP 7 — Export

Mục tiêu:

- Xuất toàn bộ dữ liệu để người dùng dùng tiếp ở công cụ khác

Export formats:

- Markdown
- JSON
- CSV
- TXT

Markdown example:

```markdown
# Episode 1 — Căn nhà cũ của ông nội

## Scene 1 — Trở về

### Beat 1

Review text:
Sau nhiều năm xa cách, Lâm Vũ cuối cùng cũng quay trở lại căn nhà cũ mà ông nội để lại cho mình.

Image prompt:
dark fantasy webtoon style, young man standing in front of an old house at dusk...
```

CSV columns:

```text
episode_id,scene_id,beat_id,review_text,characters,location,emotion,shot_type,image_prompt,negative_prompt
```

---

## 7. Roadmap đề xuất

### Phase 1 — Core data model

Tạo các entity:

- Project
- SourceChapter
- ReviewEpisode
- Scene
- Beat
- Character
- Location
- StylePreset

Mục tiêu:

- Có thể lưu/load project JSON
- Có thể tạo dữ liệu mẫu thủ công

---

### Phase 2 — Manual editing UI

Tạo giao diện để:

- Nhập source text
- Xem chapter list
- Xem episode list
- Xem scene/beat list
- Sửa review text
- Sửa prompt ảnh

Mục tiêu:

- Dù chưa có AI vẫn quản lý được project

---

### Phase 3 — AI generation pipeline

Thêm pipeline:

```text
source chapter
→ parse scenes
→ generate episode plan
→ generate beats
→ rewrite review text
→ build image prompts
```

---

### Phase 4 — Consistency system

Thêm:

- Character bible
- Location bible
- Continuity tags
- Consistency checker

---

### Phase 5 — Export polish

Thêm:

- Markdown export
- JSON export
- CSV export
- TXT export
- Copy all prompts
- Copy all review text

---

## 8. Suggested first implementation task

Start with domain and JSON persistence only.

### Task 1

Create these files:

```text
app/domain/project.py
app/domain/source_chapter.py
app/domain/episode.py
app/domain/scene.py
app/domain/beat.py
app/domain/character.py
app/domain/location.py
app/domain/style_preset.py
app/services/project_service.py
app/services/export_service.py
```

### Task 2

Implement:

- Create project
- Add source chapter
- Add character
- Add location
- Add review episode
- Add scene
- Add beat
- Save to JSON
- Load from JSON
- Export episode to Markdown

### Task 3

Add tests:

```text
tests/test_project_service.py
tests/test_export_service.py
```

Definition of first milestone:

> Người dùng có thể tạo một project mẫu, thêm một episode có scene/beat, lưu JSON, load lại, và export Markdown chứa review_text + image_prompt.
