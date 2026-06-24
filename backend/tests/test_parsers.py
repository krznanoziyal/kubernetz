"""Parser unit tests."""
import pytest

from app.parsers.drawio import DrawioParser
from app.parsers.mermaid import MermaidParser
from app.parsers.excalidraw import ExcalidrawParser
from app.models.diagram import DiagramFormat


DRAWIO_XML = """<?xml version="1.0" encoding="UTF-8"?>
<mxGraphModel>
  <root>
    <mxCell id="0" />
    <mxCell id="1" parent="0" />
    <mxCell id="cluster-1" value="Kubernetes Cluster" style="shape=mxgraph.kubernetes.cluster;" parent="1" vertex="1">
      <mxGeometry x="80" y="80" width="600" height="400" as="geometry" />
    </mxCell>
    <mxCell id="ns-default" value="default" style="dashed=1;" parent="cluster-1" vertex="1">
      <mxGeometry x="10" y="10" width="400" height="300" as="geometry" />
    </mxCell>
    <mxCell id="app-1" value="api-server" style="rounded=1;" parent="ns-default" vertex="1">
      <mxGeometry x="20" y="20" width="120" height="60" as="geometry" />
    </mxCell>
    <mxCell id="db-1" value="postgres" style="shape=cylinder;" parent="ns-default" vertex="1">
      <mxGeometry x="200" y="20" width="100" height="60" as="geometry" />
    </mxCell>
    <mxCell id="edge-1" style="edgeStyle=orthogonalEdgeStyle;" source="app-1" target="db-1" parent="1" edge="1">
      <mxGeometry relative="1" as="geometry" />
    </mxCell>
  </root>
</mxGraphModel>"""

MERMAID_TEXT = """graph TD
    subgraph cluster[Kubernetes Cluster]
        subgraph default[default namespace]
            api[api-server]
            db[(postgres)]
            redis[(redis)]
        end
        subgraph monitoring[monitoring]
            prom[prometheus]
            grafana[grafana]
        end
    end
    internet((Internet)) -->|HTTPS| ingress[nginx ingress]
    ingress --> api
    api --> db
    api --> redis
    prom --> api
"""

EXCALIDRAW_JSON = """{
  "type": "excalidraw",
  "version": 2,
  "source": "test",
  "elements": [
    {"type": "rectangle", "id": "cluster-1", "x": 0, "y": 0, "width": 600, "height": 400, "backgroundColor": "#dae8fc"},
    {"type": "text", "id": "cluster-label", "x": 10, "y": 10, "text": "Kubernetes Cluster", "containerId": "cluster-1"},
    {"type": "rectangle", "id": "ns-1", "x": 20, "y": 40, "width": 500, "height": 300, "backgroundColor": "#f9f"},
    {"type": "text", "id": "ns-label", "x": 30, "y": 50, "text": "default", "containerId": "ns-1"},
    {"type": "rectangle", "id": "app-1", "x": 50, "y": 80, "width": 100, "height": 50},
    {"type": "text", "id": "app-label", "x": 60, "y": 90, "text": "api-server", "containerId": "app-1"},
    {
      "type": "arrow", "id": "edge-1", "x": 150, "y": 105,
      "startBinding": {"elementId": "app-1", "focus": 0, "gap": 1},
      "endBinding": {"elementId": "ns-1", "focus": 0, "gap": 1}
    }
  ],
  "appState": {}
}"""


class TestDrawioParser:
    @pytest.mark.asyncio
    async def test_basic_parse(self) -> None:
        parser = DrawioParser()
        result = await parser.parse(DRAWIO_XML.encode())
        assert result.source_format == DiagramFormat.DRAWIO
        assert len(result.nodes) >= 4
        assert any(n.label == "api-server" for n in result.nodes)
        assert any(n.label == "postgres" for n in result.nodes)

    @pytest.mark.asyncio
    async def test_edges_extracted(self) -> None:
        parser = DrawioParser()
        result = await parser.parse(DRAWIO_XML.encode())
        assert len(result.edges) == 1
        assert result.edges[0].source_id == "app-1"
        assert result.edges[0].target_id == "db-1"

    @pytest.mark.asyncio
    async def test_parent_child_relationships(self) -> None:
        parser = DrawioParser()
        result = await parser.parse(DRAWIO_XML.encode())
        app_node = next(n for n in result.nodes if n.id == "app-1")
        assert app_node.parent_id == "ns-default"

    @pytest.mark.asyncio
    async def test_invalid_xml_raises(self) -> None:
        parser = DrawioParser()
        with pytest.raises(ValueError):
            await parser.parse(b"not xml at all <<>>")


class TestMermaidParser:
    @pytest.mark.asyncio
    async def test_basic_parse(self) -> None:
        parser = MermaidParser()
        result = await parser.parse(MERMAID_TEXT.encode())
        assert result.source_format == DiagramFormat.MERMAID
        node_labels = {n.label for n in result.nodes}
        assert "api-server" in node_labels or any("api" in l for l in node_labels)

    @pytest.mark.asyncio
    async def test_edges_extracted(self) -> None:
        parser = MermaidParser()
        result = await parser.parse(MERMAID_TEXT.encode())
        assert len(result.edges) > 0

    @pytest.mark.asyncio
    async def test_subgraphs_become_nodes(self) -> None:
        parser = MermaidParser()
        result = await parser.parse(MERMAID_TEXT.encode())
        node_ids = {n.id for n in result.nodes}
        assert "default" in node_ids or "monitoring" in node_ids


class TestExcalidrawParser:
    @pytest.mark.asyncio
    async def test_basic_parse(self) -> None:
        parser = ExcalidrawParser()
        result = await parser.parse(EXCALIDRAW_JSON.encode())
        assert result.source_format == DiagramFormat.EXCALIDRAW
        assert len(result.nodes) >= 2
        node_labels = {n.label for n in result.nodes}
        assert "Kubernetes Cluster" in node_labels or "api-server" in node_labels

    @pytest.mark.asyncio
    async def test_arrow_becomes_edge(self) -> None:
        parser = ExcalidrawParser()
        result = await parser.parse(EXCALIDRAW_JSON.encode())
        assert len(result.edges) == 1

    @pytest.mark.asyncio
    async def test_invalid_json_raises(self) -> None:
        parser = ExcalidrawParser()
        with pytest.raises(ValueError):
            await parser.parse(b"{invalid json")
