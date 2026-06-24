"""
Inference engine: converts a ParsedDiagram → Platform canonical model.

Strategy:
1. Classify every node into a ComponentType.
2. Find cluster nodes (or create a default one).
3. Find namespace nodes (or create a default namespace per cluster).
4. Map all other nodes into the deepest namespace that contains them.
5. Synthesize Kubernetes objects from classified nodes.
6. Synthesize edges → service-to-workload linkages and network connections.
"""
from __future__ import annotations

import re
import uuid
from typing import Optional

from .classifier import ComponentClassifier
from ..models.diagram import ParsedDiagram, ParsedNode
from ..models.platform import (
    AutoscalingConfig,
    CloudProvider,
    CloudResource,
    Cluster,
    ComponentType,
    ConfigMap,
    ContainerPort,
    ExternalDependency,
    HPAConfig,
    IngressClass,
    IngressRule,
    Labels,
    Namespace,
    NetworkPolicy,
    NodeGroup,
    ObservabilityStack,
    ObservabilityTool,
    PersistentVolumeClaim,
    Platform,
    Secret,
    Service,
    ServicePort,
    ServiceType,
    StorageRequest,
    TerraformResource,
    TerraformResourceKind,
    Workload,
    WorkloadKind,
    Ingress,
    Gateway,
    Edge,
)


