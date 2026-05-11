# Thêm chức năng Xóa cho tất cả danh sách — Hướng dẫn Vibe Code

> Thêm nút "Xóa" cho 5 danh sách: Chapters, Episodes, Beats, Characters, Locations.

---

## Tổng quan

| Tab | Danh sách | Widget hiện tại | Cần thêm |
|-----|-----------|----------------|----------|
| **Nguồn** (`SourceTab`) | Chapters | `chapter_list` (QListWidget) | Nút "Xóa chương" |
| **Kế hoạch tập** (`EpisodePlannerTab`) | Episodes | `episode_list` (QListWidget) | Nút "Xóa tập" |
| **Beat Studio** (`BeatStudioTab`) | Scenes | `scene_list` (QListWidget) | Nút "Xóa phân cảnh" |
| **Beat Studio** (`BeatStudioTab`) | Beats | `beat_table` (QTableWidget) | Nút "Xóa nhịp" |
| **Bible & Style** (`BibleStyleTab`) | Characters | `char_list` (QListWidget) | Nút "Xóa nhân vật" |
| **Bible & Style** (`BibleStyleTab`) | Locations | `loc_list` (QListWidget) | Nút "Xóa địa điểm" |

**Cách xóa dữ liệu**: Tất cả data nằm trong `Project` dataclass dưới dạng list:
- `project.source_chapters` → list[SourceChapter]
- `project.review_episodes` → list[ReviewEpisode]
- `episode.scenes` → list[Scene]
- `scene.beats` → list[Beat]
- `project.characters` → list[Character]
- `project.locations` → list[Location]

Xóa = filter list bỏ item có ID tương ứng + gọi `project.touch()`.

---

## 1. SourceTab — Xóa chương

File: `app/ui/source_tab.py`

### 1.1 Thêm nút vào `_build_ui()`

```python
# Sau self.btn_add = QPushButton("Thêm từ tệp"), thêm:
self.btn_delete_chapter = QPushButton("Xóa chương")
left_layout.addWidget(self.btn_delete_chapter)

# Connect:
self.btn_delete_chapter.clicked.connect(self._on_delete_chapter)
```

### 1.2 Thêm handler

```python
def _on_delete_chapter(self) -> None:
    """Xóa chương đang chọn khỏi project."""
    if not self.app_state.project or not self.app_state.selected_chapter_id:
        QMessageBox.warning(self, "Cảnh báo", "Hãy chọn chương cần xóa.")
        return

    chapter_id = self.app_state.selected_chapter_id
    # Tìm tên chương để hiển thị
    chapter_name = chapter_id
    for ch in self.app_state.project.source_chapters:
        if ch.chapter_id == chapter_id:
            chapter_name = ch.title
            break

    reply = QMessageBox.question(
        self, "Xác nhận xóa",
        f"Bạn có chắc muốn xóa chương '{chapter_name}'?\n"
        "Hành động này không thể hoàn tác.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return

    self.app_state.project.source_chapters = [
        ch for ch in self.app_state.project.source_chapters
        if ch.chapter_id != chapter_id
    ]
    self.app_state.project.touch()
    self.app_state.selected_chapter_id = None
    self._clear_editor()
    self.refresh_callback()
```

---

## 2. EpisodePlannerTab — Xóa tập truyện

File: `app/ui/episode_planner_tab.py`

### 2.1 Thêm nút vào `_build_ui()`

```python
# Trong right_layout (bên phải, dưới episode_list), thêm:
self.btn_delete_episode = QPushButton("Xóa tập")
right_layout.addWidget(self.btn_delete_episode)

# Connect:
self.btn_delete_episode.clicked.connect(self._on_delete_episode)
```

### 2.2 Thêm handler

```python
def _on_delete_episode(self) -> None:
    """Xóa tập truyện đang chọn khỏi project."""
    if not self.app_state.project or not self.app_state.selected_episode_id:
        QMessageBox.warning(self, "Cảnh báo", "Hãy chọn tập cần xóa.")
        return

    episode_id = self.app_state.selected_episode_id
    # Tìm tên episode
    episode_name = episode_id
    for ep in self.app_state.project.review_episodes:
        if ep.episode_id == episode_id:
            episode_name = ep.title
            break

    reply = QMessageBox.question(
        self, "Xác nhận xóa",
        f"Bạn có chắc muốn xóa tập '{episode_name}'?\n"
        "Tất cả scenes và beats trong tập này sẽ bị xóa.\n"
        "Hành động này không thể hoàn tác.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return

    self.app_state.project.review_episodes = [
        ep for ep in self.app_state.project.review_episodes
        if ep.episode_id != episode_id
    ]
    self.app_state.project.touch()
    self.app_state.selected_episode_id = None
    self.app_state.selected_scene_id = None
    self.app_state.selected_beat_id = None
    self.refresh_callback()
```

