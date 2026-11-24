from typing import Any

from mailroom.rules import parse_issue
from mailroom.subscribers import Subscriber

SENDER = "Kettlebird Tea <onboarding@resend.dev>"
UNSUBSCRIBE_URL = "https://kettlebird.example.com/unsubscribe"


def build_plan(subscribers: list[Subscriber], issue_text: str, issue_id: str) -> dict[str, Any]:
    """One message per subscriber who gave consent. Nothing is sent here."""
    issue = parse_issue(issue_text)
    messages = [
        {
            "to": s.email,
            "idempotency_key": f"{issue_id}-{s.email}",
            "text": issue.body.replace("{{first_name}}", s.first_name).replace(
                "{{unsubscribe_url}}", UNSUBSCRIBE_URL
            ),
        }
        for s in subscribers
        if s.consent
    ]
    return {"issue": issue_id, "from": SENDER, "subject": issue.subject, "messages": messages}
