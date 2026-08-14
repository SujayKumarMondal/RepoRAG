"""Middleware to publish every HTTP response to a Redis stream.

This middleware reads the response body, publishes a small record to
`reporag:endpoint:responses`, and returns the original response to the client.
"""
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.redis import get_redis


class RedisResponseStreamMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Call the next handler to get a response
        response = await call_next(request)

        try:
            # Read body safely. Many Response implementations expose
            # an async body iterator; if present we must consume it and
            # re-create the Response so the client still receives it.
            body_bytes = b""

            if getattr(response, "body_iterator", None) is not None:
                chunks = []
                async for chunk in response.body_iterator:
                    chunks.append(chunk)
                body_bytes = b"".join(chunks)

                new_response = Response(
                    content=body_bytes,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

                publish_resp = new_response
            else:
                # Some Response types already have the body available
                body_bytes = response.body if response.body is not None else b""
                publish_resp = response

            # Publish to Redis stream (non-blocking best-effort)
            try:
                r = get_redis()
                await r.xadd(
                    "reporag:endpoint:responses",
                    {
                        "path": str(request.url.path),
                        "method": request.method,
                        "status": str(publish_resp.status_code),
                        "response": body_bytes.decode("utf-8", errors="replace"),
                    },
                )
            except Exception:
                # Don't let Redis failures break the request path
                pass

            # Return the recreated response when we consumed the iterator,
            # otherwise return the original response.
            if publish_resp is not response:
                return publish_resp

        except Exception:
            # Swallow any middleware errors to avoid affecting normal responses
            pass

        return response
