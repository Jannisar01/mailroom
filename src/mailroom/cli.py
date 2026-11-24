"""The command line. Only this module prints, reads the environment, or reads today's date."""

import argparse
import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, cast

import httpx

from mailroom.dates import next_send, window_start
from mailroom.errors import MailroomError
from mailroom.guard import check_tool_call
from mailroom.plan import build_plan
from mailroom.rules import check_issue
from mailroom.sender import DEFAULT_KEY, DEFAULT_URL, get_email, send_plan
from mailroom.signups import import_signups
from mailroom.subscribers import count_by_group, joined_between, load_subscribers

DEFAULT_SUBSCRIBERS = Path("data/subscribers.csv")


def _server() -> tuple[str, str]:
    return os.environ.get("RESEND_API_URL", DEFAULT_URL), os.environ.get("RESEND_API_KEY", DEFAULT_KEY)


def cmd_subscribers(args: argparse.Namespace) -> int:
    subs = load_subscribers(args.subscribers)
    print(f"Total: {len(subs)}")
    for group, count in count_by_group(subs).items():
        print(f"  {group}: {count}")
    print(f"Gave consent: {sum(s.consent for s in subs)}")
    start: date | None = args.since or (window_start(args.run_date, args.since_days) if args.since_days is not None else None)
    if start is not None:
        print(f"Joined from {start} to {args.run_date}: {len(joined_between(subs, start, args.run_date))}")
    return 0


def cmd_next_send(args: argparse.Namespace) -> int:
    print(next_send(args.run_date))
    return 0


def cmd_check_issue(args: argparse.Namespace) -> int:
    problems = check_issue(args.issue.read_text(encoding="utf-8"))
    for p in problems:
        print(f"- {p}")
    if not problems:
        print(f"{args.issue} passes all 5 rules")
    return 1 if problems else 0


def cmd_import_signups(args: argparse.Namespace) -> int:
    good, bad = import_signups(args.signups)
    print(f"{len(good)} good rows, {len(bad)} bad rows")
    for b in bad:
        print(f"  row {b.row}: {b.reason}")
    return 1 if bad else 0


def cmd_send(args: argparse.Namespace) -> int:
    issue_text = args.issue.read_text(encoding="utf-8")
    problems = check_issue(issue_text)
    if problems:
        print(f"{args.issue} breaks {len(problems)} rule(s), not sending. Run check-issue to see them.", file=sys.stderr)
        return 1
    plan = build_plan(load_subscribers(args.subscribers), issue_text, args.issue_id or args.issue.stem)
    if args.dry_run:
        args.out.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {len(plan['messages'])} messages to {args.out}. Nothing was sent.")
        return 0
    url, key = _server()
    results = asyncio.run(
        send_plan(plan, url, key, concurrency=args.concurrency, log=lambda line: print(line, file=sys.stderr))
    )
    failed = [r for r in results if "error" in r]
    for r in results:
        print(f"{r['to']}: {r.get('id') or 'FAILED ' + r['error']}")
    print(f"Sent {len(results) - len(failed)}, failed {len(failed)}")
    return 1 if failed else 0


def cmd_status(args: argparse.Namespace) -> int:
    url, key = _server()

    async def run() -> dict[str, object]:
        async with httpx.AsyncClient(timeout=10) as client:
            return await get_email(client, url, key, args.id)

    print(json.dumps(asyncio.run(run()), indent=2))
    return 0


def cmd_guard(args: argparse.Namespace) -> int:
    """Called by a Claude Code hook. Exit 2 blocks the tool call and shows Claude the reason."""
    try:
        call = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as e:
        print(f"mailroom guard: the hook input is not JSON ({e})", file=sys.stderr)
        return 2
    problems = check_tool_call(cast(dict[str, Any], call)) if isinstance(call, dict) else []
    for p in problems:
        print(f"mailroom guard refused: {p}", file=sys.stderr)
    return 2 if problems else 0


def build_parser(today: date) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mailroom", description="Count, check and send the Steep Club newsletter.")
    sub = parser.add_subparsers(dest="command", required=True)

    def with_subscribers(p: argparse.ArgumentParser) -> None:
        p.add_argument("--subscribers", type=Path, default=DEFAULT_SUBSCRIBERS, help="subscribers CSV file")

    p = sub.add_parser("subscribers", help="count subscribers, overall and by group")
    with_subscribers(p)
    since = p.add_mutually_exclusive_group()
    since.add_argument("--since-days", type=int, help="also count who joined in the last N days")
    since.add_argument("--since", type=date.fromisoformat, help="also count who joined on or after this date")
    p.add_argument("--run-date", type=date.fromisoformat, default=today)
    p.set_defaults(func=cmd_subscribers)

    p = sub.add_parser("next-send", help="the first Monday of next month")
    p.add_argument("--run-date", type=date.fromisoformat, default=today)
    p.set_defaults(func=cmd_next_send)

    p = sub.add_parser("check-issue", help="check an issue against docs/email-rules.md")
    p.add_argument("issue", type=Path)
    p.set_defaults(func=cmd_check_issue)

    p = sub.add_parser("import-signups", help="check new sign-ups and report every bad row")
    p.add_argument("signups", type=Path)
    p.set_defaults(func=cmd_import_signups)

    p = sub.add_parser("send", help="send an issue to the practice mail server")
    with_subscribers(p)
    p.add_argument("issue", type=Path)
    p.add_argument("--issue-id", help="used in idempotency keys (default: the file name)")
    p.add_argument("--dry-run", action="store_true", help="write the plan as JSON and send nothing")
    p.add_argument("--out", type=Path, default=Path("send-plan.json"))
    p.add_argument("--concurrency", type=int, default=5)
    p.set_defaults(func=cmd_send)

    p = sub.add_parser("status", help="look up a sent email by id")
    p.add_argument("id")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("guard", help="check a Claude Code hook's tool call from standard input")
    p.set_defaults(func=cmd_guard)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser(date.today()).parse_args(argv)
    try:
        return args.func(args)
    except MailroomError as e:
        print(f"mailroom: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"mailroom: {e.filename} does not exist", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