---

## 3. BeatStudioTab — Xóa phân cảnh + Xóa nhịp truyện

File: `app/ui/beat_studio_tab.py`

### 3.1 Thêm nút xóa Scene vào `_build_ui()`

```python
# Trong scene_layout (dưới scene_list), thêm:
self.btn_delete_scene = QPushButton("Xóa phân cảnh")
scene_layout.addWidget(self.btn_delete_scene)

# Connect:
self.btn_delete_scene.clicked.connect(self._on_delete_scene)
```

### 3.2 Thêm nút xóa Beat vào `_build_ui()`

```python
# Trong beat_layout (dưới beat_table), thêm:
self.btn_delete_beat = QPushButton("Xóa nhịp truyện")
beat_layout.addWidget(self.btn_delete_beat)

# Connect:
self.btn_delete_beat.clicked.connect(self._on_delete_beat)
```

### 3.3 Thêm handlers

```python
def _on_delete_scene(self) -> None:
    """Xóa phân cảnh đang chọn khỏi episode."""
    if (
        not self.app_state.project
        or not self.app_state.selected_episode_id
        or not self.app_state.selected_scene_id
    ):
        QMessageBox.warning(self, "Cảnh báo", "Hãy chọn phân cảnh cần xóa.")
        return

    scene_id = self.app_state.selected_scene_id

    reply = QMessageBox.question(
        self, "Xác nhận xóa",
        f"Bạn có chắc muốn xóa phân cảnh '{scene_id}'?\n"
        "Tất cả beats trong phân cảnh này sẽ bị xóa.\n"
        "Hành động này không thể hoàn tác.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return

    episode = self.generation_controller.find_episode(
        self.app_state.project, self.app_state.selected_episode_id
    )
    episode.scenes = [
        sc for sc in episode.scenes if sc.scene_id != scene_id
    ]
    self.app_state.project.touch()
    self.app_state.selected_scene_id = None
    self.app_state.selected_beat_id = None
    self.refresh_callback()

def _on_delete_beat(self) -> None:
    """Xóa nhịp truyện đang chọn khỏi scene."""
    if (
        not self.app_state.project
        or not self.app_state.selected_episode_id
        or not self.app_state.selected_scene_id
        or not self.app_state.selected_beat_id
    ):
        QMessageBox.warning(self, "Cảnh báo", "Hãy chọn nhịp truyện cần xóa.")
        return

    beat_id = self.app_state.selected_beat_id

    reply = QMessageBox.question(
        self, "Xác nhận xóa",
        f"Bạn có chắc muốn xóa nhịp truyện '{beat_id}'?\n"
        "Hành động này không thể hoàn tác.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return

    scene = self.generation_controller.find_scene(
        self.app_state.project,
        self.app_state.selected_episode_id,
        self.app_state.selected_scene_id,
    )
    scene.beats = [b for b in scene.beats if b.beat_id != beat_id]
    self.app_state.project.touch()
    self.app_state.selected_beat_id = None
    self._clear_editor()
    self.refresh_callback()
```

---

## 4. BibleStyleTab — Xóa nhân vật + Xóa địa điểm

File: `app/ui/bible_style_tab.py`

### 4.1 Thêm nút vào `_build_character_bible()`

```python
# Sau self.char_list, thêm nút xóa:
self.btn_delete_char = QPushButton("Xóa nhân vật")
layout.addWidget(self.btn_delete_char)
# Nếu muốn nút nằm dưới list, dùng left_layout thay vì layout trực tiếp.
# Hoặc đơn giản hơn: thêm vào cuối hàm, trước return widget

# Connect:
self.btn_delete_char.clicked.connect(self._on_delete_char)
```

**Cách tốt hơn** — refactor `_build_character_bible()` để có layout rõ ràng:

