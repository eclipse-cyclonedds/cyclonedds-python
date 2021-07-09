from pycdr import cdr
from pycdr.types import array, sequence


@cdr
class Integer:
    seq: int
    keyval: int


@cdr
class String:
    seq: int
    keyval: str


@cdr
class IntArray:
    seq: int
    keyval: array[int, 3]

    @staticmethod
    def size():
        return 3


@cdr
class StrArray:
    seq: int
    keyval: array[str, 5]

    @staticmethod
    def size():
        return 5


@cdr
class IntSequence:
    seq: int
    keyval: sequence[int]


@cdr
class StrSequence:
    seq: int
    keyval: sequence[str, 100]  # max 100 string elements