class InferenceEngine:
    def __init__(self) -> None:
        self.classifier = ComponentClassifier()

    def infer(self, diagram: ParsedDiagram, name: str = "platform", notes: str = "") -> Platform:
        # Classify all nodes
        classified: dict[str, ComponentType] = {
            n.id: self.classifier.classify(n) for n in diagram.nodes
        }
        node_map: dict[str, ParsedNode] = {n.id: n for n in diagram.nodes}

        assumptions: list[str] = list(diagram.parser_notes)

        # ── 1. Find or create clusters ────────────────────────────────────────
        cluster_nodes = [n for n in diagram.nodes if classified[n.id] == ComponentType.CLUSTER]
        if not cluster_nodes:
            cluster_nodes = [_synthetic_node("cluster-1", "Kubernetes Cluster")]
            assumptions.append("No explicit cluster node found — created a default single cluster")

        clusters: list[Cluster] = []
        for cn in cluster_nodes:
            cluster = _build_cluster(cn)

            # ── 2. Find namespaces inside this cluster ────────────────────────
            ns_nodes = _children_of_type(cn, node_map, classified, ComponentType.NAMESPACE)
            if not ns_nodes:
                # Check for nodes that look like namespaces by nesting
                ns_nodes = [
                    n for n in diagram.nodes
                    if classified[n.id] == ComponentType.NAMESPACE
                ]
            if not ns_nodes:
                ns_nodes = [_synthetic_node("ns-default", "default")]
                assumptions.append("No namespace nodes found — placed all workloads in 'default' namespace")

            for nn in ns_nodes:
                ns = Namespace(id=nn.id, name=_k8s_name(nn.label))
                ns.labels = {"app.kubernetes.io/managed-by": "kube-blueprint"}

                # ── 3. Workloads inside namespace ─────────────────────────────
                workload_types = {
                    ComponentType.DEPLOYMENT,
                    ComponentType.STATEFULSET,
                    ComponentType.DAEMONSET,
                    ComponentType.JOB,
                    ComponentType.CRONJOB,
                }
                wl_nodes = _children_of_any_type(nn, node_map, classified, workload_types)
                for wn in wl_nodes:
                    wl = _build_workload(wn, classified[wn.id], ns.name)
                    ns.workloads.append(wl)

                    # Auto-generate a ClusterIP service for each workload
                    svc = _auto_service(wl)
                    ns.services.append(svc)

                    # Stateful workloads get a PVC
                    if classified[wn.id] == ComponentType.STATEFULSET:
                        pvc = PersistentVolumeClaim(
                            name=f"{wl.name}-data",
                            namespace=ns.name,
                            storage=StorageRequest(size="20Gi"),
                        )
                        ns.pvcs.append(pvc)
                        wl.pvc_refs.append(pvc.name)
                        assumptions.append(
                            f"Auto-generated 20Gi PVC for stateful workload '{wl.name}'"
                        )

                    # Add HPA for non-daemonset/statefulset workloads
                    if classified[wn.id] == ComponentType.DEPLOYMENT:
                        ns.autoscaling.append(
                            AutoscalingConfig(
                                name=f"{wl.name}-hpa",
                                target_ref=wl.name,
                                hpa=HPAConfig(min_replicas=2, max_replicas=10),
                            )
                        )

                # ── 4. Explicit service nodes ─────────────────────────────────
                svc_nodes = _children_of_type(nn, node_map, classified, ComponentType.SERVICE)
                for sn in svc_nodes:
                    svc = _build_service(sn, ns.name)
                    # Avoid duplicates with auto-generated services
                    existing_names = {s.name for s in ns.services}
                    if svc.name not in existing_names:
                        ns.services.append(svc)

                # ── 5. Ingress nodes ──────────────────────────────────────────
                ingress_nodes = _children_of_type(nn, node_map, classified, ComponentType.INGRESS)
                if not ingress_nodes:
                    ingress_nodes = [
                        n for n in diagram.nodes
                        if classified[n.id] == ComponentType.INGRESS
                    ]
                for ing_n in ingress_nodes:
                    ingress = _build_ingress(ing_n, ns.name, ns.services)
                    ns.ingresses.append(ingress)

                # ── 6. Gateway nodes ──────────────────────────────────────────
                gw_nodes = _children_of_type(nn, node_map, classified, ComponentType.GATEWAY)
                for gw_n in gw_nodes:
                    gw = Gateway(
                        id=gw_n.id,
                        name=_k8s_name(gw_n.label),
                        namespace=ns.name,
                        gateway_class="istio",
                    )
                    ns.gateways.append(gw)

                # ── 7. ConfigMaps ─────────────────────────────────────────────
                for wl in ns.workloads:
                    cm = ConfigMap(
                        name=f"{wl.name}-config",
                        namespace=ns.name,
                        data={"APP_ENV": "production", "LOG_LEVEL": "info"},
                    )
                    ns.configmaps.append(cm)
                    wl.configmap_refs.append(cm.name)

                # ── 8. Secrets ────────────────────────────────────────────────
                for wl in ns.workloads:
                    secret = Secret(
                        name=f"{wl.name}-secret",
                        namespace=ns.name,
                        keys=["DATABASE_URL", "API_KEY"],
                    )
                    ns.secrets.append(secret)
                    wl.secret_refs.append(secret.name)

                # ── 9. Network policy ─────────────────────────────────────────
                deny_all = NetworkPolicy(
                    name=f"{ns.name}-deny-all",
                    namespace=ns.name,
                    pod_selector={},
                    policy_types=["Ingress", "Egress"],
                )
                ns.network_policies.append(deny_all)

                cluster.namespaces.append(ns)

            # ── 10. Observability namespace ───────────────────────────────────
            obs_nodes = [n for n in diagram.nodes if classified[n.id] in (
                ComponentType.MONITORING, ComponentType.LOGGING, ComponentType.TRACING)]
            obs_tools = _infer_obs_tools(obs_nodes)
            cluster.observability = ObservabilityStack(tools=obs_tools)
            if not obs_nodes:
                assumptions.append(
                    "No observability stack detected — defaulting to Prometheus + Grafana + Loki"
                )

            # ── 11. Node group ────────────────────────────────────────────────
            cluster.node_groups.append(
                NodeGroup(name="system", instance_type="m5.xlarge", min_size=2, max_size=6, desired_size=3)
            )

            # ── 12. Orphan node assignment ────────────────────────────────────
            # Nodes not nested inside any namespace (common in Excalidraw) are
            # placed into the first available namespace as a best-effort fallback.
            assigned_ids: set[str] = set()
            for ns in cluster.namespaces:
                for wl in ns.workloads:
                    assigned_ids.add(wl.id)
                for svc in ns.services:
                    assigned_ids.add(svc.id)
                for ing in ns.ingresses:
                    assigned_ids.add(ing.id)

            workload_types = {
                ComponentType.DEPLOYMENT,
                ComponentType.STATEFULSET,
                ComponentType.DAEMONSET,
                ComponentType.JOB,
                ComponentType.CRONJOB,
            }
            orphan_wl_nodes = [
                n for n in diagram.nodes
                if n.id not in assigned_ids and classified.get(n.id) in workload_types
            ]
            if orphan_wl_nodes:
                target_ns = cluster.namespaces[0] if cluster.namespaces else Namespace(name="default")
                if not cluster.namespaces:
                    cluster.namespaces.append(target_ns)
                for wn in orphan_wl_nodes:
                    wl = _build_workload(wn, classified[wn.id], target_ns.name)
                    target_ns.workloads.append(wl)
                    target_ns.services.append(_auto_service(wl))
                    if classified[wn.id] == ComponentType.STATEFULSET:
                        pvc = PersistentVolumeClaim(
                            name=f"{wl.name}-data",
                            namespace=target_ns.name,
                            storage=StorageRequest(size="20Gi"),
                        )
                        target_ns.pvcs.append(pvc)
                        wl.pvc_refs.append(pvc.name)
                assumptions.append(
                    f"Placed {len(orphan_wl_nodes)} uncontained node(s) into namespace '{target_ns.name}'"
                )

            clusters.append(cluster)

        # ── 13. External dependencies ─────────────────────────────────────────
        ext_nodes = [n for n in diagram.nodes if classified[n.id] == ComponentType.EXTERNAL_DEPENDENCY]
        external_deps = [
            ExternalDependency(id=n.id, name=_k8s_name(n.label), kind="external")
            for n in ext_nodes
        ]

        # ── 14. Cloud resources ───────────────────────────────────────────────
        cloud_nodes = [n for n in diagram.nodes if classified[n.id] == ComponentType.CLOUD_RESOURCE]
        cloud_resources = [
            CloudResource(
                id=n.id,
                name=_k8s_name(n.label),
                kind=_infer_cloud_kind(n.label),
                provider=CloudProvider.AWS,
            )
            for n in cloud_nodes
        ]

        # ── 15. Terraform resources ───────────────────────────────────────────
        tf_nodes = [n for n in diagram.nodes if classified[n.id] == ComponentType.TERRAFORM_RESOURCE]
        tf_resources = [
            TerraformResource(
                id=n.id,
                name=_k8s_name(n.label),
                kind=TerraformResourceKind.CUSTOM,
                provider=CloudProvider.AWS,
            )
            for n in tf_nodes
        ]
        # Always generate VPC + managed cluster TF resources
        if not tf_resources:
            tf_resources = [
                TerraformResource(
                    name="vpc",
                    kind=TerraformResourceKind.VPC,
                    provider=CloudProvider.AWS,
                    variables={"cidr_block": "10.0.0.0/16", "az_count": 3},
                ),
                TerraformResource(
                    name="eks-cluster",
                    kind=TerraformResourceKind.MANAGED_K8S,
                    provider=CloudProvider.AWS,
                    variables={"kubernetes_version": "1.31"},
                    depends_on=["vpc"],
                ),
            ]
            assumptions.append("Generated default VPC + EKS Terraform resources")

        # ── 16. Edges ─────────────────────────────────────────────────────────
        edges = [
            Edge(
                id=e.id,
                source_id=e.source_id,
                target_id=e.target_id,
                label=e.label,
            )
            for e in diagram.edges
        ]

        return Platform(
            name=_k8s_name(name),
            clusters=clusters,
            external_dependencies=external_deps,
            cloud_resources=cloud_resources,
            terraform_resources=tf_resources,
            edges=edges,
            assumptions=assumptions,
        )


