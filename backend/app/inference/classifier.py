"""
Rule-based component classifier.

Maps diagram node labels / tags / shapes → ComponentType.
Order matters: more specific rules first.
"""
import re
from typing import Optional

from ..models.diagram import ParsedNode
from ..models.platform import ComponentType

# Label patterns → ComponentType
_LABEL_RULES: list[tuple[re.Pattern, ComponentType]] = [
    # Cluster / infra boundary
    (re.compile(r"\b(cluster|k8s|kubernetes|eks|gke|aks)\b", re.I), ComponentType.CLUSTER),
    # Namespaces
    (re.compile(r"\b(namespace|ns)\b", re.I), ComponentType.NAMESPACE),
    # Stateful workloads (must come before generic deployment)
    (re.compile(r"\b(postgres|postgresql|mysql|mariadb|mongodb|cassandra|cockroach|tidb|mssql|oracle|db|database|statefulset|sts)\b", re.I), ComponentType.STATEFULSET),
    (re.compile(r"\b(redis|memcache|memcached|cache|valkey)\b", re.I), ComponentType.STATEFULSET),
    (re.compile(r"\b(kafka|rabbitmq|nats|pulsar|activemq|queue|broker|zookeeper|mq)\b", re.I), ComponentType.STATEFULSET),
    # Daemon workloads
    (re.compile(r"\b(daemonset|ds|node.agent|log.agent|fluentd|fluentbit|filebeat|promtail)\b", re.I), ComponentType.DAEMONSET),
    # Jobs / CronJobs
    (re.compile(r"\b(cronjob|cron.?job|scheduled.?job)\b", re.I), ComponentType.CRONJOB),
    (re.compile(r"\b(job|batch|migration)\b", re.I), ComponentType.JOB),
    # Deployments (generic apps)
    (re.compile(r"\b(deployment|deploy|pod|app|service|api|backend|frontend|worker|server|web|gateway.?service|microservice)\b", re.I), ComponentType.DEPLOYMENT),
    # Services
    (re.compile(r"\b(svc|service|clusterip|nodeport|loadbalancer|lb)\b", re.I), ComponentType.SERVICE),
    # Ingress / Gateway
    (re.compile(r"\b(ingress|nginx|traefik|haproxy|ingress.?controller)\b", re.I), ComponentType.INGRESS),
    (re.compile(r"\b(gateway|istio|envoy|api.?gateway|gateway.?api)\b", re.I), ComponentType.GATEWAY),
    # Config / Secrets
    (re.compile(r"\b(configmap|config.?map|cm)\b", re.I), ComponentType.CONFIGMAP),
    (re.compile(r"\b(secret|vault|sealed.?secret|external.?secret|eso)\b", re.I), ComponentType.SECRET),
    # Storage
    (re.compile(r"\b(pvc|persistent.?volume|claim|storage|disk|efs|ebs|gcs|azure.?disk|nfs|ceph|rook)\b", re.I), ComponentType.PVC),
    (re.compile(r"\b(storage.?class|sc)\b", re.I), ComponentType.STORAGE_CLASS),
    # Autoscaling
    (re.compile(r"\b(hpa|horizontal.?pod.?autoscal|vpa|vertical.?pod.?autoscal|keda|autoscal)\b", re.I), ComponentType.HPA),
    # Service mesh
    (re.compile(r"\b(istio|linkerd|cilium|consul|service.?mesh|sidecar|envoy)\b", re.I), ComponentType.SERVICE_MESH),
    # Monitoring / Observability
    (re.compile(r"\b(prometheus|grafana|alertmanager|thanos|victoria|mimir|cortex|monitor)\b", re.I), ComponentType.MONITORING),
    (re.compile(r"\b(loki|elasticsearch|opensearch|fluentd|fluentbit|filebeat|logstash|log)\b", re.I), ComponentType.LOGGING),
    (re.compile(r"\b(jaeger|zipkin|tempo|otel|opentelemetry|trace|tracing|span)\b", re.I), ComponentType.TRACING),
    # External / cloud
    (re.compile(r"\b(external|outside|internet|user|client|browser|cdn|cloudfront|akamai)\b", re.I), ComponentType.EXTERNAL_DEPENDENCY),
    (re.compile(r"\b(aws|gcp|azure|cloud|s3|rds|sqs|sns|ses|route53|ecr|gcr|acr|gcs|iam)\b", re.I), ComponentType.CLOUD_RESOURCE),
    (re.compile(r"\b(terraform|tofu|opentofu|infra|vpc|subnet|security.?group|firewall)\b", re.I), ComponentType.TERRAFORM_RESOURCE),
    # Network policies
    (re.compile(r"\b(network.?policy|netpol|calico|policy)\b", re.I), ComponentType.NETWORK_POLICY),
]

_TAG_MAP: dict[str, ComponentType] = {
    "cluster": ComponentType.CLUSTER,
    "namespace": ComponentType.NAMESPACE,
    "deployment": ComponentType.DEPLOYMENT,
    "statefulset": ComponentType.STATEFULSET,
    "daemonset": ComponentType.DAEMONSET,
    "job": ComponentType.JOB,
    "cronjob": ComponentType.CRONJOB,
    "service": ComponentType.SERVICE,
    "ingress": ComponentType.INGRESS,
    "gateway": ComponentType.GATEWAY,
    "configmap": ComponentType.CONFIGMAP,
    "secret": ComponentType.SECRET,
    "pvc": ComponentType.PVC,
    "storage_class": ComponentType.STORAGE_CLASS,
    "hpa": ComponentType.HPA,
    "service_mesh": ComponentType.SERVICE_MESH,
    "monitoring": ComponentType.MONITORING,
    "logging": ComponentType.LOGGING,
    "tracing": ComponentType.TRACING,
    "external": ComponentType.EXTERNAL_DEPENDENCY,
    "cloud": ComponentType.CLOUD_RESOURCE,
    "terraform": ComponentType.TERRAFORM_RESOURCE,
    "network_policy": ComponentType.NETWORK_POLICY,
    "database": ComponentType.STATEFULSET,
    "db": ComponentType.STATEFULSET,
    "cache": ComponentType.STATEFULSET,
    "queue": ComponentType.STATEFULSET,
}

_SHAPE_HINTS: dict[str, ComponentType] = {
    "cylinder": ComponentType.STATEFULSET,
    "database": ComponentType.STATEFULSET,
    "cloud": ComponentType.CLOUD_RESOURCE,
    "subgraph": ComponentType.NAMESPACE,
}


class ComponentClassifier:
    def classify(self, node: ParsedNode) -> ComponentType:
        # 1. Explicit tags (from vision parser or user)
        for tag in node.tags:
            if tag.lower() in _TAG_MAP:
                return _TAG_MAP[tag.lower()]

        # 2. Shape hint
        if node.shape and node.shape.lower() in _SHAPE_HINTS:
            return _SHAPE_HINTS[node.shape.lower()]

        # 3. Label rules
        combined = f"{node.label} {node.notes}".strip()
        for pattern, ctype in _LABEL_RULES:
            if pattern.search(combined):
                return ctype

        # 4. Structural inference: nodes with many children → namespace/cluster
        if len(node.children) >= 3:
            return ComponentType.NAMESPACE

        return ComponentType.UNKNOWN
