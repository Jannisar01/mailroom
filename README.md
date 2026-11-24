# Mailroom

A small command-line tool for Kettlebird Tea's Steep Club newsletter: it counts subscribers, checks an issue against five rules, and sends it to a local practice mail server. Built for the Mailroom Lab (The AI Agent Factory, chapters 13 to 15). All data is made up.

```
uv sync
uv run mailroom subscribers --since-days 30
uv run mailroom check-issue issues/issue-01.md
uv run pytest
```

See AGENTS.md for every command and the project's rules.
