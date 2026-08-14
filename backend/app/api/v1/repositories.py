"""
Repository API routes.
"""

from typing import Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy import select, delete

from app.core.database import AsyncSessionLocal
from app.core.security import get_current_user, get_current_user_id
from app.models.dependency import Dependency
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.models.symbol import Symbol
from app.models.user import User
from app.schemas.repository import RepositoryCreate, RepositoryResponse
from app.services.github.client import GitHubClient
from app.services.github.repositories import GitHubRepositoryService
from app.services.github.sync import GitHubSyncService
from app.models.commit import Commit
from app.models.branch import Branch
from app.models.contributor import Contributor

router = APIRouter()


def _repo_to_dict(repo: Repository) -> dict[str, Any]:
    return {
        "id": str(repo.id),
        "owner_id": str(repo.owner_id),
        "github_repo_id": str(repo.github_repo_id),
        "name": repo.name,
        "full_name": repo.full_name,
        "description": repo.description,
        "html_url": repo.html_url,
        "clone_url": repo.clone_url,
        "default_branch": repo.default_branch,
        "language": repo.language,
        "stars": repo.stars,
        "forks": repo.forks,
        "size_kb": repo.size_kb,
        "is_private": repo.is_private,
        "ingestion_status": repo.ingestion_status,
        "ingestion_error": repo.ingestion_error,
        "last_ingested_commit": repo.last_ingested_commit,
        "created_at": repo.created_at,
        "updated_at": repo.updated_at,
    }


# ============================================================
# List GitHub repositories
# ============================================================

