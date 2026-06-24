"""
Kubernetes manifest generator.

Generates:
  k8s/base/<namespace>/<resource>.yaml      base manifests
  k8s/overlays/<env>/kustomization.yaml     per-environment kustomize overlays
  k8s/overlays/<env>/<namespace>/patch.yaml resource patches
"""
from __future__ import annotations

from .base import BaseGenerator, dump_yaml, k8s_metadata
from ..models.generation import GenerationRequest, GenerationResult
from ..models.platform import (
    AutoscalingConfig,
    Cluster,
    ConfigMap,
    HPAConfig,
    Ingress,
    Namespace,
    NetworkPolicy,
    PersistentVolumeClaim,
    Platform,
    Secret,
    Service,
    ServiceType,
    Workload,
    WorkloadKind,
)

_API_VERSIONS = {
    WorkloadKind.DEPLOYMENT: ("apps/v1", "Deployment"),
    WorkloadKind.STATEFULSET: ("apps/v1", "StatefulSet"),
    WorkloadKind.DAEMONSET: ("apps/v1", "DaemonSet"),
    WorkloadKind.JOB: ("batch/v1", "Job"),
    WorkloadKind.CRONJOB: ("batch/v1", "CronJob"),
}


class KubernetesGenerator(BaseGenerator):
    def generate(self, request: GenerationRequest, result: GenerationResult) -> None:
        platform = request.platform
        all_base_paths: list[str] = []

        for cluster in platform.clusters:
            for ns in cluster.namespaces:
                ns_paths = self._gen_namespace(ns, result)
                all_base_paths.extend(ns_paths)

        # Root kustomization over all bases
        for env in request.environments:
            self._gen_env_overlay(env, platform, result)

        # Global namespace manifests
        for cluster in platform.clusters:
            for ns in cluster.namespaces:
                self._gen_namespace_manifest(ns, result)

    # ── Namespace ─────────────────────────────────────────────────────────────

    def _gen_namespace_manifest(self, ns: Namespace, result: GenerationResult) -> None:
        doc = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": k8s_metadata(
                ns.name,
                labels={**ns.labels, "app.kubernetes.io/managed-by": "kube-blueprint"},
            ),
        }
        result.add_file(
            f"k8s/base/{ns.name}/namespace.yaml",
            dump_yaml(doc),
            f"Namespace {ns.name}",
        )

    def _gen_namespace(self, ns: Namespace, result: GenerationResult) -> list[str]:
        paths: list[str] = [f"k8s/base/{ns.name}/namespace.yaml"]
        kustomize_resources: list[str] = ["namespace.yaml"]

        for wl in ns.workloads:
            p = self._gen_workload(ns, wl, result)
            kustomize_resources.extend(p)
            paths.extend([f"k8s/base/{ns.name}/{r}" for r in p])

        for svc in ns.services:
            p = self._gen_service(ns, svc, result)
            kustomize_resources.append(p)

        for ingress in ns.ingresses:
            p = self._gen_ingress(ns, ingress, result)
            kustomize_resources.append(p)

        for cm in ns.configmaps:
            p = self._gen_configmap(ns, cm, result)
            kustomize_resources.append(p)

        for secret in ns.secrets:
            p = self._gen_secret(ns, secret, result)
            kustomize_resources.append(p)

        for pvc in ns.pvcs:
            p = self._gen_pvc(ns, pvc, result)
            kustomize_resources.append(p)

        for hpa in ns.autoscaling:
            p = self._gen_hpa(ns, hpa, result)
            kustomize_resources.append(p)

        for netpol in ns.network_policies:
            p = self._gen_network_policy(ns, netpol, result)
            kustomize_resources.append(p)

        # kustomization.yaml for this namespace base
        kust = {"apiVersion": "kustomize.config.k8s.io/v1beta1", "kind": "Kustomization", "resources": kustomize_resources}
        result.add_file(f"k8s/base/{ns.name}/kustomization.yaml", dump_yaml(kust), f"Base kustomization for {ns.name}")

        return paths

    # ── Workload ──────────────────────────────────────────────────────────────

    def _gen_workload(self, ns: Namespace, wl: Workload, result: GenerationResult) -> list[str]:
        api_version, kind = _API_VERSIONS.get(wl.kind, ("apps/v1", "Deployment"))

        env_vars = [{"name": e.name, "value": e.value} for e in wl.env if e.value]
        env_vars += [
            {"name": e.name, "valueFrom": {"secretKeyRef": {"name": e.value_from_secret, "key": e.name}}}
            for e in wl.env if e.value_from_secret
        ]
        env_vars += [
            {"name": e.name, "valueFrom": {"configMapKeyRef": {"name": e.value_from_configmap, "key": e.name}}}
            for e in wl.env if e.value_from_configmap
        ]

        # Add envFrom for referenced configmaps and secrets
        env_from = []
        for cm_ref in wl.configmap_refs:
            env_from.append({"configMapRef": {"name": cm_ref}})
        for sec_ref in wl.secret_refs:
            env_from.append({"secretRef": {"name": sec_ref}})

        container: dict = {
            "name": wl.name,
            "image": wl.image,
            "imagePullPolicy": wl.image_pull_policy,
            "resources": {
                "requests": {"cpu": wl.resources.cpu_request, "memory": wl.resources.memory_request},
                "limits": {"cpu": wl.resources.cpu_limit, "memory": wl.resources.memory_limit},
            },
        }
        if wl.ports:
            container["ports"] = [{"name": p.name, "containerPort": p.port, "protocol": p.protocol} for p in wl.ports]
        if env_vars:
            container["env"] = env_vars
        if env_from:
            container["envFrom"] = env_from
        if wl.probes.liveness:
            probe = wl.probes.liveness
            container["livenessProbe"] = {
                "httpGet": {"path": probe.path or "/healthz", "port": probe.port or (wl.ports[0].port if wl.ports else 8080)},
                "initialDelaySeconds": probe.initial_delay_seconds,
                "periodSeconds": probe.period_seconds,
            }
        if wl.probes.readiness:
            probe = wl.probes.readiness
            container["readinessProbe"] = {
                "httpGet": {"path": probe.path or "/ready", "port": probe.port or (wl.ports[0].port if wl.ports else 8080)},
                "initialDelaySeconds": probe.initial_delay_seconds,
                "periodSeconds": probe.period_seconds,
            }
        if wl.volume_mounts:
            container["volumeMounts"] = [
                {"name": vm.name, "mountPath": vm.mount_path, "readOnly": vm.read_only}
                for vm in wl.volume_mounts
            ]

        pod_spec: dict = {
            "containers": [container],
            "terminationGracePeriodSeconds": 30,
        }
        if wl.service_account:
            pod_spec["serviceAccountName"] = wl.service_account
        if wl.node_selector.labels:
            pod_spec["nodeSelector"] = wl.node_selector.labels

        selector_labels = {"app": wl.name}
        labels_dict = wl.labels.as_dict()
        labels_dict.update(selector_labels)

        if wl.kind == WorkloadKind.CRONJOB:
            spec: dict = {
                "schedule": wl.schedule or "0 * * * *",
                "jobTemplate": {
                    "spec": {
                        "template": {
                            "metadata": {"labels": labels_dict},
                            "spec": {**pod_spec, "restartPolicy": "OnFailure"},
                        }
                    }
                },
            }
        elif wl.kind == WorkloadKind.JOB:
            spec = {
                "template": {
                    "metadata": {"labels": labels_dict},
                    "spec": {**pod_spec, "restartPolicy": "OnFailure"},
                }
            }
        else:
            spec = {
                "replicas": wl.replicas,
                "selector": {"matchLabels": selector_labels},
                "template": {
                    "metadata": {"labels": labels_dict},
                    "spec": pod_spec,
                },
            }
            if wl.kind == WorkloadKind.STATEFULSET and wl.pvc_refs:
                spec["volumeClaimTemplates"] = [
                    {
                        "metadata": {"name": ref},
                        "spec": {
                            "accessModes": ["ReadWriteOnce"],
                            "resources": {"requests": {"storage": "20Gi"}},
                        },
                    }
                    for ref in wl.pvc_refs
                ]

        doc = {
            "apiVersion": api_version,
            "kind": kind,
            "metadata": k8s_metadata(wl.name, ns.name, labels=labels_dict),
            "spec": spec,
        }

        filename = f"{wl.name}.yaml"
        result.add_file(f"k8s/base/{ns.name}/{filename}", dump_yaml(doc), f"{kind} {wl.name}")
        return [filename]

    # ── Service ───────────────────────────────────────────────────────────────

    def _gen_service(self, ns: Namespace, svc: Service, result: GenerationResult) -> str:
        ports = [
            {"name": p.name, "port": p.port, "targetPort": p.target_port, "protocol": p.protocol}
            for p in svc.ports
        ]
        if svc.service_type == ServiceType.NODE_PORT:
            for i, port in enumerate(svc.ports):
                if port.node_port:
                    ports[i]["nodePort"] = port.node_port

        svc_type = svc.service_type.value
        if svc.service_type == ServiceType.HEADLESS:
            svc_type = "ClusterIP"

        spec: dict = {
            "type": svc_type,
            "selector": svc.selector,
            "ports": ports,
        }
        if svc.service_type == ServiceType.HEADLESS:
            spec["clusterIP"] = "None"

        doc = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": k8s_metadata(svc.name, ns.name, labels=svc.labels.as_dict(), annotations=svc.annotations or None),
            "spec": spec,
        }
        filename = f"{svc.name}-svc.yaml"
        result.add_file(f"k8s/base/{ns.name}/{filename}", dump_yaml(doc), f"Service {svc.name}")
        return filename

    # ── Ingress ───────────────────────────────────────────────────────────────

    def _gen_ingress(self, ns: Namespace, ingress: Ingress, result: GenerationResult) -> str:
        rules = []
        for rule in ingress.rules:
            rules.append({
                "host": rule.host,
                "http": {
                    "paths": [{
                        "path": rule.path,
                        "pathType": rule.path_type,
                        "backend": {"service": {"name": rule.service_name, "port": {"number": rule.service_port}}},
                    }]
                },
            })

        tls = [{"hosts": t.hosts, "secretName": t.secret_name} for t in ingress.tls if t.secret_name]

        annotations = {
            "kubernetes.io/ingress.class": ingress.ingress_class.value,
            **ingress.annotations,
        }
        spec: dict = {"rules": rules}
        if tls:
            spec["tls"] = tls

        doc = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": k8s_metadata(ingress.name, ns.name, labels=ingress.labels.as_dict(), annotations=annotations),
            "spec": spec,
        }
        filename = f"{ingress.name}-ingress.yaml"
        result.add_file(f"k8s/base/{ns.name}/{filename}", dump_yaml(doc), f"Ingress {ingress.name}")
        return filename

    # ── ConfigMap ─────────────────────────────────────────────────────────────

    def _gen_configmap(self, ns: Namespace, cm: ConfigMap, result: GenerationResult) -> str:
        doc = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": k8s_metadata(cm.name, ns.name),
            "data": cm.data,
        }
        filename = f"{cm.name}-cm.yaml"
        result.add_file(f"k8s/base/{ns.name}/{filename}", dump_yaml(doc), f"ConfigMap {cm.name}")
        return filename

    # ── Secret ────────────────────────────────────────────────────────────────

    def _gen_secret(self, ns: Namespace, secret: Secret, result: GenerationResult) -> str:
        doc = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": k8s_metadata(secret.name, ns.name),
            "type": secret.secret_type,
            "stringData": {k: f"<{k.upper()}_PLACEHOLDER>" for k in secret.keys},
        }
        filename = f"{secret.name}-secret.yaml"
        result.add_file(f"k8s/base/{ns.name}/{filename}", dump_yaml(doc), f"Secret {secret.name}")
        return filename

    # ── PVC ───────────────────────────────────────────────────────────────────

    def _gen_pvc(self, ns: Namespace, pvc: PersistentVolumeClaim, result: GenerationResult) -> str:
        spec: dict = {
            "accessModes": pvc.storage.access_modes,
            "resources": {"requests": {"storage": pvc.storage.size}},
        }
        if pvc.storage.storage_class_name:
            spec["storageClassName"] = pvc.storage.storage_class_name
        doc = {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": k8s_metadata(pvc.name, ns.name),
            "spec": spec,
        }
        filename = f"{pvc.name}-pvc.yaml"
        result.add_file(f"k8s/base/{ns.name}/{filename}", dump_yaml(doc), f"PVC {pvc.name}")
        return filename

    # ── HPA ───────────────────────────────────────────────────────────────────

    def _gen_hpa(self, ns: Namespace, hpa_cfg: AutoscalingConfig, result: GenerationResult) -> str:
        hpa = hpa_cfg.hpa or HPAConfig()
        metrics = []
        for metric in hpa.metrics:
            metrics.append({
                "type": "Resource",
                "resource": {
                    "name": metric.type,
                    "target": {"type": "Utilization", "averageUtilization": metric.target_value},
                },
            })
        if not metrics:
            metrics = [{
                "type": "Resource",
                "resource": {"name": "cpu", "target": {"type": "Utilization", "averageUtilization": 70}},
            }]

        doc = {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": k8s_metadata(hpa_cfg.name, ns.name),
            "spec": {
                "scaleTargetRef": {"apiVersion": "apps/v1", "kind": "Deployment", "name": hpa_cfg.target_ref},
                "minReplicas": hpa.min_replicas,
                "maxReplicas": hpa.max_replicas,
                "metrics": metrics,
            },
        }
        filename = f"{hpa_cfg.name}-hpa.yaml"
        result.add_file(f"k8s/base/{ns.name}/{filename}", dump_yaml(doc), f"HPA {hpa_cfg.name}")
        return filename

    # ── NetworkPolicy ─────────────────────────────────────────────────────────

    def _gen_network_policy(self, ns: Namespace, netpol: NetworkPolicy, result: GenerationResult) -> str:
        doc = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": k8s_metadata(netpol.name, ns.name),
            "spec": {
                "podSelector": {"matchLabels": netpol.pod_selector},
                "policyTypes": netpol.policy_types,
                "ingress": netpol.ingress_rules,
                "egress": netpol.egress_rules,
            },
        }
        filename = f"{netpol.name}-netpol.yaml"
        result.add_file(f"k8s/base/{ns.name}/{filename}", dump_yaml(doc), f"NetworkPolicy {netpol.name}")
        return filename

    # ── Overlay ───────────────────────────────────────────────────────────────

    def _gen_env_overlay(self, env: str, platform: Platform, result: GenerationResult) -> None:
        replica_map = {"dev": 1, "staging": 2, "prod": 3}
        replicas = replica_map.get(env, 2)

        bases = []
        for cluster in platform.clusters:
            for ns in cluster.namespaces:
                bases.append(f"../../base/{ns.name}")

        kust = {
            "apiVersion": "kustomize.config.k8s.io/v1beta1",
            "kind": "Kustomization",
            "namespace": "default",
            "commonLabels": {"environment": env},
            "bases": bases,
            "patches": [
                {
                    "target": {"kind": "Deployment"},
                    "patch": f"- op: replace\n  path: /spec/replicas\n  value: {replicas}",
                }
            ],
        }

        result.add_file(
            f"k8s/overlays/{env}/kustomization.yaml",
            dump_yaml(kust),
            f"Kustomize overlay for {env}",
        )
        result.add_file(
            f"environments/{env}/values.yaml",
            f"# Environment-specific values for {env}\nenvironment: {env}\nreplicas: {replicas}\n",
            f"Environment values for {env}",
        )
