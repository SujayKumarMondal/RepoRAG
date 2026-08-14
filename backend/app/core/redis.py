"""
RepoRAG Redis configuration.
"""

from typing import Optional

import redis.asyncio as redis

from app.core.config import settings


# ============================================================
# Redis Client
# ============================================================

redis_client: Optional[redis.Redis] = None


# ============================================================
# Initialize Redis
# ============================================================

async def init_redis() -> redis.Redis:
    """
    Create and initialize the Redis client.
    """

    global redis_client

    if redis_client is None:

        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

    # Verify connection
    try:
        await redis_client.ping()
    except Exception as exc:
        # Some Redis-compatible services (or older servers) don't support
        # the HELLO handshake used to negotiate RESP3. The client will
        # raise an "unknown command 'HELLO'" ResponseError in that case.
        msg = str(exc).lower()
        if "unknown command" in msg and "hello" in msg:
            # Recreate client forcing RESP2/protocol=2 and retry ping
            redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                protocol=2,
            )
            await redis_client.ping()
        else:
            raise

    return redis_client


# ============================================================
# Get Redis
# ============================================================

def get_redis() -> redis.Redis:
    """
    Return the initialized Redis client.

    Raises an error if Redis has not been initialized.
    """

    if redis_client is None:
        raise RuntimeError(
            "Redis has not been initialized. "
            "Call init_redis() during application startup."
        )

    return redis_client


# ============================================================
# Close Redis
# ============================================================

async def close_redis() -> None:
    """
    Close the Redis connection.
    """

    global redis_client

    if redis_client is not None:
        await redis_client.close()
        redis_client = None