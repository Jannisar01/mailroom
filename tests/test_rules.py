from pathlib import Path

import pytest

from mailroom.rules import (
    check_footer,
    check_greeting,
    check_issue,
    check_links,
    check_preview,
    check_subject,
)

ISSUE = (Path(__file__).parent.parent / "issues" / "issue-01.md").read_text(encoding="utf-8")
BODY = "Hi {{first_name}},\n\nRead it: https://kettlebird.example.com/a\n\nUnsubscribe: {{unsubscribe_url}}"


def issue(subject: str | None = "Hello", preview: str | None = "A short preview", body: str = BODY) -> str:
    head = ""
    if subject is not None:
        head += f"Subject: {subject}\n"
    if preview is not None:
        head += f"Preview: {preview}\n"
    return f"{head}\n{body}\n"


def test_issue_01_follows_every_rule() -> None:
    assert check_issue(ISSUE) == []


# Subject cases and answers are fixed in notes/predictions.md. Never change them to make a test pass.
@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        ("The Steep Club opens Monday", []),
        ("Your Steep Club box ships on Monday with new teas.", []),
        ("Your Steep Club box ships on Monday with fresh teas", ["too long"]),
        ("", ["empty"]),
        ("   ", ["empty"]),
        (None, ["missing"]),
    ],
)
def test_subject(subject: str | None, expected: list[str]) -> None:
    problems = check_subject(issue(subject=subject))
    assert len(problems) == len(expected)
    for p, word in zip(problems, expected):
        assert word in p


def test_preview_of_90_is_fine_and_91_is_too_long() -> None:
    assert check_preview(issue(preview="x" * 90)) == []
    assert "too long" in check_preview(issue(preview="x" * 91))[0]


def test_preview_missing() -> None:
    assert "missing" in check_preview(issue(preview=None))[0]


def test_greeting_needs_the_placeholder() -> None:
    assert check_greeting(issue(body=BODY.replace("{{first_name}}", "friend"))) != []


def test_exactly_one_link() -> None:
    assert check_links(issue()) == []
    assert "0 links" in check_links(issue(body=BODY.replace("https://kettlebird.example.com/a", "our site")))[0]
    two = BODY.replace("Read it:", "See https://kettlebird.example.com/b and")
    assert "2 links" in check_links(issue(body=two))[0]


def test_link_must_be_https() -> None:
    assert "https://" in check_links(issue(body=BODY.replace("https://", "http://")))[0]


def test_footer_must_be_the_last_line() -> None:
    assert check_footer(issue(body=BODY + "\nP.S. thanks")) != []
    assert check_footer(issue(body="Hi {{first_name}}")) != []


def test_a_broken_issue_reports_every_rule() -> None:
    assert len(check_issue("no headers at all")) == 5
