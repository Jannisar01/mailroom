# Email rules

Every issue must pass all five rules before it is sent.

1. **Subject.** A `Subject:` line, not empty, 50 characters or fewer.
2. **Preview.** A `Preview:` line, not empty, 90 characters or fewer.
3. **Greeting.** The body greets the reader with the `{{first_name}}` placeholder.
4. **One link.** The body has exactly one link, and it starts with `https://`.
5. **Footer.** The last line is `Unsubscribe: {{unsubscribe_url}}`.

Lengths count characters as Python's `len()` does (code points), so one emoji counts as one or more.
