# Tối ưu giao diện & quy trình — Hướng dẫn Vibe Code

> Sửa lỗi và tối ưu giao diện PySide6 + quy trình hoạt động của Story Review Studio.

---

## Mục lục

1. [Danh sách lỗi cần sửa](#1-danh-sách-lỗi-cần-sửa)
2. [Danh sách tối ưu giao diện](#2-danh-sách-tối-ưu-giao-diện)
3. [Code sửa lỗi chi tiết](#3-code-sửa-lỗi-chi-tiết)
4. [Code tối ưu chi tiết](#4-code-tối-ưu-chi-tiết)
5. [Cập nhật tests](#5-cập-nhật-tests)
6. [Thứ tự thực hiện](#6-thứ-tự-thực-hiện)

---

## 1. Danh sách lỗi cần sửa

| # | File | Lỗi | Mức độ |
|---|------|------|--------|
| 1 | `app/ui/main_window.py:37` | Window title có `"(Refactored)"` — cần bỏ | Thấp |
| 2 | `tests/test_pyside6_ui_smoke.py:17` | Test assert `project_panel` — attribute đã đổi thành `project_tab` | Test fail |
| 3 | `app/ui/episode_planner_tab.py:172` | Gọi `batch_controller.run_batch_onboarding()` — method không tồn tại trên `BatchWorkflowController` | Crash |
| 4 | `app/ui/bible_style_tab.py` | Thiếu buttons Thêm/Lưu/Xóa cho Character và Location — chỉ hiển thị list, không chỉnh sửa được | Chức năng thiếu |
| 5 | `app/ui/quality_repair_tab.py` | 5 buttons (Validate, Continuity, Readiness, Suggest, Repair) chưa connect signal — click không làm gì | Chức năng thiếu |
| 6 | `app/ui/export_tab.py` | Chỉ có profile-based export — thiếu format export trực tiếp (markdown, json, csv, review-txt, prompts-txt) | Chức năng thiếu |
| 7 | `app/ui/source_tab.py:153` | Gọi `add_chapter_from_file(title, num, path)` — sai signature (controller dùng keyword args) | Crash |
| 8 | `tests/test_ui_smoke.py` | Module list cũ — thiếu các tab mới (project_tab, source_tab, v.v.) | Test thiếu |

---

## 2. Danh sách tối ưu giao diện

| # | Tab | Tối ưu | Lý do |
|---|-----|--------|-------|
| A | `ProjectTab` | Thêm fields: genre, language, narration style, art style | User không edit được project metadata |
| B | `BeatStudioTab` | Thêm status bar hiển thị episode/scene đang chọn | User mất context khi chuyển tab |
| C | `EpisodePlannerTab` | Thêm nút "Full Pipeline" cho episode đã chọn | Phải chuyển tab nhiều lần |
| D | `MainWindow` | Thêm auto-save khi chuyển tab | Dễ mất dữ liệu |
| E | `ExportTab` | Thêm format selector dropdown ngoài profile | Linh hoạt hơn |

---

## 3. Code sửa lỗi chi tiết

### Lỗi 1: Window title

File: `app/ui/main_window.py`

```python
# Dòng 37 — Đổi:
self.setWindowTitle("Story Review Studio (Refactored)")
# Thành:
self.setWindowTitle("Story Review Studio")
```

---

### Lỗi 2: Smoke test reference

File: `tests/test_pyside6_ui_smoke.py`

```python
# Dòng 17 — Đổi:
self.assertIsNotNone(window.project_panel)
# Thành:
self.assertIsNotNone(window.project_tab)
```

---

### Lỗi 3: Batch onboarding method không tồn tại

File: `app/ui/episode_planner_tab.py`

`BatchWorkflowController` có method `plan_episodes_from_chapters()`, không phải `run_batch_onboarding()`.

```python
# Dòng 166-182 — Thay toàn bộ _on_batch():
def _on_batch(self) -> None:
    if not self.app_state.project:
        return

    selected_items = self.chapter_list.selectedItems()
    chapter_ids = [item.data(ITEM_ROLE) for item in selected_items]

    if not chapter_ids:
        # Nếu không chọn chapter nào → dùng tất cả
        chapter_ids = [
            ch.chapter_id for ch in self.app_state.project.source_chapters
        ]

    if not chapter_ids:
        QMessageBox.warning(self, "Cảnh báo", "Không có chương nào để lập kế hoạch.")
        return

    try:
        self.batch_controller.plan_episodes_from_chapters(
            self.app_state.project,
            chapter_ids=chapter_ids,
            tone=self._tone_map[self.tone_combo.currentText()],
            density=self._density_map[self.density_combo.currentText()],
            ai_mode=self.app_state.ai_mode,
            model=self.app_state.model,
        )
        QMessageBox.information(self, "Thông báo", "Đã lập kế hoạch hàng loạt.")
        self.refresh_callback()
    except Exception as exc:
        QMessageBox.critical(self, "Lỗi", str(exc))
```

---

### Lỗi 4: BibleStyleTab thiếu add/save/delete

File: `app/ui/bible_style_tab.py`

Thêm buttons vào `_build_character_bible()`:

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
    self.btn_del_char = QPushButton("Xóa")
    char_btn_layout.addWidget(self.btn_add_char)
    char_btn_layout.addWidget(self.btn_del_char)
    left_layout.addLayout(char_btn_layout)
    layout.addWidget(left, 1)

    # Right: form
    form = QWidget()
    form_layout = QGridLayout(form)
    self.char_name = QLineEdit()
    self.char_role = QLineEdit()
    self.char_appearance = QPlainTextEdit()
    self.char_appearance.setMaximumHeight(80)
    self.char_prompt_base = QPlainTextEdit()
    self.char_prompt_base.setMaximumHeight(80)

    form_layout.addWidget(QLabel("Tên:"), 0, 0)
    form_layout.addWidget(self.char_name, 0, 1)
    form_layout.addWidget(QLabel("Vai trò:"), 1, 0)
    form_layout.addWidget(self.char_role, 1, 1)
    form_layout.addWidget(QLabel("Ngoại hình:"), 2, 0)
    form_layout.addWidget(self.char_appearance, 2, 1)
    form_layout.addWidget(QLabel("Visual Prompt Base:"), 3, 0)
    form_layout.addWidget(self.char_prompt_base, 3, 1)

    self.btn_save_char = QPushButton("Lưu nhân vật")
    form_layout.addWidget(self.btn_save_char, 4, 0, 1, 2)

    layout.addWidget(form, 2)

    # Connect
    self.char_list.currentItemChanged.connect(self._on_char_select)
    self.btn_add_char.clicked.connect(self._on_add_char)
    self.btn_del_char.clicked.connect(self._on_del_char)
    self.btn_save_char.clicked.connect(self._on_save_char)

    return widget
```

Tương tự cho `_build_location_bible()`:

```python
def _build_location_bible(self) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    
    left = QWidget()
    left_layout = QVBoxLayout(left)
    self.loc_list = QListWidget()
    left_layout.addWidget(self.loc_list)
    
    loc_btn_layout = QHBoxLayout()
    self.btn_add_loc = QPushButton("Thêm")
    self.btn_del_loc = QPushButton("Xóa")
    loc_btn_layout.addWidget(self.btn_add_loc)
    loc_btn_layout.addWidget(self.btn_del_loc)
    left_layout.addLayout(loc_btn_layout)
    layout.addWidget(left, 1)

    form = QWidget()
    form_layout = QGridLayout(form)
    self.loc_name = QLineEdit()
    self.loc_mood = QLineEdit()
    self.loc_prompt_base = QPlainTextEdit()
    self.loc_prompt_base.setMaximumHeight(80)

    form_layout.addWidget(QLabel("Tên:"), 0, 0)
    form_layout.addWidget(self.loc_name, 0, 1)
    form_layout.addWidget(QLabel("Mood:"), 1, 0)
    form_layout.addWidget(self.loc_mood, 1, 1)
    form_layout.addWidget(QLabel("Visual Prompt Base:"), 2, 0)
    form_layout.addWidget(self.loc_prompt_base, 2, 1)

    self.btn_save_loc = QPushButton("Lưu địa điểm")
    form_layout.addWidget(self.btn_save_loc, 3, 0, 1, 2)

    layout.addWidget(form, 2)

    self.loc_list.currentItemChanged.connect(self._on_loc_select)
    self.btn_add_loc.clicked.connect(self._on_add_loc)
    self.btn_del_loc.clicked.connect(self._on_del_loc)
    self.btn_save_loc.clicked.connect(self._on_save_loc)

    return widget
```

Thêm handler methods cho `BibleStyleTab`:

```python
# ── Character handlers ──

def _on_char_select(self, current, previous) -> None:
    if not current or not self.app_state.project:
        return
    name = current.text()
    for char in self.app_state.project.characters:
        if char.name == name:
            self.char_name.setText(char.name)
            self.char_role.setText(getattr(char, "role", ""))
            self.char_appearance.setPlainText(getattr(char, "appearance", ""))
            self.char_prompt_base.setPlainText(getattr(char, "visual_prompt_base", ""))
            break

def _on_add_char(self) -> None:
    if not self.app_state.project:
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
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Lỗi", str(exc))

def _on_del_char(self) -> None:
    current = self.char_list.currentItem()
    if not current or not self.app_state.project:
        return
    name = current.text()
    self.app_state.project.characters = [
        c for c in self.app_state.project.characters if c.name != name
    ]
    self.app_state.project.touch()
    self.refresh_callback()

def _on_save_char(self) -> None:
    current = self.char_list.currentItem()
    if not current or not self.app_state.project:
        return
    name = current.text()
    for char in self.app_state.project.characters:
        if char.name == name:
            char.name = self.char_name.text()
            char.role = self.char_role.text() if hasattr(char, "role") else None
            char.appearance = self.char_appearance.toPlainText()
            char.visual_prompt_base = self.char_prompt_base.toPlainText()
            break
    self.app_state.project.touch()
    self.refresh_callback()

# ── Location handlers ──

def _on_loc_select(self, current, previous) -> None:
    if not current or not self.app_state.project:
        return
    name = current.text()
    for loc in self.app_state.project.locations:
        if loc.name == name:
            self.loc_name.setText(loc.name)
            self.loc_mood.setText(getattr(loc, "mood", ""))
            self.loc_prompt_base.setPlainText(getattr(loc, "visual_prompt_base", ""))
            break

def _on_add_loc(self) -> None:
    if not self.app_state.project:
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
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Lỗi", str(exc))

def _on_del_loc(self) -> None:
    current = self.loc_list.currentItem()
    if not current or not self.app_state.project:
        return
    name = current.text()
    self.app_state.project.locations = [
        loc for loc in self.app_state.project.locations if loc.name != name
    ]
    self.app_state.project.touch()
    self.refresh_callback()

def _on_save_loc(self) -> None:
    current = self.loc_list.currentItem()
    if not current or not self.app_state.project:
        return
    name = current.text()
    for loc in self.app_state.project.locations:
        if loc.name == name:
            loc.name = self.loc_name.text()
            loc.mood = self.loc_mood.text() if hasattr(loc, "mood") else None
            loc.visual_prompt_base = self.loc_prompt_base.toPlainText()
            break
    self.app_state.project.touch()
    self.refresh_callback()
```

---

### Lỗi 5: QualityRepairTab chưa connect buttons

File: `app/ui/quality_repair_tab.py`

Thêm signal connections và handler methods:

```python
# Thêm vào cuối _build_ui():
self.btn_validate.clicked.connect(self._on_validate)
self.btn_continuity.clicked.connect(self._on_continuity)
self.btn_readiness.clicked.connect(self._on_readiness)
self.btn_suggest.clicked.connect(self._on_suggest)
self.btn_repair.clicked.connect(self._on_repair)
```

Thêm handler methods:

```python
def _on_validate(self) -> None:
    if not self.app_state.project:
        return
    try:
        issues = self.validation_controller.validate_project(
            self.app_state.project
        )
        self._show_issues(issues)
    except Exception as exc:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Lỗi", str(exc))

def _on_continuity(self) -> None:
    if not self.app_state.project:
        return
    ep_id = self.ep_combo.currentData()
    if not ep_id:
        return
    try:
        issues = self.validation_controller.check_continuity(
            self.app_state.project, ep_id,
            ai_mode=self.app_state.ai_mode,
            model=self.app_state.model,
        )
        self._show_issues(issues)
    except Exception as exc:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Lỗi", str(exc))

def _on_readiness(self) -> None:
    if not self.app_state.project:
        return
    ep_id = self.ep_combo.currentData()
    if not ep_id:
        return
    try:
        report = self.validation_controller.production_readiness(
            self.app_state.project, ep_id,
        )
        self.results_table.setRowCount(1)
        self.results_table.setItem(0, 0, QTableWidgetItem("Readiness"))
        self.results_table.setItem(0, 1, QTableWidgetItem(
            "Sẵn sàng" if report.is_ready else "Chưa sẵn sàng"
        ))
        self.results_table.setItem(0, 2, QTableWidgetItem(str(report.score)))
    except Exception as exc:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Lỗi", str(exc))

def _on_suggest(self) -> None:
    if not self.app_state.project:
        return
    try:
        suggestions = self.repair_controller.suggest_repairs(
            self.app_state.project,
        )
        self._show_suggestions(suggestions)
    except Exception as exc:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Lỗi", str(exc))

def _on_repair(self) -> None:
    if not self.app_state.project:
        return
    try:
        applied = self.repair_controller.apply_safe_repairs(
            self.app_state.project,
        )
        self.results_table.setRowCount(1)
        self.results_table.setItem(0, 0, QTableWidgetItem("Repair"))
        self.results_table.setItem(0, 1, QTableWidgetItem("OK"))
        self.results_table.setItem(0, 2, QTableWidgetItem(
            f"Đã áp dụng {len(applied)} sửa lỗi rủi ro thấp."
        ))
        self.refresh_callback()
    except Exception as exc:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Lỗi", str(exc))

def _show_issues(self, issues) -> None:
    self.results_table.setRowCount(len(issues))
    for row, issue in enumerate(issues):
        self.results_table.setItem(row, 0, QTableWidgetItem(
            getattr(issue, "category", "unknown")
        ))
        self.results_table.setItem(row, 1, QTableWidgetItem(
            getattr(issue, "severity", "info")
        ))
        self.results_table.setItem(row, 2, QTableWidgetItem(
            getattr(issue, "message", str(issue))
        ))

def _show_suggestions(self, suggestions) -> None:
    self.results_table.setRowCount(len(suggestions))
    for row, s in enumerate(suggestions):
        self.results_table.setItem(row, 0, QTableWidgetItem(
            getattr(s, "category", "repair")
        ))
        self.results_table.setItem(row, 1, QTableWidgetItem(
            getattr(s, "risk_level", "unknown")
        ))
        self.results_table.setItem(row, 2, QTableWidgetItem(
            getattr(s, "description", str(s))
        ))
```

**Lưu ý**: Cần kiểm tra lại controller methods. Xem `ValidationController` và `RepairController`:

```python
# Kiểm tra bằng:
grep -n "def " app/controllers/validation_controller.py
grep -n "def " app/controllers/repair_controller.py
```

Điều chỉnh tên method cho khớp với controller thực tế.

---

### Lỗi 6: ExportTab thiếu format export trực tiếp

File: `app/ui/export_tab.py`

Thêm format selector + direct export button:

```python
def _build_ui(self) -> None:
    layout = QVBoxLayout(self)

    form_layout = QGridLayout()
    self.ep_combo = QComboBox()
    self.format_combo = QComboBox()
    self.format_combo.addItems([
        "markdown", "json", "csv", "review-txt", "prompts-txt"
    ])
    self.profile_combo = QComboBox()
    self.output_dir_label = QLabel("Chưa chọn thư mục xuất")
    self.btn_browse = QPushButton("Chọn thư mục...")

    form_layout.addWidget(QLabel("Tập truyện:"), 0, 0)
    form_layout.addWidget(self.ep_combo, 0, 1)
    form_layout.addWidget(QLabel("Định dạng:"), 1, 0)
    form_layout.addWidget(self.format_combo, 1, 1)
    form_layout.addWidget(QLabel("Profile:"), 2, 0)
    form_layout.addWidget(self.profile_combo, 2, 1)
    form_layout.addWidget(QLabel("Thư mục:"), 3, 0)
    form_layout.addWidget(self.output_dir_label, 3, 1)
    form_layout.addWidget(self.btn_browse, 3, 2)

    layout.addLayout(form_layout)

    btn_layout = QHBoxLayout()
    self.btn_export_format = QPushButton("Xuất theo định dạng")
    self.btn_export_profile = QPushButton("Xuất theo Profile")
    btn_layout.addWidget(self.btn_export_format)
    btn_layout.addWidget(self.btn_export_profile)
    layout.addLayout(btn_layout)

    layout.addWidget(QLabel("Các tệp đã tạo:"))
    self.created_files_list = QListWidget()
    layout.addWidget(self.created_files_list)

    # Connect signals
    self.btn_browse.clicked.connect(self._on_browse)
    self.btn_export_format.clicked.connect(self._on_export_format)
    self.btn_export_profile.clicked.connect(self._on_export_profile)
```

Thêm handler cho format export:

```python
def _on_export_format(self) -> None:
    """Xuất trực tiếp theo format (markdown, json, csv...)."""
    if not self.app_state.project:
        return

    ep_id = self.ep_combo.currentData()
    output_dir = self.output_dir_label.text()
    fmt = self.format_combo.currentText()

    if not ep_id or "Chưa chọn" in output_dir:
        QMessageBox.warning(self, "Cảnh báo", "Hãy chọn tập và thư mục xuất.")
        return

    try:
        path = self.export_controller.export_episode(
            self.app_state.project, ep_id, fmt, output_dir,
        )
        self.created_files_list.clear()
        self.created_files_list.addItem(str(path))
        QMessageBox.information(self, "Thông báo", f"Đã xuất: {path}")
    except Exception as exc:
        QMessageBox.critical(self, "Lỗi", str(exc))

def _on_export_profile(self) -> None:
    """Xuất theo export profile (đã tạo sẵn)."""
    # Giữ nguyên logic cũ của _on_export()
    ...
```

**Lưu ý**: Kiểm tra `ExportController.export_episode()` signature:

```python
grep -n "def export" app/controllers/export_controller.py
```

---

### Lỗi 7: SourceTab sai signature khi gọi add_chapter_from_file

File: `app/ui/source_tab.py`

```python
# Dòng 153 — Đổi:
self.project_controller.add_chapter_from_file(title, num, path)
# Thành:
self.project_controller.add_chapter_from_file(
    title=title,
    chapter_number=num,
    text_file=path,
)
```

Vì `ProjectController.add_chapter_from_file()` dùng keyword-only arguments:

```python
def add_chapter_from_file(
    self,
    *,           # ← keyword-only
    title: str,
    chapter_number: int,
    text_file: str | Path,
) -> SourceChapter:
```

---

## 4. Code tối ưu chi tiết

### Tối ưu A: ProjectTab thêm project metadata fields

File: `app/ui/project_tab.py`

Thêm vào `_build_ui()` trong info_group:

```python
# Thêm sau title_edit
self.genre_edit = QLineEdit()
self.language_combo = QComboBox()
self.language_combo.addItems(["vi", "en", "ja", "ko", "zh"])
self.narration_combo = QComboBox()
self.narration_combo.addItems([
    "mysterious", "dramatic", "neutral", "humorous", "fast-paced"
])
self.art_style_edit = QLineEdit("dark fantasy webtoon")

info_layout.addWidget(QLabel("Thể loại:"), 1, 0)
info_layout.addWidget(self.genre_edit, 1, 1)
info_layout.addWidget(QLabel("Ngôn ngữ:"), 2, 0)
info_layout.addWidget(self.language_combo, 2, 1)
info_layout.addWidget(QLabel("Phong cách kể:"), 3, 0)
info_layout.addWidget(self.narration_combo, 3, 1)
info_layout.addWidget(QLabel("Art Style:"), 4, 0)
info_layout.addWidget(self.art_style_edit, 4, 1)

# Đổi dòng button layout thành row 5
btn_layout = QGridLayout()
# ... buttons ở hàng mới
info_layout.addLayout(btn_layout, 5, 0, 1, 2)
info_layout.addWidget(self.path_label, 6, 0, 1, 2)
```

Cập nhật `refresh()`:

```python
def refresh(self) -> None:
    if self.app_state.project:
        p = self.app_state.project
        self.title_edit.setText(p.title)
        self.genre_edit.setText(p.genre)
        self.language_combo.setCurrentText(p.language)
        self.narration_combo.setCurrentText(p.default_narration_style)
        self.art_style_edit.setText(p.default_art_style)
        self.path_label.setText(str(self.app_state.project_path or ""))
    else:
        self.path_label.setText("Chưa mở dự án nào")

    self.ai_mode_combo.setCurrentText(self.app_state.ai_mode)
    self.model_edit.setText(self.app_state.model or "")
```

Cập nhật `_on_new()` để truyền metadata:

```python
def _on_new(self) -> None:
    from PySide6.QtWidgets import QMessageBox
    try:
        self.project_controller.create_project(
            self.title_edit.text(),
            genre=self.genre_edit.text(),
            language=self.language_combo.currentText(),
            default_narration_style=self.narration_combo.currentText(),
            default_art_style=self.art_style_edit.text(),
        )
        self.refresh_callback()
    except Exception as exc:
        QMessageBox.critical(self, "Lỗi", str(exc))
```

Thêm sync khi user sửa fields (connect signal + handler):

```python
# Connect:
self.genre_edit.textChanged.connect(self._sync_project_metadata)
self.language_combo.currentTextChanged.connect(self._sync_project_metadata)
self.narration_combo.currentTextChanged.connect(self._sync_project_metadata)
self.art_style_edit.textChanged.connect(self._sync_project_metadata)
self.title_edit.textChanged.connect(self._sync_project_metadata)

def _sync_project_metadata(self) -> None:
    if not self.app_state.project:
        return
    p = self.app_state.project
    p.title = self.title_edit.text()
    p.genre = self.genre_edit.text()
    p.language = self.language_combo.currentText()
    p.default_narration_style = self.narration_combo.currentText()
    p.default_art_style = self.art_style_edit.text()
    p.touch()
```

---

### Tối ưu B: BeatStudioTab — hiển thị context

File: `app/ui/beat_studio_tab.py`

Thêm context label ở đầu tab:

```python
# Thêm vào đầu _build_ui(), trước action_layout:
self.context_label = QLabel("Chưa chọn tập truyện — chọn tại tab 'Kế hoạch tập'")
self.context_label.setStyleSheet(
    "font-weight: bold; padding: 4px; background: #f0f0f0; border-radius: 4px;"
)
main_layout.addWidget(self.context_label)
```

Cập nhật `refresh()` để set context label:

```python
def refresh(self) -> None:
    # ... existing code ...
    if self.app_state.selected_episode_id and self.app_state.project:
        ep = self.generation_controller.find_episode(
            self.app_state.project, self.app_state.selected_episode_id
        )
        self.context_label.setText(
            f"Tập: {ep.title} | Scenes: {len(ep.scenes)}"
        )
    else:
        self.context_label.setText(
            "Chưa chọn tập truyện — chọn tại tab 'Kế hoạch tập'"
        )
```

---

### Tối ưu C: EpisodePlannerTab — thêm Full Pipeline button

File: `app/ui/episode_planner_tab.py`

```python
# Thêm sau btn_batch:
self.btn_pipeline = QPushButton("Chạy Full Pipeline cho tập đã chọn")
mid_layout.addWidget(self.btn_pipeline)

# Connect:
self.btn_pipeline.clicked.connect(self._on_full_pipeline)
```

Handler:

```python
def _on_full_pipeline(self) -> None:
    ep_id = self.app_state.selected_episode_id
    if not ep_id or not self.app_state.project:
        QMessageBox.warning(self, "Cảnh báo", "Hãy chọn một tập truyện.")
        return

    try:
        ep = self.generation_controller.find_episode(
            self.app_state.project, ep_id,
        )
        # Generate beats → rewrite → build prompts
        self.generation_controller.generate_beats(
            self.app_state.project, ep_id,
            ai_mode=self.app_state.ai_mode,
            model=self.app_state.model,
        )
        self.generation_controller.rewrite_review(
            self.app_state.project, ep_id,
            tone=self._tone_map[self.tone_combo.currentText()],
            ai_mode=self.app_state.ai_mode,
            model=self.app_state.model,
        )
        self.generation_controller.build_prompts(
            self.app_state.project, ep_id,
            ai_mode=self.app_state.ai_mode,
            model=self.app_state.model,
        )
        QMessageBox.information(
            self, "Thông báo",
            f"Full pipeline hoàn tất cho tập '{ep.title}'."
        )
        self.refresh_callback()
    except Exception as exc:
        QMessageBox.critical(self, "Lỗi", str(exc))
```

---

### Tối ưu D: MainWindow — auto-save khi chuyển tab

File: `app/ui/main_window.py`

```python
# Thêm vào _build_ui(), sau self.tabs:
self.tabs.currentChanged.connect(self._on_tab_changed)
```

```python
def _on_tab_changed(self, index: int) -> None:
    """Auto-save project khi chuyển tab (nếu project đang mở và có path)."""
    if self.app_state.project and self.app_state.project_path:
        try:
            self.project_controller.save_project()
        except Exception:
            pass  # Không block UI nếu auto-save fail
    # Refresh tab mới
    tab = self.tabs.widget(index)
    if hasattr(tab, "refresh"):
        tab.refresh()
```

---

## 5. Cập nhật tests

### File: `tests/test_ui_smoke.py`

Update module list cho phù hợp codebase mới:

```python
def test_ui_import_needs_no_credentials(self) -> None:
    with patch.dict(os.environ, {}, clear=True):
        modules = [
            "app.ui.main_window",
            "app.ui.app_state",
            "app.ui.project_tab",
            "app.ui.source_tab",
            "app.ui.episode_planner_tab",
            "app.ui.beat_studio_tab",
            "app.ui.bible_style_tab",
            "app.ui.quality_repair_tab",
            "app.ui.export_tab",
            "app.ui.app_runner",
            # Legacy panels vẫn giữ:
            "app.ui.project_panel",
            "app.ui.source_chapter_panel",
            "app.ui.episode_panel",
            "app.ui.beat_browser",
            "app.ui.beat_editor",
            "app.ui.export_panel",
        ]
        for module_name in modules:
            with self.subTest(module_name=module_name):
                module = importlib.import_module(module_name)
                self.assertIsNotNone(module)
```

---

## 6. Thứ tự thực hiện

Làm theo thứ tự này để không bị chồng chéo:

### Bước 1: Sửa lỗi crash (quan trọng nhất)

1. **Lỗi 7**: `source_tab.py` — sửa `add_chapter_from_file()` call
2. **Lỗi 3**: `episode_planner_tab.py` — sửa `run_batch_onboarding()`
3. **Lỗi 1**: `main_window.py` — bỏ `"(Refactored)"`

### Bước 2: Sửa chức năng thiếu

4. **Lỗi 5**: `quality_repair_tab.py` — connect 5 buttons
5. **Lỗi 4**: `bible_style_tab.py` — thêm CRUD buttons
6. **Lỗi 6**: `export_tab.py` — thêm format export

### Bước 3: Tối ưu trải nghiệm

7. **Tối ưu A**: `project_tab.py` — thêm metadata fields
8. **Tối ưu B**: `beat_studio_tab.py` — context label
9. **Tối ưu C**: `episode_planner_tab.py` — Full Pipeline button
10. **Tối ưu D**: `main_window.py` — auto-save

### Bước 4: Cập nhật tests

11. **Lỗi 2**: `test_pyside6_ui_smoke.py` — fix `project_panel`
12. **Lỗi 8**: `test_ui_smoke.py` — update module list

### Bước 5: Chạy verify

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -v
```

---

## Kiểm tra controllers trước khi implement

Chạy các lệnh sau để verify method signatures:

```bash
# Xem ExportController methods
grep -n "def " app/controllers/export_controller.py

# Xem ValidationController methods
grep -n "def " app/controllers/validation_controller.py

# Xem RepairController methods
grep -n "def " app/controllers/repair_controller.py

# Xem BibleController methods
grep -n "def " app/controllers/bible_controller.py

# Xem BatchWorkflowController methods
grep -n "def " app/controllers/batch_workflow_controller.py
```

Điều chỉnh tên method trong UI code cho khớp với kết quả.