```python
def _build_character_bible(self) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)

    # Left: list + buttons
    left = QWidget()
    left_layout = QVBoxLayout(left)
    self.char_list = QListWidget()
    left_layout.addWidget(self.char_list)

    char_btn_layout = QHBoxLayout()
    self.btn_add_char = QPushButton("Thêm")
    self.btn_delete_char = QPushButton("Xóa")
    char_btn_layout.addWidget(self.btn_add_char)
    char_btn_layout.addWidget(self.btn_delete_char)
    left_layout.addLayout(char_btn_layout)
    layout.addWidget(left, 1)

    # Right: form (giữ nguyên)
    form = QWidget()
    form_layout = QGridLayout(form)
    self.char_name = QLineEdit()
    self.char_appearance = QPlainTextEdit()
    self.char_prompt_base = QPlainTextEdit()

    form_layout.addWidget(QLabel("Tên:"), 0, 0)
    form_layout.addWidget(self.char_name, 0, 1)
    form_layout.addWidget(QLabel("Ngoại hình:"), 1, 0)
    form_layout.addWidget(self.char_appearance, 1, 1)
    form_layout.addWidget(QLabel("Visual Prompt Base:"), 2, 0)
    form_layout.addWidget(self.char_prompt_base, 2, 1)

    layout.addWidget(form, 2)

    # Connect
    self.char_list.currentItemChanged.connect(self._on_char_select)
    self.btn_add_char.clicked.connect(self._on_add_char)
    self.btn_delete_char.clicked.connect(self._on_delete_char)

    return widget
```

### 4.2 Thêm nút vào `_build_location_bible()`

```python
def _build_location_bible(self) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)

    # Left: list + buttons
    left = QWidget()
    left_layout = QVBoxLayout(left)
    self.loc_list = QListWidget()
    left_layout.addWidget(self.loc_list)

    loc_btn_layout = QHBoxLayout()
    self.btn_add_loc = QPushButton("Thêm")
    self.btn_delete_loc = QPushButton("Xóa")
    loc_btn_layout.addWidget(self.btn_add_loc)
    loc_btn_layout.addWidget(self.btn_delete_loc)
    left_layout.addLayout(loc_btn_layout)
    layout.addWidget(left, 1)

    # Right: form (giữ nguyên)
    form = QWidget()
    form_layout = QGridLayout(form)
    self.loc_name = QLineEdit()
    self.loc_prompt_base = QPlainTextEdit()

    form_layout.addWidget(QLabel("Tên:"), 0, 0)
    form_layout.addWidget(self.loc_name, 0, 1)
    form_layout.addWidget(QLabel("Visual Prompt Base:"), 1, 0)
    form_layout.addWidget(self.loc_prompt_base, 1, 1)

    layout.addWidget(form, 2)

    # Connect
    self.loc_list.currentItemChanged.connect(self._on_loc_select)
    self.btn_add_loc.clicked.connect(self._on_add_loc)
    self.btn_delete_loc.clicked.connect(self._on_delete_loc)

    return widget
```

### 4.3 Thêm handlers cho Character

```python
def _on_char_select(self, current, previous) -> None:
    """Load thông tin nhân vật khi chọn từ list."""
    if not current or not self.app_state.project:
        return
    name = current.text()
    for char in self.app_state.project.characters:
        if char.name == name:
            self.char_name.setText(char.name)
            self.char_appearance.setPlainText(char.appearance)
            self.char_prompt_base.setPlainText(char.visual_prompt_base)
            break

def _on_add_char(self) -> None:
    """Thêm nhân vật mới."""
    if not self.app_state.project:
        QMessageBox.warning(self, "Cảnh báo", "Hãy mở dự án trước.")
        return
    from PySide6.QtWidgets import QInputDialog
    name, ok = QInputDialog.getText(self, "Thêm nhân vật", "Tên nhân vật:")
    if ok and name:
        try:
            self.bible_controller.add_character(
                self.app_state.project, name=name
            )
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

def _on_delete_char(self) -> None:
    """Xóa nhân vật đang chọn."""
    current = self.char_list.currentItem()
    if not current or not self.app_state.project:
        QMessageBox.warning(self, "Cảnh báo", "Hãy chọn nhân vật cần xóa.")
        return

    name = current.text()
    reply = QMessageBox.question(
        self, "Xác nhận xóa",
        f"Bạn có chắc muốn xóa nhân vật '{name}'?\n"
        "Hành động này không thể hoàn tác.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return

    self.app_state.project.characters = [
        c for c in self.app_state.project.characters if c.name != name
    ]
    self.app_state.project.touch()
    self.refresh_callback()
```

