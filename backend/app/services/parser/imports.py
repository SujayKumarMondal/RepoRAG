"""
Import/dependency extraction.
"""

import ast
from typing import Any


class ImportExtractor:
    """
    Extracts imports from source files.
    """

    def extract(
        self,
        content: str,
        language: str | None,
        ast_result: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:

        if language == "python":
            return self._extract_python(
                content
            )

        return self._extract_generic(
            content,
            language,
        )

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
                ast.Import,
            ):

                for alias in node.names:

                    results.append(
                        {
                            "module": alias.name,
                            "name": alias.asname,
                            "type": "import",
                        }
                    )

            elif isinstance(
                node,
                ast.ImportFrom,
            ):

                module = node.module or ""

                for alias in node.names:

                    results.append(
                        {
                            "module": module,
                            "name": alias.name,
                            "alias": alias.asname,
                            "type": "from_import",
                        }
                    )

        return results

    def _extract_generic(
        self,
        content: str,
        language: str | None,
    ) -> list[dict[str, Any]]:

        results = []

        for line in content.splitlines():

            stripped = line.strip()

            if stripped.startswith(
                "import "
            ):

                results.append(
                    {
                        "module": stripped[
                            len("import "):
                        ].strip(),
                        "type": "import",
                    }
                )

            elif stripped.startswith(
                "from "
            ) and " import " in stripped:

                module = stripped.split(
                    " import ",
                    1,
                )[0][len("from "):]

                results.append(
                    {
                        "module": module.strip(),
                        "type": "from_import",
                    }
                )

        return results