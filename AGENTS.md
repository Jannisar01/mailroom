# Mailroom

Mailroom is a command-line tool for one newsletter: Kettlebird Tea's Steep Club. It reads the subscribers, checks an issue, and sends it to a practice mail server.

## Rules

- Use uv for everything: `uv run mailroom ...`, `uv run pytest`, `uv run pyright`.
- Never use a real person's email address. Use @example.com, and @resend.dev for practice sends.
- Behaviors first: the expected answers are written as tests, shown failing, then the code is written.
- I decide the test cases and their answers. Never change an expected answer to make a test pass. If one looks wrong, stop and say so.
- Never read today's date inside the logic. Only `cli.py` reads it; everything else takes a run date.
- When something breaks, show the full error before changing anything.
- One module per job in `src/mailroom/`. Only `cli.py` prints, reads the environment, or reads today's date.
- Errors the user can fix raise `MailroomError` (or a subclass) with one plain sentence. The command line turns them into exit code 1.
- Every function has type hints. `uv run pyright` (strict) must report 0 errors.
- Retry only what can succeed later: no connection, a timeout, a 429 or a 5xx, at most 3 tries with growing waits. Never retry a 4xx.
- Every send has an idempotency key made from the issue and the recipient.
- Two guards in code: send only to a server on localhost, and only to @example.com or @resend.dev. The recipient rule lives in one place: `recipients.py`.
- Work on a branch, open a pull request, and merge only when the checks are green and a reviewer approved. Never push to main directly.

## Decisions

- **httpx, not the Resend SDK.** resend 2.55.0 wraps the same POST /emails call with a 30 second timeout and an idempotency key, but it never retries. Mailroom needs its own retry anyway, so the SDK adds a dependency for no gain.
- **Emoji length:** `len()` counts code points, so some emoji count as two. Good enough for a 50 character limit.
- **https only:** the one link in an issue must start with `https://`.

## Commands

```
uv run mailroom subscribers [--since-days N | --since YYYY-MM-DD] [--run-date YYYY-MM-DD]
uv run mailroom next-send [--run-date YYYY-MM-DD]
uv run mailroom check-issue issues/issue-01.md
uv run mailroom import-signups data/new-signups.csv
uv run mailroom send issues/issue-01.md --dry-run
uv run mailroom send issues/issue-01.md          # needs: npx emulate@0.12.3 start --service resend
uv run mailroom status <email id>
uv run mailroom guard < hook-input.json          # exit 2 blocks a Claude Code tool call
```

The server address and key come from `RESEND_API_URL` and `RESEND_API_KEY`, defaulting to `http://localhost:4000` and `re_practice`.
