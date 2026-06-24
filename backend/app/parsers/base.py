"""Abstract base class for all diagram parsers."""
from abc import ABC, abstractmethod
from typing import Optional

from ..models.diagram import ParsedDiagram


class BaseParser(ABC):
    @abstractmethod
    async def parse(self, content: bytes, content_type: Optional[str] = None) -> ParsedDiagram:
        """Parse raw bytes and return a format-agnostic ParsedDiagram."""