### 4.4 Thêm handlers cho Location

```python
def _on_loc_select(self, current, previous) -> None:
    """Load thông tin địa điểm khi chọn từ list."""
    if not current or not self.app_state.project:
        return
    name = current.text()
    for loc in self.app_state.project.locations:
        if loc.name == name:
            self.loc_name.setText(loc.name)
            self.loc_prompt_base.setPlainText(loc.visual_prompt_base)
            break

def _on_add_loc(self) -> None:
    """Thêm địa điểm mới."""
    if not self.app_state.project:
        QMessageBox.warning(self, "Cảnh báo", "Hãy mở dự án trước.")
        return
    from PySide6.QtWidgets import QInputDialog
    name, ok = QInputDialog.getText(self, "Thêm địa điểm", "Tên địa điểm:")
    if ok and name:
        try:
            self.bible_controller.add_location(
                self.app_state.project, name=name
            )
            self.refresh_callback()
        except Exception as exc:
            QMessageBox.critical(self, "Lỗi", str(exc))

def _on_delete_loc(self) -> None:
    """Xóa địa điểm đang chọn."""
    current = self.loc_list.currentItem()
    if not current or not self.app_state.project:
        QMessageBox.warning(self, "Cảnh báo", "Hãy chọn địa điểm cần xóa.")
        return

    name = current.text()
    reply = QMessageBox.question(
        self, "Xác nhận xóa",
        f"Bạn có chắc muốn xóa địa điểm '{name}'?\n"
        "Hành động này không thể hoàn tác.",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return

    self.app_state.project.locations = [
        loc for loc in self.app_state.project.locations if loc.name != name
    ]
    self.app_state.project.touch()
    self.refresh_callback()
```

---

## 5. Thêm import QMessageBox (nếu chưa có)

Kiểm tra từng file — nếu chưa import `QMessageBox`, thêm vào:

```python
from PySide6.QtWidgets import QMessageBox
```

Các file cần kiểm tra:
- `source_tab.py` — **đã có** QMessageBox
- `episode_planner_tab.py` — **đã có** QMessageBox
- `beat_studio_tab.py` — **đã có** QMessageBox
- `bible_style_tab.py` — **chưa có** → cần thêm `QMessageBox, QInputDialog` vào import

---

## 6. Verify controllers

Kiểm tra `BibleController` có method `add_character` và `add_location`:

```bash
grep -n "def add_character\|def add_location" app/controllers/bible_controller.py
```

Nếu không có, dùng cách trực tiếp (tạo domain object):

```python
from app.domain.character import Character
from app.infrastructure.id_generator import generate_id

# Thay self.bible_controller.add_character(...) bằng:
char = Character(character_id=generate_id("char"), name=name)
self.app_state.project.characters.append(char)
self.app_state.project.touch()
```

Tương tự cho Location:

```python
from app.domain.location import Location

loc = Location(location_id=generate_id("loc"), name=name)
self.app_state.project.locations.append(loc)
self.app_state.project.touch()
```

---

## 7. Thứ tự thực hiện

1. Thêm xóa **Character** + **Location** (BibleStyleTab) — đơn giản nhất
2. Thêm xóa **Chapter** (SourceTab)
3. Thêm xóa **Episode** (EpisodePlannerTab)
4. Thêm xóa **Scene** + **Beat** (BeatStudioTab)
5. Test: Tạo project → thêm data → xóa từng loại → verify project JSON

---

## Tóm tắt files cần sửa

| File | Thêm gì |
|------|---------|
| `app/ui/source_tab.py` | Nút "Xóa chương" + handler `_on_delete_chapter` |
| `app/ui/episode_planner_tab.py` | Nút "Xóa tập" + handler `_on_delete_episode` |
| `app/ui/beat_studio_tab.py` | Nút "Xóa phân cảnh" + "Xóa nhịp" + 2 handlers |
| `app/ui/bible_style_tab.py` | Nút "Xóa nhân vật" + "Xóa địa điểm" + refactor layout + 6 handlers |

Tổng: **4 files sửa**, không cần tạo file mới.
