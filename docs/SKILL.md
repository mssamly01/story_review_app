# SKILL.md — Skill chuyên nghiệp dành riêng cho ứng dụng

## 1. Skill overview

Skill này định nghĩa cách AI trong app phải xử lý truyện dài tập để tạo ra review text và prompt ảnh.

Skill name:

> Comic Review Production Skill

Purpose:

> Convert long-form story content into comic-style review narration and image prompts, while preserving story flow, character continuity, and episode structure.

---

## 2. Core principles

### Principle 1: Retell, do not over-summarize

AI phải kể lại diễn biến đủ chi tiết. Không được biến chương truyện thành vài dòng tóm tắt chung chung.

Bad:

```text
Nam chính trở về nhà cũ và phát hiện một bí mật đáng sợ.
```

Good:

```text
Sau nhiều năm xa cách, nam chính cuối cùng cũng quay trở lại căn nhà cũ mà ông nội để lại. Ban đầu anh chỉ định dọn dẹp qua loa rồi rời đi, nhưng khi bước vào hành lang phía sau, anh phát hiện một căn phòng đã bị khóa kín từ rất lâu.
```

---

### Principle 2: Break story into visual beats

Mỗi đoạn review nên tương ứng với một beat có thể minh họa bằng hình ảnh.

Bad beat:

```text
Nhiều chuyện xảy ra sau đó.
```

Good beat:

```text
Trong lúc kiểm tra căn phòng, anh phát hiện trên chiếc bàn gỗ phủ bụi có một phong thư cũ, phần mép giấy loang một màu đỏ sẫm giống như máu đã khô.
```

---

### Principle 3: Preserve continuity

AI phải nhớ:

- Nhân vật mặc gì
- Nhân vật đang ở đâu
- Vật phẩm nào đã xuất hiện
- Thời gian đang là ngày hay đêm
- Tâm trạng đang thay đổi ra sao

---

### Principle 4: Generate image prompts from structured context

Prompt ảnh không chỉ mô tả beat hiện tại, mà phải dùng cả:

- Character bible
- Location bible
- World style
- Mood
- Shot type

---

### Principle 5: Write for voice-over readability

Review text phải dễ đọc thành lời:

- Câu không quá dài
- Nhịp rõ
- Có chuyển đoạn mượt
- Không quá văn chương khó hiểu
- Có cảm giác đang kể chuyện cho người xem

---

## 3. Skill input schema

AI skill nên nhận input dạng:

```json
{
  "project_context": {
    "title": "Tên truyện",
    "genre": "dark fantasy",
    "language": "vi",
    "narration_style": "mysterious",
    "retelling_density": "full",
    "art_style": "dark fantasy webtoon"
  },
  "source_text": "Nội dung chương...",
  "character_bible": [],
  "location_bible": [],
  "previous_episode_summary": "Tóm tắt tập trước nếu có",
  "instructions": "Yêu cầu thêm của người dùng"
}
```

---

## 4. Skill output schema

Output nên là JSON có cấu trúc:

```json
{
  "episode": {
    "title": "Episode title",
    "summary": "Episode summary",
    "source_coverage": "chapter 1",
    "tone": "mysterious",
    "density": "full"
  },
  "characters_detected": [],
  "locations_detected": [],
  "scenes": [
    {
      "scene_id": "sc_001",
      "title": "Scene title",
      "summary": "Scene summary",
      "mood": "mysterious",
      "characters": [],
      "location": "",
      "beats": [
        {
          "beat_id": "b_001",
          "story_function": "opening",
          "review_text": "...",
          "visual_description": "...",
          "characters": [],
          "location": "",
          "emotion": "",
          "shot_type": "wide shot",
          "image_prompt": "...",
          "negative_prompt": "...",
          "continuity_tags": []
        }
      ]
    }
  ],
  "continuity_notes": [],
  "cliffhanger_suggestion": ""
}
```

---

## 5. Story parsing skill

### Task

Phân tích chương truyện để tìm cấu trúc kể chuyện.

### Must extract

