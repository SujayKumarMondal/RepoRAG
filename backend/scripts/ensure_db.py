"""
Utility script to ensure the database is ready for RepoRAG.
This will run the SQLAlchemy `Base.metadata.create_all` via the async engine
and create the `vector` extension if needed.

Usage:
    (venv) > python scripts/ensure_db.py

Note: The environment variable `DATABASE_URL` must be set (see app/core/config.py).
"""

import asyncio
import sys

from app.core.database import ensure_database_ready, check_database_connection


async def main() -> int:
    try:
        await check_database_connection()
    except Exception as exc:
        print("ERROR: Unable to reach database:", exc)
        return 1

    try:
        await ensure_database_ready()
        print("OK: Database tables and extensions are verified/created.")
        return 0

    except Exception as exc:
        print("ERROR: Failed to ensure database readiness:", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
