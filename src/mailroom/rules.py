import re
from dataclasses import dataclass

# Limits come from docs/email-rules.md. len() counts code points, so an emoji may count as more than one.
SUBJECT_MAX = 50
PREVIEW_MAX = 90
GREETING = "{{first_name}}"
FOOTER = "Unsubscribe: {{unsubscribe_url}}"
LINK = re.compile(r"\b[a-z][a-z0-9+.-]*://\S+", re.IGNORECASE)


@dataclass(frozen=True)
class Issue:
    subject: str | None
    preview: str | None
    body: str


def parse_issue(text: str) -> Issue:
    """Header lines ("Key: value") come first, then a blank line, then the body."""
    headers: dict[str, str] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines) and lines[i].strip():
        key, sep, value = lines[i].partition(":")
        if not sep:
            break
        headers[key.strip().lower()] = value.strip()
        i += 1
    return Issue(headers.get("subject"), headers.get("preview"), "\n".join(lines[i:]).strip())


def _check_line(name: str, value: str | None, limit: int) -> list[str]:
    if value is None:
        return [f"{name} is missing"]
    if not value.strip():
        return [f"{name} is empty"]
    if len(value) > limit:
        return [f"{name} is too long: {len(value)} characters, the limit is {limit}"]
    return []


def check_subject(issue_text: str) -> list[str]:
    return _check_line("subject", parse_issue(issue_text).subject, SUBJECT_MAX)


def check_preview(issue_text: str) -> list[str]:
    return _check_line("preview", parse_issue(issue_text).preview, PREVIEW_MAX)


def check_greeting(issue_text: str) -> list[str]:
    if GREETING not in parse_issue(issue_text).body:
        return [f"greeting is missing the {GREETING} placeholder"]
    return []


def check_links(issue_text: str) -> list[str]:
    links = LINK.findall(parse_issue(issue_text).body)
    if len(links) != 1:
        return [f"body has {len(links)} links, it needs exactly one"]
    if not links[0].lower().startswith("https://"):
        return [f"link {links[0]} must start with https://"]
    return []


def check_footer(issue_text: str) -> list[str]:
    body = parse_issue(issue_text).body
    last = body.splitlines()[-1].strip() if body else ""
    if last != FOOTER:
        return [f"the last line must be {FOOTER!r}"]
    return []


def check_issue(issue_text: str) -> list[str]:
    return [
        *check_subject(issue_text),
        *check_preview(issue_text),
        *check_greeting(issue_text),
        *check_links(issue_text),
        *check_footer(issue_text),
    ]
