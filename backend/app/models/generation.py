"""Request/response models for generation and validation APIs."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .platform import Platform


class IssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    ASSUMPTION = "assumption"


class ValidationIssue(BaseModel):
    severity: IssueSeverity
    code: str
    message: str
    component_id: Optional[str] = None
    component_name: Optional[str] = None
    suggestion: Optional[str] = None
    auto_fixable: bool = False


class ValidationReport(BaseModel):
    passed: bool
    errors: List[ValidationIssue] = Field(default_factory=list)
    warnings: List[ValidationIssue] = Field(default_factory=list)
    info: List[ValidationIssue] = Field(default_factory=list)
    assumptions: List[ValidationIssue] = Field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return len(self.errors) + len(self.warnings)

    def add(self, issue: ValidationIssue) -> None:
        match issue.severity:
            case IssueSeverity.ERROR:
                self.errors.append(issue)
            case IssueSeverity.WARNING:
                self.warnings.append(issue)
            case IssueSeverity.INFO:
                self.info.append(issue)
            case IssueSeverity.ASSUMPTION:
                self.assumptions.append(issue)
        if issue.severity == IssueSeverity.ERROR:
            self.passed = False


class GenerationRequest(BaseModel):
    platform: Platform
    environments: List[str] = Field(default_factory=lambda: ["dev", "staging", "prod"])
    generate_helm: bool = True
    generate_argocd: bool = True
    generate_terraform: bool = True
    generate_observability: bool = True
    generate_policies: bool = True
    gitops_tool: str = "argocd"
    terraform_backend: str = "s3"
    helm_repo_url: Optional[str] = None
    extra_options: Dict[str, Any] = Field(default_factory=dict)


class GeneratedFile(BaseModel):
    path: str
    content: str
    description: str = ""


class GenerationResult(BaseModel):
    platform_id: str
    files: List[GeneratedFile] = Field(default_factory=list)
    validation: ValidationReport
    assumptions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    def add_file(self, path: str, content: str, description: str = "") -> None:
        self.files.append(GeneratedFile(path=path, content=content, description=description))
