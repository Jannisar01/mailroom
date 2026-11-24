import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pytest

from mailroom.errors import SendError
from mailroom.plan import build_plan
from mailroom.sender import NOT_RUNNING, get_email, post_email, send_plan
from mailroom.subscribers import Subscriber, load_subscribers

ROOT = Path(__file__).parent.parent
ISSUE = (ROOT / "issues" / "issue-01.md").read_text(encoding="utf-8")
URL = "http://localhost:4000"
PAYLOAD: dict[str, Any] = {"from": "a@resend.dev", "to": ["b@example.com"], "subject": "s", "text": "t"}


async def no_sleep(_: float) -> None:
    pass


def client_answering(*statuses: int, seen: list[httpx.Request] | None = None) -> httpx.AsyncClient:
    answers = iter(statuses)

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        status = next(answers)
        return httpx.Response(status, json={"id": "em_1"} if status < 400 else {"message": f"server said {status}"})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def post(client: httpx.AsyncClient) -> dict[str, Any]:
    return asyncio.run(post_email(client, URL, "re_practice", PAYLOAD, "issue-01-b@example.com", no_sleep))


def test_plan_has_one_message_per_consenting_subscriber() -> None:
    plan = build_plan(load_subscribers(ROOT / "data" / "subscribers.csv"), ISSUE, "issue-01")
    assert len(plan["messages"]) == 20
    assert plan["subject"] == "The Steep Club opens Monday"
    json.dumps(plan)  # must be plain JSON


def test_plan_fills_the_placeholders() -> None:
    ada = Subscriber("Ada Park", "ada.park@example.com", "green", date(2026, 1, 1), True)
    text = build_plan([ada], ISSUE, "issue-01")["messages"][0]["text"]
    assert text.startswith("Hi Ada,")
    assert "{{" not in text


def test_idempotency_key_is_issue_plus_recipient() -> None:
    ada = Subscriber("Ada Park", "ada.park@example.com", "green", date(2026, 1, 1), True)
    assert build_plan([ada], ISSUE, "issue-01")["messages"][0]["idempotency_key"] == "issue-01-ada.park@example.com"


def test_request_carries_bearer_key_and_idempotency_key() -> None:
    seen: list[httpx.Request] = []
    post(client_answering(200, seen=seen))
    assert seen[0].method == "POST" and str(seen[0].url) == f"{URL}/emails"
    assert seen[0].headers["Authorization"] == "Bearer re_practice"
    assert seen[0].headers["Idempotency-Key"] == "issue-01-b@example.com"


def test_retries_a_503_then_succeeds() -> None:
    seen: list[httpx.Request] = []
    assert post(client_answering(503, 429, 200, seen=seen))["id"] == "em_1"
    assert len(seen) == 3


def test_gives_up_after_three_tries() -> None:
    with pytest.raises(SendError, match="gave up after 3 tries"):
        post(client_answering(500, 500, 500))


@pytest.mark.parametrize("status", [400, 401, 403, 422])
def test_never_retries_a_4xx_and_shows_the_server_message(status: int) -> None:
    seen: list[httpx.Request] = []
    with pytest.raises(SendError, match=f"server said {status}"):
        post(client_answering(status, seen=seen))
    assert len(seen) == 1


def test_no_connection_says_how_to_start_the_server() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(SendError, match="npx emulate"):
        post(httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    assert "not running" in NOT_RUNNING


def test_unknown_id_is_a_plain_404_message() -> None:
    with pytest.raises(SendError, match="no email with id em_x"):
        asyncio.run(get_email(client_answering(404), URL, "re_practice", "em_x"))


def test_refuses_a_server_that_is_not_localhost() -> None:
    with pytest.raises(SendError, match="localhost"):
        asyncio.run(send_plan({"messages": []}, "https://api.resend.com", "k"))


def test_refuses_the_whole_plan_if_one_recipient_is_not_practice() -> None:
    plan = {"from": "a@resend.dev", "subject": "s", "messages": [
        {"to": "a@example.com", "idempotency_key": "k1", "text": "t"},
        {"to": "sara.ali@gmail.com", "idempotency_key": "k2", "text": "t"},
    ]}
    seen: list[httpx.Request] = []
    with pytest.raises(SendError, match="sara.ali@gmail.com"):
        asyncio.run(send_plan(plan, URL, "k", client=client_answering(200, 200, seen=seen)))
    assert seen == []


def test_never_more_than_the_concurrency_limit_at_once() -> None:
    in_flight = 0
    most = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal in_flight, most
        in_flight += 1
        most = max(most, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return httpx.Response(200, json={"id": "em"})

    plan = build_plan(load_subscribers(ROOT / "data" / "subscribers.csv"), ISSUE, "issue-01")
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    results = asyncio.run(send_plan(plan, URL, "k", concurrency=3, client=client))
    assert len(results) == 20 and all("id" in r for r in results)
    assert most == 3


def test_zero_concurrency_is_refused_instead_of_hanging() -> None:
    with pytest.raises(SendError, match="concurrency must be 1 or more"):
        asyncio.run(send_plan({"messages": []}, URL, "k", concurrency=0))
