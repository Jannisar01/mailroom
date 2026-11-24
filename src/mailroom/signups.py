import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError, field_validator

from mailroom.errors import DataError
from mailroom.recipients import recipient_problem


class Signup(BaseModel):
    name: str
    email: str
    group: Literal["green", "black", "oolong"]
    joined_on: date
    consent: Literal["yes", "no"]

    @field_validator("name")
    @classmethod
    def name_is_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name is empty")
        return value.strip()

    @field_validator("email")
    @classmethod
    def email_is_a_practice_address(cls, value: str) -> str:
        problem = recipient_problem(value)
        if problem:
            raise ValueError(problem)
        return value.strip()


@dataclass(frozen=True)
class BadRow:
    row: int
    reason: str


def import_signups(path: Path) -> tuple[list[Signup], list[BadRow]]:
    """Check every row and report every bad one, instead of stopping at the first."""
    if not path.exists():
        raise DataError(f"{path} does not exist")
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    good: list[Signup] = []
    bad: list[BadRow] = []
    for number, row in enumerate(rows, start=2):  # row 1 is the header
        try:
            good.append(Signup.model_validate(row))
        except ValidationError as e:
            reason = "; ".join(f"{err['loc'][0]}: {err['msg']}" for err in e.errors())
            bad.append(BadRow(number, reason))
    return good, bad
