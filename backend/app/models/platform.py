"""
Canonical domain model for a KubeBlueprint platform.

Every parser, inference engine, validator, and generator operates on these
types. Keep them stable — they are the contract between all subsystems.
"""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─── Enumerations ────────────────────────────────────────────────────────────

class CloudProvider(str, Enum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    GENERIC = "generic"
    CUSTOM = "custom"


class ComponentType(str, Enum):
    CLUSTER = "cluster"
    NAMESPACE = "namespace"
    DEPLOYMENT = "deployment"
    STATEFULSET = "statefulset"
    DAEMONSET = "daemonset"
    JOB = "job"
    CRONJOB = "cronjob"
    SERVICE = "service"
    INGRESS = "ingress"
    GATEWAY = "gateway"
    CONFIGMAP = "configmap"
    SECRET = "secret"
    PVC = "pvc"
    STORAGE_CLASS = "storage_class"
    HPA = "hpa"
    VPA = "vpa"
    SERVICE_MESH = "service_mesh"
    MONITORING = "monitoring"
    LOGGING = "logging"
    TRACING = "tracing"
    EXTERNAL_DEPENDENCY = "external_dependency"
    CLOUD_RESOURCE = "cloud_resource"
    TERRAFORM_RESOURCE = "terraform_resource"
    NETWORK_POLICY = "network_policy"
    RBAC = "rbac"
    NODE_GROUP = "node_group"
    UNKNOWN = "unknown"


class WorkloadKind(str, Enum):
    DEPLOYMENT = "Deployment"
    STATEFULSET = "StatefulSet"
    DAEMONSET = "DaemonSet"
    JOB = "Job"
    CRONJOB = "CronJob"


class ServiceType(str, Enum):
    CLUSTER_IP = "ClusterIP"
    NODE_PORT = "NodePort"
    LOAD_BALANCER = "LoadBalancer"
    EXTERNAL_NAME = "ExternalName"
    HEADLESS = "Headless"


class IngressClass(str, Enum):
    NGINX = "nginx"
    TRAEFIK = "traefik"
    ISTIO = "istio"
    ALBLB = "alb"
    GCELB = "gce"
    HAPROXY = "haproxy"
    CUSTOM = "custom"


class ObservabilityTool(str, Enum):
    PROMETHEUS = "prometheus"
    GRAFANA = "grafana"
    LOKI = "loki"
    TEMPO = "tempo"
    JAEGER = "jaeger"
    ALERTMANAGER = "alertmanager"
    VICTORIA_METRICS = "victoria-metrics"
    ELASTIC = "elasticsearch"
    OPENSEARCH = "opensearch"
    DATADOG = "datadog"
    NEW_RELIC = "new-relic"
    CUSTOM = "custom"


class TerraformResourceKind(str, Enum):
    VPC = "vpc"
    SUBNET = "subnet"
    SECURITY_GROUP = "security_group"
    LOAD_BALANCER = "load_balancer"
    MANAGED_K8S = "managed_kubernetes"
    NODE_POOL = "node_pool"
    IAM_ROLE = "iam_role"
    SERVICE_ACCOUNT = "service_account"
    DNS_ZONE = "dns_zone"
    STORAGE_BUCKET = "storage_bucket"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    SECRET_BACKEND = "secret_backend"
    REGISTRY = "registry"
    CUSTOM = "custom"


# ─── Sub-models ──────────────────────────────────────────────────────────────

class ResourceRequirements(BaseModel):
    cpu_request: str = "100m"
    memory_request: str = "128Mi"
    cpu_limit: str = "500m"
    memory_limit: str = "512Mi"


class ContainerPort(BaseModel):
    name: str
    port: int
    protocol: str = "TCP"


class EnvVar(BaseModel):
    name: str
    value: Optional[str] = None
    value_from_secret: Optional[str] = None
    value_from_configmap: Optional[str] = None


class VolumeMount(BaseModel):
    name: str
    mount_path: str
    read_only: bool = False


class HealthProbe(BaseModel):
    path: Optional[str] = None
    port: Optional[int] = None
    initial_delay_seconds: int = 10
    period_seconds: int = 10
    failure_threshold: int = 3


class Probes(BaseModel):
    liveness: Optional[HealthProbe] = None
    readiness: Optional[HealthProbe] = None
    startup: Optional[HealthProbe] = None


class ServicePort(BaseModel):
    name: str
    port: int
    target_port: int
    protocol: str = "TCP"
    node_port: Optional[int] = None


class IngressRule(BaseModel):
    host: str
    path: str = "/"
    path_type: str = "Prefix"
    service_name: str
    service_port: int


class TLSConfig(BaseModel):
    hosts: List[str] = Field(default_factory=list)
    secret_name: Optional[str] = None


class StorageRequest(BaseModel):
    size: str = "10Gi"
    access_modes: List[str] = Field(default_factory=lambda: ["ReadWriteOnce"])
    storage_class_name: Optional[str] = None


class AutoscalingMetric(BaseModel):
    type: str = "cpu"
    target_value: int = 70


class HPAConfig(BaseModel):
    min_replicas: int = 1
    max_replicas: int = 5
    metrics: List[AutoscalingMetric] = Field(default_factory=list)


class NodeSelector(BaseModel):
    labels: Dict[str, str] = Field(default_factory=dict)
    taints: List[Dict[str, str]] = Field(default_factory=list)
    tolerations: List[Dict[str, Any]] = Field(default_factory=list)


class Labels(BaseModel):
    app: Optional[str] = None
    component: Optional[str] = None
    environment: Optional[str] = None
    tier: Optional[str] = None
    extra: Dict[str, str] = Field(default_factory=dict)

    def as_dict(self) -> Dict[str, str]:
        d = {}
        if self.app:
            d["app"] = self.app
        if self.component:
            d["app.kubernetes.io/component"] = self.component
        if self.environment:
            d["environment"] = self.environment
        if self.tier:
            d["tier"] = self.tier
        d.update(self.extra)
        return d


# ─── Primary Entities ────────────────────────────────────────────────────────

class ConfigMap(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    namespace: str = "default"
    data: Dict[str, str] = Field(default_factory=dict)
    labels: Labels = Field(default_factory=Labels)
    annotations: Dict[str, str] = Field(default_factory=dict)


class Secret(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    namespace: str = "default"
    secret_type: str = "Opaque"
    keys: List[str] = Field(default_factory=list)
    labels: Labels = Field(default_factory=Labels)
    annotations: Dict[str, str] = Field(default_factory=dict)
    external_secret_store: Optional[str] = None


class PersistentVolumeClaim(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    namespace: str = "default"
    storage: StorageRequest = Field(default_factory=StorageRequest)
    labels: Labels = Field(default_factory=Labels)


class StorageClass(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    provisioner: str
    reclaim_policy: str = "Retain"
    volume_binding_mode: str = "WaitForFirstConsumer"
    parameters: Dict[str, str] = Field(default_factory=dict)


class AutoscalingConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    target_ref: str
    hpa: Optional[HPAConfig] = None
    vpa_enabled: bool = False


class NetworkPolicy(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    namespace: str = "default"
    pod_selector: Dict[str, str] = Field(default_factory=dict)
    policy_types: List[str] = Field(default_factory=lambda: ["Ingress", "Egress"])
    ingress_rules: List[Dict[str, Any]] = Field(default_factory=list)
    egress_rules: List[Dict[str, Any]] = Field(default_factory=list)


class Workload(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    namespace: str = "default"
    kind: WorkloadKind = WorkloadKind.DEPLOYMENT
    replicas: int = 1
    image: str = "placeholder:latest"
    image_pull_policy: str = "IfNotPresent"
    ports: List[ContainerPort] = Field(default_factory=list)
    env: List[EnvVar] = Field(default_factory=list)
    resources: ResourceRequirements = Field(default_factory=ResourceRequirements)
    probes: Probes = Field(default_factory=Probes)
    volume_mounts: List[VolumeMount] = Field(default_factory=list)
    pvc_refs: List[str] = Field(default_factory=list)
    configmap_refs: List[str] = Field(default_factory=list)
    secret_refs: List[str] = Field(default_factory=list)
    node_selector: NodeSelector = Field(default_factory=NodeSelector)
    labels: Labels = Field(default_factory=Labels)
    annotations: Dict[str, str] = Field(default_factory=dict)
    service_account: Optional[str] = None
    schedule: Optional[str] = None  # for CronJob
    use_helm: bool = False
    helm_chart: Optional[str] = None
    component_type: ComponentType = ComponentType.DEPLOYMENT


class Service(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    namespace: str = "default"
    service_type: ServiceType = ServiceType.CLUSTER_IP
    ports: List[ServicePort] = Field(default_factory=list)
    selector: Dict[str, str] = Field(default_factory=dict)
    workload_ref: Optional[str] = None
    labels: Labels = Field(default_factory=Labels)
    annotations: Dict[str, str] = Field(default_factory=dict)


class Ingress(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    namespace: str = "default"
    ingress_class: IngressClass = IngressClass.NGINX
    rules: List[IngressRule] = Field(default_factory=list)
    tls: List[TLSConfig] = Field(default_factory=list)
    annotations: Dict[str, str] = Field(default_factory=dict)
    labels: Labels = Field(default_factory=Labels)


class Gateway(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    namespace: str = "default"
    gateway_class: str = "istio"
    listeners: List[Dict[str, Any]] = Field(default_factory=list)
    labels: Labels = Field(default_factory=Labels)
    annotations: Dict[str, str] = Field(default_factory=dict)


class ObservabilityStack(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tools: List[ObservabilityTool] = Field(
        default_factory=lambda: [
            ObservabilityTool.PROMETHEUS,
            ObservabilityTool.GRAFANA,
            ObservabilityTool.ALERTMANAGER,
        ]
    )
    namespace: str = "monitoring"
    enable_service_monitors: bool = True
    enable_pod_monitors: bool = False
    enable_tracing: bool = False
    loki_enabled: bool = True
    tempo_enabled: bool = False
    custom_dashboards: List[str] = Field(default_factory=list)
    alert_receiver: str = "pagerduty"
    retention_days: int = 15


class TerraformResource(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    kind: TerraformResourceKind
    provider: CloudProvider = CloudProvider.AWS
    module_source: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    outputs: List[str] = Field(default_factory=list)
    depends_on: List[str] = Field(default_factory=list)


class ExternalDependency(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    kind: str
    endpoint: Optional[str] = None
    managed: bool = False
    cloud_resource_ref: Optional[str] = None
    notes: str = ""


class CloudResource(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    kind: str
    provider: CloudProvider
    region: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    terraform_ref: Optional[str] = None


class NodeGroup(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    instance_type: str = "m5.large"
    min_size: int = 1
    max_size: int = 5
    desired_size: int = 2
    labels: Dict[str, str] = Field(default_factory=dict)
    taints: List[Dict[str, str]] = Field(default_factory=list)


class Namespace(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    workloads: List[Workload] = Field(default_factory=list)
    services: List[Service] = Field(default_factory=list)
    ingresses: List[Ingress] = Field(default_factory=list)
    gateways: List[Gateway] = Field(default_factory=list)
    configmaps: List[ConfigMap] = Field(default_factory=list)
    secrets: List[Secret] = Field(default_factory=list)
    pvcs: List[PersistentVolumeClaim] = Field(default_factory=list)
    autoscaling: List[AutoscalingConfig] = Field(default_factory=list)
    network_policies: List[NetworkPolicy] = Field(default_factory=list)
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)


class Cluster(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    provider: CloudProvider = CloudProvider.AWS
    kubernetes_version: str = "1.31"
    region: Optional[str] = None
    namespaces: List[Namespace] = Field(default_factory=list)
    node_groups: List[NodeGroup] = Field(default_factory=list)
    storage_classes: List[StorageClass] = Field(default_factory=list)
    observability: Optional[ObservabilityStack] = None
    service_mesh: Optional[str] = None
    networking_plugin: str = "cilium"
    ingress_controller: IngressClass = IngressClass.NGINX


class Edge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    target_id: str
    label: Optional[str] = None
    protocol: Optional[str] = None
    port: Optional[int] = None
    bidirectional: bool = False


class Platform(BaseModel):
    """Root model representing the entire inferred platform."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "my-platform"
    description: str = ""
    clusters: List[Cluster] = Field(default_factory=list)
    external_dependencies: List[ExternalDependency] = Field(default_factory=list)
    cloud_resources: List[CloudResource] = Field(default_factory=list)
    terraform_resources: List[TerraformResource] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)
    environments: List[str] = Field(default_factory=lambda: ["dev", "staging", "prod"])
    gitops_tool: str = "argocd"
    assumptions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
