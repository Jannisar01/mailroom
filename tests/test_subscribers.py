from datetime import date
from pathlib import Path

import pytest

from mailroom.errors import DataError
from mailroom.subscribers import count_by_group, joined_between, load_subscribers
from mailroom.dates import next_send, window_start

DATA = Path(__file__).parent.parent / "data" / "subscribers.csv"
RUN = date(2026, 11, 20)


def test_counts_24_subscribers() -> None:
    assert len(load_subscribers(DATA)) == 24


def test_counts_8_in_each_of_three_groups() -> None:
    assert count_by_group(load_subscribers(DATA)) == {"black": 8, "green": 8, "oolong": 8}


def test_counts_20_who_gave_consent() -> None:
    assert sum(s.consent for s in load_subscribers(DATA)) == 20


def test_count_follows_the_file_not_a_fixed_number(tmp_path: Path) -> None:
    lines = DATA.read_text(encoding="utf-8").splitlines()[:7]
    small = tmp_path / "six.csv"
    small.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert len(load_subscribers(small)) == 6


def test_seven_joined_in_the_last_30_days() -> None:
    assert len(joined_between(load_subscribers(DATA), window_start(RUN, 30), RUN)) == 7


def test_joined_on_21_october_counts_and_20_october_does_not() -> None:
    names = {s.name for s in joined_between(load_subscribers(DATA), window_start(RUN, 30), RUN)}
    assert "Elif Kaya" in names
    assert "Hugo Lind" not in names


def test_since_an_exact_date() -> None:
    assert len(joined_between(load_subscribers(DATA), date(2026, 10, 1), RUN)) == 8


@pytest.mark.parametrize(
    ("run_date", "expected"),
    [
        (date(2026, 11, 20), date(2026, 12, 7)),
        (date(2026, 12, 7), date(2027, 1, 4)),
        (date(2026, 12, 31), date(2027, 1, 4)),
        (date(2027, 1, 31), date(2027, 2, 1)),  # the 1st is itself a Monday
    ],
)
def test_next_send_is_first_monday_of_next_month(run_date: date, expected: date) -> None:
    assert next_send(run_date) == expected


def test_impossible_date_names_the_row(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text(DATA.read_text(encoding="utf-8").replace("2026-04-17", "2026-02-30"), encoding="utf-8")
    with pytest.raises(DataError, match="row 11.*2026-02-30"):
        load_subscribers(bad)


def test_missing_file_is_a_plain_error(tmp_path: Path) -> None:
    with pytest.raises(DataError, match="does not exist"):
        load_subscribers(tmp_path / "nope.csv")
