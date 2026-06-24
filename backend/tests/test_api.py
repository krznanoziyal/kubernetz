"""API integration tests using HTTPX + FastAPI TestClient."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.platform import (
    Cluster, CloudProvider, Namespace, Platform, Workload, WorkloadKind,
    Service, ServicePort, ContainerPort, Labels,
)

client = TestClient(app)


def _minimal_platform() -> dict:
    wl = Workload(
        name="api",
        namespace="default",
        kind=WorkloadKind.DEPLOYMENT,
        image="myrepo/api:1.0.0",
        ports=[ContainerPort(name="http", port=8080)],
    )
    svc = Service(
        name="api",
        namespace="default",
        workload_ref="api",
        selector={"app": "api"},
        ports=[ServicePort(name="http", port=8080, target_port=8080)],
    )
    ns = Namespace(name="default", workloads=[wl], services=[svc])
    cluster = Cluster(name="main", provider=CloudProvider.AWS, namespaces=[ns])
    platform = Platform(name="test-platform", clusters=[cluster])
    return platform.model_dump()


class TestHealth:
    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestDiagramParsing:
    MERMAID_TEXT = "graph TD\n  api[api-server] --> db[(postgres)]"

    def test_mermaid_parse_returns_platform(self):
        resp = client.post("/api/v1/diagram/mermaid", json={"text": self.MERMAID_TEXT, "name": "test"})
        assert resp.status_code == 200
        body = resp.json()
        assert "platform" in body
        assert "parsed" in body
        assert body["platform"]["name"] == "test"

    def test_mermaid_parse_detects_nodes(self):
        resp = client.post("/api/v1/diagram/mermaid", json={"text": self.MERMAID_TEXT})
        assert resp.status_code == 200
        parsed = resp.json()["parsed"]
        assert len(parsed["nodes"]) >= 1

    def test_mermaid_empty_text_returns_400(self):
        resp = client.post("/api/v1/diagram/mermaid", json={"text": ""})
        assert resp.status_code == 400

    def test_drawio_parse(self):
        xml = b"""<?xml version="1.0"?><mxGraphModel><root>
          <mxCell id="0"/><mxCell id="1" parent="0"/>
          <mxCell id="n1" value="api-server" style="rounded=1;" parent="1" vertex="1">
            <mxGeometry x="0" y="0" width="100" height="50" as="geometry"/>
          </mxCell>
        </root></mxGraphModel>"""
        resp = client.post(
            "/api/v1/diagram/parse",
            files={"file": ("test.xml", xml, "application/xml")},
            data={"name": "drawio-test"},
        )
        assert resp.status_code == 200
        assert "platform" in resp.json()


class TestValidation:
    def test_valid_platform_passes(self):
        platform = _minimal_platform()
        resp = client.post("/api/v1/architecture/validate", json=platform)
        assert resp.status_code == 200
        body = resp.json()
        assert "passed" in body
        assert "errors" in body

    def test_invalid_platform_returns_errors(self):
        platform = _minimal_platform()
        # Remove resources → triggers W003
        platform["clusters"][0]["namespaces"][0]["workloads"][0]["resources"]["cpu_request"] = ""
        platform["clusters"][0]["namespaces"][0]["workloads"][0]["resources"]["memory_request"] = ""
        resp = client.post("/api/v1/architecture/validate", json=platform)
        assert resp.status_code == 200
        body = resp.json()
        issue_codes = [i["code"] for i in body.get("warnings", []) + body.get("errors", [])]
        assert any(code.startswith("W0") or code.startswith("S0") or code.startswith("N0") or code.startswith("SEC") for code in issue_codes)


class TestGeneration:
    def _make_request(self) -> dict:
        return {
            "platform": _minimal_platform(),
            "environments": ["dev", "prod"],
            "generate_helm": True,
            "generate_argocd": True,
            "generate_terraform": True,
            "generate_observability": True,
        }

    def test_generate_returns_files(self):
        resp = client.post("/api/v1/generate/", json=self._make_request())
        assert resp.status_code == 200
        body = resp.json()
        assert "files" in body
        assert len(body["files"]) > 0

    def test_generate_includes_k8s_manifests(self):
        resp = client.post("/api/v1/generate/", json=self._make_request())
        files = {f["path"] for f in resp.json()["files"]}
        assert any(p.startswith("k8s/") for p in files)

    def test_generate_includes_helm_charts(self):
        resp = client.post("/api/v1/generate/", json=self._make_request())
        files = {f["path"] for f in resp.json()["files"]}
        assert any(p.startswith("helm/") for p in files)

    def test_generate_includes_terraform(self):
        resp = client.post("/api/v1/generate/", json=self._make_request())
        files = {f["path"] for f in resp.json()["files"]}
        assert any(p.startswith("terraform/") for p in files)

    def test_generate_includes_argocd(self):
        resp = client.post("/api/v1/generate/", json=self._make_request())
        files = {f["path"] for f in resp.json()["files"]}
        assert any(p.startswith("argo-cd/") for p in files)

    def test_generate_includes_readme(self):
        resp = client.post("/api/v1/generate/", json=self._make_request())
        files = {f["path"] for f in resp.json()["files"]}
        assert "README.md" in files


class TestExport:
    def test_export_zip_returns_binary(self):
        request = {
            "platform": _minimal_platform(),
            "environments": ["dev"],
            "generate_helm": False,
            "generate_argocd": False,
            "generate_terraform": False,
            "generate_observability": False,
        }
        resp = client.post("/api/v1/export/zip", json=request)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        assert len(resp.content) > 0

    def test_export_zip_is_valid_zip(self):
        import io
        import zipfile
        request = {
            "platform": _minimal_platform(),
            "environments": ["dev"],
            "generate_helm": True,
            "generate_argocd": True,
            "generate_terraform": True,
            "generate_observability": True,
        }
        resp = client.post("/api/v1/export/zip", json=request)
        assert resp.status_code == 200
        buf = io.BytesIO(resp.content)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
        assert len(names) > 5
        assert any("k8s" in n for n in names)
