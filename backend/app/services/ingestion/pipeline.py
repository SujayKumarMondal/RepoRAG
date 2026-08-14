"""
RepoRAG repository ingestion pipeline.
"""

from dataclasses import dataclass, field
from typing import Any

from app.services.ingestion.file_filter import (
    RepositoryFileFilter,
)
from app.services.parser.ast_parser import (
    ASTParser,
)
from app.services.parser.imports import (
    ImportExtractor,
)
from app.services.parser.routes import (
    RouteExtractor,
)
from app.services.parser.symbols import (
    SymbolExtractor,
)


@dataclass
class ProcessedFile:
    """
    Result of processing one source file.
    """

    path: str

    content: str

    language: str | None = None

    chunks: list[dict[str, Any]] = field(
        default_factory=list
    )

    symbols: list[dict[str, Any]] = field(
        default_factory=list
    )

    imports: list[dict[str, Any]] = field(
        default_factory=list
    )

    routes: list[dict[str, Any]] = field(
        default_factory=list
    )


class IngestionPipeline:
    """
    Coordinates:

    GitHub files
        ↓
    filtering
        ↓
    parsing
        ↓
    symbols
        ↓
    imports
        ↓
    routes
        ↓
    chunks
    """

    def __init__(
        self,
        file_filter: RepositoryFileFilter | None = None,
    ) -> None:

        self.file_filter = (
            file_filter
            or RepositoryFileFilter()
        )

        self.ast_parser = ASTParser()

        self.symbol_extractor = SymbolExtractor()

        self.import_extractor = ImportExtractor()

        self.route_extractor = RouteExtractor()

    async def process_file(
        self,
        path: str,
        content: str,
    ) -> ProcessedFile:

        if not self.file_filter.should_process(path):
            raise ValueError(
                f"File is not supported: {path}"
            )

        language = (
            self.ast_parser.detect_language(path)
        )

        ast_result = (
            self.ast_parser.parse(
                content,
                language,
            )
        )

        symbols = (
            self.symbol_extractor.extract(
                content,
                language,
                ast_result,
            )
        )

        imports = (
            self.import_extractor.extract(
                content,
                language,
                ast_result,
            )
        )

        routes = (
            self.route_extractor.extract(
                content,
                language,
                ast_result,
            )
        )

        chunks = self.ast_parser.create_chunks(
            content=content,
            language=language,
            symbols=symbols,
        )

        return ProcessedFile(
            path=path,
            content=content,
            language=language,
            chunks=chunks,
            symbols=symbols,
            imports=imports,
            routes=routes,
        )

    async def process_repository(
        self,
        files: list[dict[str, Any]],
    ) -> list[ProcessedFile]:

        results = []

        for file in files:

            path = file.get("path", "")

            content = file.get(
                "content",
                "",
            )

            if not content:
                continue

            try:
                result = await self.process_file(
                    path,
                    content,
                )

                results.append(result)

            except Exception:
                # Individual file failures should not
                # stop the complete repository ingestion.
                continue

        return results