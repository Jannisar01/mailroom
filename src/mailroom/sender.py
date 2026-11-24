import asyncio
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

import httpx

from mailroom.errors import SendError
from mailroom.recipients import recipient_problem

DEFAULT_URL = "http://localhost:4000"
DEFAULT_KEY = "re_practice"
TRIES = 3
NOT_RUNNING = (
    "the practice server is not running. Start it with: npx emulate@0.12.3 start --service resend"
)

Sleep = Callable[[float], Awaitable[None]]
Log = Callable[[str], None]


def _no_log(_: str) -> None:
    pass


def check_practice_server(url: str) -> None:
    """Guard one: Mailroom only ever talks to a server on this computer."""
    if urlparse(url).hostname not in ("localhost", "127.0.0.1", "::1"):
        raise SendError(f"refusing to send to {url}: only the practice server on localhost is allowed")


def _server_message(response: httpx.Response) -> str:
    try:
        body: Any = response.json()
    except ValueError:
        return response.text or response.reason_phrase
    if isinstance(body, dict) and "message" in body:
        return str(body["message"])  # pyright: ignore[reportUnknownArgumentType]
    return response.text


def _retryable(status: int) -> bool:
    return status == 429 or status >= 500


async def post_email(
    client: httpx.AsyncClient,
    url: str,
    key: str,
    payload: dict[str, Any],
    idempotency_key: str,
    sleep: Sleep = asyncio.sleep,
    log: Log = _no_log,
) -> dict[str, Any]:
    """POST /emails. Retries only what can succeed later: no connection, a timeout, a 429 or a 5xx."""
    headers = {"Authorization": f"Bearer {key}", "Idempotency-Key": idempotency_key}
    for attempt in range(1, TRIES + 1):
        try:
            response = await client.post(f"{url}/emails", json=payload, headers=headers)
        except httpx.ConnectError:
            problem = NOT_RUNNING
        except httpx.TimeoutException:
            problem = "the practice server timed out"
        else:
            if response.status_code < 400:
                return response.json()
            if not _retryable(response.status_code):
                raise SendError(f"{response.status_code}: {_server_message(response)}")
            problem = f"{response.status_code}: {_server_message(response)}"
        if attempt == TRIES:
            raise SendError(f"gave up after {TRIES} tries: {problem}")
        wait = 0.5 * 2 ** (attempt - 1)
        log(f"try {attempt} failed ({problem}), waiting {wait}s")
        await sleep(wait)
    raise AssertionError("unreachable")


async def get_email(client: httpx.AsyncClient, url: str, key: str, email_id: str) -> dict[str, Any]:
    try:
        response = await client.get(f"{url}/emails/{email_id}", headers={"Authorization": f"Bearer {key}"})
    except httpx.ConnectError:
        raise SendError(NOT_RUNNING) from None
    if response.status_code == 404:
        raise SendError(f"no email with id {email_id}")
    if response.status_code >= 400:
        raise SendError(f"{response.status_code}: {_server_message(response)}")
    return response.json()


async def send_plan(
    plan: dict[str, Any],
    url: str,
    key: str,
    concurrency: int = 5,
    client: httpx.AsyncClient | None = None,
    sleep: Sleep = asyncio.sleep,
    log: Log = _no_log,
) -> list[dict[str, str]]:
    """Send every message in the plan, at most `concurrency` at a time. One failure does not stop the rest."""
    check_practice_server(url)
    if concurrency < 1:
        raise SendError(f"concurrency must be 1 or more, got {concurrency}")
    messages: list[dict[str, str]] = plan["messages"]
    for m in messages:  # guard two: check every recipient before sending any
        problem = recipient_problem(m["to"])
        if problem:
            raise SendError(problem)

    limit = asyncio.Semaphore(concurrency)
    http = client or httpx.AsyncClient(timeout=10)

    async def one(m: dict[str, str]) -> dict[str, str]:
        payload = {"from": plan["from"], "to": [m["to"]], "subject": plan["subject"], "text": m["text"]}
        async with limit:
            try:
                sent = await post_email(http, url, key, payload, m["idempotency_key"], sleep, log)
                return {"to": m["to"], "id": str(sent.get("id", ""))}
            except SendError as e:
                return {"to": m["to"], "error": str(e)}

    try:
        return list(await asyncio.gather(*(one(m) for m in messages)))
    finally:
        if client is None:
            await http.aclose()
