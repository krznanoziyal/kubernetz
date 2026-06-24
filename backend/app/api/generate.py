"""
Generation endpoint.

POST /api/v1/generate/  - generate all project files from a Platform model
"""
import logging

from fastapi import APIRouter, HTTPException

from ..models.generation import GenerationRequest, GenerationResult
from ..generators.kubernetes import KubernetesGenerator
from ..generators.helm import HelmGenerator
from ..generators.argocd import ArgoCDGenerator
from ..generators.terraform import TerraformGenerator
from ..generators.observability import ObservabilityGenerator
from ..validators.engine import ValidationEngine

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/")
async def generate(request: GenerationRequest) -> GenerationResult:
    """
    Validate the platform model and generate all requested project files.
    """
    validator = ValidationEngine()
    validation = validator.validate(request.platform)

    result = GenerationResult(
        platform_id=request.platform.id,
        validation=validation,
        assumptions=request.platform.assumptions,
    )

    if validation.errors:
        # Return partial result with validation errors so the user can fix them
        return result

    generators = [KubernetesGenerator()]
    if request.generate_helm:
        generators.append(HelmGenerator())
    if request.generate_argocd:
        generators.append(ArgoCDGenerator())
    if request.generate_terraform:
        generators.append(TerraformGenerator())
    if request.generate_observability:
        generators.append(ObservabilityGenerator())

    for gen in generators:
        try:
            gen.generate(request, result)
        except Exception as exc:
            log.exception("Generator %s failed", type(gen).__name__)
            result.warnings.append(f"{type(gen).__name__} failed: {exc}")

    _add_root_readme(request, result)
    return result


def _add_root_readme(request: GenerationRequest, result: GenerationResult) -> None:
    from ..generators.base import render_root_readme
    result.add_file("README.md", render_root_readme(request.platform), "Platform README")
