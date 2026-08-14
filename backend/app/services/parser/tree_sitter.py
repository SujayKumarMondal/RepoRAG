"""
Tree-sitter integration.

This module intentionally provides a small abstraction around
Tree-sitter so the rest of RepoRAG can remain parser-agnostic.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedTree:
    """
    Wrapper around a parsed syntax tree.
    """

    language: str

    tree: Any | None

    source_code: str


class TreeSitterParser:
    """
    Tree-sitter parser abstraction.

    Language-specific grammar packages can be added later.
    """

    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
    }

    def detect_language(
        self,
        extension: str,
    ) -> str | None:

        return self.LANGUAGE_EXTENSIONS.get(
            extension.lower()
        )

    def parse(
        self,
        source_code: str,
        language: str,
    ) -> ParsedTree:

        try:
            from tree_sitter import Parser

            # Grammar loading is intentionally separated
            # because grammar package APIs differ.

            parser = Parser()

            # The actual language object will be configured
            # when supported grammar packages are selected.

            return ParsedTree(
                language=language,
                tree=None,
                source_code=source_code,
            )

        except ImportError:

            return ParsedTree(
                language=language,
                tree=None,
                source_code=source_code,
            )