"""Run the minimal Tkinter desktop UI."""

from __future__ import annotations

from app.ui.main_window import create_main_window


def run_app() -> None:
    root, _window = create_main_window()
    root.mainloop()


if __name__ == "__main__":
    run_app()

