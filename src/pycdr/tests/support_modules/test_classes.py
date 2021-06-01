from pycdr import cdr
import pycdr.types as pt

from enum import IntEnum, auto



@cdr
class SingleInt:
    value: int


@cdr
class SingleString:
    value: str


@cdr
class SingleFloat:
    value: float


@cdr
class SingleBool:
    value: bool


@cdr
class SingleSequence:
    value: pt.sequence[int]


@cdr
class SingleArray:
    value: pt.array[pt.uint16, 3]


@cdr
class SingleUint16:
    value: pt.uint16


@cdr
class SingleBoundedSequence:
    value: pt.sequence[int, 3]


@cdr
class SingleBoundedString:
    value: pt.bound_str[10]


class BasicEnum(IntEnum):
    One = auto()
    Two = auto()
    Three = auto()


@cdr
class SingleEnum:
    value: BasicEnum


@cdr
class SingleNested:
    value: SingleInt


@cdr(keylist=['a'])
class Keyed:
    a: int
    b: int


@cdr(keylist=[])
class Keyless:
    a: int
    b: int


@cdr
class AllPrimitives:
    a: pt.int8 = 123
    b: pt.uint8 = 212
    c: pt.int16 = 7834
    d: pt.uint16 = 2817
    e: pt.int32 = 12987421
    f: pt.uint32 = 328732
    g: pt.int64 = 84987349873
    h: pt.uint64 = 12987181827
    i: pt.float32 = 1.0
    j: pt.float64 = 1287.1878


@pt.union(int)
class EasyUnion:
    a: pt.case[1, int]
    b: pt.case[2, bool]


@cdr
class SingleUnion:
    value: EasyUnion
