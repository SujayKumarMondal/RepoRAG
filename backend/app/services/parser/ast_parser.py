"""
AST-aware source-code parser.
"""

from pathlib import PurePosixPath
from typing import Any


class ASTParser:
    """
    High-level AST parsing and code chunking service.
    """

    EXTENSION_LANGUAGE_MAP = {
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
        ".cs": "csharp",
        ".php": "php",
        ".rb": "ruby",
        ".swift": "swift",
        ".kt": "kotlin",
        ".sql": "sql",
    }

    def detect_language(
        self,
        path: str,
    ) -> str | None:

        extension = PurePosixPath(
            path
        ).suffix.lower()

        return self.EXTENSION_LANGUAGE_MAP.get(
            extension
        )

    def parse(
        self,
        content: str,
        language: str | None,
    ) -> dict[str, Any]:

        if not language:
            return {
                "language": None,
                "tree": None,
            }

        try:
            from app.services.parser.tree_sitter import (
                TreeSitterParser,
            )

            parser = TreeSitterParser()

            result = parser.parse(
                content,
                language,
            )

            return {
                "language": language,
                "tree": result.tree,
                "source_code": content,
            }

        except Exception:
            return {
                "language": language,
                "tree": None,
                "source_code": content,
            }

    def create_chunks(
        self,
        content: str,
        language: str | None,
        symbols: list[dict[str, Any]],
        max_lines: int = 80,
    ) -> list[dict[str, Any]]:

        lines = content.splitlines()

        if not lines:
            return []

        chunks: list[dict[str, Any]] = []

        # Prefer symbol-aware chunks.
        for symbol in symbols:

            start_line = symbol.get(
                "start_line",
                1,
            )

            end_line = symbol.get(
                "end_line",
                start_line,
            )

            start_index = max(
                start_line - 1,
                0,
            )

            end_index = min(
                end_line,
                len(lines),
            )

            chunk_content = "\n".join(
                lines[start_index:end_index]
            )

            if not chunk_content.strip():
                continue

            chunks.append(
                {
                    "content": chunk_content,
                    "start_line": start_line,
                    "end_line": end_line,
                    "chunk_type": symbol.get(
                        "symbol_type",
                        "symbol",
                    ),
                    "symbol_name": symbol.get(
                        "name"
                    ),
                    "symbol_type": symbol.get(
                        "symbol_type"
                    ),
                    "language": language,
                }
            )

        # If no symbols were detected, fall back
        # to deterministic line-based chunks.

        if not chunks:

            for start in range(
                0,
                len(lines),
                max_lines,
            ):

                end = min(
                    start + max_lines,
                    len(lines),
                )

                chunk_content = "\n".join(
                    lines[start:end]
                )

                chunks.append(
                    {
                        "content": chunk_content,
                        "start_line": start + 1,
                        "end_line": end,
                        "chunk_type": "block",
                        "symbol_name": None,
                        "symbol_type": None,
                        "language": language,
                    }
                )

        return chunks