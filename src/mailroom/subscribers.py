import csv
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from mailroom.errors import DataError


@dataclass(frozen=True)
class Subscriber:
    name: str
    email: str
    group: str
    joined_on: date
    consent: bool

    @property
    def first_name(self) -> str:
        return self.name.split()[0]


def load_subscribers(path: Path) -> list[Subscriber]:
    if not path.exists():
        raise DataError(f"{path} does not exist")
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    subscribers: list[Subscriber] = []
    for number, row in enumerate(rows, start=2):  # row 1 is the header
        try:
            joined_on = date.fromisoformat(row["joined_on"])
        except KeyError:
            raise DataError(f"{path} has no joined_on column") from None
        except ValueError:
            raise DataError(
                f"{path} row {number}: joined_on {row['joined_on']!r} is not a real date"
            ) from None
        subscribers.append(
            Subscriber(
                name=row["name"],
                email=row["email"],
                group=row["group"],
                joined_on=joined_on,
                consent=row["consent"] == "yes",
            )
        )
    return subscribers


def count_by_group(subscribers: list[Subscriber]) -> dict[str, int]:
    return dict(sorted(Counter(s.group for s in subscribers).items()))


def joined_between(subscribers: list[Subscriber], start: date, end: date) -> list[Subscriber]:
    """Both ends count: someone who joined on start or on end is included."""
    return [s for s in subscribers if start <= s.joined_on <= end]
