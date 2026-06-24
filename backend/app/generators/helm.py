"""
Helm chart generator.

For each workload that benefits from Helm packaging, generates:
  helm/<chart-name>/Chart.yaml
  helm/<chart-name>/values.yaml
  helm/<chart-name>/values-dev.yaml
  helm/<chart-name>/values-staging.yaml
  helm/<chart-name>/values-prod.yaml
  helm/<chart-name>/templates/deployment.yaml
  helm/<chart-name>/templates/service.yaml
  helm/<chart-name>/templates/ingress.yaml
  helm/<chart-name>/templates/hpa.yaml
  helm/<chart-name>/templates/_helpers.tpl

Also generates a top-level helmfile.yaml for orchestrating all charts.
"""
from __future__ import annotations

from .base import BaseGenerator, dump_yaml
from ..models.generation import GenerationRequest, GenerationResult
from ..models.platform import Workload, Namespace, Cluster, WorkloadKind

_KNOWN_CHARTS: dict[str, str] = {
    "postgres": "oci://registry-1.docker.io/bitnamicharts/postgresql",
    "postgresql": "oci://registry-1.docker.io/bitnamicharts/postgresql",
    "mysql": "oci://registry-1.docker.io/bitnamicharts/mysql",
    "redis": "oci://registry-1.docker.io/bitnamicharts/redis",
    "kafka": "oci://registry-1.docker.io/bitnamicharts/kafka",
    "rabbitmq": "oci://registry-1.docker.io/bitnamicharts/rabbitmq",
    "elasticsearch": "oci://registry-1.docker.io/bitnamicharts/elasticsearch",
    "mongodb": "oci://registry-1.docker.io/bitnamicharts/mongodb",
    "nginx": "https://kubernetes.github.io/ingress-nginx",
    "prometheus": "https://prometheus-community.github.io/helm-charts",
    "grafana": "https://grafana.github.io/helm-charts",
    "loki": "https://grafana.github.io/helm-charts",
}


