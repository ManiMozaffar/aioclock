from enum import Enum
from itertools import chain
from typing import Iterable, TypeVar

T = TypeVar("T")


def flatten_chain(matrix: list[Iterable[T]]) -> list[T]:
    return list(chain.from_iterable(matrix))


class StrEnum(str, Enum):
    """
    StrEnum subclasses that create variants using `auto()` will have values equal to their names

    Enums inheriting from this class that set values using `enum.auto()` will have variant values
        equal to their names
    """

    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[str]) -> str:
        """
        Uses the name as the automatic value, rather than an integer
        See https://docs.python.org/3/library/enum.html#using-automatic-values for reference
        """
        return name

    def __str__(self) -> str:
        return str(self.value)
