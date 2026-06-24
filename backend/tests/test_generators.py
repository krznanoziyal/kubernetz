"""Generator integration tests."""
import pytest
import yaml

from app.generators.kubernetes import KubernetesGenerator
from app.generators.helm import HelmGenerator
from app.generators.argocd import ArgoCDGenerator
from app.generators.terraform import TerraformGenerator
from app.models.generation import GenerationRequest, GenerationResult, ValidationReport
from app.models.platform import (
    Cluster, CloudProvider, Namespace, Platform, Workload, WorkloadKind,
    Service, ServiceType, ServicePort, PersistentVolumeClaim, Labels,
    ContainerPort, AutoscalingConfig, HPAConfig,
)


def _make_platform() -> Platform:
    wl = Workload(
        name="api-server",
        namespace="default",
        kind=WorkloadKind.DEPLOYMENT,
        replicas=2,
        image="myrepo/api:1.0.0",
        ports=[ContainerPort(name="http", port=8080)],
    )
    db = Workload(
        name="postgres",
        namespace="default",
        kind=WorkloadKind.STATEFULSET,
        image="postgres:16",
        ports=[ContainerPort(name="postgres", port=5432)],
        pvc_refs=["postgres-data"],
    )
    pvc = PersistentVolumeClaim(name="postgres-data", namespace="default")
    svc = Service(
        name="api-server",
        namespace="default",
        workload_ref="api-server",
        selector={"app": "api-server"},
        ports=[ServicePort(name="http", port=8080, target_port=8080)],
    )
    hpa = AutoscalingConfig(name="api-server-hpa", target_ref="api-server", hpa=HPAConfig(min_replicas=2, max_replicas=10))

    ns = Namespace(
        name="default",
        workloads=[wl, db],
        services=[svc],
        pvcs=[pvc],
        autoscaling=[hpa],
    )
    cluster = Cluster(name="main-cluster", provider=CloudProvider.AWS, namespaces=[ns])
    return Platform(name="test-platform", clusters=[cluster])


def _make_request(platform: Platform | None = None) -> GenerationRequest:
    return GenerationRequest(
        platform=platform or _make_platform(),
        environments=["dev", "staging", "prod"],
    )


def _empty_result(platform_id: str) -> GenerationResult:
    return GenerationResult(
        platform_id=platform_id,
        validation=ValidationReport(passed=True),
    )


class TestKubernetesGenerator:
    def setup_method(self):
        self.gen = KubernetesGenerator()

    def _generate(self, request: GenerationRequest) -> GenerationResult:
        result = _empty_result(request.platform.id)
        self.gen.generate(request, result)
        return result

    def _files(self, result: GenerationResult) -> dict[str, str]:
        return {f.path: f.content for f in result.files}

    def test_generates_deployment(self):
        result = self._generate(_make_request())
        files = self._files(result)
        k8s_files = [k for k in files if k.startswith("k8s/base/default/")]
        assert any("api-server" in k for k in k8s_files)

    def test_deployment_yaml_valid(self):
        result = self._generate(_make_request())
        files = self._files(result)
        deploy_path = "k8s/base/default/api-server.yaml"
        assert deploy_path in files
        doc = yaml.safe_load(files[deploy_path])
        assert doc["kind"] == "Deployment"
        assert doc["spec"]["replicas"] == 2

    def test_statefulset_yaml_valid(self):
        result = self._generate(_make_request())
        files = self._files(result)
        sts_path = "k8s/base/default/postgres.yaml"
        assert sts_path in files
        doc = yaml.safe_load(files[sts_path])
        assert doc["kind"] == "StatefulSet"

    def test_service_yaml_generated(self):
        result = self._generate(_make_request())
        files = self._files(result)
        svc_path = "k8s/base/default/api-server-svc.yaml"
        assert svc_path in files
        doc = yaml.safe_load(files[svc_path])
        assert doc["kind"] == "Service"

    def test_hpa_yaml_generated(self):
        result = self._generate(_make_request())
        files = self._files(result)
        hpa_path = "k8s/base/default/api-server-hpa-hpa.yaml"
        assert hpa_path in files
        doc = yaml.safe_load(files[hpa_path])
        assert doc["kind"] == "HorizontalPodAutoscaler"

    def test_overlays_generated_per_env(self):
        result = self._generate(_make_request())
        files = self._files(result)
        for env in ["dev", "staging", "prod"]:
            assert f"k8s/overlays/{env}/kustomization.yaml" in files

    def test_kustomization_includes_namespace_bases(self):
        result = self._generate(_make_request())
        files = self._files(result)
        kust = yaml.safe_load(files["k8s/overlays/dev/kustomization.yaml"])
        assert any("base/default" in b for b in kust.get("bases", []))