# ─── Builders ─────────────────────────────────────────────────────────────────

def _build_cluster(node: ParsedNode) -> Cluster:
    provider = _infer_provider(node.label)
    return Cluster(
        id=node.id,
        name=_k8s_name(node.label) or "main-cluster",
        provider=provider,
        kubernetes_version="1.31",
    )


def _build_workload(node: ParsedNode, ctype: ComponentType, namespace: str) -> Workload:
    kind_map = {
        ComponentType.STATEFULSET: WorkloadKind.STATEFULSET,
        ComponentType.DAEMONSET: WorkloadKind.DAEMONSET,
        ComponentType.JOB: WorkloadKind.JOB,
        ComponentType.CRONJOB: WorkloadKind.CRONJOB,
    }
    kind = kind_map.get(ctype, WorkloadKind.DEPLOYMENT)
    wl_name = _k8s_name(node.label)
    image = _infer_image(node.label)
    port = _infer_port(node.label)

    wl = Workload(
        id=node.id,
        name=wl_name,
        namespace=namespace,
        kind=kind,
        replicas=1 if kind != WorkloadKind.DEPLOYMENT else 2,
        image=image,
        component_type=ctype,
        labels=Labels(app=wl_name, component=wl_name),
    )
    if port:
        wl.ports.append(ContainerPort(name="http", port=port))
    return wl


def _auto_service(wl: Workload) -> Service:
    port = wl.ports[0].port if wl.ports else 80
    svc_type = ServiceType.CLUSTER_IP
    if wl.kind == WorkloadKind.STATEFULSET:
        svc_type = ServiceType.HEADLESS
    return Service(
        name=f"{wl.name}",
        namespace=wl.namespace,
        service_type=svc_type,
        selector={"app": wl.name},
        workload_ref=wl.name,
        ports=[ServicePort(name="http", port=port, target_port=port)],
        labels=Labels(app=wl.name),
    )


def _build_service(node: ParsedNode, namespace: str) -> Service:
    name = _k8s_name(node.label)
    svc_type_map = {
        "loadbalancer": ServiceType.LOAD_BALANCER,
        "lb": ServiceType.LOAD_BALANCER,
        "nodeport": ServiceType.NODE_PORT,
        "headless": ServiceType.HEADLESS,
    }
    svc_type = ServiceType.CLUSTER_IP
    for kw, st in svc_type_map.items():
        if kw in node.label.lower():
            svc_type = st
            break
    return Service(
        id=node.id,
        name=name,
        namespace=namespace,
        service_type=svc_type,
        ports=[ServicePort(name="http", port=80, target_port=8080)],
        labels=Labels(app=name),
    )