@router.get("/repositories")
async def list_repositories(
    current_user: dict[str, Any] = Depends(get_current_user),
    github_access_token: str | None = None,
):
    """Fetch repositories available to the authenticated GitHub user."""

    try:
        github_client = GitHubClient()
        if not github_access_token:
            github_access_token = current_user.get("github_access_token")

        if not github_access_token:
            async with AsyncSessionLocal() as db:
                user_id = current_user.get("sub")
                if user_id:
                    result = await db.execute(select(User).where(User.id == user_id))
                    u = result.scalar_one_or_none()
                    if u and getattr(u, "github_access_token", None):
                        github_access_token = u.github_access_token

        if not github_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub access token is required.",
            )
        
        service = GitHubRepositoryService(client=github_client, access_token=github_access_token)

        repositories = await service.list_repositories(username=None)

        user_id = current_user.get("sub")
        if user_id:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user is not None:
                    for repo_data in repositories:
                        repo_id = str(repo_data.get("id"))
                        repo_result = await db.execute(
                            select(Repository).where(
                                Repository.owner_id == user.id,
                                Repository.github_repo_id == repo_id,
                            )
                        )
                        repo = repo_result.scalar_one_or_none()

                        if repo is None:
                            repo = Repository(
                                owner_id=user.id,
                                github_repo_id=repo_id,
                                name=(repo_data.get("name") or "").strip() or "repository",
                                full_name=(repo_data.get("full_name") or "").strip() or repo_data.get("name") or "repository",
                                description=repo_data.get("description"),
                                html_url=(repo_data.get("html_url") or ""),
                                clone_url=repo_data.get("clone_url"),
                                default_branch=(repo_data.get("default_branch") or "main"),
                                language=repo_data.get("language"),
                                stars=int(repo_data.get("stargazers_count") or 0),
                                forks=int(repo_data.get("forks_count") or 0),
                                size_kb=int((repo_data.get("size") or 0) * 1024),
                                is_private=bool(repo_data.get("private")),
                            )
                            db.add(repo)
                        else:
                            repo.name = (repo_data.get("name") or repo.name).strip() or repo.name
                            repo.full_name = (repo_data.get("full_name") or repo.full_name).strip() or repo.full_name
                            repo.description = repo_data.get("description")
                            repo.html_url = repo_data.get("html_url") or repo.html_url
                            repo.clone_url = repo_data.get("clone_url")
                            repo.default_branch = repo_data.get("default_branch") or repo.default_branch
                            repo.language = repo_data.get("language")
                            repo.stars = int(repo_data.get("stargazers_count") or repo.stars)
                            repo.forks = int(repo_data.get("forks_count") or repo.forks)
                            repo.size_kb = int((repo_data.get("size") or (repo.size_kb // 1024)) * 1024)
                            repo.is_private = bool(repo_data.get("private"))

                    await db.commit()

        return {
            "count": len(repositories),
            "repositories": repositories,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to fetch repositories: {exc}",
        )


@router.post("/repositories", status_code=status.HTTP_201_CREATED)
async def create_repository(
    payload: RepositoryCreate,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Register a GitHub repository in RepoRAG."""

    async with AsyncSessionLocal() as db:
        user_id = current_user.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Current user id is missing.")

        user_result = await db.execute(select(User).where(User.id == user_id))
        known_user = user_result.scalar_one_or_none()
        if known_user is None:
            raise HTTPException(status_code=404, detail="Authenticated user not found.")

        existing = await db.execute(
            select(Repository).where(
                Repository.owner_id == known_user.id,
                Repository.github_repo_id == payload.github_repo_id,
            )
        )
        repo = existing.scalar_one_or_none()

        if repo is None:
            repo = Repository(
                owner_id=known_user.id,
                github_repo_id=payload.github_repo_id,
                name=payload.name,
                full_name=payload.full_name,
                description=payload.description,
                html_url=payload.html_url,
                clone_url=payload.clone_url,
                default_branch=payload.default_branch,
                language=payload.language,
                stars=payload.stars,
                forks=payload.forks,
                size_kb=payload.size_kb * 1024,
                is_private=payload.is_private,
            )
            db.add(repo)
            await db.commit()
            await db.refresh(repo)

        return _repo_to_dict(repo)


# NOTE: The owner/repo handlers were intentionally moved later in the
# file to avoid route precedence collisions with ID-based routes such
# as `/repositories/{repository_id}/files`.


# ============================================================
# Repository branches
# ============================================================

@router.get("/repositories/{owner}/{repo}/branches")
async def get_repository_branches(
    owner: str,
    repo: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    github_access_token: str | None = None,
):
    """Fetch branches of a GitHub repository."""

    try:
        github_client = GitHubClient()
        
        if not github_access_token:
            github_access_token = current_user.get("github_access_token")

        if not github_access_token:
            async with AsyncSessionLocal() as db:
                user_id = current_user.get("sub")
                if user_id:
                    result = await db.execute(select(User).where(User.id == user_id))
                    u = result.scalar_one_or_none()
                    if u and getattr(u, "github_access_token", None):
                        github_access_token = u.github_access_token

        if not github_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub access token is required.",
            )
        
        service = GitHubRepositoryService(client=github_client, access_token=github_access_token)

        branches = await service.get_branches(owner=owner, repo=repo)
        return {"owner": owner, "repository": repo, "branches": branches}

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to fetch branches: {exc}",
        )


# ============================================================
# Repository details
# ============================================================

@router.get("/repositories/{repository_id}")
async def get_repository_by_id(
    repository_id: int = Path(..., description="GitHub repository numeric id"),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Fetch a repository stored in RepoRAG."""

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))
        repo = result.scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")

        if str(repo.owner_id) != str(current_user.get("sub")):
            raise HTTPException(status_code=403, detail="This repository is not owned by the current user.")

        return _repo_to_dict(repo)


@router.get("/repositories/{repository_id}/files")
async def get_repository_files(
    repository_id: int = Path(..., description="GitHub repository numeric id"),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))
        repo = result.scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")
        files = await db.execute(select(RepositoryFile).where(RepositoryFile.repository_id == repo.id).order_by(RepositoryFile.path))
        return {"repository_id": str(repository_id), "files": [{
            "id": str(item.id),
            "path": item.path,
            "filename": item.filename,
            "extension": item.extension,
            "language": item.language,
            "size_bytes": item.size_bytes,
            "processing_status": item.processing_status,
        } for item in files.scalars().all()]}


@router.get("/repositories/{repository_id}/files/{file_id}")
async def get_repository_file_by_id(
    file_id: UUID = Path(..., description="Repository file UUID"),
    repository_id: int = Path(..., description="GitHub repository numeric id"),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    async with AsyncSessionLocal() as db:
        # Validate repository exists and belongs to user
        repo_result = await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))
        repo = repo_result.scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")

        result = await db.execute(
            select(RepositoryFile).where(
                RepositoryFile.id == file_id,
                RepositoryFile.repository_id == repo.id,
            )
        )
        file = result.scalar_one_or_none()
        if file is None:
            raise HTTPException(status_code=404, detail="Repository file not found.")
        return {
            "id": str(file.id),
            "repository_id": str(file.repository_id),
            "path": file.path,
            "filename": file.filename,
            "extension": file.extension,
            "language": file.language,
            "size_bytes": file.size_bytes,
            "processing_status": file.processing_status,
            "extra_metadata": file.extra_metadata,
        }


