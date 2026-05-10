# DESIGN.md — Thiết kế tổng thể app

## 1. Product concept

Ứng dụng là một **comic-style narrative production system**.

Nó giúp người dùng làm việc theo quy trình:

```text
Import story
→ Parse story
→ Build bible
→ Plan episode
→ Split scenes
→ Generate beats
→ Rewrite review text
→ Generate image prompts
→ Check continuity
→ Export
```

---

## 2. Core user workflow

### Step 1: Create Project

Người dùng tạo project cho một bộ truyện.

Project fields:

- Title
- Author/source note
- Genre
- Language
- Default narration style
- Default art style
- Retelling density

---

### Step 2: Import Source Chapters

Người dùng nhập từng chương truyện.

Each `SourceChapter` includes:

- Chapter title
- Chapter number
- Raw text
- Notes
- Import date

---

### Step 3: Parse Story

App phân tích chương để nhận diện:

- Characters
- Locations
- Objects
- Events
- Conflicts
- Emotional shifts
- Scene boundaries

---

### Step 4: Build Bible

App tạo hoặc cập nhật:

- Character Bible
- Location Bible
- World Style
- Object/prop notes

Người dùng có thể sửa để đảm bảo prompt ổn định.

---

### Step 5: Plan Episode

Người dùng chọn:

- Source chapters
- Density
- Tone
- Target beat count
- Cliffhanger preference

App tạo:

- Review episode
- Scene list
- Beat plan

---

### Step 6: Generate Beat Content

Mỗi beat được tạo gồm:

- Review text
- Visual description
- Shot type
- Emotion
- Prompt image
- Negative prompt
- Continuity tags

---

### Step 7: Edit & Polish

Người dùng chỉnh:

- Review text
- Beat order
- Beat importance
- Prompt image
- Character references
- Location references

---

### Step 8: Export

App xuất:

- Full episode review script
- Beat table
- Prompt list
- JSON project data
- CSV for spreadsheet workflow

---

## 3. Main screens

## 3.1. Project Dashboard

Purpose:

- Xem toàn bộ project
- Quản lý series, arc, chapter, episode

Sections:

- Project info
- Source chapters
- Review episodes
- Characters
- Locations
- Export shortcuts

---

## 3.2. Source Chapter Editor

Purpose:

- Nhập và chỉnh text gốc
- Xem metadata
- Chạy parse

UI elements:

- Chapter list sidebar
- Raw text editor
- Word count
- Parse button
- Parsed result preview

---

## 3.3. Episode Planner

Purpose:

- Tạo tập review từ source chapters

UI elements:

- Source chapter selector
- Density selector
- Tone selector
- Target beat count
- Generate episode outline button
- Scene list preview

---

## 3.4. Scene & Beat Outline

Purpose:

- Quản lý cấu trúc episode

UI elements:

- Scene list
- Beat list under each scene
- Drag reorder beat
- Add/delete beat
- Scene summary
- Beat status

Beat status:

- Planned
- Review text generated
- Prompt generated
- Needs review
- Approved

---

## 3.5. Beat Editor

Purpose:

- Sửa từng beat chi tiết

Fields:

- Review text
- Visual description
- Image prompt
- Negative prompt
- Characters
- Location
- Emotion
- Shot type
- Story function
- Continuity tags

Actions:

- Rewrite text
- Expand text
- Shorten text
- Make more dramatic
- Regenerate prompt
- Copy prompt
- Mark approved

---

## 3.6. Character Bible Panel

Purpose:

- Quản lý nhân vật dài tập

Fields:

- Name
- Alias
- Role
- Personality
- Appearance
- Default outfit
- Voice/narration notes
- Visual prompt base
- Relationship notes

---

## 3.7. Location Bible Panel

Purpose:

- Quản lý địa điểm và bối cảnh

Fields:

- Name
- Description
- Mood
- Lighting
- Visual prompt base
- Related scenes

---

## 3.8. Prompt Studio

Purpose:

- Kiểm tra và tinh chỉnh prompt ảnh

Features:

- Prompt preview
- Style preset selector
- Character/location prompt injection
- Negative prompt editor
- Batch copy prompts

---

## 3.9. Export Panel

Purpose:

- Xuất dữ liệu theo format mong muốn

Export options:

- Full Markdown episode
- JSON project
- CSV beat table
- TXT review script only
- TXT prompts only

---

## 4. Domain model overview

### Project

```json
{
  "project_id": "project_001",
  "title": "Story Title",
  "genre": "dark fantasy",
  "language": "vi",
  "default_narration_style": "mysterious",
  "default_art_style": "dark fantasy webtoon",
  "source_chapters": [],
  "review_episodes": [],
  "characters": [],
  "locations": [],
  "style_presets": []
}
```

