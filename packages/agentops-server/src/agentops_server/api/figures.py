from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings

router = APIRouter()


def _figures_dir() -> Path:
    return Path(settings.figures_dir).resolve()


@router.get("/papers/{paper_id}/figures/{filename}")
async def get_figure(paper_id: str, filename: str) -> FileResponse:
    # Path-traversal guard: reject any filename with path separators or '..'
    if "/" in filename or "\\" in filename or filename.startswith(".."):
        raise HTTPException(status_code=400, detail="invalid filename")
    if filename != f"fig_{paper_id.replace('.', '_')}_1.jpg":
        raise HTTPException(status_code=404, detail="figure not found for paper")

    figures_dir = _figures_dir()
    candidate = (figures_dir / filename).resolve()

    # Ensure the resolved path is inside the figures directory
    if not candidate.is_relative_to(figures_dir):
        raise HTTPException(status_code=400, detail="invalid filename")

    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail=f"figure {filename} not found")

    return FileResponse(str(candidate), media_type="image/jpeg")
