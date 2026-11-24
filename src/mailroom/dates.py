from datetime import date, timedelta


def window_start(run_date: date, days: int) -> date:
    """The first day of "the last N days", counting the run date itself as day 0."""
    return run_date - timedelta(days=days)


def next_send(run_date: date) -> date:
    """The first Monday of the month after run_date."""
    if run_date.month == 12:
        first = date(run_date.year + 1, 1, 1)
    else:
        first = date(run_date.year, run_date.month + 1, 1)
    return first + timedelta(days=(0 - first.weekday()) % 7)
