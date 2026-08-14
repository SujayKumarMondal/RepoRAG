"""
API route extraction.
"""

import re
from typing import Any


class RouteExtractor:
    """
    Extracts HTTP routes from source code.

    Supports common FastAPI/Flask/Express-style patterns.
    """

    ROUTE_PATTERNS = [
        re.compile(
            r'@\w+\.(get|post|put|patch|delete|options|head)'
            r'\(\s*["\']([^"\']+)'
        ),
        re.compile(
            r'@app\.(get|post|put|patch|delete)'
            r'\(\s*["\']([^"\']+)'
        ),
        re.compile(
            r'app\.(get|post|put|patch|delete)'
            r'\(\s*["\']([^"\']+)'
        ),
    ]

    def extract(
        self,
        content: str,
        language: str | None,
        ast_result: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:

        routes = []

        for line_number, line in enumerate(
            content.splitlines(),
            start=1,
        ):

            for pattern in self.ROUTE_PATTERNS:

                match = pattern.search(line)

                if not match:
                    continue

                routes.append(
                    {
                        "method": match.group(1).upper(),
                        "path": match.group(2),
                        "line": line_number,
                    }
                )

        return routes