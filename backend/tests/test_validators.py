"""Validation engine tests."""
import pytest

from app.validators.engine import ValidationEngine
from app.models.platform import (
    Cluster, CloudProvider, Namespace, Platform, Workload, WorkloadKind,
    Service, ServiceType, ServicePort, PersistentVolumeClaim, Labels, Ingress,
    IngressRule, IngressClass,
)
from app.models.generation import IssueSeverity


def _minimal_platform(**kwargs) -> Platform:
    return Platform(name="test", clusters=[], **kwargs)


def _cluster_with_ns(ns: Namespace) -> Cluster:
    return Cluster(name="test-cluster", provider=CloudProvider.AWS, namespaces=[ns])


class TestWorkloadRules:
    def setup_method(self):
        self.engine = ValidationEngine()

    def test_no_ports_warning(self):
        wl = Workload(name="api", namespace="default", kind=WorkloadKind.DEPLOYMENT, ports=[])
        ns = Namespace(name="default", workloads=[wl], services=[
            Service(name="api", namespace="default", workload_ref="api",
                    ports=[ServicePort(name="http", port=80, target_port=8080)],
                    selector={"app": "api"})
        ])
        platform = _minimal_platform(clusters=[_cluster_with_ns(ns)])
        report = self.engine.validate(platform)
        codes = [i.code for i in report.warnings]
        assert "W001" in codes

    def test_placeholder_image_warning(self):
        wl = Workload(name="api", namespace="default", image="placeholder:latest")
        ns = Namespace(name="default", workloads=[wl], services=[
            Service(name="api", namespace="default", workload_ref="api",
                    ports=[ServicePort(name="http", port=80, target_port=8080)],
                    selector={"app": "api"})
        ])
        platform = _minimal_platform(clusters=[_cluster_with_ns(ns)])
        report = self.engine.validate(platform)
        assert any(i.code == "W002" for i in report.warnings)

    def test_missing_service_warning(self):
        wl = Workload(name="api", namespace="default", kind=WorkloadKind.DEPLOYMENT)
        ns = Namespace(name="default", workloads=[wl], services=[])
        platform = _minimal_platform(clusters=[_cluster_with_ns(ns)])
        report = self.engine.validate(platform)
        assert any(i.code == "W004" for i in report.warnings)

    def test_missing_resources_error(self):
        from app.models.platform import ResourceRequirements
        wl = Workload(
            name="api", namespace="default",
            resources=ResourceRequirements(cpu_request="", memory_request=""),
        )
        ns = Namespace(name="default", workloads=[wl])
        platform = _minimal_platform(clusters=[_cluster_with_ns(ns)])
        report = self.engine.validate(platform)
        assert any(i.code == "W003" or i.code == "W003" for i in report.warnings + report.errors)


class TestNetworkingRules:
    def setup_method(self):
        self.engine = ValidationEngine()

    def test_empty_selector_warning(self):
        svc = Service(name="api-svc", namespace="default", selector={},
                      ports=[ServicePort(name="http", port=80, target_port=8080)])
        ns = Namespace(name="default", services=[svc])
        platform = _minimal_platform(clusters=[_cluster_with_ns(ns)])
        report = self.engine.validate(platform)
        assert any(i.code == "N001" for i in report.warnings)

    def test_ingress_references_missing_service_error(self):
        rule = IngressRule(host="example.com", service_name="nonexistent", service_port=80)
        ingress = Ingress(name="main-ingress", namespace="default", rules=[rule], ingress_class=IngressClass.NGINX)
        ns = Namespace(name="default", ingresses=[ingress])
        platform = _minimal_platform(clusters=[_cluster_with_ns(ns)])
        report = self.engine.validate(platform)
        assert any(i.code == "N002" for i in report.errors)

    def test_no_network_policy_warning(self):
        ns = Namespace(name="default", network_policies=[])
        platform = _minimal_platform(clusters=[_cluster_with_ns(ns)])
        report = self.engine.validate(platform)
        assert any(i.code == "N004" for i in report.warnings)


class TestStorageRules:
    def setup_method(self):
        self.engine = ValidationEngine()

    def test_statefulset_without_pvc_error(self):
        wl = Workload(name="postgres", namespace="default", kind=WorkloadKind.STATEFULSET, pvc_refs=[])
        ns = Namespace(name="default", workloads=[wl])
        platform = _minimal_platform(clusters=[_cluster_with_ns(ns)])
        report = self.engine.validate(platform)
        assert any(i.code == "S001" for i in report.errors)

    def test_unknown_pvc_ref_error(self):
        wl = Workload(name="postgres", namespace="default", kind=WorkloadKind.STATEFULSET, pvc_refs=["nonexistent-pvc"])
        ns = Namespace(name="default", workloads=[wl], pvcs=[])
        platform = _minimal_platform(clusters=[_cluster_with_ns(ns)])
        report = self.engine.validate(platform)
        assert any(i.code == "S002" for i in report.errors)

    def test_valid_pvc_ref_passes(self):
        pvc = PersistentVolumeClaim(name="postgres-data", namespace="default")
        wl = Workload(name="postgres", namespace="default", kind=WorkloadKind.STATEFULSET, pvc_refs=["postgres-data"])
        ns = Namespace(name="default", workloads=[wl], pvcs=[pvc])
        platform = _minimal_platform(clusters=[_cluster_with_ns(ns)])
        report = self.engine.validate(platform)
        storage_errors = [i for i in report.errors if i.code.startswith("S")]
        assert len(storage_errors) == 0
