"""
GitHub API client.

Handles:
- GitHub OAuth token exchange
- Authenticated GitHub API requests
- GitHub user information
- Repository information
"""

from typing import Any

import httpx

from app.core.config import settings


class GitHubClient:
    """
    Client for interacting with GitHub APIs.
    """

    def __init__(self) -> None:
        self.api_url = settings.GITHUB_API_URL.rstrip("/")
        self.client_id = settings.GITHUB_CLIENT_ID
        self.client_secret = settings.GITHUB_CLIENT_SECRET
        self.redirect_uri = settings.GITHUB_REDIRECT_URI

    # ============================================================
    # OAuth
    # ============================================================

    async def exchange_code_for_token(
        self,
        code: str,
    ) -> str:
        """
        Exchange the temporary GitHub OAuth authorization code
        for a GitHub access token.
        """

        url = "https://github.com/login/oauth/access_token"

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        headers = {
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                data=payload,
                headers=headers,
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"GitHub token exchange failed: "
                f"{response.status_code} - {response.text}"
            )

        data = response.json()

        if "error" in data:
            raise RuntimeError(
                f"GitHub OAuth error: "
                f"{data.get('error_description', data.get('error'))}"
            )

        access_token = data.get("access_token")

        if not access_token:
            raise RuntimeError(
                "GitHub did not return an access token."
            )

        return access_token

    # ============================================================
    # Generic API request
    # ============================================================

    async def request(
        self,
        method: str,
        endpoint: str,
        access_token: str,
        **kwargs: Any,
    ) -> Any:
        """
        Make an authenticated request to GitHub API.
        """

        endpoint = endpoint.lstrip("/")

        url = f"{self.api_url}/{endpoint}"

        headers = kwargs.pop("headers", {})

        headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs,
            )

        if response.status_code >= 400:
            raise RuntimeError(
                f"GitHub API request failed: "
                f"{response.status_code} - {response.text}"
            )

        return response.json()

    # ============================================================
    # Convenience HTTP methods
    # ============================================================

    async def get(
        self,
        endpoint: str,
        access_token: str,
        **kwargs: Any,
    ) -> Any:
        return await self.request(
            method="GET",
            endpoint=endpoint,
            access_token=access_token,
            **kwargs,
        )

    # ============================================================
    # Current GitHub User
    # ============================================================

    async def get_authenticated_user(
        self,
        access_token: str,
    ) -> dict[str, Any]:
        """
        Get the GitHub user associated with an access token.
        """

        return await self.request(
            method="GET",
            endpoint="/user",
            access_token=access_token,
        )

    # ============================================================
    # User Emails
    # ============================================================

    async def get_user_emails(
        self,
        access_token: str,
    ) -> list[dict[str, Any]]:
        """
        Get authenticated user's GitHub email addresses.
        """

        return await self.request(
            method="GET",
            endpoint="/user/emails",
            access_token=access_token,
        )

    # ============================================================
    # Repositories
    # ============================================================

    async def get_user_repositories(
        self,
        access_token: str,
        page: int = 1,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get repositories accessible to the authenticated user.
        """

        return await self.request(
            method="GET",
            endpoint="/user/repos",
            access_token=access_token,
            params={
                "page": page,
                "per_page": per_page,
                "sort": "updated",
            },
        )

    # ============================================================
    # Repository
    # ============================================================

    async def get_repository(
        self,
        access_token: str,
        owner: str,
        repo: str,
    ) -> dict[str, Any]:
        """
        Get a specific repository.
        """

        return await self.request(
            method="GET",
            endpoint=f"/repos/{owner}/{repo}",
            access_token=access_token,
        )

    # ============================================================
    # Branches
    # ============================================================

    async def get_branches(
        self,
        access_token: str,
        owner: str,
        repo: str,
    ) -> list[dict[str, Any]]:
        """
        Get repository branches.
        """

        return await self.request(
            method="GET",
            endpoint=f"/repos/{owner}/{repo}/branches",
            access_token=access_token,
        )

    # ============================================================
    # Repository Contents
    # ============================================================

    async def get_contents(
        self,
        access_token: str,
        owner: str,
        repo: str,
        path: str = "",
    ) -> Any:
        """
        Get repository file/directory contents.
        """

        endpoint = f"/repos/{owner}/{repo}/contents/{path}"

        return await self.request(
            method="GET",
            endpoint=endpoint,
            access_token=access_token,
        )

    # ============================================================
    # Repository Tree
    # ============================================================

    async def get_git_tree(
        self,
        access_token: str,
        owner: str,
        repo: str,
        tree_sha: str,
        recursive: bool = True,
    ) -> dict[str, Any]:
        """
        Get a Git repository tree.
        """

        return await self.request(
            method="GET",
            endpoint=f"/repos/{owner}/{repo}/git/trees/{tree_sha}",
            access_token=access_token,
            params={
                "recursive": "1" if recursive else "0",
            },
        )