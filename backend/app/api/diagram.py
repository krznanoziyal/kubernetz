"""
Diagram upload and parsing endpoints.

POST /api/v1/diagram/parse   - upload a file and get back a ParsedDiagram + Platform
POST /api/v1/diagram/mermaid - parse raw mermaid text
"""
import base64
import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import get_settings
from ..models.diagram import DiagramFormat, ParsedDiagram
from ..models.platform import Platform
from ..parsers import get_parser
from ..inference.engine import InferenceEngine

log = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.post("/parse")
async def parse_diagram(
    file: UploadFile = File(...),
    name: Optional[str] = Form(default=None),
    notes: Optional[str] = Form(default=None),
) -> dict:
    """
    Accept a diagram file and return the parsed intermediate form plus the inferred Platform model.
    Supported: .xml (draw.io), .excalidraw, .png, .jpg, .svg
    """
    if file.size and file.size > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    content = await file.read()
    filename = file.filename or ""
    content_type = file.content_type or ""

    fmt = _detect_format(filename, content_type, content)
    parser = get_parser(fmt)

    try:
        parsed: ParsedDiagram = await parser.parse(content, content_type=content_type)
    except Exception as exc:
        log.exception("Parser failed for format %s", fmt)
        raise HTTPException(status_code=422, detail=f"Could not parse diagram: {exc}") from exc

    engine = InferenceEngine()
    platform = engine.infer(parsed, name=name or _stem(filename), notes=notes or "")

    return {"parsed": parsed.model_dump(), "platform": platform.model_dump()}


@router.post("/mermaid")
async def parse_mermaid(body: dict) -> dict:
    """Accept raw Mermaid architecture text and return the inferred Platform."""
    text = body.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="text field is required")

    from ..parsers.mermaid import MermaidParser
    parser = MermaidParser()
    parsed = await parser.parse(text.encode(), content_type="text/plain")

    engine = InferenceEngine()
    platform = engine.infer(parsed, name=body.get("name", "mermaid-platform"))

    return {"parsed": parsed.model_dump(), "platform": platform.model_dump()}


def _detect_format(filename: str, content_type: str, content: bytes) -> DiagramFormat:
    fn = filename.lower()
    if fn.endswith(".xml") or fn.endswith(".drawio"):
        return DiagramFormat.DRAWIO
    if fn.endswith(".excalidraw"):
        return DiagramFormat.EXCALIDRAW
    if fn.endswith(".png") or content_type == "image/png":
        return DiagramFormat.IMAGE_PNG
    if fn.endswith(".jpg") or fn.endswith(".jpeg") or content_type == "image/jpeg":
        return DiagramFormat.IMAGE_JPG
    if fn.endswith(".svg") or content_type == "image/svg+xml":
        return DiagramFormat.IMAGE_SVG
    # Sniff draw.io XML
    if content[:5] in (b"<?xml", b"<mxGr"):
        return DiagramFormat.DRAWIO
    # Sniff Excalidraw JSON
    if content[:1] == b"{" and b'"excalidraw"' in content[:200]:
        return DiagramFormat.EXCALIDRAW
    return DiagramFormat.UNKNOWN


def _stem(filename: str) -> str:
    import os
    return os.path.splitext(os.path.basename(filename))[0] or "platform"
