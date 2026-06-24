"""
Observability / monitoring generator.

Generates:
  observability/
    kube-prometheus-stack/
      values.yaml
      values-dev.yaml
      values-staging.yaml
      values-prod.yaml
    loki-stack/
      values.yaml
    dashboards/
      platform-overview.json   (Grafana dashboard)
    alerts/
      platform-alerts.yaml     (PrometheusRule)
    service-monitors/
      <namespace>-sm.yaml      (ServiceMonitor per namespace)
    README.md
"""
from __future__ import annotations

import json

from .base import BaseGenerator, dump_yaml
from ..models.generation import GenerationRequest, GenerationResult
from ..models.platform import ObservabilityTool


class ObservabilityGenerator(BaseGenerator):
    def generate(self, request: GenerationRequest, result: GenerationResult) -> None:
        platform = request.platform

        for cluster in platform.clusters:
            obs = cluster.observability
            if not obs:
                continue

            self._gen_kube_prometheus_stack(obs, request.environments, result)
            if ObservabilityTool.LOKI in obs.tools:
                self._gen_loki(obs, result)
            if ObservabilityTool.TEMPO in obs.tools:
                self._gen_tempo(result)

            for ns in cluster.namespaces:
                if obs.enable_service_monitors and ns.services:
                    self._gen_service_monitor(ns, result)

            self._gen_alert_rules(cluster, result)
            self._gen_grafana_dashboard(platform, result)
            self._gen_readme(obs, result)

    def _gen_kube_prometheus_stack(self, obs, environments: list[str], result: GenerationResult) -> None:
        values = {
            "fullnameOverride": "prometheus",
            "defaultRules": {
                "create": True,
                "rules": {
                    "alertmanager": True, "etcd": True, "general": True,
                    "k8s": True, "kubeApiserver": True, "kubeApiserverAvailability": True,
                    "kubePrometheusNodeAlerting": True, "kubePrometheusNodeRecording": True,
                    "kubeScheduler": True, "kubeStateMetrics": True, "kubelet": True,
                    "network": True, "node": True, "prometheus": True,
                },
            },
            "alertmanager": {
                "enabled": True,
                "config": {
                    "global": {"resolve_timeout": "5m"},
                    "route": {
                        "group_by": ["alertname", "namespace"],
                        "group_wait": "30s",
                        "group_interval": "5m",
                        "repeat_interval": "4h",
                        "receiver": "null",
                        "routes": [{"matchers": ["alertname=Watchdog"], "receiver": "null"}],
                    },
                    "receivers": [{"name": "null"}],
                },
            },
            "grafana": {
                "enabled": True,
                "adminPassword": "<GRAFANA_ADMIN_PASSWORD_PLACEHOLDER>",
                "ingress": {
                    "enabled": True,
                    "ingressClassName": "nginx",
                    "hosts": ["grafana.example.com"],
                },
                "persistence": {"enabled": True, "size": "10Gi"},
                "dashboardProviders": {
                    "dashboardproviders.yaml": {
                        "apiVersion": 1,
                        "providers": [{"name": "default", "orgId": 1, "folder": "", "type": "file", "disableDeletion": False, "editable": True, "options": {"path": "/var/lib/grafana/dashboards"}}],
                    }
                },
                "sidecar": {"dashboards": {"enabled": True, "label": "grafana_dashboard"}},
            },
            "prometheus": {
                "prometheusSpec": {
                    "retention": f"{obs.retention_days}d",
                    "storageSpec": {"volumeClaimTemplate": {"spec": {"accessModes": ["ReadWriteOnce"], "resources": {"requests": {"storage": "50Gi"}}}}},
                    "serviceMonitorSelectorNilUsesHelmValues": False,
                    "podMonitorSelectorNilUsesHelmValues": False,
                    "ruleSelectorNilUsesHelmValues": False,
                },
            },
            "nodeExporter": {"enabled": True},
            "kubeStateMetrics": {"enabled": True},
        }
        result.add_file("observability/kube-prometheus-stack/values.yaml", dump_yaml(values), "Kube Prometheus Stack values")

        for env in environments:
            retention = {"dev": 7, "staging": 14, "prod": 30}.get(env, 15)
            storage = {"dev": "20Gi", "staging": "50Gi", "prod": "200Gi"}.get(env, "50Gi")
            env_values = {
                "prometheus": {
                    "prometheusSpec": {
                        "retention": f"{retention}d",
                        "storageSpec": {"volumeClaimTemplate": {"spec": {"resources": {"requests": {"storage": storage}}}}},
                    }
                },
                "grafana": {
                    "ingress": {"hosts": [f"grafana.{env}.example.com"]},
                },
            }
            result.add_file(f"observability/kube-prometheus-stack/values-{env}.yaml", dump_yaml(env_values), f"Kube Prometheus Stack {env} values")

    def _gen_loki(self, obs, result: GenerationResult) -> None:
        values = {
            "loki": {
                "auth_enabled": False,
                "storage": {"type": "filesystem"},
                "commonConfig": {"replication_factor": 1},
                "schemaConfig": {
                    "configs": [{
                        "from": "2024-01-01",
                        "store": "tsdb",
                        "object_store": "filesystem",
                        "schema": "v13",
                        "index": {"prefix": "loki_index_", "period": "24h"},
                    }]
                },
            },
            "singleBinary": {"replicas": 1, "persistence": {"size": "20Gi"}},
            "gateway": {"enabled": True},
            "monitoring": {"selfMonitoring": {"enabled": False}, "lokiCanary": {"enabled": False}},
        }
        result.add_file("observability/loki-stack/values.yaml", dump_yaml(values), "Loki stack values")

    def _gen_tempo(self, result: GenerationResult) -> None:
        values = {
            "tempo": {
                "storage": {"trace": {"backend": "local", "local": {"path": "/var/tempo/traces"}}},
                "retention": "72h",
            },
            "persistence": {"enabled": True, "size": "10Gi"},
        }
        result.add_file("observability/tempo/values.yaml", dump_yaml(values), "Tempo values")

    def _gen_service_monitor(self, ns, result: GenerationResult) -> None:
        for svc in ns.services:
            if not svc.ports:
                continue
            port_name = svc.ports[0].name
            doc = {
                "apiVersion": "monitoring.coreos.com/v1",
                "kind": "ServiceMonitor",
                "metadata": {
                    "name": f"{svc.name}-sm",
                    "namespace": ns.name,
                    "labels": {"release": "prometheus"},
                },
                "spec": {
                    "selector": {"matchLabels": svc.selector or {"app": svc.name}},
                    "endpoints": [{"port": port_name, "interval": "30s", "path": "/metrics"}],
                    "namespaceSelector": {"matchNames": [ns.name]},
                },
            }
            result.add_file(
                f"observability/service-monitors/{ns.name}-{svc.name}-sm.yaml",
                dump_yaml(doc),
                f"ServiceMonitor for {svc.name}",
            )

    def _gen_alert_rules(self, cluster, result: GenerationResult) -> None:
        workload_names = [wl.name for ns in cluster.namespaces for wl in ns.workloads]
        rules = []

        for wl_name in workload_names:
            rules += [
                {
                    "alert": f"{wl_name.replace('-', '_').title()}HighErrorRate",
                    "expr": f'rate(http_requests_total{{job="{wl_name}",status=~"5.."}}[5m]) / rate(http_requests_total{{job="{wl_name}"}}[5m]) > 0.05',
                    "for": "5m",
                    "labels": {"severity": "warning", "workload": wl_name},
                    "annotations": {
                        "summary": f"High error rate on {wl_name}",
                        "description": f"Error rate for {wl_name} is above 5% for 5 minutes.",
                    },
                },
                {
                    "alert": f"{wl_name.replace('-', '_').title()}PodCrashLooping",
                    "expr": f'increase(kube_pod_container_status_restarts_total{{container="{wl_name}"}}[1h]) > 5',
                    "for": "5m",
                    "labels": {"severity": "critical", "workload": wl_name},
                    "annotations": {
                        "summary": f"{wl_name} is crash-looping",
                        "description": f"Pod {wl_name} has restarted more than 5 times in the last hour.",
                    },
                },
            ]

        # Cluster-level alerts
        rules += [
            {
                "alert": "HighCPUUsage",
                "expr": '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 85',
                "for": "10m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "High node CPU utilization (>85%)"},
            },
            {
                "alert": "HighMemoryUsage",
                "expr": "(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100 > 85",
                "for": "10m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "High node memory utilization (>85%)"},
            },
            {
                "alert": "PersistentVolumeAlmostFull",
                "expr": "kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes * 100 > 85",
                "for": "5m",
                "labels": {"severity": "warning"},
                "annotations": {"summary": "PVC almost full (>85%)"},
            },
        ]

        doc = {
            "apiVersion": "monitoring.coreos.com/v1",
            "kind": "PrometheusRule",
            "metadata": {
                "name": f"{cluster.name}-alerts",
                "namespace": "monitoring",
                "labels": {"release": "prometheus", "role": "alert-rules"},
            },
            "spec": {"groups": [{"name": f"{cluster.name}.rules", "rules": rules}]},
        }
        result.add_file(f"observability/alerts/{cluster.name}-alerts.yaml", dump_yaml(doc), f"Alert rules for {cluster.name}")

    def _gen_grafana_dashboard(self, platform, result: GenerationResult) -> None:
        dashboard = {
            "title": f"{platform.name} Overview",
            "uid": "platform-overview",
            "schemaVersion": 38,
            "version": 1,
            "refresh": "30s",
            "time": {"from": "now-6h", "to": "now"},
            "panels": [
                {
                    "id": 1,
                    "title": "CPU Usage",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                    "targets": [{"expr": '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)', "legendFormat": "{{instance}}"}],
                },
                {
                    "id": 2,
                    "title": "Memory Usage",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
                    "targets": [{"expr": "(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100", "legendFormat": "{{instance}}"}],
                },
                {
                    "id": 3,
                    "title": "Pod Count by Namespace",
                    "type": "stat",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                    "targets": [{"expr": "count by (namespace) (kube_pod_info)", "legendFormat": "{{namespace}}"}],
                },
                {
                    "id": 4,
                    "title": "HTTP Request Rate",
                    "type": "timeseries",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                    "targets": [{"expr": 'sum by (job) (rate(http_requests_total[5m]))', "legendFormat": "{{job}}"}],
                },
            ],
        }
        result.add_file(
            "observability/dashboards/platform-overview.json",
            json.dumps(dashboard, indent=2),
            "Grafana platform overview dashboard",
        )
        # ConfigMap to load dashboard via sidecar
        cm = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "platform-overview-dashboard",
                "namespace": "monitoring",
                "labels": {"grafana_dashboard": "1"},
            },
            "data": {"platform-overview.json": json.dumps(dashboard)},
        }
        result.add_file("observability/dashboards/platform-overview-cm.yaml", dump_yaml(cm), "Dashboard ConfigMap")

    def _gen_readme(self, obs, result: GenerationResult) -> None:
        tools_list = "\n".join(f"- {t.value}" for t in obs.tools)
        content = f"""# Observability Stack

## Deployed Tools

{tools_list}

## Accessing Dashboards

```bash
# Port-forward Grafana locally
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Open http://localhost:3000
# Default credentials: admin / <GRAFANA_ADMIN_PASSWORD_PLACEHOLDER>
```

## Accessing Prometheus

```bash
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
```

## Accessing Alertmanager

```bash
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-alertmanager 9093:9093
```

## Querying Logs (Loki)

```bash
# Using Grafana Explore with data source: Loki
# Or use logcli:
logcli query '{{namespace="default"}}' --addr=http://localhost:3100
```

## Alert Configuration

Alert rules are in `observability/alerts/`. Edit the PrometheusRule resources to adjust thresholds.
ServiceMonitors are in `observability/service-monitors/`. Add scrape targets by creating new ServiceMonitor resources.

## Retention Policy

| Environment | Metrics Retention | Logs Retention |
|---|---|---|
| dev | 7d | 3d |
| staging | 14d | 7d |
| prod | 30d | 30d |
"""
        result.add_file("observability/README.md", content, "Observability README")