class HelmGenerator(BaseGenerator):
    def generate(self, request: GenerationRequest, result: GenerationResult) -> None:
        helmfile_releases: list[dict] = []

        for cluster in request.platform.clusters:
            for ns in cluster.namespaces:
                for wl in ns.workloads:
                    chart_ref = _known_chart(wl)
                    if chart_ref:
                        # Third-party chart — generate wrapper values
                        self._gen_third_party_wrapper(ns, wl, chart_ref, request.environments, result)
                    else:
                        # Custom chart
                        self._gen_custom_chart(ns, wl, cluster, request.environments, result)

                    helmfile_releases.append(_helmfile_release(ns, wl, chart_ref, request.environments))

        result.add_file("helm/helmfile.yaml", dump_yaml({"releases": helmfile_releases}), "Helmfile orchestrating all charts")

    # ── Custom chart ──────────────────────────────────────────────────────────

    def _gen_custom_chart(
        self,
        ns: Namespace,
        wl: Workload,
        cluster: Cluster,
        environments: list[str],
        result: GenerationResult,
    ) -> None:
        chart_name = wl.name
        base = f"helm/{chart_name}"
        port = wl.ports[0].port if wl.ports else 8080

        # Chart.yaml
        result.add_file(f"{base}/Chart.yaml", dump_yaml({
            "apiVersion": "v2",
            "name": chart_name,
            "description": f"Helm chart for {chart_name}",
            "type": "application",
            "version": "0.1.0",
            "appVersion": "latest",
        }), f"Helm Chart.yaml for {chart_name}")

        # Base values.yaml
        values = {
            "replicaCount": wl.replicas,
            "image": {
                "repository": wl.image.split(":")[0],
                "tag": wl.image.split(":")[-1] if ":" in wl.image else "latest",
                "pullPolicy": wl.image_pull_policy,
            },
            "service": {
                "type": "ClusterIP",
                "port": port,
            },
            "ingress": {
                "enabled": bool(ns.ingresses),
                "className": "nginx",
                "hosts": [{"host": f"{chart_name}.example.com", "paths": [{"path": "/", "pathType": "Prefix"}]}],
                "tls": [],
            },
            "resources": {
                "requests": {"cpu": wl.resources.cpu_request, "memory": wl.resources.memory_request},
                "limits": {"cpu": wl.resources.cpu_limit, "memory": wl.resources.memory_limit},
            },
            "autoscaling": {
                "enabled": True,
                "minReplicas": 2,
                "maxReplicas": 10,
                "targetCPUUtilizationPercentage": 70,
            },
            "nodeSelector": {},
            "tolerations": [],
            "affinity": {},
            "podAnnotations": {},
            "serviceAccount": {"create": True, "name": ""},
            "env": {},
            "secrets": {},
        }
        result.add_file(f"{base}/values.yaml", dump_yaml(values), f"Default values for {chart_name}")

        # Per-environment overrides
        replica_map = {"dev": 1, "staging": 2, "prod": 3}
        for env in environments:
            env_values = {
                "replicaCount": replica_map.get(env, 2),
                "ingress": {"hosts": [{"host": f"{chart_name}.{env}.example.com", "paths": [{"path": "/", "pathType": "Prefix"}]}]},
            }
            result.add_file(f"{base}/values-{env}.yaml", dump_yaml(env_values), f"{env} values for {chart_name}")

        # Templates
        self._gen_deployment_template(base, chart_name, port, result)
        self._gen_service_template(base, chart_name, port, result)
        self._gen_ingress_template(base, chart_name, port, result)
        self._gen_hpa_template(base, chart_name, result)
        self._gen_helpers_tpl(base, chart_name, result)
        self._gen_serviceaccount_template(base, chart_name, result)

    def _gen_deployment_template(self, base: str, chart_name: str, port: int, result: GenerationResult) -> None:
        tpl = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "%(n)s.fullname" . }}
  labels:
    {{- include "%(n)s.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "%(n)s.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        {{- with .Values.podAnnotations }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      labels:
        {{- include "%(n)s.selectorLabels" . | nindent 8 }}
    spec:
      serviceAccountName: {{ include "%(n)s.serviceAccountName" . }}
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - name: http
              containerPort: %(port)d
              protocol: TCP
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          {{- if .Values.env }}
          env:
            {{- range $key, $val := .Values.env }}
            - name: {{ $key }}
              value: {{ $val | quote }}
            {{- end }}
          {{- end }}
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
""" % {"n": chart_name, "port": port}
        result.add_file(f"{base}/templates/deployment.yaml", tpl, f"Deployment template for {chart_name}")

    def _gen_service_template(self, base: str, chart_name: str, port: int, result: GenerationResult) -> None:
        tpl = """apiVersion: v1
kind: Service
metadata:
  name: {{ include "%(n)s.fullname" . }}
  labels:
    {{- include "%(n)s.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: http
      protocol: TCP
      name: http
  selector:
    {{- include "%(n)s.selectorLabels" . | nindent 4 }}
""" % {"n": chart_name}
        result.add_file(f"{base}/templates/service.yaml", tpl, f"Service template for {chart_name}")

    def _gen_ingress_template(self, base: str, chart_name: str, port: int, result: GenerationResult) -> None:
        tpl = """{{- if .Values.ingress.enabled -}}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "%(n)s.fullname" . }}
  labels:
    {{- include "%(n)s.labels" . | nindent 4 }}
  {{- with .Values.ingress.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  {{- if .Values.ingress.className }}
  ingressClassName: {{ .Values.ingress.className }}
  {{- end }}
  {{- if .Values.ingress.tls }}
  tls:
    {{- range .Values.ingress.tls }}
    - hosts:
        {{- range .hosts }}
        - {{ . | quote }}
        {{- end }}
      secretName: {{ .secretName }}
    {{- end }}
  {{- end }}
  rules:
    {{- range .Values.ingress.hosts }}
    - host: {{ .host | quote }}
      http:
        paths:
          {{- range .paths }}
          - path: {{ .path }}
            pathType: {{ .pathType }}
            backend:
              service:
                name: {{ include "%(n)s.fullname" $ }}
                port:
                  number: {{ $.Values.service.port }}
          {{- end }}
    {{- end }}
{{- end }}
""" % {"n": chart_name}
        result.add_file(f"{base}/templates/ingress.yaml", tpl, f"Ingress template for {chart_name}")

    def _gen_hpa_template(self, base: str, chart_name: str, result: GenerationResult) -> None:
        tpl = """{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "%(n)s.fullname" . }}
  labels:
    {{- include "%(n)s.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "%(n)s.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
{{- end }}
""" % {"n": chart_name}
        result.add_file(f"{base}/templates/hpa.yaml", tpl, f"HPA template for {chart_name}")

    def _gen_helpers_tpl(self, base: str, chart_name: str, result: GenerationResult) -> None:
        tpl = """{{/*
Expand the name of the chart.
*/}}
{{- define "%(n)s.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "%(n)s.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%%s-%%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "%(n)s.chart" -}}
{{- printf "%%s-%%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "%(n)s.labels" -}}
helm.sh/chart: {{ include "%(n)s.chart" . }}
{{ include "%(n)s.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "%(n)s.selectorLabels" -}}
app.kubernetes.io/name: {{ include "%(n)s.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "%(n)s.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "%(n)s.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
""" % {"n": chart_name}
        result.add_file(f"{base}/templates/_helpers.tpl", tpl, f"Helm helpers for {chart_name}")

    def _gen_serviceaccount_template(self, base: str, chart_name: str, result: GenerationResult) -> None:
        tpl = """{{- if .Values.serviceAccount.create -}}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "%(n)s.serviceAccountName" . }}
  labels:
    {{- include "%(n)s.labels" . | nindent 4 }}
{{- end }}
""" % {"n": chart_name}
        result.add_file(f"{base}/templates/serviceaccount.yaml", tpl, f"ServiceAccount template for {chart_name}")

    # ── Third-party wrapper ───────────────────────────────────────────────────

    def _gen_third_party_wrapper(
        self,
        ns: Namespace,
        wl: Workload,
        chart_ref: str,
        environments: list[str],
        result: GenerationResult,
    ) -> None:
        base = f"helm/{wl.name}"
        values = _default_third_party_values(wl)
        result.add_file(f"{base}/values.yaml", dump_yaml(values), f"Values for third-party chart {wl.name}")
        result.add_file(f"{base}/Chart.yaml", dump_yaml({
            "apiVersion": "v2",
            "name": wl.name,
            "description": f"Wrapper chart for {wl.name}",
            "type": "application",
            "version": "0.1.0",
            "dependencies": [{"name": wl.name.split("-")[0], "version": "*", "repository": chart_ref}],
        }), f"Dependency chart for {wl.name}")

        for env in environments:
            replica_map = {"dev": 1, "staging": 1, "prod": 3}
            env_values = {"replicaCount": replica_map.get(env, 1)}
            result.add_file(f"{base}/values-{env}.yaml", dump_yaml(env_values), f"{env} values for {wl.name}")


def _known_chart(wl: Workload) -> str | None:
    name = wl.name.lower()
    for kw, ref in _KNOWN_CHARTS.items():
        if kw in name:
            return ref
    return None


def _default_third_party_values(wl: Workload) -> dict:
    name = wl.name.lower()
    if "postgres" in name:
        return {"auth": {"postgresPassword": "<POSTGRES_PASSWORD_PLACEHOLDER>", "database": name}, "primary": {"persistence": {"size": "20Gi"}}}
    if "redis" in name:
        return {"auth": {"enabled": True, "password": "<REDIS_PASSWORD_PLACEHOLDER>"}, "replica": {"replicaCount": 1}}
    if "kafka" in name:
        return {"replicaCount": 1, "zookeeper": {"replicaCount": 1}}
    return {}


def _helmfile_release(ns: Namespace, wl: Workload, chart_ref: str | None, environments: list[str]) -> dict:
    values = [f"helm/{wl.name}/values.yaml"]
    values += [f"helm/{wl.name}/values-{{{{ .Environment.Name }}}}.yaml"]
    return {
        "name": wl.name,
        "namespace": ns.name,
        "chart": chart_ref or f"./helm/{wl.name}",
        "values": values,
    }
