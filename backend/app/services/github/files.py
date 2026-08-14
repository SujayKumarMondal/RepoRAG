"""
GitHub repository file operations.
"""

import base64
from typing import Any

from app.services.github.client import GitHubClient


class GitHubFileService:
    """
    Handles GitHub repository contents and tree operations.
    """

    def __init__(
        self,
        client: GitHubClient,
        access_token: str,
    ) -> None:
        self.client = client
        self.access_token = access_token

    async def get_tree(
        self,
        owner: str,
        repo: str,
        branch: str,
    ) -> list[dict[str, Any]]:

        branch_data = await self.client.get(
            f"/repos/{owner}/{repo}/branches/{branch}",
            self.access_token,
        )

        commit_sha = branch_data["commit"]["sha"]

        commit = await self.client.get(
            f"/repos/{owner}/{repo}/git/commits/{commit_sha}",
            self.access_token,
        )

        tree_sha = commit["tree"]["sha"]

        tree = await self.client.get(
            f"/repos/{owner}/{repo}/git/trees/{tree_sha}?recursive=1",
            self.access_token,
        )

        return tree.get("tree", [])

    async def list_files(
        self,
        owner: str,
        repo: str,
        branch: str,
    ) -> list[dict[str, Any]]:

        tree = await self.get_tree(
            owner,
            repo,
            branch,
        )

        return [
            item
            for item in tree
            if item.get("type") == "blob"
        ]

    async def get_file(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str | None = None,
    ) -> dict[str, Any]:

        endpoint = (
            f"/repos/{owner}/{repo}/contents/{path}"
        )

        if ref:
            endpoint += f"?ref={ref}"

        return await self.client.get(endpoint, self.access_token)

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str | None = None,
    ) -> str:

        data = await self.get_file(
            owner,
            repo,
            path,
            ref,
        )

        encoded_content = data.get("content", "")

        if not encoded_content:
            return ""

        encoded_content = encoded_content.replace(
            "\n",
            "",
        )

        try:
            decoded = base64.b64decode(
                encoded_content
            )

            return decoded.decode(
                "utf-8",
                errors="replace",
            )

        except Exception:
            return ""