---

### SourceChapter

```json
{
  "chapter_id": "ch_001",
  "title": "Chương 1",
  "chapter_number": 1,
  "raw_text": "...",
  "notes": "",
  "parsed_scene_ids": []
}
```

---

### ReviewEpisode

```json
{
  "episode_id": "ep_001",
  "title": "Căn nhà cũ",
  "source_chapter_ids": ["ch_001"],
  "tone": "mysterious",
  "density": "full",
  "scene_ids": ["sc_001", "sc_002"],
  "status": "draft"
}
```

---

### Scene

```json
{
  "scene_id": "sc_001",
  "episode_id": "ep_001",
  "title": "Trở về nhà cũ",
  "summary": "Lâm Vũ trở về căn nhà ông nội để lại.",
  "characters": ["lam_vu"],
  "location": "old_house",
  "mood": "lonely, mysterious",
  "beat_ids": ["b_001", "b_002"]
}
```

---

### Beat

```json
{
  "beat_id": "b_001",
  "scene_id": "sc_001",
  "order_index": 1,
  "source_refs": ["ch_001:p1-p3"],
  "story_function": "opening",
  "characters": ["lam_vu"],
  "location": "old_house",
  "action": "returns to old house",
  "emotion": "lonely",
  "shot_type": "wide shot",
  "review_text": "Sau nhiều năm xa cách, Lâm Vũ cuối cùng cũng quay trở lại căn nhà cũ mà ông nội để lại cho mình.",
  "visual_description": "Lâm Vũ đứng trước căn nhà cũ vào lúc chiều tối.",
  "image_prompt": "dark fantasy webtoon style, young man standing in front of an old countryside house at dusk, lonely mood, cinematic wide shot",
  "negative_prompt": "low quality, blurry, distorted anatomy, inconsistent face, watermark, text",
  "continuity_tags": ["lam_vu_black_jacket", "old_house", "dusk"]
}
```

---

## 5. Retelling density design

### Full

- Kể gần đầy đủ
- Nhiều beat
- Ít lược bỏ
- Phù hợp nội dung dài, nhiều tập

### Balanced

- Giữ cảnh chính
- Rút nhẹ cảnh phụ
- Phù hợp sản xuất nhanh

### Condensed

- Tập trung mạch chính
- Ít beat hơn
- Phù hợp recap ngắn

Default nên là **Full** hoặc **Balanced**, vì app không phải app summary.

---

## 6. Narration style design

### Neutral

Giọng kể rõ ràng, ít bình luận.

### Dramatic

Nhấn nhá mạnh, nhiều câu dẫn căng thẳng.

### Mysterious

Tập trung không khí bí ẩn, câu văn chậm và gợi tò mò.

### Humorous

Có bình luận nhẹ, gần kiểu reviewer thân thiện.

### Fast-paced

Câu ngắn, nhanh, hợp Shorts/TikTok.

---

## 7. Art style preset design

Each preset includes:

- Name
- Description
- Positive style prompt
- Negative prompt additions
- Lighting rules
- Character design rules
- Background detail level

Example:

```json
{
  "style_id": "dark_fantasy_webtoon",
  "name": "Dark Fantasy Webtoon",
  "positive_prompt": "dark fantasy webtoon style, cinematic lighting, detailed background, dramatic shadows, high quality illustration",
  "negative_prompt": "low quality, blurry, flat lighting, inconsistent style, watermark, text",
  "lighting": "moonlight, rim light, deep shadows",
  "background_detail": "high"
}
```

---

## 8. Data persistence

Project should be saved as JSON.

Recommended file structure:

```text
projects/
  story_title/
    project.json
    exports/
      episode_001.md
      episode_001.csv
      episode_001_prompts.txt
```

---

## 9. Final product direction

Ứng dụng nên được định vị là:

> Một hệ thống sản xuất nội dung review truyện dài tập theo tư duy truyện tranh, giúp chuyển truyện gốc thành các đoạn kể lại có cấu trúc, kèm prompt ảnh minh họa nhất quán cho từng beat.

Không nên định vị là:

- Summary tool
- Video editor
- Manga drawing app
- Generic AI writer

Câu mô tả chuẩn:

> Import truyện, chia thành episode/scene/beat, viết lại thành review narration, tạo image prompt theo từng beat, giữ nhất quán nhân vật và bối cảnh, rồi xuất thành script/prompt để dùng trong quy trình sản xuất nội dung.
