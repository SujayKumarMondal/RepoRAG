"""
Repository dependency graph API routes.
"""

from collections import defaultdict, deque
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.dependency import Dependency
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile


router = APIRouter()


# ============================================================
# Complete dependency graph
# ============================================================

@router.get("/graph/{repository_id}")
async def get_dependency_graph(repository_id: int = Path(..., description="GitHub repository numeric id")):
    """Return the complete dependency graph of a repository."""

    async with AsyncSessionLocal() as db:
        repo = (await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))).scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")

        deps = (await db.execute(select(Dependency).where(Dependency.repository_id == repo.id))).scalars().all()
        files = (await db.execute(select(RepositoryFile).where(RepositoryFile.repository_id == repo.id))).scalars().all()

        node_map = {item.path: {"id": str(item.id), "path": item.path, "filename": item.filename} for item in files}
        edges = [{"source": source_path, "target": target_path, "dependency_type": dep.dependency_type} for dep in deps for source_path, target_path in [
            (next((f.path for f in files if f.id == dep.source_file_id), dep.source_file_id), next((f.path for f in files if f.id == dep.target_file_id), dep.target_file_id))
        ]]

        return {
            "repository_id": str(repository_id),
            "nodes": list(node_map.values()),
            "edges": edges,
        }


# ============================================================
# File dependencies
# ============================================================

@router.get("/graph/{repository_id}/file/{file_path:path}")
async def get_file_dependencies(repository_id: int = Path(..., description="GitHub repository numeric id"), file_path: str = Path(..., description="Repository file path")):
    """Return dependencies of a specific file."""

    async with AsyncSessionLocal() as db:
        # Resolve repository and use internal UUID
        repo = (await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))).scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")

        file_row = (await db.execute(select(RepositoryFile).where(RepositoryFile.repository_id == repo.id, RepositoryFile.path == file_path))).scalar_one_or_none()
        if file_row is None:
            # Provide a short sample of available paths to help debug mismatches
            available = (await db.execute(select(RepositoryFile.path).where(RepositoryFile.repository_id == repo.id).limit(50))).scalars().all()
            raise HTTPException(status_code=404, detail={
                "error": "File not found in repository.",
                "requested": file_path,
                "available_sample_count": len(available),
                "available_sample": available[:20],
            })

        outgoing = (await db.execute(select(Dependency).where(Dependency.repository_id == repo.id, Dependency.source_file_id == file_row.id))).scalars().all()
        incoming = (await db.execute(select(Dependency).where(Dependency.repository_id == repo.id, Dependency.target_file_id == file_row.id))).scalars().all()

        return {
            "repository_id": str(repository_id),
            "file": file_path,
            "dependencies": [
                {'target': (await db.get(RepositoryFile, item.target_file_id)).path, 'type': item.dependency_type} for item in outgoing
            ],
            "dependents": [
                {'source': (await db.get(RepositoryFile, item.source_file_id)).path, 'type': item.dependency_type} for item in incoming
            ],
        }


    @router.get("/graph/{repository_id}/file_by_path")
    async def get_file_dependencies_by_query(
        repository_id: int = Path(..., description="GitHub repository numeric id"),
        file_path: str = Query(..., description="Repository file path"),
    ):
        """Return dependencies of a specific file (accepts `file_path` as query param)."""

        async with AsyncSessionLocal() as db:
            repo = (await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))).scalar_one_or_none()
            if repo is None:
                raise HTTPException(status_code=404, detail="Repository not found.")

            file_row = (await db.execute(select(RepositoryFile).where(RepositoryFile.repository_id == repo.id, RepositoryFile.path == file_path))).scalar_one_or_none()
            if file_row is None:
                available = (await db.execute(select(RepositoryFile.path).where(RepositoryFile.repository_id == repo.id).limit(50))).scalars().all()
                raise HTTPException(status_code=404, detail={
                    "error": "File not found in repository.",
                    "requested": file_path,
                    "available_sample_count": len(available),
                    "available_sample": available[:20],
                })

            outgoing = (await db.execute(select(Dependency).where(Dependency.repository_id == repo.id, Dependency.source_file_id == file_row.id))).scalars().all()
            incoming = (await db.execute(select(Dependency).where(Dependency.repository_id == repo.id, Dependency.target_file_id == file_row.id))).scalars().all()

            return {
                "repository_id": str(repository_id),
                "file": file_path,
                "dependencies": [
                    {'target': (await db.get(RepositoryFile, item.target_file_id)).path, 'type': item.dependency_type} for item in outgoing
                ],
                "dependents": [
                    {'source': (await db.get(RepositoryFile, item.source_file_id)).path, 'type': item.dependency_type} for item in incoming
                ],
            }


