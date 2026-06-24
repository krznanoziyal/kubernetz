from fastapi import APIRouter

from .diagram import router as diagram_router
from .architecture import router as architecture_router
from .generate import router as generate_router
from .export import router as export_router

router = APIRouter()

router.include_router(diagram_router, prefix="/diagram", tags=["diagram"])
router.include_router(architecture_router, prefix="/architecture", tags=["architecture"])
router.include_router(generate_router, prefix="/generate", tags=["generate"])
router.include_router(export_router, prefix="/export", tags=["export"])