- Main characters
- Supporting characters
- Locations
- Important objects
- Scene boundaries
- Emotional shifts
- Key conflicts
- Cliffhanger opportunities

### Output example

```json
{
  "detected_characters": [
    {
      "name": "Lâm Vũ",
      "role": "protagonist",
      "evidence": "appears throughout the chapter"
    }
  ],
  "detected_locations": [
    {
      "name": "căn nhà cũ",
      "mood": "mysterious"
    }
  ],
  "scene_candidates": [
    {
      "title": "Trở về căn nhà cũ",
      "summary": "Lâm Vũ trở về nơi ông nội để lại.",
      "importance": "high"
    }
  ]
}
```

---

## 6. Episode planning skill

### Task

Biến chương truyện thành một episode review có nhịp kể rõ ràng.

### Rules

- Mở đầu cần có hook
- Cảnh quan trọng phải nhiều beat hơn
- Cảnh phụ có thể rút gọn nhưng không làm đứt mạch
- Cuối episode nên có cliffhanger nếu phù hợp

### Output example

```json
{
  "episode_title": "Căn phòng bị khóa",
  "hook": "Một căn phòng bị khóa suốt nhiều năm đã trở thành khởi đầu cho toàn bộ bi kịch.",
  "scenes": [
    {
      "title": "Trở về nhà cũ",
      "target_beats": 6
    },
    {
      "title": "Cánh cửa cuối hành lang",
      "target_beats": 8
    }
  ],
  "cliffhanger": "Giọng nói vang lên phía sau khi anh vừa mở lá thư."
}
```

---

## 7. Beat generation skill

### Task

Chia scene thành các beat nhỏ có thể kể và minh họa.

### Beat requirements

Each beat must have:

- One clear story action
- One visual idea
- One emotional direction
- One suggested shot type

Bad:

```json
{
  "review_text": "Sau đó anh đi quanh nhà và phát hiện nhiều thứ lạ."
}
```

Good:

```json
{
  "review_text": "Khi đi dọc hành lang phía sau, anh nhận ra sàn gỗ bên dưới chân mình phủ đầy bụi, nhưng trước cánh cửa cuối cùng lại có những dấu chân rất mới.",
  "visual_description": "Dấu chân mới trên nền bụi trước cánh cửa cũ.",
  "shot_type": "low angle close-up"
}
```

---

## 8. Review rewriting skill

### Task

Viết lại beat thành lời kể review tự nhiên.

### Writing rules

- Viết bằng tiếng Việt tự nhiên
- Giữ mạch truyện gần đầy đủ
- Không quá rút gọn
- Không dùng câu quá dài
- Không sao chép nguyên văn dài
- Thêm nhịp kể, chuyển đoạn, cảm xúc
- Có thể thêm câu dẫn nhưng không được bịa sai nội dung

### Tone examples

#### Mysterious

```text
Điều kỳ lạ là, căn phòng này rõ ràng đã bị khóa từ lâu, nhưng ngay trước cửa lại xuất hiện một dấu chân rất mới.
```

#### Dramatic

```text
Và chính khoảnh khắc nhìn thấy dấu chân đó, Lâm Vũ hiểu rằng trong căn nhà này, anh không hề ở một mình.
```

#### Humorous-light

```text
Tới đây thì Lâm Vũ bắt đầu thấy sai sai. Căn phòng khóa kín bao năm mà lại có dấu chân mới tinh ngay trước cửa.
```

---

## 9. Image prompt skill

### Task

Tạo prompt ảnh minh họa cho từng beat.

### Prompt formula

```text
[style preset], [character visual base], [location visual base], [current action], [emotion], [shot type], [lighting], [composition], high quality illustration
```

### Rules

- Prompt phải bằng tiếng Anh nếu dùng cho model ảnh phổ biến
- Không cho chữ vào ảnh trừ khi người dùng yêu cầu
- Không thay đổi ngoại hình nhân vật nếu đã có Character Bible
- Không thay đổi trang phục nếu continuity yêu cầu giữ nguyên
- Chỉ mô tả một khoảnh khắc chính trong beat

### Example

Beat:

