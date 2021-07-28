from cyclonedds.idl import idl
from cyclonedds.idl.types import array, sequence


@idl
class Integer:
    seq: int
    keyval: int

    @classmethod
    def postfix(cls):
        return "integer"


@idl
class String:
    seq: int
    keyval: str

    @classmethod
    def postfix(cls):
        return "string"


@idl
class IntArray:
    seq: int
    keyval: array[int, 3]

    @staticmethod
    def size():
        return 3

    @classmethod
    def postfix(cls):
        return "int_array"


@idl
class StrArray:
    seq: int
    keyval: array[str, 5]

    @staticmethod
    def size():
        return 5

    @classmethod
    def postfix(cls):
        return "str_array"


@idl
class IntSequence:
    seq: int
    keyval: sequence[int]

    @classmethod
    def postfix(cls):
        return "int_sequence"


@idl
class StrSequence:
    seq: int
    keyval: sequence[str, 100]  # max 100 string elements

    @classmethod
    def postfix(cls):
        return "str_sequence"


datatypes = [Integer, String, IntArray, StrArray, IntSequence, StrSequence]
