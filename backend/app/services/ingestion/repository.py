"""
Repository ingestion orchestration.
"""

from typing import Any

from app.services.github.client import GitHubClient
from app.services.github.files import GitHubFileService
from app.services.github.repositories import (
    GitHubRepositoryService,
)
from app.services.ingestion.file_filter import (
    RepositoryFileFilter,
)


class RepositoryIngestionService:
    """
    Fetches a GitHub repository and prepares its files
    for the RepoRAG processing pipeline.
    """

    def __init__(
        self,
        github_client: GitHubClient,
        access_token: str,
        include_tests: bool = True,
        include_documentation: bool = True,
    ) -> None:

        self.github_repository_service = (
            GitHubRepositoryService(
                github_client,
                access_token,
            )
        )

        self.github_file_service = (
            GitHubFileService(
                github_client,
                access_token,
            )
        )

        self.file_filter = RepositoryFileFilter(
            include_tests=include_tests,
            include_documentation=include_documentation,
        )

    async def fetch_repository(
        self,
        owner: str,
        repo: str,
        branch: str | None = None,
    ) -> dict[str, Any]:

        repository = (
            await self.github_repository_service
            .get_repository(
                owner,
                repo,
            )
        )

        if branch is None:
            branch = repository.get(
                "default_branch",
                "main",
            )

        return {
            "repository": repository,
            "branch": branch,
        }

    async def fetch_files(
        self,
        owner: str,
        repo: str,
        branch: str,
    ) -> list[dict[str, Any]]:

        files = (
            await self.github_file_service
            .list_files(
                owner,
                repo,
                branch,
            )
        )

        return [
            file
            for file in files
            if self.file_filter.should_process(
                file.get("path", "")
            )
        ]

    async def fetch_file_contents(
        self,
        owner: str,
        repo: str,
        branch: str,
        files: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        results = []

        for file in files:

            path = file["path"]

            content = (
                await self.github_file_service
                .get_file_content(
                    owner,
                    repo,
                    path,
                    branch,
                )
            )

            results.append(
                {
                    **file,
                    "content": content,
                }
            )

        return results