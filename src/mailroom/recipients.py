ALLOWED_DOMAINS = ("example.com", "resend.dev")


def recipient_problem(address: str) -> str | None:
    """The one recipient rule: practice mail only goes to @example.com or @resend.dev."""
    addr = address.strip()
    if "<" in addr:  # "Name <someone@example.com>"
        addr = addr[addr.rfind("<") + 1 :].rstrip(">").strip()
    local, at, domain = addr.rpartition("@")
    if not at or not local or not domain or " " in addr:
        return f"{address!r} is not an email address"
    if domain.lower() not in ALLOWED_DOMAINS:
        return f"{address} is not a practice address: only @example.com and @resend.dev may receive mail"
    return None
