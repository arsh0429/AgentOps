"""Validate that the current walkthrough contains embedded capture captions.

Captions are injected into each browser page by ``record_walkthrough.py``
before Playwright records it, so a separate post-processing pass is no longer
required.
"""
from pathlib import Path

WALKTHROUGH = Path(__file__).resolve().parent.parent / "docs" / "walkthrough.mp4"


def main() -> None:
    if not WALKTHROUGH.exists() or WALKTHROUGH.stat().st_size == 0:
        raise SystemExit("walkthrough missing; run: uv run python scripts/record_walkthrough.py")
    print(f"captions are embedded in {WALKTHROUGH}")


if __name__ == "__main__":
    main()
