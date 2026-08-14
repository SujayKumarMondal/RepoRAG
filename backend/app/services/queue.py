"""
Simple Redis-backed job queue for ingestion jobs.

This provides enqueueing, cancelling, and storing job metadata.
"""
import json
import uuid
from typing import Any

from app.core.redis import get_redis


JOB_QUEUE_KEY = "reporag:job_queue"
JOB_META_KEY_FMT = "reporag:job:{job_id}:meta"


async def enqueue_job(job_id: str, metadata: dict[str, Any]) -> None:
    r = get_redis()
    # store metadata for the worker
    await r.set(JOB_META_KEY_FMT.format(job_id=job_id), json.dumps(metadata))
    # push to queue (right push so worker can BRPOP)
    await r.lpush(JOB_QUEUE_KEY, job_id)


async def dequeue_job(timeout: int = 5) -> tuple[str | None, dict[str, Any] | None]:
    r = get_redis()
    res = await r.brpop(JOB_QUEUE_KEY, timeout=timeout)
    if not res:
        return None, None
    # res is (key, job_id)
    job_id = res[1]
    meta_raw = await r.get(JOB_META_KEY_FMT.format(job_id=job_id))
    meta = json.loads(meta_raw) if meta_raw else None
    return job_id, meta


async def get_job_meta(job_id: str) -> dict[str, Any] | None:
    r = get_redis()
    raw = await r.get(JOB_META_KEY_FMT.format(job_id=job_id))
    if not raw:
        return None
    return json.loads(raw)


async def set_job_meta(job_id: str, meta: dict[str, Any]) -> None:
    r = get_redis()
    await r.set(JOB_META_KEY_FMT.format(job_id=job_id), json.dumps(meta))


async def delete_job_meta(job_id: str) -> None:
    r = get_redis()
    await r.delete(JOB_META_KEY_FMT.format(job_id=job_id))
