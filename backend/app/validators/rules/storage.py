"""Storage validation rules."""
from .workloads import BaseRuleSet
from ...models.generation import ValidationReport
from ...models.platform import Platform, WorkloadKind


class StorageRules(BaseRuleSet):
    def check(self, platform: Platform, report: ValidationReport) -> None:
        for cluster in platform.clusters:
            for ns in cluster.namespaces:
                pvc_names = {p.name for p in ns.pvcs}

                for wl in ns.workloads:
                    # S001: Stateful workloads must have a PVC
                    if wl.kind == WorkloadKind.STATEFULSET and not wl.pvc_refs:
                        self._error(
                            report, "S001",
                            f"StatefulSet '{wl.name}' has no PersistentVolumeClaim.",
                            component_id=wl.id,
                            component_name=wl.name,
                            suggestion="Add a volumeClaimTemplate or a PVC reference.",
                        )

                    # S002: PVC refs must resolve
                    for ref in wl.pvc_refs:
                        if ref not in pvc_names:
                            self._error(
                                report, "S002",
                                f"Workload '{wl.name}' references unknown PVC '{ref}'.",
                                component_id=wl.id,
                                component_name=wl.name,
                                suggestion=f"Create a PVC named '{ref}' or fix the reference.",
                            )

                # S003: PVCs without a storage class name will use the default StorageClass
                sc_names = {sc.name for sc in cluster.storage_classes}
                for pvc in ns.pvcs:
                    if pvc.storage.storage_class_name and pvc.storage.storage_class_name not in sc_names:
                        self._warn(
                            report, "S003",
                            f"PVC '{pvc.name}' requests StorageClass '{pvc.storage.storage_class_name}' "
                            "which is not defined in this cluster.",
                            component_id=pvc.id,
                            component_name=pvc.name,
                            suggestion="Add a StorageClass definition to the cluster or remove the explicit storageClassName.",
                        )
