"""
Architecture editing and validation endpoints.

POST /api/v1/architecture/validate  - validate a Platform model
PUT  /api/v1/architecture/          - update/replace a Platform model
"""
from fastapi import APIRouter, HTTPException

from ..models.platform import Platform
from ..models.generation import ValidationReport
from ..validators.engine import ValidationEngine

router = APIRouter()


@router.post("/validate")
async def validate_architecture(platform: Platform) -> ValidationReport:
    """Run all validators against the given Platform and return a report."""
    engine = ValidationEngine()
    return engine.validate(platform)


@router.post("/")
async def update_architecture(platform: Platform) -> Platform:
    """Accept an edited Platform model and return it back (validated echo)."""
    return platform