# ============================================================
# Symbol dependencies
# ============================================================

# @router.get("/graph/{repository_id}/symbol/{symbol}")
# async def get_symbol_dependencies(repository_id: int = Path(..., description="GitHub repository numeric id"), symbol: str = Path(..., description="Symbol name")):
#     """Return relationships involving a symbol."""

#     return {"repository_id": str(repository_id), "symbol": symbol, "dependencies": [], "dependents": []}


@router.get("/graph/{repository_id}/symbol_by_name")
async def get_symbol_dependencies_by_query(
    repository_id: int = Path(..., description="GitHub repository numeric id"),
    symbol: str = Query(..., description="Symbol name"),
):
    """Return relationships involving a symbol (accepts `symbol` as query param)."""

    async with AsyncSessionLocal() as db:
        repo = (await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))).scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")

        # Placeholder: return same shape as path-based endpoint. Implement lookups later if needed.
        return {"repository_id": str(repository_id), "symbol": symbol, "dependencies": [], "dependents": []}


@router.get("/graph/{repository_id}/symbol/{symbol}")
async def get_symbol_dependencies_by_path(repository_id: int = Path(..., description="GitHub repository numeric id"), symbol: str = Path(..., description="Symbol name")):
    """Return relationships involving a symbol (path param variant)."""

    async with AsyncSessionLocal() as db:
        repo = (await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))).scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")

        return {"repository_id": str(repository_id), "symbol": symbol, "dependencies": [], "dependents": []}


# ============================================================
# Dependency path
# ============================================================

# @router.get("/graph/{repository_id}/path")
# async def find_dependency_path(
#     repository_id: int = Path(..., description="GitHub repository numeric id"),
#     source: str = Query(..., description="Source symbol"),
#     target: str = Query(..., description="Target symbol"),
# ):
#     """Find a dependency path between two files. Accepts `source` and `target` as query params."""

#     async with AsyncSessionLocal() as db:
#         repo = (await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))).scalar_one_or_none()
#         if repo is None:
#             raise HTTPException(status_code=404, detail="Repository not found.")

#         deps = (await db.execute(select(Dependency).where(Dependency.repository_id == repo.id))).scalars().all()
#         files = {item.id: item.path for item in (await db.execute(select(RepositoryFile).where(RepositoryFile.repository_id == repo.id))).scalars().all()}

#         adj = defaultdict(list)
#         for dep in deps:
            
#             src = files.get(dep.source_file_id)
#             tgt = files.get(dep.target_file_id)
#             if src and tgt:
#                 adj[src].append(tgt)

#         queue = deque([(source, [source])])
#         visited = set()
#         while queue:
#             node, path = queue.popleft()
#             if node in visited:
#                 continue
#             visited.add(node)
#             if node == target:
#                 return {"repository_id": str(repository_id), "source": source, "target": target, "path": path}
#             for nxt in adj.get(node, []):
#                 if nxt not in visited:
#                     queue.append((nxt, path + [nxt]))

#         return {"repository_id": str(repository_id), "source": source, "target": target, "path": []}


@router.get("/graph/{repository_id}/path/{source}/{target}")
async def find_dependency_path_by_path(
    repository_id: int = Path(..., description="GitHub repository numeric id"),
    source: str = Path(..., description="Source symbol"),
    target: str = Path(..., description="Target symbol"),
):
    """Find a dependency path between two files (path param variant)."""

    async with AsyncSessionLocal() as db:
        repo = (await db.execute(select(Repository).where(Repository.github_repo_id == repository_id))).scalar_one_or_none()
        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found.")

        deps = (await db.execute(select(Dependency).where(Dependency.repository_id == repo.id))).scalars().all()
        files = {item.id: item.path for item in (await db.execute(select(RepositoryFile).where(RepositoryFile.repository_id == repo.id))).scalars().all()}

        adj = defaultdict(list)
        for dep in deps:
            src = files.get(dep.source_file_id)
            tgt = files.get(dep.target_file_id)
            if src and tgt:
                adj[src].append(tgt)

        queue = deque([(source, [source])])
        visited = set()
        while queue:
            node, path = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            if node == target:
                return {"repository_id": str(repository_id), "source": source, "target": target, "path": path}
            for nxt in adj.get(node, []):
                if nxt not in visited:
                    queue.append((nxt, path + [nxt]))

        return {"repository_id": str(repository_id), "source": source, "target": target, "path": []}