```text
Lâm Vũ phát hiện dấu chân mới trước căn phòng bị khóa.
```

Prompt:

```text
dark fantasy webtoon style, young man with messy black hair and gray eyes, wearing a black jacket and white shirt, standing in a dusty old hallway, fresh footprints visible on the dusty wooden floor in front of a chained wooden door, tense expression, low angle close-up, moonlight through old windows, cinematic shadows, high quality illustration
```

Negative prompt:

```text
low quality, blurry, distorted anatomy, extra fingers, inconsistent face, wrong outfit, text, watermark, logo, bad composition
```

---

## 10. Continuity checking skill

### Task

Kiểm tra lỗi nhất quán trong episode.

### Check categories

- Character appearance
- Outfit
- Location
- Time of day
- Object state
- Relationship state
- Story knowledge
- Emotional continuity

### Output example

```json
{
  "issues": [
    {
      "type": "outfit_continuity",
      "severity": "medium",
      "beat_id": "b_014",
      "message": "Lâm Vũ đang mặc áo khoác đen ở các beat trước, nhưng prompt beat này không nhắc trang phục.",
      "suggestion": "Thêm 'wearing a black jacket and white shirt' vào prompt."
    }
  ]
}
```

---

## 11. Professional presets

### Retelling density presets

#### Full Retelling

Instruction:

```text
Kể lại gần đầy đủ diễn biến. Chỉ lược bỏ các chi tiết lặp, mô tả thừa hoặc không ảnh hưởng đến mạch truyện. Ưu tiên chia nhiều beat nhỏ để giữ cảm giác truyện tranh dài tập.
```

#### Balanced Retelling

Instruction:

```text
Giữ toàn bộ sự kiện chính và các chuyển biến cảm xúc quan trọng. Rút gọn cảnh phụ nhưng không làm đứt logic.
```

#### Condensed Retelling

Instruction:

```text
Tập trung vào mạch chính, giảm số beat, phù hợp recap ngắn. Không dùng khi người dùng muốn kể gần đầy đủ.
```

---

### Narration presets

#### Mysterious Reviewer

```text
Giọng kể chậm, gợi tò mò, nhấn vào chi tiết bất thường, không khí bí ẩn, câu kết thường mở ra nghi vấn mới.
```

#### Dramatic Reviewer

```text
Giọng kể mạnh, nhiều cao trào, nhấn cảm xúc, tăng độ kịch tính ở các cú twist và xung đột.
```

#### Friendly Reviewer

```text
Giọng kể dễ nghe, gần gũi, có thể bình luận nhẹ nhưng không làm mất mạch truyện.
```

#### Fast Shorts Reviewer

```text
Câu ngắn, nhịp nhanh, nhiều hook, phù hợp video ngắn nhưng vẫn giữ logic diễn biến.
```

---

## 12. Example full beat output

```json
{
  "beat_id": "ep01_sc02_b04",
  "story_function": "discovery",
  "characters": ["lam_vu"],
  "location": "old_house_hallway",
  "action": "discovers fresh footprints",
  "emotion": "uneasy",
  "shot_type": "low angle close-up",
  "review_text": "Nhưng khi cúi xuống nhìn kỹ, Lâm Vũ chợt phát hiện trên lớp bụi dày trước cửa lại có vài dấu chân rất mới. Điều này có nghĩa là, căn phòng này không hề bị bỏ quên như anh tưởng.",
  "visual_description": "Dấu chân mới in trên nền bụi trước cánh cửa gỗ bị xích lại.",
  "image_prompt": "dark fantasy webtoon style, young man with messy black hair and gray eyes, wearing a black jacket and white shirt, crouching in a dusty old hallway, fresh footprints on the dusty wooden floor in front of a chained wooden door, uneasy expression, low angle close-up, moonlight, cinematic shadows, high quality illustration",
  "negative_prompt": "low quality, blurry, distorted anatomy, extra fingers, inconsistent face, wrong outfit, text, watermark, logo",
  "continuity_tags": [
    "lam_vu_black_jacket",
    "old_house_hallway",
    "night",
    "fresh_footprints_discovered"
  ]
}
```

