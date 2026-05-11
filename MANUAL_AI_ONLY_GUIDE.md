# Hướng dẫn Vibe Code — Chỉ dùng Manual AI
 
> **Mục tiêu**: Chuyển toàn bộ ứng dụng sang workflow Manual AI — user lấy prompt ra ngoài cho AI (ChatGPT/Claude/Gemini) xử lý, rồi dán JSON kết quả lại vào app qua cửa sổ dialog.
 
---
 
## Mục lục
 
1. [Tổng quan quy trình](#1-tổng-quan-quy-trình)
2. [Plan — Danh sách thay đổi](#2-plan--danh-sách-thay-đổi)
3. [Code — Bước 1: Tạo ManualAIController](#3-code--bước-1-tạo-manualaicontroller)
4. [Code — Bước 2: Tạo Dialog classes](#4-code--bước-2-tạo-dialog-classes)
5. [Code — Bước 3: Sửa MainWindow](#5-code--bước-3-sửa-mainwindow)
6. [Code — Bước 4: Sửa SourceTab](#6-code--bước-4-sửa-sourcetab)
7. [Code — Bước 5: Sửa EpisodePlannerTab](#7-code--bước-5-sửa-episodeplanertab)
8. [Code — Bước 6: Sửa BeatStudioTab](#8-code--bước-6-sửa-beatstudiotab)
9. [Code — Bước 7: Sửa ManualAIService._input_rewrite()](#9-code--bước-7-sửa-manualaiservice_input_rewrite)
10. [Code — Bước 8: Sửa ManualAIService._input_prompts()](#10-code--bước-8-sửa-manualaiservice_input_prompts)
11. [Code — Bước 9: Thêm nút xóa (tất cả danh sách)](#11-code--bước-9-thêm-nút-xóa)
12. [Prompt — 6 prompt templates có sẵn](#12-prompt--6-prompt-templates-có-sẵn)
13. [Verify — Kiểm tra sau khi implement](#13-verify--kiểm-tra-sau-khi-implement)
 
---
 
## 1. Tổng quan quy trình
 
### Quy trình Manual AI (user-in-the-loop)
 
```
Bước 0: Chuẩn bị
├── Tab "Dự án" → Tạo/Mở project
├── Tab "Nguồn" → Import chapter text từ file .txt
├── Tab "Bible / Style" → Thêm characters, locations, style presets
│
Bước 1: Parse Story
├── Tab "Nguồn" → Chọn chương → Click "Lấy Prompt Parse"
├── Dialog hiện prompt → Copy → Paste vào AI
├── AI trả JSON → Click "Dán kết quả Parse" → Paste JSON → Áp dụng
│
Bước 2: Plan Episode
├── Tab "Kế hoạch tập" → Chọn chương + tone + density
├── Click "Lấy Prompt Plan" → Copy → AI xử lý → "Dán kết quả Plan"
│
Bước 3: Generate Beats
├── Tab "Beat Studio" → Chọn step "generate-beats"
├── Click "Lấy Prompt" → Copy → AI xử lý → "Dán kết quả"
│
Bước 4: Rewrite Review
├── Tab "Beat Studio" → Chọn step "rewrite-review"
├── Click "Lấy Prompt" → Copy → AI xử lý → "Dán kết quả"
│
Bước 5: Build Image Prompts
├── Tab "Beat Studio" → Chọn step "build-prompts"
├── Click "Lấy Prompt" → Copy → AI xử lý → "Dán kết quả"
│
Bước 6: Quality Check → Tab "Chất lượng"
Bước 7: Export → Tab "Xuất bản"
```
 
### Kiến trúc (theo AGENTS.md Rule 4)
 
```
UI (Dialog) → ManualAIController → ManualAIService → prompt_template + input_data
                                                    ← import result → update Project
```
 
---
 
## 2. Plan — Danh sách thay đổi
 
### Files mới cần tạo (2 files)
 
| # | File | Mô tả |
|---|------|--------|
| 1 | `app/controllers/manual_ai_controller.py` | Controller cho Manual AI workflow |
| 2 | `app/ui/manual_ai_dialogs.py` | 2 dialog classes: PromptExportDialog + ResultImportDialog |
 
### Files cần sửa (5 files)
 
| # | File | Thay đổi |
|---|------|----------|
| 3 | `app/ui/main_window.py` | Thêm ManualAIController, truyền vào 3 tabs, fix window title |
| 4 | `app/ui/source_tab.py` | Thêm manual_ai_controller param, thêm 2 buttons Parse, thêm nút Xóa chương, bỏ nút Parse cũ |
| 5 | `app/ui/episode_planner_tab.py` | Thêm manual_ai_controller param, thêm 2 buttons Plan, thêm nút Xóa tập, bỏ nút Plan/Batch cũ |
| 6 | `app/ui/beat_studio_tab.py` | Thêm manual_ai_controller param, thêm dropdown + 2 buttons cho 3 steps, thêm nút Xóa scene/beat, bỏ 3 nút gen cũ |
| 7 | `app/services/manual_ai_service.py` | Sửa `_input_rewrite()` và `_input_prompts()` — gom theo scene thay vì per-beat |
 
### Thứ tự thực hiện
 
```
Bước 1 → Bước 2 → Bước 3 → Bước 4 → Bước 5 → Bước 6 → Bước 7 → Bước 8 → Bước 9 → Verify
```
 
---
 
## 3. Code — Bước 1: Tạo ManualAIController
 
Tạo file mới: `app/controllers/manual_ai_controller.py`
 
```python
"""Controller for Manual AI workflow (export prompt → external AI → import result)."""
 
from __future__ import annotations
 
from typing import Any
 
from app.domain.project import Project
from app.services.manual_ai_service import ManualAIService
from app.services.project_service import ProjectService
 
 
class ManualAIController:
    """UI calls this controller; controller delegates to ManualAIService."""
 
    def __init__(self, project_service: ProjectService | None = None) -> None:
        self.project_service = project_service or ProjectService()
        self.service = ManualAIService(self.project_service)
 
    def export_prompt(
        self,
        project: Project,
        step: str,
        *,
        chapter_id: str | None = None,
        episode_id: str | None = None,
        tone: str | None = None,
        density: str | None = None,
        style_preset_id: str | None = None,
    ) -> str:
        """Return clipboard-ready prompt text."""
        exported = self.service.export_prompt(
            project,
            step=step,
            chapter_id=chapter_id,
            episode_id=episode_id,
            tone=tone,
            density=density,
            style_preset_id=style_preset_id,
        )
        return self.service.format_prompt_for_clipboard(exported)
 
    def import_result(
        self,
        project: Project,
        step: str,
        result_data: dict[str, Any],
        *,
        chapter_id: str | None = None,
        episode_id: str | None = None,
        tone: str | None = None,
        density: str | None = None,
        style_preset_id: str | None = None,
    ) -> str:
        """Apply AI result to project. Returns summary message."""
        return self.service.import_result(
            project,
            step=step,
            result_data=result_data,
            chapter_id=chapter_id,
            episode_id=episode_id,
            tone=tone,
            density=density,
            style_preset_id=style_preset_id,
        )
```
 
---
 
## 4. Code — Bước 2: Tạo Dialog classes
 
Tạo file mới: `app/ui/manual_ai_dialogs.py`
 
```python
"""Dialog windows for Manual AI workflow.
 
PromptExportDialog — shows prompt text, user copies to external AI.
ResultImportDialog — user pastes JSON result from external AI.
"""
 
from __future__ import annotations
 
import json
import re
 
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)
from PySide6.QtGui import QGuiApplication
 
 
class PromptExportDialog(QDialog):
    """Read-only dialog showing prompt text with a Copy button."""
 
    def __init__(
        self,
        prompt_text: str,
        step_name: str = "",
        parent: object = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Lấy Prompt — {step_name}")
        self.resize(850, 600)
        self.prompt_text = prompt_text
        self._build_ui()
 
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
 
        layout.addWidget(QLabel(
            "Copy toàn bộ nội dung bên dưới → paste vào ChatGPT / Claude / Gemini.\n"
            "AI sẽ trả về JSON. Sau đó dùng nút 'Dán kết quả' để import."
        ))
 
        self.text_view = QPlainTextEdit()
        self.text_view.setPlainText(self.prompt_text)
        self.text_view.setReadOnly(True)
        layout.addWidget(self.text_view)
 
        btn_layout = QHBoxLayout()
        self.btn_copy = QPushButton("Copy vào Clipboard")
        self.btn_close = QPushButton("Đóng")
        btn_layout.addWidget(self.btn_copy)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_close)
        layout.addLayout(btn_layout)
 
        self.btn_copy.clicked.connect(self._on_copy)
        self.btn_close.clicked.connect(self.accept)
 
    def _on_copy(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.prompt_text)
        self.btn_copy.setText("Đã copy!")
 
 
class ResultImportDialog(QDialog):
    """Dialog where user pastes JSON result from external AI."""
 
    def __init__(
        self,
        step_name: str = "",
        parent: object = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Dán kết quả AI — {step_name}")
        self.resize(850, 600)
        self.result_data: dict | None = None
        self._build_ui()
 
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
 
        layout.addWidget(QLabel(
            "Paste JSON kết quả từ AI vào ô bên dưới.\n"
            "Hỗ trợ JSON thuần hoặc JSON trong markdown code block (```json ... ```)."
        ))
 
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText(
            'Paste JSON tại đây...\n{\n  "scenes": [...]\n}'
        )
        layout.addWidget(self.text_edit)
 
        btn_layout = QHBoxLayout()
        self.btn_paste = QPushButton("Paste từ Clipboard")
        self.btn_apply = QPushButton("Áp dụng kết quả")
        self.btn_cancel = QPushButton("Hủy")
        btn_layout.addWidget(self.btn_paste)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
 
        self.btn_paste.clicked.connect(self._on_paste)
        self.btn_apply.clicked.connect(self._on_apply)
        self.btn_cancel.clicked.connect(self.reject)
 
    def _on_paste(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            text = clipboard.text()
            if text:
                self.text_edit.setPlainText(text)
 
    def _on_apply(self) -> None:
        raw = self.text_edit.toPlainText().strip()
        if not raw:
            QMessageBox.warning(self, "Cảnh báo", "Chưa có dữ liệu JSON.")
            return
 
        cleaned = self._strip_markdown_code_block(raw)
        try:
            self.result_data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            QMessageBox.critical(
                self, "Lỗi JSON", f"Không thể parse JSON:\n{exc}",
            )
            return
 
        self.accept()
 
    @staticmethod
    def _strip_markdown_code_block(text: str) -> str:
        """Remove ```json ... ``` wrapper if present."""
        match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?\s*```",
            text,
            re.DOTALL,
        )
        if match:
            return match.group(1).strip()
        return text
```
 
---
 
## 5. Code — Bước 3: Sửa MainWindow
 
File: `app/ui/main_window.py`
 
### 3.1 Thêm import
 
```python
# Thêm dòng này sau dòng import BatchWorkflowController:
from app.controllers.manual_ai_controller import ManualAIController
```
 
### 3.2 Fix window title
 
```python
# Đổi:
self.setWindowTitle("Story Review Studio (Refactored)")
# Thành:
self.setWindowTitle("Story Review Studio")
```
 
### 3.3 Tạo controller
 
```python
# Thêm sau dòng self.batch_controller = ...:
self.manual_ai_controller = ManualAIController(ps)
```
 
### 3.4 Truyền controller vào 3 tabs
 
```python
# SourceTab — thêm self.manual_ai_controller:
self.source_tab = SourceTab(
    self.app_state, self.project_controller, self.generation_controller,
    self.manual_ai_controller, self.refresh_all_tabs
)
 
# EpisodePlannerTab — thêm self.manual_ai_controller:
self.planner_tab = EpisodePlannerTab(
    self.app_state, self.project_controller, self.generation_controller,
    self.batch_controller, self.manual_ai_controller, self.refresh_all_tabs
)
 
# BeatStudioTab — thêm self.manual_ai_controller:
self.studio_tab = BeatStudioTab(
    self.app_state, self.generation_controller, self.manual_ai_controller,
    self.refresh_all_tabs
)
```
 
---
 
## 6. Code — Bước 4: Sửa SourceTab
 
File: `app/ui/source_tab.py`
 
### 4.1 Thêm import + param
 
```python
# Trong TYPE_CHECKING block, thêm:
from app.controllers.manual_ai_controller import ManualAIController
 
# Sửa __init__ thêm param:
def __init__(
    self,
    app_state: AppState,
    project_controller: ProjectController,
    generation_controller: GenerationController,
    manual_ai_controller: ManualAIController,   # ← THÊM
    refresh_callback: callable,
    parent: QWidget | None = None,
) -> None:
    ...
    self.manual_ai_controller = manual_ai_controller  # ← THÊM
```
 
### 4.2 Sửa _build_ui — bỏ nút Parse cũ, thêm Manual AI buttons + nút Xóa
 
```python
# BỎ dòng cũ:
self.btn_parse = QPushButton("Phân tích truyện (Parse)")
# BỎ signal connect cũ:
self.btn_parse.clicked.connect(self._on_parse)
 
# THÊM nút Xóa bên trái (cạnh nút "Thêm từ tệp"):
btn_list_layout = QHBoxLayout()
self.btn_add = QPushButton("Thêm từ tệp")
self.btn_delete_chapter = QPushButton("Xóa chương")
btn_list_layout.addWidget(self.btn_add)
btn_list_layout.addWidget(self.btn_delete_chapter)
left_layout.addLayout(btn_list_layout)
 
# THÊM Manual AI buttons bên phải (thay thế nút Parse):
ai_layout = QHBoxLayout()
ai_layout.addWidget(QLabel("Manual AI:"))
self.btn_prompt_parse = QPushButton("Lấy Prompt Parse")
self.btn_import_parse = QPushButton("Dán kết quả Parse")
ai_layout.addWidget(self.btn_prompt_parse)
ai_layout.addWidget(self.btn_import_parse)
right_layout.addLayout(ai_layout)
 
# Connect signals:
self.btn_delete_chapter.clicked.connect(self._on_delete_chapter)
self.btn_prompt_parse.clicked.connect(self._on_prompt_parse)
self.btn_import_parse.clicked.connect(self._on_import_parse)
```
 
### 4.3 Thêm handlers — bỏ _on_parse cũ
 
```python
# BỎ method _on_parse() cũ. THÊM 3 methods mới:
 
def _on_delete_chapter(self) -> None:
    if not self.app_state.project or not self.app_state.selected_chapter_id:
        return
    reply = QMessageBox.question(
        self, "Xác nhận", "Bạn có chắc muốn xóa chương này?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return
    cid = self.app_state.selected_chapter_id
    self.app_state.project.source_chapters = [
        ch for ch in self.app_state.project.source_chapters
        if ch.chapter_id != cid
    ]
    self.app_state.selected_chapter_id = None
    self.app_state.project.touch()
    self.refresh_callback()
 
def _on_prompt_parse(self) -> None:
    if not self.app_state.project or not self.app_state.selected_chapter_id:
        QMessageBox.warning(self, "Cảnh báo", "Hãy chọn một chương trước.")
        return
    try:
        from app.ui.manual_ai_dialogs import PromptExportDialog
        prompt_text = self.manual_ai_controller.export_prompt(
            self.app_state.project,
            "parse-story",
            chapter_id=self.app_state.selected_chapter_id,
        )
        dialog = PromptExportDialog(prompt_text, "Parse Story", self)
        dialog.exec()
    except Exception as exc:
        QMessageBox.critical(self, "Lỗi", str(exc))
 
def _on_import_parse(self) -> None:
    if not self.app_state.project or not self.app_state.selected_chapter_id:
        QMessageBox.warning(self, "Cảnh báo", "Hãy chọn một chương trước.")
        return
    try:
        from app.ui.manual_ai_dialogs import ResultImportDialog
        dialog = ResultImportDialog("Parse Story", self)
        if dialog.exec() and dialog.result_data is not None:
            summary = self.manual_ai_controller.import_result(
                self.app_state.project,
                "parse-story",
                dialog.result_data,
                chapter_id=self.app_state.selected_chapter_id,
            )
            QMessageBox.information(self, "Thành công", summary)
            self.refresh_callback()
    except Exception as exc:
        QMessageBox.critical(self, "Lỗi", str(exc))
```
 
---
 
## 7. Code — Bước 5: Sửa EpisodePlannerTab
 
File: `app/ui/episode_planner_tab.py`
 
### 5.1 Thêm import + param
 
```python
# Trong TYPE_CHECKING block, thêm:
from app.controllers.manual_ai_controller import ManualAIController
 
# Sửa __init__ thêm param (sau batch_controller):
def __init__(
    self,
    app_state: AppState,
    project_controller: ProjectController,
    generation_controller: GenerationController,
    batch_controller: BatchWorkflowController,
    manual_ai_controller: ManualAIController,   # ← THÊM
    refresh_callback: callable,
    parent: QWidget | None = None,
) -> None:
    ...
    self.manual_ai_controller = manual_ai_controller  # ← THÊM
```
 
### 5.2 Sửa _build_ui — bỏ nút Plan/Batch cũ, thêm Manual AI + Xóa
 
```python
# BỎ:
self.btn_plan = QPushButton("Lập kế hoạch tập")
self.btn_batch = QPushButton("Lập kế hoạch hàng loạt")
# BỎ signal connects:
self.btn_plan.clicked.connect(self._on_plan)
self.btn_batch.clicked.connect(self._on_batch)
 
# THÊM Manual AI buttons (ở mid_layout, chỗ cũ của btn_plan/btn_batch):
mid_layout.addWidget(QLabel("── Manual AI ──"))
self.btn_prompt_plan = QPushButton("Lấy Prompt Plan Episode")
self.btn_import_plan = QPushButton("Dán kết quả Plan")
mid_layout.addWidget(self.btn_prompt_plan)
mid_layout.addWidget(self.btn_import_plan)
 
# THÊM nút Xóa ở cột phải (dưới episode_list):
self.btn_delete_episode = QPushButton("Xóa tập")
right_layout.addWidget(self.btn_delete_episode)
 
# Connect signals:
self.btn_prompt_plan.clicked.connect(self._on_prompt_plan)
self.btn_import_plan.clicked.connect(self._on_import_plan)
self.btn_delete_episode.clicked.connect(self._on_delete_episode)
```
 
### 5.3 Thêm handlers — bỏ _on_plan/_on_batch cũ
 
```python
# BỎ _on_plan() và _on_batch(). THÊM:
 
def _selected_chapter_id(self) -> str | None:
    selected_items = self.chapter_list.selectedItems()
    if not selected_items:
        return None
    return selected_items[0].data(ITEM_ROLE)
 
def _current_tone(self) -> str:
    return self._tone_map.get(self.tone_combo.currentText(), "mysterious")
 
def _current_density(self) -> str:
    return self._density_map.get(self.density_combo.currentText(), "full")
 
def _on_prompt_plan(self) -> None:
    if not self.app_state.project:
        QMessageBox.warning(self, "Cảnh báo", "Hãy tạo hoặc mở dự án trước.")
        return
    chapter_id = self._selected_chapter_id()
    if not chapter_id:
        QMessageBox.warning(self, "Cảnh báo", "Hãy chọn ít nhất một chương.")
        return
    try:
        from app.ui.manual_ai_dialogs import PromptExportDialog
        prompt_text = self.manual_ai_controller.export_prompt(
            self.app_state.project,
            "plan-episode",
            chapter_id=chapter_id,
            tone=self._current_tone(),
            density=self._current_density(),
        )
        dialog = PromptExportDialog(prompt_text, "Plan Episode", self)
        dialog.exec()
    except Exception as exc:
        QMessageBox.critical(self, "Lỗi", str(exc))
 
def _on_import_plan(self) -> None:
    if not self.app_state.project:
        QMessageBox.warning(self, "Cảnh báo", "Hãy tạo hoặc mở dự án trước.")
        return
    chapter_id = self._selected_chapter_id()
    if not chapter_id:
        QMessageBox.warning(self, "Cảnh báo", "Hãy chọn ít nhất một chương.")
        return
    try:
        from app.ui.manual_ai_dialogs import ResultImportDialog
        dialog = ResultImportDialog("Plan Episode", self)
        if dialog.exec() and dialog.result_data is not None:
            summary = self.manual_ai_controller.import_result(
                self.app_state.project,
                "plan-episode",
                dialog.result_data,
                chapter_id=chapter_id,
                tone=self._current_tone(),
                density=self._current_density(),
            )
            QMessageBox.information(self, "Thành công", summary)
            self.refresh_callback()
    except Exception as exc:
        QMessageBox.critical(self, "Lỗi", str(exc))
 
def _on_delete_episode(self) -> None:
    if not self.app_state.project or not self.app_state.selected_episode_id:
        return
    reply = QMessageBox.question(
        self, "Xác nhận", "Bạn có chắc muốn xóa tập này?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return
    eid = self.app_state.selected_episode_id
    self.app_state.project.review_episodes = [
        ep for ep in self.app_state.project.review_episodes
        if ep.episode_id != eid
    ]
    self.app_state.selected_episode_id = None
    self.app_state.project.touch()
    self.refresh_callback()
```
 
---
 
## 8. Code — Bước 6: Sửa BeatStudioTab
 
File: `app/ui/beat_studio_tab.py`
 
### 6.1 Thêm import + param
 
```python
# Trong TYPE_CHECKING block, thêm:
from app.controllers.manual_ai_controller import ManualAIController
 
# Sửa __init__ thêm param:
def __init__(
    self,
    app_state: AppState,
    generation_controller: GenerationController,
    manual_ai_controller: ManualAIController,   # ← THÊM
    refresh_callback: callable,
    parent: QWidget | None = None,
) -> None:
    ...
    self.manual_ai_controller = manual_ai_controller  # ← THÊM
```
 
### 6.2 Sửa _build_ui — bỏ 3 nút gen cũ, thêm dropdown + Manual AI buttons + nút Xóa
 
```python
# BỎ 3 nút cũ:
self.btn_gen_beats = QPushButton("Tạo nhịp truyện (Generate Beats)")
self.btn_gen_review = QPushButton("Viết lại Review")
self.btn_gen_prompts = QPushButton("Xây dựng Prompt")
# BỎ signal connects:
self.btn_gen_beats.clicked.connect(self._on_gen_beats)
self.btn_gen_review.clicked.connect(self._on_gen_review)
self.btn_gen_prompts.clicked.connect(self._on_gen_prompts)
 
# THÊM Action Bar mới (thay thế cái cũ):
action_layout = QHBoxLayout()
action_layout.addWidget(QLabel("Pipeline step:"))
 
self.step_combo = QComboBox()
self.step_combo.addItems(["generate-beats", "rewrite-review", "build-prompts"])
action_layout.addWidget(self.step_combo)
 
self.btn_prompt = QPushButton("Lấy Prompt")
self.btn_import = QPushButton("Dán kết quả")
action_layout.addWidget(self.btn_prompt)
action_layout.addWidget(self.btn_import)
main_layout.addLayout(action_layout)
 
# THÊM nút Xóa scene + beat (ở scene_layout và beat_layout):
self.btn_delete_scene = QPushButton("Xóa phân cảnh")
scene_layout.addWidget(self.btn_delete_scene)
 
self.btn_delete_beat = QPushButton("Xóa nhịp truyện")
beat_layout.addWidget(self.btn_delete_beat)
 
# Connect signals:
self.btn_prompt.clicked.connect(self._on_prompt)
self.btn_import.clicked.connect(self._on_import)
self.btn_delete_scene.clicked.connect(self._on_delete_scene)
self.btn_delete_beat.clicked.connect(self._on_delete_beat)
```
 
Lưu ý: Cần `from PySide6.QtWidgets import QComboBox` (đã có trong imports hiện tại).
 
### 6.3 Thêm handlers — bỏ 3 _on_gen cũ
 
```python
# BỎ _on_gen_beats(), _on_gen_review(), _on_gen_prompts(). THÊM:
 
def _on_prompt(self) -> None:
    if not self.app_state.project or not self.app_state.selected_episode_id:
        QMessageBox.warning(self, "Cảnh báo", "Hãy chọn tập truyện trước.")
        return
    step = self.step_combo.currentText()
    try:
        from app.ui.manual_ai_dialogs import PromptExportDialog
        prompt_text = self.manual_ai_controller.export_prompt(
            self.app_state.project,
            step,
            episode_id=self.app_state.selected_episode_id,
        )
        dialog = PromptExportDialog(prompt_text, step, self)
        dialog.exec()
    except Exception as exc:
        QMessageBox.critical(self, "Lỗi", str(exc))
 
def _on_import(self) -> None:
    if not self.app_state.project or not self.app_state.selected_episode_id:
        QMessageBox.warning(self, "Cảnh báo", "Hãy chọn tập truyện trước.")
        return
    step = self.step_combo.currentText()
    try:
        from app.ui.manual_ai_dialogs import ResultImportDialog
        dialog = ResultImportDialog(step, self)
        if dialog.exec() and dialog.result_data is not None:
            summary = self.manual_ai_controller.import_result(
                self.app_state.project,
                step,
                dialog.result_data,
                episode_id=self.app_state.selected_episode_id,
            )
            QMessageBox.information(self, "Thành công", summary)
            self.refresh_callback()
    except Exception as exc:
        QMessageBox.critical(self, "Lỗi", str(exc))
 
def _on_delete_scene(self) -> None:
    if (not self.app_state.project
            or not self.app_state.selected_episode_id
            or not self.app_state.selected_scene_id):
        return
    reply = QMessageBox.question(
        self, "Xác nhận", "Bạn có chắc muốn xóa phân cảnh này?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return
    sid = self.app_state.selected_scene_id
    for ep in self.app_state.project.review_episodes:
        if ep.episode_id == self.app_state.selected_episode_id:
            ep.scenes = [s for s in ep.scenes if s.scene_id != sid]
            break
    self.app_state.selected_scene_id = None
    self.app_state.project.touch()
    self.refresh_callback()
 
def _on_delete_beat(self) -> None:
    if (not self.app_state.project
            or not self.app_state.selected_scene_id
            or not self.app_state.selected_beat_id):
        return
    reply = QMessageBox.question(
        self, "Xác nhận", "Bạn có chắc muốn xóa nhịp truyện này?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return
    bid = self.app_state.selected_beat_id
    for ep in self.app_state.project.review_episodes:
        for sc in ep.scenes:
            if sc.scene_id == self.app_state.selected_scene_id:
                sc.beats = [b for b in sc.beats if b.beat_id != bid]
                break
    self.app_state.selected_beat_id = None
    self.app_state.project.touch()
    self.refresh_callback()
```
 
### 6.4 Sửa refresh() — bỏ logic enable/disable nút gen cũ
 
```python
# BỎ các dòng:
self.btn_gen_beats.setEnabled(...)
self.btn_gen_review.setEnabled(...)
self.btn_gen_prompts.setEnabled(...)
 
# THÊM (thay thế):
has_episode = self.app_state.selected_episode_id is not None
self.btn_prompt.setEnabled(has_episode)
self.btn_import.setEnabled(has_episode)
```
 
---
 
## 9. Code — Bước 7: Sửa ManualAIService._input_rewrite()
 
File: `app/services/manual_ai_service.py`
 
### Vấn đề hiện tại
 
Hiện tại `_input_rewrite()` tạo 1 entry cho **MỖI beat**, mỗi entry chứa toàn bộ `episode.to_dict()` + `scene.to_dict()` + `source_chapter_context` → prompt rất dài, data lặp N lần.
 
### Code sửa
 
Thay thế toàn bộ method `_input_rewrite()` (khoảng dòng 247-275):
 
```python
def _input_rewrite(
    self,
    project: Project,
    episode_id: str | None,
    tone: str | None,
    density: str | None,
) -> dict[str, Any]:
    episode = self._require_episode(project, episode_id)
    source_chapters = self._chapters_for_episode(
        project, episode.source_chapter_ids,
    )
    scenes_input = []
    for scene in episode.scenes:
        scenes_input.append({
            "scene": scene.to_dict(),
            "beats": [beat.to_dict() for beat in scene.ordered_beats()],
            "narration_style": tone or episode.tone,
            "retelling_density": density or episode.density,
        })
    return {
        "episode_id": episode.episode_id,
        "episode_title": episode.title,
        "source_chapter_context": [
            {
                "chapter_id": ch.chapter_id,
                "title": ch.title,
                "raw_text": ch.raw_text,
            }
            for ch in source_chapters
        ],
        "scenes": scenes_input,
    }
```
 
**Trước**: 10 beats → episode dict lặp 10 lần + source text lặp 10 lần.
**Sau**: Context chung 1 lần, mỗi scene chứa danh sách beats.
 
---
 
## 10. Code — Bước 8: Sửa ManualAIService._input_prompts()
 
File: `app/services/manual_ai_service.py`
 
### Vấn đề tương tự
 
`_input_prompts()` cũng lặp episode/scene/bible cho mỗi beat.
 
### Code sửa
 
Thay thế toàn bộ method `_input_prompts()` (khoảng dòng 277-307):
 
```python
def _input_prompts(
    self,
    project: Project,
    episode_id: str | None,
    style_preset_id: str | None,
) -> dict[str, Any]:
    episode = self._require_episode(project, episode_id)
    style_preset = self._find_style_preset(project, style_preset_id)
    scenes_input = []
    for scene in episode.scenes:
        scenes_input.append({
            "scene": scene.to_dict(),
            "beats": [beat.to_dict() for beat in scene.ordered_beats()],
        })
    return {
        "episode_id": episode.episode_id,
        "episode_title": episode.title,
        "character_bible": [c.to_dict() for c in project.characters],
        "location_bible": [loc.to_dict() for loc in project.locations],
        "style_preset": style_preset.to_dict() if style_preset else {},
        "scenes": scenes_input,
    }
```
 
---
 
## 11. Code — Bước 9: Thêm nút xóa
 
Nút xóa cho **characters** và **locations** nằm trong `BibleStyleTab`.
 
File: `app/ui/bible_style_tab.py`
 
### Thêm nút + handler cho Characters
 
```python
# Trong _build_ui(), sau self.char_list:
self.btn_delete_char = QPushButton("Xóa nhân vật")
# addWidget vào layout tương ứng
 
# Handler:
def _on_delete_char(self) -> None:
    if not self.app_state.project:
        return
    current = self.char_list.currentItem()
    if not current:
        return
    reply = QMessageBox.question(
        self, "Xác nhận", "Bạn có chắc muốn xóa nhân vật này?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return
    name = current.text()
    self.app_state.project.characters = [
        c for c in self.app_state.project.characters if c.name != name
    ]
    self.app_state.project.touch()
    self.refresh_callback()
 
# Connect:
self.btn_delete_char.clicked.connect(self._on_delete_char)
```
 
### Thêm nút + handler cho Locations
 
```python
# Tương tự:
self.btn_delete_loc = QPushButton("Xóa địa điểm")
 
def _on_delete_loc(self) -> None:
    if not self.app_state.project:
        return
    current = self.loc_list.currentItem()
    if not current:
        return
    reply = QMessageBox.question(
        self, "Xác nhận", "Bạn có chắc muốn xóa địa điểm này?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return
    name = current.text()
    self.app_state.project.locations = [
        loc for loc in self.app_state.project.locations if loc.name != name
    ]
    self.app_state.project.touch()
    self.refresh_callback()
 
self.btn_delete_loc.clicked.connect(self._on_delete_loc)
```
 
---
 
## 12. Prompt — 6 prompt templates có sẵn
 
Tất cả prompt templates nằm trong `app/prompts/`. `ManualAIService` tự động load chúng khi user click "Lấy Prompt".
 
| File | Pipeline Step | Input chính | Output chính |
|------|--------------|-------------|-------------|
| `story_parser_prompt.md` | parse-story | source_text, character_bible, location_bible | detected_characters, scene_candidates, important_events |
| `episode_planner_prompt.md` | plan-episode | parsed_chapters, narration_style, retelling_density | episode, scenes[], cliffhanger |
| `beat_generator_prompt.md` | generate-beats | scene, source_chapter_context, retelling_density | beats[] (action, emotion, shot_type, visual_description) |
| `review_rewriter_prompt.md` | rewrite-review | scene, beats[], source_chapter_context, narration_style | rewritten_beats[] (beat_id, review_text) |
| `image_prompt_builder_prompt.md` | build-prompts | scene, beats[], character_bible, location_bible, style_preset | prompts[] (beat_id, image_prompt, negative_prompt) |
| `continuity_checker_prompt.md` | (chưa dùng trong Manual AI) | episode, beats | issues[] |
 
### Prompt flow khi user click "Lấy Prompt"
 
```
ManualAIController.export_prompt(project, step, ...)
  → ManualAIService.export_prompt(...)
    → PromptTemplateLoader.load(prompt_name)      # load .md file
    → ManualAIService._build_input_data(...)       # build JSON input
  → ManualAIService.format_prompt_for_clipboard(...)
    → Ghép: prompt_template + "\n\n## Runtime input\n```json\n" + input_data + "\n```"
  → Return chuỗi text sẵn sàng paste vào AI
```
 
### Prompt flow khi user click "Dán kết quả"
 
```
ManualAIController.import_result(project, step, result_data, ...)
  → ManualAIService.import_result(...)
    → step == "parse-story"   → _import_parse()    → dùng StoryParserService
    → step == "plan-episode"  → _import_plan()     → dùng EpisodePlannerService
    → step == "generate-beats"→ _import_beats()    → dùng BeatGeneratorService
    → step == "rewrite-review"→ _import_rewrite()  → dùng ReviewRewriterService
    → step == "build-prompts" → _import_prompts()  → dùng PromptBuilderService
  → Tất cả đều inject kết quả qua _SingleResponseGateway → service xử lý như AI thật
  → Return summary message
```
 
---
 
## 13. Verify — Kiểm tra sau khi implement
 
### Chạy tests
 
```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -v
```
 
### Kiểm tra thủ công
 
1. Mở app → Tạo project mới → Import chapter text
2. Tab "Nguồn" → Chọn chương → Click "Lấy Prompt Parse" → Kiểm tra dialog hiện đúng
3. Copy prompt → paste thử vào ChatGPT → lấy JSON result
4. Click "Dán kết quả Parse" → paste JSON → kiểm tra import thành công
5. Tab "Kế hoạch tập" → Chọn chương → Click "Lấy Prompt Plan" → kiểm tra dialog
6. Tab "Beat Studio" → Chọn step "generate-beats" → "Lấy Prompt" → kiểm tra
7. Chọn step "rewrite-review" → "Lấy Prompt" → kiểm tra **prompt gọn hơn** (context không lặp)
8. Kiểm tra nút Xóa ở tất cả tabs → xác nhận dialog → item biến mất
 
### Checklist cuối
 
- [ ] `manual_ai_controller.py` tồn tại và import được
- [ ] `manual_ai_dialogs.py` tồn tại, cả 2 dialog class hoạt động
- [ ] Window title = "Story Review Studio" (không có "(Refactored)")
- [ ] SourceTab: có "Lấy Prompt Parse" + "Dán kết quả Parse" + "Xóa chương"
- [ ] EpisodePlannerTab: có "Lấy Prompt Plan" + "Dán kết quả Plan" + "Xóa tập"
- [ ] BeatStudioTab: có dropdown step + "Lấy Prompt" + "Dán kết quả" + "Xóa phân cảnh" + "Xóa nhịp truyện"
- [ ] BibleStyleTab: có "Xóa nhân vật" + "Xóa địa điểm"
- [ ] `_input_rewrite()` gom theo scene (không lặp context per-beat)
- [ ] `_input_prompts()` gom theo scene (không lặp bible per-beat)
- [ ] Tests pass: `QT_QPA_PLATFORM=offscreen python -m pytest tests/ -v`