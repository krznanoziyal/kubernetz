"""Networking validation rules."""
from .workloads import BaseRuleSet
from ...models.generation import ValidationReport
from ...models.platform import Platform, ServiceType


class NetworkingRules(BaseRuleSet):
    def check(self, platform: Platform, report: ValidationReport) -> None:
        for cluster in platform.clusters:
            for ns in cluster.namespaces:
                workload_names = {wl.name for wl in ns.workloads}
                service_names = {s.name for s in ns.services}

                # N001: Services must have a selector that matches at least one workload label
                for svc in ns.services:
                    if not svc.selector:
                        self._warn(
                            report, "N001",
                            f"Service '{svc.name}' has an empty selector — it will not route to any pods.",
                            component_id=svc.id,
                            component_name=svc.name,
                            suggestion="Set spec.selector to match the pod labels of the target workload.",
                        )

                # N002: Ingress rules must reference an existing service
                for ingress in ns.ingresses:
                    for rule in ingress.rules:
                        if rule.service_name not in service_names:
                            self._error(
                                report, "N002",
                                f"Ingress '{ingress.name}' rule references unknown service '{rule.service_name}'.",
                                component_id=ingress.id,
                                component_name=ingress.name,
                                suggestion=f"Create a Service named '{rule.service_name}' or fix the ingress rule.",
                            )

                # N003: LoadBalancer services are expensive — warn for non-ingress use
                for svc in ns.services:
                    if svc.service_type == ServiceType.LOAD_BALANCER:
                        backing_ingress = any(
                            rule.service_name == svc.name
                            for ing in ns.ingresses
                            for rule in ing.rules
                        )
                        if not backing_ingress:
                            self._warn(
                                report, "N003",
                                f"Service '{svc.name}' is type LoadBalancer but is not referenced by any Ingress. "
                                "This will provision a cloud load balancer per service.",
                                component_id=svc.id,
                                component_name=svc.name,
                                suggestion="Use ClusterIP + Ingress unless you need a dedicated LB.",
                            )

                # N004: Namespace without a network policy
                if not ns.network_policies:
                    self._warn(
                        report, "N004",
                        f"Namespace '{ns.name}' has no NetworkPolicy — all pods are reachable by default.",
                        suggestion="Add a default-deny NetworkPolicy and explicit allow rules.",
                    )
