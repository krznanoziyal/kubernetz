"""Central validation engine — collects all rule modules and runs them."""
from ..models.generation import ValidationReport
from ..models.platform import Platform
from .rules.workloads import WorkloadRules
from .rules.networking import NetworkingRules
from .rules.storage import StorageRules
from .rules.security import SecurityRules


class ValidationEngine:
    def __init__(self) -> None:
        self._rule_sets = [
            WorkloadRules(),
            NetworkingRules(),
            StorageRules(),
            SecurityRules(),
        ]

    def validate(self, platform: Platform) -> ValidationReport:
        report = ValidationReport(passed=True)
        for rule_set in self._rule_sets:
            rule_set.check(platform, report)
        return report
