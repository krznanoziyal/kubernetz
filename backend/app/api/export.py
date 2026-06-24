"""
Export endpoint — returns generated files as a zip archive.

POST /api/v1/export/zip
"""
import io
import zipfile

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..models.generation import GenerationRequest, GenerationResult
from .generate import generate

router = APIRouter()


@router.post("/zip")
async def export_zip(request: GenerationRequest) -> StreamingResponse:
    """Generate all files and stream them back as a zip archive."""
    result: GenerationResult = await generate(request)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in result.files:
            zf.writestr(f.path, f.content)

    buf.seek(0)
    platform_name = request.platform.name.replace(" ", "-").lower()
    filename = f"{platform_name}-blueprint.zip"

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
