"""
Source-code symbol extraction.
"""

import ast
from typing import Any


class SymbolExtractor:
    """
    Extracts functions, classes and methods.

    Python gets AST-aware extraction.
    Other languages currently use a conservative fallback.
    """

    def extract(
        self,
        content: str,
        language: str | None,
        ast_result: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:

        if language == "python":
            return self._extract_python(content)

        return self._extract_generic(content)

    def _extract_python(
        self,
        content: str,
    ) -> list[dict[str, Any]]:

        results = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return results

        for node in ast.walk(tree):

            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):

                results.append(
                    {
                        "name": node.name,
                        "qualified_name": node.name,
                        "symbol_type": "function",
                        "start_line": node.lineno,
                        "end_line": getattr(
                            node,
                            "end_lineno",
                            node.lineno,
                        ),
                        "signature": self._python_signature(
                            node
                        ),
                        "docstring": ast.get_docstring(
                            node
                        ),
                    }
                )

            elif isinstance(
                node,
                ast.ClassDef,
            ):

                results.append(
                    {
                        "name": node.name,
                        "qualified_name": node.name,
                        "symbol_type": "class",
                        "start_line": node.lineno,
                        "end_line": getattr(
                            node,
                            "end_lineno",
                            node.lineno,
                        ),
                        "signature": f"class {node.name}",
                        "docstring": ast.get_docstring(
                            node
                        ),
                    }
                )

        return sorted(
            results,
            key=lambda item: item["start_line"],
        )

    def _python_signature(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> str:

        prefix = (
            "async def"
            if isinstance(
                node,
                ast.AsyncFunctionDef,
            )
            else "def"
        )

        return f"{prefix} {node.name}(...)"

    def _extract_generic(
        self,
        content: str,
    ) -> list[dict[str, Any]]:

        results = []

        for line_number, line in enumerate(
            content.splitlines(),
            start=1,
        ):

            stripped = line.strip()

            if stripped.startswith(
                "function "
            ):

                name = stripped.split(
                    "function ",
                    1,
                )[1].split(
                    "(",
                    1,
                )[0]

                results.append(
                    {
                        "name": name,
                        "qualified_name": name,
                        "symbol_type": "function",
                        "start_line": line_number,
                        "end_line": line_number,
                    }
                )

            elif stripped.startswith(
                "class "
            ):

                name = stripped.split(
                    "class ",
                    1,
                )[1].split(
                    "(",
                    1,
                )[0].split(
                    ":",
                    1,
                )[0]

                results.append(
                    {
                        "name": name.strip(),
                        "qualified_name": name.strip(),
                        "symbol_type": "class",
                        "start_line": line_number,
                        "end_line": line_number,
                    }
                )

        return results