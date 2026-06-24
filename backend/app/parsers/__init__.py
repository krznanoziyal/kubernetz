from .base import BaseParser
from .drawio import DrawioParser
from .excalidraw import ExcalidrawParser
from .mermaid import MermaidParser
from .image import ImageParser
from ..models.diagram import DiagramFormat


def get_parser(fmt: DiagramFormat) -> BaseParser:
    match fmt:
        case DiagramFormat.DRAWIO:
            return DrawioParser()
        case DiagramFormat.EXCALIDRAW:
            return ExcalidrawParser()
        case DiagramFormat.MERMAID:
            return MermaidParser()
        case DiagramFormat.IMAGE_PNG | DiagramFormat.IMAGE_JPG | DiagramFormat.IMAGE_SVG:
            return ImageParser()
        case _:
            # Best-effort: try Drawio first, fall back to image
            return DrawioParser()


__all__ = ["BaseParser", "DrawioParser", "ExcalidrawParser", "MermaidParser", "ImageParser", "get_parser"]
