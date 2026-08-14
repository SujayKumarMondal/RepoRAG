"""
Repository analysis service: health, code-quality, security findings.
"""
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func

from app.core.database import AsyncSessionLocal
from app.models.analysis import Analysis
from app.models.repository_file import RepositoryFile
from app.models.code_chunk import CodeChunk
from app.models.symbol import Symbol
from app.models.dependency import Dependency


SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"aws_secret_access_key", re.I),
    re.compile(r"-----BEGIN (RSA|OPENSSH|EC) PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9_]{36}"),
    re.compile(r"[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"),
]


class AnalysisService:
    def __init__(self, repository_id: str):
        self.repository_id = repository_id

    async def run(self) -> Analysis:
        async with AsyncSessionLocal() as db:
            # basic stats
            file_count = (await db.execute(select(func.count()).select_from(RepositoryFile).where(RepositoryFile.repository_id == self.repository_id))).scalar_one()
            chunk_count = (await db.execute(select(func.count()).select_from(CodeChunk).join(RepositoryFile, RepositoryFile.id == CodeChunk.file_id).where(RepositoryFile.repository_id == self.repository_id))).scalar_one()
            symbol_count = (await db.execute(select(func.count()).select_from(Symbol).join(RepositoryFile, RepositoryFile.id == Symbol.file_id).where(RepositoryFile.repository_id == self.repository_id))).scalar_one()

            # languages distribution
            languages = await db.execute(
                select(RepositoryFile.language, func.count(RepositoryFile.language)).where(RepositoryFile.repository_id == self.repository_id).group_by(RepositoryFile.language)
            )

            # duplicate detection: code chunks with same content_hash
            dups = await db.execute(
                select(CodeChunk.content_hash, func.count(CodeChunk.id)).join(RepositoryFile, RepositoryFile.id == CodeChunk.file_id).where(RepositoryFile.repository_id == self.repository_id).group_by(CodeChunk.content_hash).having(func.count(CodeChunk.id) > 1)
            )
            duplicate_groups = dups.all()

            # dead code: symbols not referenced in dependencies
            sym_res = await db.execute(select(Symbol).join(RepositoryFile).where(RepositoryFile.repository_id == self.repository_id))
            symbols = sym_res.scalars().all()

            referenced_names = set()
            deps = await db.execute(select(Dependency).where(Dependency.repository_id == self.repository_id))
            for d in deps.scalars().all():
                if d.target_symbol:
                    referenced_names.add(d.target_symbol)

            dead_symbols = [s for s in symbols if s.name not in referenced_names]

            # security scanning: look for secrets in repository files
            findings: list[dict[str, Any]] = []
            files = (await db.execute(select(RepositoryFile).where(RepositoryFile.repository_id == self.repository_id))).scalars().all()
            for f in files:
                # load file content if stored in metadata (some code stores file content elsewhere)
                content = f.extra_metadata.get("content") if f.extra_metadata else None
                # if content not available in metadata, try to load chunks for this file
                if not content:
                    chunk = (await db.execute(select(CodeChunk).where(CodeChunk.file_id == f.id).limit(1))).scalars().first()
                    content = chunk.content if chunk else ""

                if not content:
                    continue

                for pattern in SECRET_PATTERNS:
                    for m in pattern.finditer(content):
                        findings.append({"file": f.path, "match": m.group(0)[:200], "pattern": pattern.pattern, "severity": "critical" if "PRIVATE KEY" in (m.group(0) or "") else "high"})

            # code quality heuristics
            large_files = []
            todos = 0
            avg_tokens = 0
            token_counts = (await db.execute(select(func.avg(CodeChunk.token_count)).join(RepositoryFile).where(RepositoryFile.repository_id == self.repository_id))).scalar_one() or 0
            avg_tokens = float(token_counts)

            for f in files:
                if f.size_bytes and f.size_bytes > 200_000:
                    large_files.append(f.path)
                if f.extra_metadata and isinstance(f.extra_metadata, dict):
                    if f.extra_metadata.get("contains_todos"):
                        todos += 1

            # simple scoring
            score = 100
            score -= min(30, len(duplicate_groups) * 2)
            score -= min(30, len(large_files) * 1)
            score -= min(20, len(findings) * 3)
            score = max(0, int(score))

            result = {
                "files": int(file_count or 0),
                "code_chunks": int(chunk_count or 0),
                "symbols": int(symbol_count or 0),
                "languages": {k: int(v) for k, v in languages.all() if k is not None},
                "duplicate_groups": [{"hash": h, "count": c} for h, c in duplicate_groups],
                "dead_symbols_count": len(dead_symbols),
                "dead_symbols_sample": [s.name for s in dead_symbols[:20]],
                "security_findings": findings,
                "large_files": large_files[:20],
                "avg_chunk_tokens": avg_tokens,
                "code_quality_score": score,
            }

            analysis = Analysis(
                repository_id=self.repository_id,
                analysis_type="repository_health",
                status="completed",
                summary=f"Repository analysis completed: score={score}",
                result=result,
                findings_count=len(findings),
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )

            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)

            return analysis
