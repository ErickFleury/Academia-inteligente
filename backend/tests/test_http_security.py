import asyncio

import pytest

from app.http_security import MAX_IMAGE_BYTES, HttpSecurityMiddleware


def exercise(path, chunks, headers=(), method="PUT"):
    sent, reads, received = [], [], []
    messages = iter(chunks)

    async def receive():
        reads.append(True)
        return next(messages)

    async def send(message):
        sent.append(message)

    async def app(scope, receive, send):
        received.append(await receive())
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    asyncio.run(
        HttpSecurityMiddleware(app)(
            {"type": "http", "method": method, "path": path, "headers": headers}, receive, send
        )
    )
    return sent, reads, received


@pytest.mark.parametrize(
    "path,method",
    [
        ("/social-profiles/me/image", "PUT"),
        ("/social-profiles/comments/id/image", "PUT"),
        ("/progress/post/images/0", "PUT"),
        ("/progress/image-only", "POST"),
        ("/equipment/admin/models/id/image", "PUT"),
    ],
)
def test_oversized_declared_upload_is_rejected_before_body_or_framework(path, method):
    sent, reads, received = exercise(
        path, [], [(b"content-length", str(MAX_IMAGE_BYTES + 1).encode())], method
    )
    assert sent[0]["status"] == 413
    assert not reads and not received


def test_chunked_upload_is_bounded_without_trusting_content_length():
    sent, reads, received = exercise(
        "/social-profiles/me/image",
        [
            {"type": "http.request", "body": b"a" * (2 * 1024 * 1024), "more_body": True},
            {"type": "http.request", "body": b"a" * (2 * 1024 * 1024), "more_body": True},
            {"type": "http.request", "body": b"a" * (2 * 1024 * 1024), "more_body": True},
        ],
        [(b"content-length", b"1")],
    )
    assert sent[0]["status"] == 413 and len(reads) == 3 and not received


def test_valid_upload_is_preserved_and_response_cannot_be_cached():
    sent, _, received = exercise(
        "/progress/post/images/0",
        [
            {"type": "http.request", "body": b"first", "more_body": True},
            {"type": "http.request", "body": b"second", "more_body": False},
        ],
    )
    assert received[0]["body"] == b"firstsecond"
    assert dict(sent[0]["headers"])[b"cache-control"] == b"no-store"
    assert dict(sent[0]["headers"])[b"x-content-type-options"] == b"nosniff"


def test_reference_upload_accepts_150_mib_intact():
    body = b"a" * (150 * 1024 * 1024)
    sent, _, received = exercise(
        "/ai/references",
        [{"type": "http.request", "body": body, "more_body": False}],
        [(b"content-length", str(len(body)).encode())],
        "POST",
    )
    assert sent[0]["status"] == 200
    assert received[0]["body"] == body


@pytest.mark.parametrize("declared", [False, True])
def test_reference_upload_rejects_one_byte_over_150_mib(declared):
    limit = 150 * 1024 * 1024
    sent, reads, received = exercise(
        "/ai/references",
        []
        if declared
        else [
            {"type": "http.request", "body": b"a" * limit, "more_body": True},
            {"type": "http.request", "body": b"b", "more_body": False},
        ],
        [(b"content-length", str(limit + 1).encode())] if declared else [],
        "POST",
    )
    assert sent[0]["status"] == 413
    assert sent[1]["body"] == b'{"detail":"document_size"}'
    assert not received
    if declared:
        assert not reads
