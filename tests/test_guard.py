import json
import subprocess
import sys
from typing import Any

import pytest

from mailroom.guard import check_tool_call
from mailroom.recipients import recipient_problem


@pytest.mark.parametrize("address", ["delivered@resend.dev", "ada.park@example.com", "Ada <ada.park@example.com>"])
def test_practice_addresses_pass(address: str) -> None:
    assert recipient_problem(address) is None


@pytest.mark.parametrize("address", ["sara.ali@gmail.com", "x@example.com.evil.io", "not-an-address", "a b@example.com"])
def test_other_addresses_fail(address: str) -> None:
    assert recipient_problem(address) is not None


def test_send_email_to_a_real_address_is_refused() -> None:
    call = {"tool_name": "mcp__resend__send-email", "tool_input": {"to": "sara.ali@gmail.com"}}
    assert "sara.ali@gmail.com" in check_tool_call(call)[0]


def test_cc_and_bcc_are_checked_too() -> None:
    call = {"tool_name": "send-email", "tool_input": {"to": ["a@example.com"], "cc": "b@gmail.com", "bcc": ["c@yahoo.com"]}}
    assert len(check_tool_call(call)) == 2


def test_batch_checks_every_email() -> None:
    call = {
        "tool_name": "mcp__resend__send_batch_emails",
        "tool_input": {"emails": [{"to": "a@example.com"}, {"to": "z@gmail.com"}]},
    }
    assert len(check_tool_call(call)) == 1


def test_practice_send_passes() -> None:
    assert check_tool_call({"tool_name": "send-email", "tool_input": {"to": "delivered@resend.dev"}}) == []


def test_other_tools_pass() -> None:
    assert check_tool_call({"tool_name": "Bash", "tool_input": {"command": "echo sara.ali@gmail.com"}}) == []


def run_guard(call: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "mailroom.cli", "guard"], input=json.dumps(call), capture_output=True, text=True
    )


def test_guard_command_exits_2_with_a_reason() -> None:
    result = run_guard({"tool_name": "send-email", "tool_input": {"to": "sara.ali@gmail.com"}})
    assert result.returncode == 2
    assert "sara.ali@gmail.com" in result.stderr


def test_guard_command_exits_0_for_practice_mail_and_other_tools() -> None:
    assert run_guard({"tool_name": "send-email", "tool_input": {"to": "delivered@resend.dev"}}).returncode == 0
    assert run_guard({"tool_name": "Read", "tool_input": {"file_path": "x"}}).returncode == 0
