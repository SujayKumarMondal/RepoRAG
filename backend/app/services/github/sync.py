"""
GitHub synchronization service.

Fetches branches, commits, and contributors and persists them to the DB.
"""

from typing import Any, List

from app.services.github.client import GitHubClient
from app.services.github.repositories import GitHubRepositoryService


class GitHubSyncService:
    def __init__(self, client: GitHubClient, access_token: str) -> None:
        self.client = client
        self.access_token = access_token
        self.repo_service = GitHubRepositoryService(client, access_token)

    async def list_branches(self, owner: str, repo: str) -> List[dict[str, Any]]:
        return await self.repo_service.get_branches(owner, repo)

    async def list_commits(self, owner: str, repo: str, branch: str | None = None, per_page: int = 100, page: int = 1) -> List[dict[str, Any]]:
        endpoint = f"/repos/{owner}/{repo}/commits?per_page={per_page}&page={page}"
        if branch:
            endpoint += f"&sha={branch}"
        return await self.client.get(endpoint, self.access_token)

    async def list_contributors(self, owner: str, repo: str, per_page: int = 100, page: int = 1) -> List[dict[str, Any]]:
        endpoint = f"/repos/{owner}/{repo}/contributors?per_page={per_page}&page={page}"
        return await self.client.get(endpoint, self.access_token)