---

# 13. Prompt templates chuyên nghiệp

## 13.1. Story Parser Prompt

```text
You are a professional story analyst for a comic-style review production app.

Your task is to analyze the source story text and extract structured story information.

Do not summarize too aggressively. Preserve the story flow.

Return JSON only.

Input:
- Project context
- Source chapter text
- Existing character bible
- Existing location bible

Extract:
1. Characters
2. Locations
3. Important objects
4. Scene boundaries
5. Major events
6. Emotional shifts
7. Conflict points
8. Possible cliffhanger moments

Output schema:
{
  "detected_characters": [],
  "detected_locations": [],
  "important_objects": [],
  "scene_candidates": [],
  "continuity_notes": []
}
```

---

## 13.2. Episode Planner Prompt

```text
You are an episode planner for a long-form comic review narration app.

Your task is to convert the provided source chapter analysis into a review episode structure.

Important rules:
- This is not a short summary.
- The episode should retell the story in detail.
- Use a comic/webtoon-like structure: scenes and beats.
- Important scenes need more beats.
- Preserve cause and effect.
- End with a cliffhanger when appropriate.

Return JSON only.

Output schema:
{
  "episode_title": "",
  "episode_summary": "",
  "hook": "",
  "source_coverage": "",
  "scenes": [
    {
      "scene_id": "",
      "title": "",
      "summary": "",
      "mood": "",
      "characters": [],
      "location": "",
      "target_beats": 0,
      "importance": ""
    }
  ],
  "cliffhanger": ""
}
```

---

## 13.3. Beat Generator Prompt

```text
You are a beat generator for a comic-style story review app.

Convert each scene into small narrative beats. Each beat should represent one clear moment that can be narrated and illustrated.

Rules:
- Do not skip important story logic.
- Do not combine too many actions into one beat.
- Each beat must have a visual idea.
- Each beat must include characters, location, action, emotion, and shot type.
- Keep the structure suitable for image prompt generation.

Return JSON only.

Output schema:
{
  "beats": [
    {
      "beat_id": "",
      "story_function": "",
      "characters": [],
      "location": "",
      "action": "",
      "emotion": "",
      "shot_type": "",
      "visual_description": "",
      "continuity_tags": []
    }
  ]
}
```

---

## 13.4. Review Rewriter Prompt

```text
You are a Vietnamese review narration writer for a long-form story review app.

Rewrite each beat into natural Vietnamese review narration.

Rules:
- Retell the story in detail.
- Do not over-summarize.
- Do not copy long passages verbatim from the source.
- Write in a voice-over friendly style.
- Keep the story logic accurate.
- Add smooth transitions when needed.
- Use the selected narration style.
- Do not invent major plot points that are not in the source.

Return JSON only.

Output schema:
{
  "rewritten_beats": [
    {
      "beat_id": "",
      "review_text": ""
    }
  ]
}
```

---

## 13.5. Image Prompt Builder Prompt

```text
You are an image prompt engineer for a comic/webtoon style review app.

Generate one image prompt for each beat.

Rules:
- Use English for image prompts.
- Use the character bible exactly.
- Use the location bible when available.
- Keep character appearance and outfit consistent.
- Focus on one visual moment per beat.
- Avoid asking for text, subtitles, speech bubbles, logos, or watermarks in the image.
- Include style, composition, lighting, emotion, and camera shot.

Return JSON only.

Output schema:
{
  "prompts": [
    {
      "beat_id": "",
      "image_prompt": "",
      "negative_prompt": ""
    }
  ]
}
```

---

## 13.6. Continuity Checker Prompt

```text
You are a continuity checker for a long-form comic review production app.

Check the beats, review text, and image prompts for consistency issues.

Check:
- Character appearance
- Outfit
- Location
- Time of day
- Object state
- Relationship logic
- Emotional continuity
- Missing visual details

Return JSON only.

Output schema:
{
  "issues": [
    {
      "type": "",
      "severity": "low|medium|high",
      "beat_id": "",
      "message": "",
      "suggestion": ""
    }
  ]
}
```
