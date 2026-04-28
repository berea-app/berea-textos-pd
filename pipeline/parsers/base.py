"""Base interface every Bible parser implements.

A parser is responsible for taking a downloaded source archive and emitting a
flat sequence of ``ParsedVerse`` instances. Normalization (grouping by book,
sorting, validating against the canon) happens later in ``pipeline.normalize``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

from ..normalize import ParsedVerse


class BibleParser(ABC):
    """Convert a downloaded source archive to ParsedVerse instances.

    Implementations declare ``name`` (used in build_info.parser) and ``parse``.
    They MUST be deterministic: given the same source bytes they emit the same
    sequence of verses.
    """

    name: str

    @abstractmethod
    def parse(self, source_path: Path) -> Iterable[ParsedVerse]:
        """Yield ParsedVerse instances. Order is not significant; normalize
        re-orders into canonical order before packing."""
        raise NotImplementedError
