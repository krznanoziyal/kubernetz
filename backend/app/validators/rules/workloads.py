"""Workload-level validation rules."""
from abc import ABC, abstractmethod

from ...models.generation import IssueSeverity, ValidationIssue, ValidationReport
from ...models.platform import Platform, WorkloadKind


class BaseRuleSet(ABC):
    @abstractmethod
    def check(self, platform: Platform, report: ValidationReport) -> None:
        pass

    def _error(self, report: ValidationReport, code: str, msg: str, component_id: str = "", component_name: str = "", suggestion: str = "") -> None:
        report.add(ValidationIssue(
            severity=IssueSeverity.ERROR,
            code=code,
            message=msg,
            component_id=component_id,
            component_name=component_name,
            suggestion=suggestion,
            auto_fixable=bool(suggestion),
        ))

    def _warn(self, report: ValidationReport, code: str, msg: str, component_id: str = "", component_name: str = "", suggestion: str = "") -> None:
        report.add(ValidationIssue(
            severity=IssueSeverity.WARNING,
            code=code,
            message=msg,
            component_id=component_id,
            component_name=component_name,
            suggestion=suggestion,
        ))

    def _info(self, report: ValidationReport, code: str, msg: str) -> None:
        report.add(ValidationIssue(severity=IssueSeverity.INFO, code=code, message=msg))

    def _assumption(self, report: ValidationReport, code: str, msg: str) -> None:
        report.add(ValidationIssue(severity=IssueSeverity.ASSUMPTION, code=code, message=msg))


class WorkloadRules(BaseRuleSet):
    def check(self, platform: Platform, report: ValidationReport) -> None:
        for cluster in platform.clusters:
            for ns in cluster.namespaces:
                service_targets = {s.workload_ref for s in ns.services if s.workload_ref}

                for wl in ns.workloads:
                    # W001: workload must have at least one port defined
                    if not wl.ports:
                        self._warn(
                            report, "W001",
                            f"Workload '{wl.name}' in namespace '{ns.name}' has no container ports defined.",
                            component_id=wl.id,
                            component_name=wl.name,
                            suggestion="Add at least one ContainerPort (e.g. 8080/TCP).",
                        )

                    # W002: placeholder image
                    if "placeholder" in wl.image or wl.image.endswith(":latest"):
                        self._warn(
                            report, "W002",
                            f"Workload '{wl.name}' uses a placeholder or :latest image tag '{wl.image}'.",
                            component_id=wl.id,
                            component_name=wl.name,
                            suggestion="Pin the image to a specific digest or semver tag.",
                        )

                    # W003: resource requests must be set
                    if not wl.resources.cpu_request or not wl.resources.memory_request:
                        self._error(
                            report, "W003",
                            f"Workload '{wl.name}' is missing resource requests.",
                            component_id=wl.id,
                            component_name=wl.name,
                            suggestion="Set resources.requests.cpu and resources.requests.memory.",
                        )

                    # W004: no service backing this workload
                    if wl.name not in service_targets and wl.kind in (WorkloadKind.DEPLOYMENT, WorkloadKind.STATEFULSET):
                        self._warn(
                            report, "W004",
                            f"Workload '{wl.name}' has no backing Service.",
                            component_id=wl.id,
                            component_name=wl.name,
                            suggestion="Add a Service with selector matching this workload's labels.",
                        )

                    # W005: no liveness probe
                    if not wl.probes.liveness:
                        self._warn(
                            report, "W005",
                            f"Workload '{wl.name}' has no liveness probe.",
                            component_id=wl.id,
                            component_name=wl.name,
                            suggestion="Define a livenessProbe so Kubernetes can restart unhealthy pods.",
                        )

                    # W006: no readiness probe
                    if not wl.probes.readiness:
                        self._warn(
                            report, "W006",
                            f"Workload '{wl.name}' has no readiness probe.",
                            component_id=wl.id,
                            component_name=wl.name,
                            suggestion="Define a readinessProbe so pods are only sent traffic when ready.",
                        )

                # W007: no workloads in namespace
                if not ns.workloads:
                    self._info(
                        report, "W007",
                        f"Namespace '{ns.name}' contains no workloads.",
                    )
