"""Parser for Excalidraw .excalidraw JSON exports."""
import json
from typing import Optional

from .base import BaseParser
from ..models.diagram import DiagramFormat, ParsedDiagram, ParsedEdge, ParsedNode


class ExcalidrawParser(BaseParser):
    async def parse(self, content: bytes, content_type: Optional[str] = None) -> ParsedDiagram:
        try:
            data = json.loads(content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"Invalid Excalidraw JSON: {exc}") from exc

        elements = data.get("elements", [])
        nodes: list[ParsedNode] = []
        edges: list[ParsedEdge] = []

        # First pass: collect all text elements so we can annotate shapes
        text_by_container: dict[str, str] = {}
        for el in elements:
            if el.get("type") == "text" and el.get("containerId"):
                text_by_container[el["containerId"]] = el.get("text", "").strip()

        # Second pass: build nodes and edges
        for el in elements:
            eid = el.get("id", "")
            etype = el.get("type", "")

            if etype in ("arrow", "line") and el.get("startBinding") and el.get("endBinding"):
                src = el["startBinding"].get("elementId", "")
                tgt = el["endBinding"].get("elementId", "")
                if src and tgt:
                    edges.append(
                        ParsedEdge(
                            id=eid,
                            source_id=src,
                            target_id=tgt,
                            label=text_by_container.get(eid) or el.get("label"),
                            style={"strokeStyle": el.get("strokeStyle"), "opacity": el.get("opacity")},
                            raw_attributes=el,
                        )
                    )
                continue

            if etype in ("text",):
                # Standalone text nodes may be labels for context
                pass

            if etype in ("rectangle", "ellipse", "diamond", "image", "frame"):
                label = text_by_container.get(eid, "")
                if not label:
                    # Try bound text elements
                    for sub in elements:
                        if sub.get("type") == "text" and sub.get("containerId") == eid:
                            label = sub.get("text", "").strip()
                            break

                x = el.get("x", 0.0)
                y = el.get("y", 0.0)
                w = el.get("width", 0.0)
                h = el.get("height", 0.0)

                nodes.append(
                    ParsedNode(
                        id=eid,
                        label=label,
                        raw_label=label,
                        shape=etype,
                        bounds=(float(x), float(y), float(w), float(h)),
                        style={
                            "backgroundColor": el.get("backgroundColor"),
                            "strokeColor": el.get("strokeColor"),
                            "roughness": el.get("roughness"),
                        },
                        tags=el.get("customData", {}).get("tags", []),
                        raw_attributes=el,
                    )
                )

        return ParsedDiagram(
            source_format=DiagramFormat.EXCALIDRAW,
            nodes=nodes,
            edges=edges,
            raw_text=content.decode("utf-8", errors="replace"),
        )
