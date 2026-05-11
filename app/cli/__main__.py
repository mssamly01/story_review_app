"""Allow ``python -m app.cli ...`` to continue working after the package split."""

from __future__ import annotations

from app.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
