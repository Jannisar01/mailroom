# What a reviewer checks

1. **The checks are green.** pytest and pyright passed on this pull request.
2. **Tests came first.** A new behavior has a test, and no existing expected answer changed. If one did, the pull request says why.
3. **The evidence is there.** The description shows the command that was run and its output.
4. **No real addresses.** Every address is @example.com or @resend.dev.
5. **The rules hold.** Only `cli.py` prints or reads today's date. The recipient rule is only in `recipients.py`. Nothing retries a 4xx.
6. **Small.** One change per pull request. If the title needs "and", split it.