def _build_ingress(node: ParsedNode, namespace: str, services: list[Service]) -> Ingress:
    name = _k8s_name(node.label) or "ingress"
    rules = []
    for svc in services:
        port = svc.ports[0].port if svc.ports else 80
        rules.append(
            IngressRule(
                host=f"{svc.name}.example.com",
                path="/",
                service_name=svc.name,
                service_port=port,
            )
        )
    return Ingress(
        id=node.id,
        name=name,
        namespace=namespace,
        rules=rules,
        ingress_class=IngressClass.NGINX,
        annotations={"nginx.ingress.kubernetes.io/rewrite-target": "/"},
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _children_of_type(
    parent: ParsedNode,
    node_map: dict[str, ParsedNode],
    classified: dict[str, ComponentType],
    ctype: ComponentType,
) -> list[ParsedNode]:
    return [
        node_map[cid]
        for cid in parent.children
        if cid in node_map and classified.get(cid) == ctype
    ]


def _children_of_any_type(
    parent: ParsedNode,
    node_map: dict[str, ParsedNode],
    classified: dict[str, ComponentType],
    ctypes: set[ComponentType],
) -> list[ParsedNode]:
    return [
        node_map[cid]
        for cid in parent.children
        if cid in node_map and classified.get(cid) in ctypes
    ]


def _synthetic_node(node_id: str, label: str) -> ParsedNode:
    return ParsedNode(id=node_id, label=label)


def _k8s_name(label: str) -> str:
    """Convert an arbitrary label to a valid Kubernetes resource name."""
    name = label.lower().strip()
    name = re.sub(r"[^a-z0-9\-]", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name[:63] or "unnamed"


def _infer_provider(label: str) -> CloudProvider:
    l = label.lower()
    if "aws" in l or "eks" in l:
        return CloudProvider.AWS
    if "gcp" in l or "gke" in l:
        return CloudProvider.GCP
    if "azure" in l or "aks" in l:
        return CloudProvider.AZURE
    return CloudProvider.AWS


def _infer_image(label: str) -> str:
    known = {
        "nginx": "nginx:1.27",
        "postgres": "postgres:16",
        "postgresql": "postgres:16",
        "mysql": "mysql:8.4",
        "redis": "redis:7",
        "kafka": "confluentinc/cp-kafka:7.7.0",
        "rabbitmq": "rabbitmq:3.13-management",
        "elasticsearch": "docker.elastic.co/elasticsearch/elasticsearch:8.15.0",
        "grafana": "grafana/grafana:11.0.0",
        "prometheus": "prom/prometheus:v2.53.0",
        "loki": "grafana/loki:3.0.0",
    }
    lbl = label.lower().strip()
    for kw, img in known.items():
        if kw in lbl:
            return img
    # Default placeholder
    name = _k8s_name(label) or "app"
    return f"your-registry/{name}:latest"


def _infer_port(label: str) -> Optional[int]:
    known_ports = {
        "postgres": 5432, "postgresql": 5432, "mysql": 3306,
        "redis": 6379, "kafka": 9092, "rabbitmq": 5672,
        "elasticsearch": 9200, "mongodb": 27017,
        "nginx": 80, "grafana": 3000, "prometheus": 9090, "loki": 3100,
    }
    lbl = label.lower()
    for kw, port in known_ports.items():
        if kw in lbl:
            return port
    # Heuristic: HTTP apps default to 8080
    return 8080


def _infer_cloud_kind(label: str) -> str:
    l = label.lower()
    for kw in ("rds", "postgres", "mysql", "database", "db"):
        if kw in l:
            return "database"
    for kw in ("s3", "bucket", "gcs", "blob"):
        if kw in l:
            return "object_storage"
    for kw in ("sqs", "sns", "pubsub", "queue"):
        if kw in l:
            return "queue"
    return "cloud_service"


def _infer_obs_tools(nodes: list[ParsedNode]) -> list[ObservabilityTool]:
    tools = set()
    for n in nodes:
        label = n.label.lower()
        if "prometheus" in label:
            tools.add(ObservabilityTool.PROMETHEUS)
        if "grafana" in label:
            tools.add(ObservabilityTool.GRAFANA)
        if "alert" in label:
            tools.add(ObservabilityTool.ALERTMANAGER)
        if "loki" in label:
            tools.add(ObservabilityTool.LOKI)
        if "tempo" in label:
            tools.add(ObservabilityTool.TEMPO)
        if "jaeger" in label:
            tools.add(ObservabilityTool.JAEGER)

    if not tools:
        tools = {
            ObservabilityTool.PROMETHEUS,
            ObservabilityTool.GRAFANA,
            ObservabilityTool.ALERTMANAGER,
            ObservabilityTool.LOKI,
        }
    return sorted(tools, key=lambda t: t.value)
