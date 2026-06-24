"""Security validation rules."""
from .workloads import BaseRuleSet
from ...models.generation import ValidationReport
from ...models.platform import Platform


class SecurityRules(BaseRuleSet):
    def check(self, platform: Platform, report: ValidationReport) -> None:
        for cluster in platform.clusters:
            for ns in cluster.namespaces:
                # SEC001: Workloads without a dedicated service account
                for wl in ns.workloads:
                    if not wl.service_account:
                        self._warn(
                            report, "SEC001",
                            f"Workload '{wl.name}' uses the default service account. "
                            "It inherits all permissions of the default SA.",
                            component_id=wl.id,
                            component_name=wl.name,
                            suggestion="Create a dedicated ServiceAccount with least-privilege RBAC.",
                        )

                # SEC002: Secrets referenced but not defined
                secret_names = {s.name for s in ns.secrets}
                for wl in ns.workloads:
                    for ref in wl.secret_refs:
                        if ref not in secret_names:
                            self._warn(
                                report, "SEC002",
                                f"Workload '{wl.name}' references undefined Secret '{ref}'.",
                                component_id=wl.id,
                                component_name=wl.name,
                                suggestion=f"Create a Secret named '{ref}' or remove the reference.",
                            )

                # SEC003: Secrets with no external store should be flagged
                for secret in ns.secrets:
                    if not secret.external_secret_store:
                        self._info(
                            report, "SEC003",
                            f"Secret '{secret.name}' has no external store configured. "
                            "Consider using External Secrets Operator or Vault.",
                        )

                # SEC004: Ingress without TLS
                for ingress in ns.ingresses:
                    if not ingress.tls:
                        self._warn(
                            report, "SEC004",
                            f"Ingress '{ingress.name}' has no TLS configuration.",
                            component_id=ingress.id,
                            component_name=ingress.name,
                            suggestion="Add TLS with a cert-manager Certificate or a pre-provisioned secret.",
                        )
