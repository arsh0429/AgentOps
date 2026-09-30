"""Generate a compact AgentOps walkthrough GIF from the MP4 hero segment."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "docs" / "walkthrough.mp4"
OUTPUT = REPO / "docs" / "walkthrough.gif"


def _ffmpeg_executable() -> str:
    installed = shutil.which("ffmpeg")
    if installed:
        return installed
    portable = imageio_ffmpeg.get_ffmpeg_exe()
    if portable:
        return portable
    root = Path.home() / "AppData" / "Local" / "ms-playwright"
    candidates = sorted(root.glob("ffmpeg-*/ffmpeg-*.exe"), reverse=True)
    if candidates:
        return str(candidates[0])
    raise SystemExit("ffmpeg is unavailable; run: uv run playwright install chromium")


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit("walkthrough missing; run scripts/record_walkthrough.py first")
    with tempfile.TemporaryDirectory() as directory:
        frame_pattern = str(Path(directory) / "frame-%04d.png")
        subprocess.run(
            [
                _ffmpeg_executable(), "-y", "-loglevel", "error", "-i", str(SOURCE),
                "-t", "30", "-r", "6", "-vf", "scale=720:-1", frame_pattern,
            ],
            check=True,
        )
        paths = sorted(Path(directory).glob("frame-*.png"))
        if not paths:
            raise SystemExit("no GIF frames were produced")
        frames = [Image.open(path).convert("P", palette=Image.Palette.ADAPTIVE) for path in paths]
        frames[0].save(
            OUTPUT,
            save_all=True,
            append_images=frames[1:],
            duration=167,
            loop=0,
            optimize=True,
            disposal=2,
        )
    print(f"wrote {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
