"""
Parser for draw.io / diagrams.net XML exports.

draw.io saves diagrams as mxGraph XML. The root element is <mxGraphModel>
containing an <root> with <mxCell> children. Grouped elements use the
parent attribute to denote containment.
"""
import html
import re
import xml.etree.ElementTree as ET
from typing import Optional
from urllib.parse import unquote

from .base import BaseParser
from ..models.diagram import DiagramFormat, ParsedDiagram, ParsedEdge, ParsedNode


class DrawioParser(BaseParser):
    async def parse(self, content: bytes, content_type: Optional[str] = None) -> ParsedDiagram:
        text = content.decode("utf-8", errors="replace")
        # draw.io sometimes URL-encodes or wraps the XML
        if text.strip().startswith("%3C"):
            text = unquote(text)

        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise ValueError(f"Invalid draw.io XML: {exc}") from exc

        # Locate mxGraphModel root (may be nested)
        model = root if root.tag == "mxGraphModel" else root.find(".//mxGraphModel")
        if model is None:
            # Some exports embed the XML inside a <diagram> element
            diagram_el = root.find(".//diagram")
            if diagram_el is not None and diagram_el.text:
                inner = unquote(diagram_el.text.strip())
                model = ET.fromstring(inner)

        if model is None:
            raise ValueError("Could not locate mxGraphModel in draw.io XML")

        nodes: list[ParsedNode] = []
        edges: list[ParsedEdge] = []
        notes: list[str] = []

        for cell in model.iter("mxCell"):
            cell_id = cell.get("id", "")
            if cell_id in ("0", "1"):
                continue  # draw.io root cells

            label = _clean_label(cell.get("label", ""))
            style = _parse_style(cell.get("style", ""))
            parent = cell.get("parent", "")
            source = cell.get("source")
            target = cell.get("target")

            geo = cell.find("mxGeometry")
            bounds = None
            if geo is not None:
                try:
                    bounds = (
                        float(geo.get("x", 0)),
                        float(geo.get("y", 0)),
                        float(geo.get("width", 0)),
                        float(geo.get("height", 0)),
                    )
                except (ValueError, TypeError):
                    pass

            if source and target:
                edges.append(
                    ParsedEdge(
                        id=cell_id,
                        source_id=source,
                        target_id=target,
                        label=label or None,
                        style=style,
                        raw_attributes=dict(cell.attrib),
                    )
                )
            else:
                node = ParsedNode(
                    id=cell_id,
                    label=label,
                    raw_label=cell.get("label", ""),
                    shape=style.get("shape"),
                    bounds=bounds,
                    parent_id=parent if parent not in ("0", "1") else None,
                    style=style,
                    raw_attributes=dict(cell.attrib),
                )
                nodes.append(node)

        # Build parent→children index
        id_map = {n.id: n for n in nodes}
        for node in nodes:
            if node.parent_id and node.parent_id in id_map:
                id_map[node.parent_id].children.append(node.id)

        return ParsedDiagram(
            source_format=DiagramFormat.DRAWIO,
            nodes=nodes,
            edges=edges,
            raw_text=text,
            parser_notes=notes,
        )


def _clean_label(raw: str) -> str:
    """Strip HTML tags and decode entities from draw.io cell labels."""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    return " ".join(text.split())


def _parse_style(style_str: str) -> dict:
    """Convert draw.io style string to a key-value dict."""
    result: dict = {}
    for part in style_str.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, _, v = part.partition("=")
            result[k.strip()] = v.strip()
        else:
            result[part] = True
    return result
