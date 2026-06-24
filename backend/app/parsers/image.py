"""
Vision-based parser for PNG/JPG/SVG diagram images.

Uses the Anthropic Claude API with vision to extract architecture components
from an image and produce a ParsedDiagram. Falls back to a minimal stub when
no API key is configured so the rest of the pipeline still runs.
"""
import base64
import json
import logging
import uuid
from typing import Optional

from .base import BaseParser
from ..config import get_settings
from ..models.diagram import DiagramFormat, ParsedDiagram, ParsedEdge, ParsedNode

log = logging.getLogger(__name__)

_EXTRACTION_PROMPT = """
You are an expert Kubernetes platform architect analyzing an architecture diagram.

Examine the image carefully and extract ALL components and connections visible.

Return a JSON object with this exact structure:
{
  "nodes": [
    {
      "id": "unique_id",
      "label": "human readable name",
      "shape": "rectangle|circle|cylinder|diamond|cloud|database|queue|other",
      "parent_id": "id_of_containing_group_or_null",
      "tags": ["kubernetes", "namespace", "deployment", "service", "database", etc],
      "notes": "any annotation text near this component"
    }
  ],
  "edges": [
    {
      "id": "unique_edge_id",
      "source_id": "node_id",
      "target_id": "node_id",
      "label": "connection label or null"
    }
  ],
  "parser_notes": ["any observations about the diagram that might help with inference"]
}

Classification hints:
- Rectangles with dashed borders → namespace or cluster
- Cylinders → databases or persistent storage
- Rounded rectangles → services or workloads
- Clouds → external services or cloud providers
- Hexagons → Kubernetes concepts
- Arrows between components → network connections or data flows
- Groups/swimlanes → namespaces or environments
- Label text like "nginx", "postgres", "redis", "kafka" → specific technology choices

Be exhaustive. Every visible shape and connection should become a node or edge.
"""


class ImageParser(BaseParser):
    async def parse(self, content: bytes, content_type: Optional[str] = None) -> ParsedDiagram:
        settings = get_settings()

        if not settings.anthropic_api_key:
            log.warning("ANTHROPIC_API_KEY not set — using stub image parser")
            return _stub_diagram(content_type)

        return await _parse_with_claude(content, content_type or "image/png", settings.anthropic_api_key)


async def _parse_with_claude(content: bytes, content_type: str, api_key: str) -> ParsedDiagram:
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic package not installed — run: pip install anthropic") from exc

    client = anthropic.AsyncAnthropic(api_key=api_key)

    b64 = base64.standard_b64encode(content).decode()
    media_type = content_type if content_type in ("image/png", "image/jpeg", "image/gif", "image/webp") else "image/png"

    response = await client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": _EXTRACTION_PROMPT},
                ],
            }
        ],
    )

    raw_text = response.content[0].text
    # Extract JSON block from response
    json_match = _extract_json(raw_text)
    if not json_match:
        raise ValueError("Claude did not return valid JSON in image analysis")

    data = json.loads(json_match)

    nodes = [
        ParsedNode(
            id=n.get("id", str(uuid.uuid4())),
            label=n.get("label", ""),
            shape=n.get("shape"),
            parent_id=n.get("parent_id"),
            tags=n.get("tags", []),
            notes=n.get("notes", ""),
            raw_attributes=n,
        )
        for n in data.get("nodes", [])
    ]

    edges = [
        ParsedEdge(
            id=e.get("id", str(uuid.uuid4())),
            source_id=e.get("source_id", ""),
            target_id=e.get("target_id", ""),
            label=e.get("label"),
            raw_attributes=e,
        )
        for e in data.get("edges", [])
    ]

    # Determine media-type based format
    fmt_map = {
        "image/png": DiagramFormat.IMAGE_PNG,
        "image/jpeg": DiagramFormat.IMAGE_JPG,
        "image/svg+xml": DiagramFormat.IMAGE_SVG,
    }
    fmt = fmt_map.get(content_type, DiagramFormat.IMAGE_PNG)

    return ParsedDiagram(
        source_format=fmt,
        nodes=nodes,
        edges=edges,
        raw_text=raw_text,
        parser_notes=data.get("parser_notes", []),
    )


def _extract_json(text: str) -> Optional[str]:
    import re
    # Try ```json ... ``` block
    m = re.search(r"```json\s*([\s\S]+?)```", text)
    if m:
        return m.group(1).strip()
    # Try raw { ... }
    m = re.search(r"(\{[\s\S]+\})", text)
    if m:
        return m.group(1).strip()
    return None


def _stub_diagram(content_type: Optional[str]) -> ParsedDiagram:
    """Minimal stub returned when vision API is unavailable."""
    fmt_map = {
        "image/png": DiagramFormat.IMAGE_PNG,
        "image/jpeg": DiagramFormat.IMAGE_JPG,
        "image/svg+xml": DiagramFormat.IMAGE_SVG,
    }
    fmt = fmt_map.get(content_type or "", DiagramFormat.IMAGE_PNG)
    return ParsedDiagram(
        source_format=fmt,
        nodes=[
            ParsedNode(id="cluster-1", label="Kubernetes Cluster", shape="rectangle", tags=["cluster"]),
            ParsedNode(id="ns-default", label="default", shape="rectangle", parent_id="cluster-1", tags=["namespace"]),
            ParsedNode(id="app-1", label="app", shape="rectangle", parent_id="ns-default", tags=["deployment"]),
        ],
        edges=[],
        parser_notes=["Stub diagram: set ANTHROPIC_API_KEY for real image parsing"],
    )
