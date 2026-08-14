"""
LLM context construction.
"""

from typing import Any


class ContextBuilder:
    """
    Builds structured context from retrieved code.
    """

    def __init__(
        self,
        max_characters: int = 30000,
    ) -> None:

        self.max_characters = max_characters

    def build(
        self,
        query: str,
        results: list[dict[str, Any]],
    ) -> str:

        sections = []

        total_length = 0

        for index, result in enumerate(
            results,
            start=1,
        ):

            file_path = result.get(
                "file_path",
                "unknown",
            )

            start_line = result.get(
                "start_line"
            )

            end_line = result.get(
                "end_line"
            )

            content = result.get(
                "content",
                "",
            )

            location = file_path

            if start_line:
                location += (
                    f":{start_line}"
                )

                if end_line:
                    location += (
                        f"-{end_line}"
                    )

            section = (
                f"### Source {index}\n"
                f"File: {location}\n\n"
                f"```text\n"
                f"{content}\n"
                f"```\n"
            )

            if (
                total_length
                + len(section)
                > self.max_characters
            ):
                break

            sections.append(section)

            total_length += len(section)

        header = (
            "The following source-code context "
            "was retrieved from the repository:\n\n"
        )

        return header + "\n".join(
            sections
        )