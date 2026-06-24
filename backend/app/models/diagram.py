"""Models for parsed diagram output (format-agnostic intermediate form)."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class DiagramFormat(str, Enum):
    DRAWIO = "drawio"
    EXCALIDRAW = "excalidraw"
    MERMAID = "mermaid"
    IMAGE_PNG = "image/png"
    IMAGE_JPG = "image/jpeg"
    IMAGE_SVG = "image/svg+xml"
    UNKNOWN = "unknown"


class ParsedNode(BaseModel):
    """A single element extracted from a diagram."""
    id: str
    label: str
    raw_label: str = ""
    shape: Optional[str] = None
    # Bounding box in diagram coordinates (x, y, width, height)
    bounds: Optional[Tuple[float, float, float, float]] = None
    parent_id: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    style: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    notes: str = ""
    raw_attributes: Dict[str, Any] = Field(default_factory=dict)


class ParsedEdge(BaseModel):
    """A connection between two nodes in the diagram."""
    id: str
    source_id: str
    target_id: str
    label: Optional[str] = None
    style: Dict[str, Any] = Field(default_factory=dict)
    raw_attributes: Dict[str, Any] = Field(default_factory=dict)


class ParsedDiagram(BaseModel):
    """Unified intermediate representation produced by any parser."""
    source_format: DiagramFormat
    nodes: List[ParsedNode] = Field(default_factory=list)
    edges: List[ParsedEdge] = Field(default_factory=list)
    raw_text: str = ""
    page_count: int = 1
    parser_notes: List[str] = Field(default_factory=list)
