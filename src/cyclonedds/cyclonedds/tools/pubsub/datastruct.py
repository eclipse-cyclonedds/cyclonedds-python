from pycdr import cdr
from pycdr.types import array, sequence


@cdr
class Integer:
    seq: int
    keyval: int

    @classmethod
    def postfix(cls):
        return "integer"


@cdr
class String:
    seq: int
    keyval: str

    @classmethod
    def postfix(cls):
        return "string"


@cdr
class IntArray:
    seq: int
    keyval: array[int, 3]

    @staticmethod
    def size():
        return 3

    @classmethod
    def postfix(cls):
        return "int_array"


@cdr
class StrArray:
    seq: int
    keyval: array[str, 5]

    @staticmethod
    def size():
        return 5

    @classmethod
    def postfix(cls):
        return "str_array"


@cdr
class IntSequence:
    seq: int
    keyval: sequence[int]

    @classmethod
    def postfix(cls):
        return "int_sequence"


@cdr
class StrSequence:
    seq: int
    keyval: sequence[str, 100]  # max 100 string elements

    @classmethod
    def postfix(cls):
        return "str_sequence"


datatypes = [Integer, String, IntArray, StrArray, IntSequence, StrSequence]
