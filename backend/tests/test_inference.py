"""Inference engine tests."""
import pytest

from app.inference.engine import InferenceEngine
from app.inference.classifier import ComponentClassifier
from app.models.diagram import DiagramFormat, ParsedDiagram, ParsedEdge, ParsedNode
from app.models.platform import ComponentType, WorkloadKind


def _make_diagram(*nodes, edges=None):
    return ParsedDiagram(
        source_format=DiagramFormat.MERMAID,
        nodes=list(nodes),
        edges=edges or [],
    )


class TestClassifier:
    def setup_method(self):
        self.clf = ComponentClassifier()

    def _node(self, label, shape=None, tags=None):
        return ParsedNode(id="n1", label=label, shape=shape, tags=tags or [])

    def test_cluster_by_label(self):
        assert self.clf.classify(self._node("Kubernetes Cluster")) == ComponentType.CLUSTER

    def test_eks_detected(self):
        assert self.clf.classify(self._node("EKS Cluster")) == ComponentType.CLUSTER

    def test_namespace_by_label(self):
        assert self.clf.classify(self._node("default namespace")) == ComponentType.NAMESPACE

    def test_postgres_is_statefulset(self):
        assert self.clf.classify(self._node("postgres")) == ComponentType.STATEFULSET

    def test_redis_is_statefulset(self):
        assert self.clf.classify(self._node("redis cache")) == ComponentType.STATEFULSET

    def test_deployment_by_label(self):
        assert self.clf.classify(self._node("api-server")) == ComponentType.DEPLOYMENT

    def test_ingress_detection(self):
        assert self.clf.classify(self._node("nginx ingress")) == ComponentType.INGRESS

    def test_prometheus_is_monitoring(self):
        assert self.clf.classify(self._node("prometheus")) == ComponentType.MONITORING

    def test_cylinder_shape_is_statefulset(self):
        assert self.clf.classify(self._node("mydb", shape="cylinder")) == ComponentType.STATEFULSET

    def test_cloud_shape(self):
        assert self.clf.classify(self._node("aws s3", shape="cloud")) == ComponentType.CLOUD_RESOURCE

    def test_explicit_tag_overrides_label(self):
        node = ParsedNode(id="n1", label="something weird", tags=["namespace"])
        assert self.clf.classify(node) == ComponentType.NAMESPACE

    def test_unknown_falls_back(self):
        assert self.clf.classify(self._node("xyz-unknown-thing-12345")) == ComponentType.UNKNOWN


class TestInferenceEngine:
    def setup_method(self):
        self.engine = InferenceEngine()

    def test_minimal_diagram_produces_platform(self):
        diagram = _make_diagram(
            ParsedNode(id="c1", label="Kubernetes Cluster", children=["ns1"]),
            ParsedNode(id="ns1", label="default", parent_id="c1", children=["app1"]),
            ParsedNode(id="app1", label="api-server", parent_id="ns1"),
        )
        platform = self.engine.infer(diagram, name="test-platform")
        assert platform.name == "test-platform"
        assert len(platform.clusters) == 1
        cluster = platform.clusters[0]
        assert len(cluster.namespaces) >= 1

    def test_postgres_becomes_statefulset(self):
        diagram = _make_diagram(
            ParsedNode(id="c1", label="Cluster", children=["ns1"]),
            ParsedNode(id="ns1", label="default", parent_id="c1", children=["pg"]),
            ParsedNode(id="pg", label="postgres", parent_id="ns1"),
        )
        platform = self.engine.infer(diagram)
        ns = platform.clusters[0].namespaces[0]
        wl = next((w for w in ns.workloads if "postgres" in w.name), None)
        assert wl is not None
        assert wl.kind == WorkloadKind.STATEFULSET

    def test_statefulset_gets_pvc(self):
        diagram = _make_diagram(
            ParsedNode(id="c1", label="Cluster", children=["ns1"]),
            ParsedNode(id="ns1", label="default", parent_id="c1", children=["pg"]),
            ParsedNode(id="pg", label="postgres", parent_id="ns1"),
        )
        platform = self.engine.infer(diagram)
        ns = platform.clusters[0].namespaces[0]
        assert len(ns.pvcs) >= 1

    def test_default_cluster_created_when_missing(self):
        diagram = _make_diagram(
            ParsedNode(id="app1", label="api-server"),
        )
        platform = self.engine.infer(diagram)
        assert len(platform.clusters) == 1
        assert "default cluster" in " ".join(platform.assumptions).lower() or len(platform.clusters) == 1

    def test_observability_defaults(self):
        diagram = _make_diagram(
            ParsedNode(id="c1", label="Cluster"),
        )
        platform = self.engine.infer(diagram)
        cluster = platform.clusters[0]
        assert cluster.observability is not None

    def test_edges_preserved(self):
        diagram = _make_diagram(
            ParsedNode(id="c1", label="Cluster", children=["ns1"]),
            ParsedNode(id="ns1", label="default", parent_id="c1", children=["app1", "db1"]),
            ParsedNode(id="app1", label="api", parent_id="ns1"),
            ParsedNode(id="db1", label="postgres", parent_id="ns1"),
            edges=[ParsedEdge(id="e1", source_id="app1", target_id="db1", label="SQL")],
        )
        platform = self.engine.infer(diagram)
        assert len(platform.edges) == 1
        assert platform.edges[0].source_id == "app1"

    def test_k8s_name_normalization(self):
        diagram = _make_diagram(
            ParsedNode(id="c1", label="My Awesome Cluster!!!", children=["ns1"]),
            ParsedNode(id="ns1", label="Production Namespace", parent_id="c1"),
        )
        platform = self.engine.infer(diagram)
        cluster = platform.clusters[0]
        assert cluster.name == cluster.name.lower()
        assert " " not in cluster.name
