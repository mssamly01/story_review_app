"""Run the minimal PySide6 desktop UI."""

from __future__ import annotations

from app.ui.main_window import create_main_window


def run_app() -> None:
    app, window = create_main_window()
    window.show()
    app.exec()


if __name__ == "__main__":
    run_app()
