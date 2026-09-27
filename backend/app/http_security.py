"""Bound binary uploads before framework buffering and disable sensitive API caching."""

import re

from starlette.responses import JSONResponse

MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_UPLOAD = re.compile(
    r"^(?:/progress/image-only|/progress/[^/]+/images/[^/]+|"
    r"/social-profiles/me/image|/social-profiles/comments/[^/]+/image)/?$"
)


class HttpSecurityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def secure_send(message):
            if message["type"] == "http.response.start":
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() not in {b"cache-control", b"x-content-type-options"}
                ]
                message = dict(
                    message,
                    headers=headers
                    + [
                        (b"cache-control", b"no-store"),
                        (b"x-content-type-options", b"nosniff"),
                    ],
                )
            await send(message)

        if scope["method"] in {"POST", "PUT"} and IMAGE_UPLOAD.fullmatch(scope["path"]):
            headers = dict(scope.get("headers", []))
            try:
                declared = int(headers.get(b"content-length", b"0"))
                if declared < 0:
                    raise ValueError
            except ValueError:
                return await JSONResponse({"detail": "Invalid content length"}, 400)(
                    scope, receive, secure_send
                )
            if declared > MAX_IMAGE_BYTES:
                return await JSONResponse({"detail": "Image size is invalid"}, 413)(
                    scope, receive, secure_send
                )
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                if len(body) + len(chunk) > MAX_IMAGE_BYTES:
                    return await JSONResponse({"detail": "Image size is invalid"}, 413)(
                        scope, receive, secure_send
                    )
                body.extend(chunk)
                if not message.get("more_body", False):
                    break
            original_receive = receive
            delivered = False

            async def bounded_receive():
                nonlocal delivered
                if delivered:
                    return await original_receive()
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}

            receive = bounded_receive
        await self.app(scope, receive, secure_send)
