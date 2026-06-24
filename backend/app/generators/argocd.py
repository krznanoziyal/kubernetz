"""
Argo CD GitOps generator.

Generates:
  argo-cd/bootstrap/install.yaml           Argo CD install (kustomize ref)
  argo-cd/bootstrap/kustomization.yaml
  argo-cd/apps/root-app.yaml               App-of-Apps root
  argo-cd/apps/<namespace>-app.yaml        Application per namespace
  argo-cd/appsets/<platform>-appset.yaml   ApplicationSet for multi-env promotion
  argo-cd/projects/<platform>-project.yaml AppProject
"""
from __future__ import annotations

from .base import BaseGenerator, dump_yaml, k8s_metadata
from ..models.generation import GenerationRequest, GenerationResult


_ARGOCD_VERSION = "v2.12.0"
_ARGOCD_INSTALL_URL = f"https://raw.githubusercontent.com/argoproj/argo-cd/{_ARGOCD_VERSION}/manifests/install.yaml"


class ArgoCDGenerator(BaseGenerator):
    def generate(self, request: GenerationRequest, result: GenerationResult) -> None:
        platform = request.platform
        pname = platform.name
        envs = request.environments
        repo_url = "https://github.com/your-org/your-repo"

        self._gen_bootstrap(result)
        self._gen_project(pname, envs, result)
        self._gen_root_app(pname, repo_url, result)

        for cluster in platform.clusters:
            for ns in cluster.namespaces:
                self._gen_namespace_app(pname, ns.name, repo_url, envs, result)

        self._gen_appset(pname, platform, repo_url, envs, result)

    def _gen_bootstrap(self, result: GenerationResult) -> None:
        kust = {
            "apiVersion": "kustomize.config.k8s.io/v1beta1",
            "kind": "Kustomization",
            "namespace": "argocd",
            "resources": [
                "https://raw.githubusercontent.com/argoproj/argo-cd/v2.12.0/manifests/install.yaml",
            ],
            "patches": [
                {
                    "patch": "- op: replace\n  path: /data/server.insecure\n  value: 'false'",
                    "target": {"kind": "ConfigMap", "name": "argocd-cmd-params-cm"},
                }
            ],
        }
        result.add_file("argo-cd/bootstrap/kustomization.yaml", dump_yaml(kust), "Argo CD bootstrap kustomization")
        result.add_file(
            "argo-cd/bootstrap/namespace.yaml",
            dump_yaml({"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": "argocd"}}),
            "argocd namespace",
        )

    def _gen_project(self, pname: str, envs: list[str], result: GenerationResult) -> None:
        ns_whitelist = [{"group": "*", "kind": "*"}]
        doc = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "AppProject",
            "metadata": k8s_metadata(pname, "argocd"),
            "spec": {
                "description": f"Project for {pname}",
                "sourceRepos": ["*"],
                "destinations": [{"namespace": "*", "server": "https://kubernetes.default.svc"}],
                "clusterResourceWhitelist": ns_whitelist,
                "namespaceResourceWhitelist": ns_whitelist,
                "orphanedResources": {"warn": True},
                "syncWindows": [
                    {
                        "kind": "allow",
                        "schedule": "0 8-20 * * MON-FRI",
                        "duration": "12h",
                        "applications": ["*"],
                        "namespaces": ["*"],
                        "clusters": ["*"],
                        "manualSync": True,
                    }
                ],
            },
        }
        result.add_file(f"argo-cd/projects/{pname}-project.yaml", dump_yaml(doc), f"AppProject {pname}")

    def _gen_root_app(self, pname: str, repo_url: str, result: GenerationResult) -> None:
        doc = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Application",
            "metadata": {
                "name": f"{pname}-root",
                "namespace": "argocd",
                "finalizers": ["resources-finalizer.argocd.argoproj.io"],
            },
            "spec": {
                "project": pname,
                "source": {
                    "repoURL": repo_url,
                    "targetRevision": "HEAD",
                    "path": "argo-cd/apps",
                    "directory": {"recurse": True},
                },
                "destination": {"server": "https://kubernetes.default.svc", "namespace": "argocd"},
                "syncPolicy": {
                    "automated": {"prune": True, "selfHeal": True},
                    "syncOptions": ["CreateNamespace=true", "PrunePropagationPolicy=foreground"],
                    "retry": {"limit": 5, "backoff": {"duration": "5s", "factor": 2, "maxDuration": "3m"}},
                },
            },
        }
        result.add_file("argo-cd/apps/root-app.yaml", dump_yaml(doc), "Argo CD App-of-Apps root")

    def _gen_namespace_app(self, pname: str, ns_name: str, repo_url: str, envs: list[str], result: GenerationResult) -> None:
        for env in envs:
            app_name = f"{ns_name}-{env}"
            doc = {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "Application",
                "metadata": {
                    "name": app_name,
                    "namespace": "argocd",
                    "labels": {"app.kubernetes.io/part-of": pname, "environment": env},
                    "finalizers": ["resources-finalizer.argocd.argoproj.io"],
                },
                "spec": {
                    "project": pname,
                    "source": {
                        "repoURL": repo_url,
                        "targetRevision": "HEAD",
                        "path": f"k8s/overlays/{env}",
                    },
                    "destination": {"server": "https://kubernetes.default.svc", "namespace": ns_name},
                    "syncPolicy": {
                        "automated": {
                            "prune": env != "prod",
                            "selfHeal": True,
                        },
                        "syncOptions": ["CreateNamespace=true", "ApplyOutOfSyncOnly=true"],
                        "retry": {"limit": 5, "backoff": {"duration": "5s", "factor": 2, "maxDuration": "3m"}},
                    },
                    "ignoreDifferences": [
                        {
                            "group": "apps",
                            "kind": "Deployment",
                            "jsonPointers": ["/spec/replicas"],
                        }
                    ],
                },
            }
            result.add_file(f"argo-cd/apps/{app_name}.yaml", dump_yaml(doc), f"Argo CD Application {app_name}")

    def _gen_appset(self, pname: str, platform, repo_url: str, envs: list[str], result: GenerationResult) -> None:
        ns_names = [ns.name for c in platform.clusters for ns in c.namespaces]
        doc = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "ApplicationSet",
            "metadata": k8s_metadata(f"{pname}-appset", "argocd"),
            "spec": {
                "generators": [
                    {
                        "matrix": {
                            "generators": [
                                {"list": {"elements": [{"namespace": ns} for ns in ns_names]}},
                                {"list": {"elements": [{"env": e} for e in envs]}},
                            ]
                        }
                    }
                ],
                "template": {
                    "metadata": {
                        "name": "{{namespace}}-{{env}}",
                        "namespace": "argocd",
                        "labels": {"app.kubernetes.io/part-of": pname, "environment": "{{env}}"},
                    },
                    "spec": {
                        "project": pname,
                        "source": {
                            "repoURL": repo_url,
                            "targetRevision": "HEAD",
                            "path": "k8s/overlays/{{env}}",
                        },
                        "destination": {
                            "server": "https://kubernetes.default.svc",
                            "namespace": "{{namespace}}",
                        },
                        "syncPolicy": {
                            "automated": {"prune": True, "selfHeal": True},
                            "syncOptions": ["CreateNamespace=true"],
                        },
                    },
                },
            },
        }
        result.add_file(f"argo-cd/appsets/{pname}-appset.yaml", dump_yaml(doc), f"ApplicationSet {pname}")