@router.get("/repositories/{repository_id}/symbols")
async def get_repository_symbols(
    repository_id: int = Path(..., description="GitHub repository numeric id"),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    async with AsyncSessionLocal() as db:
        # Resolve repository and use its internal UUID for queries
        repo_result = await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))
        repo = repo_result.scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")

        file_ids_result = await db.execute(
            select(RepositoryFile.id).where(RepositoryFile.repository_id == repo.id)
        )
        file_ids = file_ids_result.scalars().all()

        if not file_ids:
            return {"repository_id": str(repository_id), "symbols": []}

        result = await db.execute(select(Symbol).where(Symbol.file_id.in_(file_ids)))
        symbols = result.scalars().all()

        return {
            "repository_id": str(repository_id),
            "symbols": [
                {
                    "id": str(item.id),
                    "name": item.name,
                    "qualified_name": item.qualified_name,
                    "symbol_type": item.symbol_type,
                    "start_line": item.start_line,
                    "end_line": item.end_line,
                    "signature": item.signature,
                }
                for item in symbols
            ],
        }


@router.get("/repositories/{repository_id}/dependencies")
async def get_repository_dependencies(
    repository_id: int = Path(..., description="GitHub repository numeric id"),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    async with AsyncSessionLocal() as db:
        # Resolve repository and use its internal UUID for queries
        repo_result = await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))
        repo = repo_result.scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")

        result = await db.execute(select(Dependency).where(Dependency.repository_id == repo.id).order_by(Dependency.created_at))
        entries = result.scalars().all()
        return {"repository_id": str(repository_id), "dependencies": [{
            "id": str(item.id),
            "source_file_id": str(item.source_file_id),
            "target_file_id": str(item.target_file_id),
            "dependency_type": item.dependency_type,
            "source_symbol": item.source_symbol,
            "target_symbol": item.target_symbol,
        } for item in entries]}


# ============================================================
# GitHub Sync / Metadata
# ============================================================


