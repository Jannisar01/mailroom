from typing import Any

from mailroom.recipients import recipient_problem

SEND_TOOLS = ("send-email", "send-batch-emails")


def _addresses(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
    return []


def check_tool_call(call: dict[str, Any]) -> list[str]:
    """Problems with a Claude Code hook's tool call. Tools that do not send mail always pass."""
    name = str(call.get("tool_name", "")).replace("_", "-")
    if not name.endswith(SEND_TOOLS):
        return []
    tool_input: Any = call.get("tool_input") or {}
    emails: Any = tool_input.get("emails", []) if name.endswith("send-batch-emails") else [tool_input]
    problems: list[str] = []
    for email in emails:
        for field in ("to", "cc", "bcc"):
            for address in _addresses(email.get(field)):
                problem = recipient_problem(address)
                if problem:
                    problems.append(f"{field}: {problem}")
    return problems
