"""
Parser for Mermaid architecture / graph diagrams.

Supports:
  - graph TD / LR / RL / BT
  - flowchart TD / LR
  - C4Context / C4Container
  - architecture-beta (Mermaid v11+)

Returns a ParsedDiagram from the abstract node/edge structure.
"""
import re
import uuid
from typing import Optional

from .base import BaseParser
from ..models.diagram import DiagramFormat, ParsedDiagram, ParsedEdge, ParsedNode

# Patterns
_NODE_RE = re.compile(
    r"""
    (?P<id>[A-Za-z0-9_\-]+)          # node ID
    (?:
        \[(?P<rect>[^\]]*)\]          # rectangle label
      | \((?P<round>[^)]*)\)          # rounded / circle
      | \{(?P<diamond>[^}]*)\}        # diamond
      | \[\[(?P<sub>[^\]]*)\]\]       # subroutine
      | \(\((?P<circ>[^)]*)\)\)       # circle
      | \>(?P<asym>[^\]]*)\]          # asymmetric
    )?
    """,
    re.VERBOSE,
)
_EDGE_RE = re.compile(
    r"""
    (?P<src>[A-Za-z0-9_\-]+)
    \s*
    (?:-->|---|\-\.-?>?|===>?|--\|?|--o|--x)   # edge type
    \|?(?P<label>[^|>]*?)\|?
    \s*
    (?P<tgt>[A-Za-z0-9_\-]+)
    """,
    re.VERBOSE,
)
_SUBGRAPH_RE = re.compile(r"subgraph\s+(?P<id>[A-Za-z0-9_\-\s]+?)(?:\[(?P<label>[^\]]+)\])?$")


class MermaidParser(BaseParser):
    async def parse(self, content: bytes, content_type: Optional[str] = None) -> ParsedDiagram:
        text = content.decode("utf-8", errors="replace").strip()
        nodes: dict[str, ParsedNode] = {}
        edges: list[ParsedEdge] = []
        notes: list[str] = []

        # Track subgraph context (simple stack)
        subgraph_stack: list[str] = []

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("%%"):
                continue

            # Skip diagram type declarations
            if re.match(r"^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|gitGraph|architecture|C4)", line, re.I):
                continue

            # Subgraph start
            sg_match = _SUBGRAPH_RE.match(line)
            if sg_match:
                sg_id = sg_match.group("id").strip().replace(" ", "_")
                sg_label = sg_match.group("label") or sg_id
                parent = subgraph_stack[-1] if subgraph_stack else None
                if sg_id not in nodes:
                    nodes[sg_id] = ParsedNode(
                        id=sg_id,
                        label=sg_label,
                        shape="subgraph",
                        parent_id=parent,
                    )
                subgraph_stack.append(sg_id)
                continue

            if line == "end":
                if subgraph_stack:
                    subgraph_stack.pop()
                continue

            # Edge detection
            edge_match = _EDGE_RE.search(line)
            if edge_match:
                src_id = edge_match.group("src")
                tgt_id = edge_match.group("tgt")
                label = (edge_match.group("label") or "").strip()
                parent = subgraph_stack[-1] if subgraph_stack else None

                for nid in (src_id, tgt_id):
                    if nid not in nodes:
                        nodes[nid] = ParsedNode(id=nid, label=nid, parent_id=parent)

                edges.append(
                    ParsedEdge(
                        id=str(uuid.uuid4()),
                        source_id=src_id,
                        target_id=tgt_id,
                        label=label or None,
                    )
                )
                continue

            # Standalone node definition
            node_match = _NODE_RE.match(line)
            if node_match and node_match.group("id"):
                nid = node_match.group("id")
                label = (
                    node_match.group("rect")
                    or node_match.group("round")
                    or node_match.group("diamond")
                    or node_match.group("sub")
                    or node_match.group("circ")
                    or node_match.group("asym")
                    or nid
                )
                shape = _shape_from_match(node_match)
                parent = subgraph_stack[-1] if subgraph_stack else None
                if nid not in nodes:
                    nodes[nid] = ParsedNode(id=nid, label=label.strip(), shape=shape, parent_id=parent)

        # Populate parent→children
        node_list = list(nodes.values())
        id_map = {n.id: n for n in node_list}
        for node in node_list:
            if node.parent_id and node.parent_id in id_map:
                id_map[node.parent_id].children.append(node.id)

        return ParsedDiagram(
            source_format=DiagramFormat.MERMAID,
            nodes=node_list,
            edges=edges,
            raw_text=text,
            parser_notes=notes,
        )


def _shape_from_match(m: re.Match) -> str:
    if m.group("rect"):
        return "rectangle"
    if m.group("round"):
        return "rounded"
    if m.group("diamond"):
        return "diamond"
    if m.group("circ"):
        return "circle"
    return "default"