class TestHelmGenerator:
    def setup_method(self):
        self.gen = HelmGenerator()

    def _generate(self, request: GenerationRequest) -> GenerationResult:
        result = _empty_result(request.platform.id)
        self.gen.generate(request, result)
        return result

    def _files(self, result: GenerationResult) -> dict[str, str]:
        return {f.path: f.content for f in result.files}

    def test_chart_yaml_generated(self):
        result = self._generate(_make_request())
        files = self._files(result)
        # api-server is a custom chart
        assert "helm/api-server/Chart.yaml" in files

    def test_chart_yaml_valid(self):
        result = self._generate(_make_request())
        files = self._files(result)
        chart = yaml.safe_load(files["helm/api-server/Chart.yaml"])
        assert chart["apiVersion"] == "v2"
        assert chart["name"] == "api-server"

    def test_values_yaml_generated(self):
        result = self._generate(_make_request())
        files = self._files(result)
        assert "helm/api-server/values.yaml" in files

    def test_env_values_generated(self):
        result = self._generate(_make_request())
        files = self._files(result)
        for env in ["dev", "staging", "prod"]:
            assert f"helm/api-server/values-{env}.yaml" in files

    def test_deployment_template_exists(self):
        result = self._generate(_make_request())
        files = self._files(result)
        assert "helm/api-server/templates/deployment.yaml" in files

    def test_helmfile_generated(self):
        result = self._generate(_make_request())
        files = self._files(result)
        assert "helm/helmfile.yaml" in files


class TestArgoCDGenerator:
    def setup_method(self):
        self.gen = ArgoCDGenerator()

    def _generate(self, request: GenerationRequest) -> GenerationResult:
        result = _empty_result(request.platform.id)
        self.gen.generate(request, result)
        return result

    def _files(self, result: GenerationResult) -> dict[str, str]:
        return {f.path: f.content for f in result.files}

    def test_bootstrap_kustomization_generated(self):
        result = self._generate(_make_request())
        files = self._files(result)
        assert "argo-cd/bootstrap/kustomization.yaml" in files

    def test_root_app_generated(self):
        result = self._generate(_make_request())
        files = self._files(result)
        assert "argo-cd/apps/root-app.yaml" in files
        doc = yaml.safe_load(files["argo-cd/apps/root-app.yaml"])
        assert doc["kind"] == "Application"

    def test_project_generated(self):
        result = self._generate(_make_request())
        files = self._files(result)
        assert "argo-cd/projects/test-platform-project.yaml" in files
        doc = yaml.safe_load(files["argo-cd/projects/test-platform-project.yaml"])
        assert doc["kind"] == "AppProject"

    def test_apps_generated_per_env(self):
        result = self._generate(_make_request())
        files = self._files(result)
        for env in ["dev", "staging", "prod"]:
            assert any(f"default-{env}" in k for k in files)

    def test_appset_generated(self):
        result = self._generate(_make_request())
        files = self._files(result)
        assert any("appset" in k for k in files)


class TestTerraformGenerator:
    def setup_method(self):
        self.gen = TerraformGenerator()

    def _generate(self, request: GenerationRequest) -> GenerationResult:
        result = _empty_result(request.platform.id)
        self.gen.generate(request, result)
        return result

    def _files(self, result: GenerationResult) -> dict[str, str]:
        return {f.path: f.content for f in result.files}

    def test_main_tf_generated(self):
        result = self._generate(_make_request())
        files = self._files(result)
        assert "terraform/main.tf" in files

    def test_variables_tf_generated(self):
        result = self._generate(_make_request())
        files = self._files(result)
        assert "terraform/variables.tf" in files

    def test_outputs_tf_generated(self):
        result = self._generate(_make_request())
        files = self._files(result)
        assert "terraform/outputs.tf" in files

    def test_backend_tf_generated(self):
        result = self._generate(_make_request())
        files = self._files(result)
        assert "terraform/backend.tf" in files

    def test_vpc_module_generated(self):
        result = self._generate(_make_request())
        files = self._files(result)
        assert "terraform/modules/vpc/main.tf" in files

    def test_eks_module_generated(self):
        result = self._generate(_make_request())
        files = self._files(result)
        assert "terraform/modules/eks/main.tf" in files

    def test_tfvars_per_env(self):
        result = self._generate(_make_request())
        files = self._files(result)
        for env in ["dev", "staging", "prod"]:
            assert f"terraform/environments/{env}.tfvars" in files
