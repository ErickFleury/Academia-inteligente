import asyncio

from app.main import create_app


def test_api_accepts_frontend_cors_preflight() -> None:
    sent: list[dict[str, object]] = []
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "OPTIONS",
        "scheme": "http",
        "path": "/social-profiles/me/image",
        "raw_path": b"/social-profiles/me/image",
        "query_string": b"",
        "headers": [
            (b"origin", b"http://localhost:5173"),
            (b"access-control-request-method", b"PUT"),
            (b"access-control-request-headers", b"authorization,content-type"),
        ],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    asyncio.run(create_app()(scope, receive, send))

    response = next(message for message in sent if message["type"] == "http.response.start")
    headers = dict(response["headers"])
    assert response["status"] == 200
    assert headers[b"access-control-allow-origin"] == b"http://localhost:5173"
    assert b"authorization" in headers[b"access-control-allow-headers"].lower()
    assert b"PUT" in headers[b"access-control-allow-methods"]
