"""
GitHub repository operations.
"""

from typing import Any

from app.services.github.client import GitHubClient


class GitHubRepositoryService:
    """
    High-level GitHub repository operations.
    """

    def __init__(
        self,
        client: GitHubClient,
        access_token: str,
    ) -> None:
        self.client = client
        self.access_token = access_token

    async def get_repository(
        self,
        owner: str,
        repo: str,
    ) -> dict[str, Any]:
        """
        Get repository information.
        """

        return await self.client.get(
            f"/repos/{owner}/{repo}",
            self.access_token,
        )

    async def list_repositories(
        self,
        username: str | None = None,
        per_page: int = 100,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """
        List repositories for the authenticated user
        or a specified GitHub user.
        """

        if username:
            endpoint = (
                f"/users/{username}/repos"
                f"?per_page={per_page}"
                f"&page={page}"
            )
        else:
            endpoint = (
                f"/user/repos"
                f"?per_page={per_page}"
                f"&page={page}"
            )

        return await self.client.get(
            endpoint,
            self.access_token,
        )

    async def get_default_branch(
        self,
        owner: str,
        repo: str,
    ) -> str:
        repository = await self.get_repository(
            owner,
            repo,
        )

        return repository.get(
            "default_branch",
            "main",
        )
        
        
    async def get_branches(
        self,
        owner: str,
        repo: str,
    ) -> list[dict[str, Any]]:
        """
        Get repository branches.
        """

        return await self.client.get(
            f"/repos/{owner}/{repo}/branches",
            self.access_token,
        )

    async def get_branch(
        self,
        owner: str,
        repo: str,
        branch: str,
    ) -> dict[str, Any]:
        """
        Get a single branch by name.
        """

        return await self.client.get(
            f"/repos/{owner}/{repo}/branches/{branch}",
            self.access_token,
        )

    async def get_latest_commit(
        self,
        owner: str,
        repo: str,
        branch: str,
    ) -> str:

        branch_data = await self.get_branch(
            owner,
            repo,
            branch,
        )

        return branch_data["commit"]["sha"]