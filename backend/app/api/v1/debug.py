"""
Debug endpoints for verifying Redis connectivity and writes.
"""

import json
from fastapi import APIRouter

from app.core.redis import get_redis

router = APIRouter()


@router.post("/redis/test")
async def redis_test():
    """Write a test key and an entry to a stream, then read back the key."""
    r = get_redis()

    # Simple set/get
    await r.set("reporag:debug:test_key", "alive")
    val = await r.get("reporag:debug:test_key")

    # Add a message to a stream
    stream_id = await r.xadd("reporag:debug:stream", {"payload": json.dumps({"status": "ok"})})

    return {"key_value": val, "stream_id": stream_id}
