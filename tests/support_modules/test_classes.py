from cyclonedds.idl import idl
import cyclonedds.idl.types as pt

from enum import IntEnum, auto



@idl
class SingleInt:
    value: int


@idl
class SingleString:
    value: str


@idl
class SingleFloat:
    value: float


@idl
class SingleBool:
    value: bool


@idl
class SingleSequence:
    value: pt.sequence[int]


@idl
class SingleArray:
    value: pt.array[pt.uint16, 3]


@idl
class SingleUint16:
    value: pt.uint16


@idl
class SingleBoundedSequence:
    value: pt.sequence[int, 3]


@idl
class SingleBoundedString:
    value: pt.bounded_str[10]


class BasicEnum(IntEnum):
    One = auto()
    Two = auto()
    Three = auto()


@idl
class SingleEnum:
    value: BasicEnum


@idl
class SingleNested:
    value: SingleInt


@idl(keylist=['a'])
class Keyed:
    a: int
    b: int


@idl(keylist=[])
class Keyless:
    a: int
    b: int


@idl
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


@idl
class SingleUnion:
    value: EasyUnion