@router.post("/repositories/{repository_id}/sync")
async def sync_repository_metadata(
    repository_id: int = Path(..., description="GitHub repository numeric id"),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Fetch repository metadata (branches, commits, contributors) from GitHub and persist to DB."""

    async with AsyncSessionLocal() as db:
        repo = (await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))).scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")
        if str(repo.owner_id) != str(current_user.get("sub")):
            raise HTTPException(status_code=403, detail="This repository is not owned by the current user.")

        access_token = current_user.get("github_access_token")
        if not access_token:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(User).where(User.id == current_user.get("sub")))
                u = result.scalar_one_or_none()
                if u and getattr(u, "github_access_token", None):
                    access_token = u.github_access_token

        if not access_token:
            raise HTTPException(status_code=401, detail="GitHub access token is required.")

        client = GitHubClient()
        sync_service = GitHubSyncService(client, access_token)

        owner, name = repo.full_name.split("/", 1)

        # Fetch branches
        branches = await sync_service.list_branches(owner, name)

        # Replace existing branches for this repo
        await db.execute(delete(Branch).where(Branch.repository_id == repo.id))

        for b in branches:
            commit_sha = None
            if isinstance(b.get("commit"), dict):
                commit_sha = b.get("commit", {}).get("sha")

            db.add(Branch(repository_id=repo.id, name=b.get("name"), commit_sha=commit_sha, is_protected=bool(b.get("protected", False))))

        # Fetch contributors (first page)
        contributors = await sync_service.list_contributors(owner, name)

        await db.execute(delete(Contributor).where(Contributor.repository_id == repo.id))

        for c in contributors:
            db.add(Contributor(repository_id=repo.id, login=c.get("login"), contributions=int(c.get("contributions") or 0), avatar_url=c.get("avatar_url"), html_url=c.get("html_url")))

        # Fetch recent commits on default branch (first page)
        commits = await sync_service.list_commits(owner, name, branch=repo.default_branch)

        await db.execute(delete(Commit).where(Commit.repository_id == repo.id))

        for cm in commits:
            sha = cm.get("sha")
            commit_info = cm.get("commit", {})
            author = commit_info.get("author") or {}
            # Parse authored date string (ISO8601) into a datetime object
            authored_dt = None
            authored_date_str = author.get("date")
            if authored_date_str:
                try:
                    # GitHub returns timestamps like '2026-08-11T18:41:13Z'
                    authored_dt = datetime.fromisoformat(authored_date_str.replace("Z", "+00:00"))
                except Exception:
                    authored_dt = None

            db.add(Commit(
                repository_id=repo.id,
                sha=sha,
                message=commit_info.get("message"),
                author_name=author.get("name"),
                author_email=author.get("email"),
                authored_date=authored_dt,
                html_url=cm.get("html_url"),
            ))

        await db.commit()

        return {"repository_id": str(repository_id), "branches": len(branches), "contributors": len(contributors), "commits": len(commits)}


@router.get("/repositories/{repository_id}/contributors")
async def get_repository_contributors(repository_id: int = Path(..., description="GitHub repository numeric id"), current_user: dict[str, Any] = Depends(get_current_user)):
    async with AsyncSessionLocal() as db:
        repo = (await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))).scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")
        result = await db.execute(select(Contributor).where(Contributor.repository_id == repo.id).order_by(Contributor.contributions.desc()))
        entries = result.scalars().all()
        return {"repository_id": str(repository_id), "contributors": [{"login": e.login, "contributions": e.contributions, "avatar_url": e.avatar_url, "html_url": e.html_url} for e in entries]}


@router.get("/repositories/{repository_id}/commits")
async def get_repository_commits(repository_id: int = Path(..., description="GitHub repository numeric id"), current_user: dict[str, Any] = Depends(get_current_user)):
    async with AsyncSessionLocal() as db:
        repo = (await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))).scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")
        result = await db.execute(select(Commit).where(Commit.repository_id == repo.id).order_by(Commit.created_at.desc()))
        entries = result.scalars().all()
        return {"repository_id": str(repository_id), "commits": [{"sha": e.sha, "message": e.message, "author_name": e.author_name, "author_email": e.author_email, "authored_date": e.authored_date, "html_url": e.html_url} for e in entries]}


# ============================================================
# Delete repository
# ============================================================

@router.delete(
    "/repositories/{repository_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_repository(
    repository_id: int = Path(..., description="GitHub repository numeric id"),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Remove a repository and its associated RepoRAG data."""

    async with AsyncSessionLocal() as db:
        repo = (await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))).scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")
        if str(repo.owner_id) != str(current_user.get("sub")):
            raise HTTPException(status_code=403, detail="This repository is not owned by the current user.")
        await db.delete(repo)
        await db.commit()

    return None


# ============================================================
# Get GitHub repository (by owner/name)
# ============================================================

@router.get("/repositories/{owner}/{repo}")
async def get_repository(
    owner: str,
    repo: str,
    current_user: dict[str, Any] = Depends(get_current_user),
    github_access_token: str | None = None,
):
    """Fetch a specific GitHub repository."""

    try:
        github_client = GitHubClient()

        if not github_access_token:
            github_access_token = current_user.get("github_access_token")

        if not github_access_token:
            async with AsyncSessionLocal() as db:
                user_id = current_user.get("sub")
                if user_id:
                    result = await db.execute(select(User).where(User.id == user_id))
                    u = result.scalar_one_or_none()
                    if u and getattr(u, "github_access_token", None):
                        github_access_token = u.github_access_token

        if not github_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub access token is required.",
            )

        service = GitHubRepositoryService(client=github_client, access_token=github_access_token)

        repository = await service.get_repository(owner=owner, repo=repo)
        return repository

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to fetch repository: {exc}",
        )