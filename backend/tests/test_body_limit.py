import json
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from app.body_limit import RequestBodyLimitMiddleware


@pytest.mark.anyio
async def test_chunked_body_without_content_length_is_rejected() -> None:
    downstream_called = False
    messages = [
        {"type": "http.request", "body": b"1234", "more_body": True},
        {"type": "http.request", "body": b"56789", "more_body": False},
    ]
    sent: list[dict[str, Any]] = []

    async def downstream(
        _scope: dict[str, Any],
        _receive: Callable[[], Awaitable[dict[str, Any]]],
        _send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        nonlocal downstream_called
        downstream_called = True

    async def receive() -> dict[str, Any]:
        return messages.pop(0)

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    middleware = RequestBodyLimitMiddleware(downstream, max_body_bytes=8)
    await middleware(
        {
            "type": "http",
            "headers": [],
            "state": {},
        },
        receive,
        send,
    )

    assert downstream_called is False
    assert sent[0]["status"] == 413
    payload = json.loads(sent[1]["body"])
    assert payload["error"]["code"] == "REQUEST_TOO_LARGE"


@pytest.mark.anyio
async def test_allowed_body_is_replayed_exactly_once() -> None:
    messages = [
        {"type": "http.request", "body": b'{"log_', "more_body": True},
        {"type": "http.request", "body": b'text":"x"}', "more_body": False},
    ]
    downstream_bodies: list[bytes] = []

    async def downstream(
        _scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        _send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        message = await receive()
        downstream_bodies.append(message["body"])

    async def receive() -> dict[str, Any]:
        return messages.pop(0)

    async def send(_message: dict[str, Any]) -> None:
        return None

    middleware = RequestBodyLimitMiddleware(downstream, max_body_bytes=32)
    await middleware(
        {
            "type": "http",
            "headers": [],
            "state": {},
        },
        receive,
        send,
    )

    assert downstream_bodies == [b'{"log_text":"x"}']
