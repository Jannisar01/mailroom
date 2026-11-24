from pathlib import Path

from mailroom.signups import import_signups

SIGNUPS = Path(__file__).parent.parent / "data" / "new-signups.csv"


def test_three_good_rows_and_five_bad() -> None:
    good, bad = import_signups(SIGNUPS)
    assert [g.name for g in good] == ["Zoe Marsh", "Fern Ito", "Gus Ward"]
    assert [b.row for b in bad] == [3, 4, 5, 6, 7]


def test_every_bad_row_names_the_field() -> None:
    _, bad = import_signups(SIGNUPS)
    assert [b.reason.split(":")[0] for b in bad] == ["email", "group", "joined_on", "name", "consent"]


def test_a_real_looking_address_is_refused(tmp_path: Path) -> None:
    f = tmp_path / "s.csv"
    f.write_text("name,email,group,joined_on,consent\nSara Ali,sara.ali@gmail.com,green,2026-11-21,yes\n", encoding="utf-8")
    _, bad = import_signups(f)
    assert "practice address" in bad[0].reason
