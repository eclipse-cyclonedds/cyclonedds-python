from cyclonedds.idl import IdlStruct, IdlUnion
from cyclonedds.idl.annotations import keylist, key
import cyclonedds.idl.types as pt

from enum import IntEnum, auto
from dataclasses import dataclass



@dataclass
class SingleInt(IdlStruct):
    value: int


@dataclass
class SingleString(IdlStruct):
    value: str


@dataclass
class SingleFloat(IdlStruct):
    value: float


@dataclass
class SingleBool(IdlStruct):
    value: bool


@dataclass
class SingleSequence(IdlStruct):
    value: pt.sequence[int]


@dataclass
class SingleArray(IdlStruct):
    value: pt.array[pt.uint16, 3]


@dataclass
class SingleUint16(IdlStruct):
    value: pt.uint16


@dataclass
class SingleBoundedSequence(IdlStruct):
    value: pt.sequence[int, 3]


@dataclass
class SingleBoundedString(IdlStruct):
    value: pt.bounded_str[10]


class BasicEnum(IntEnum):
    One = auto()
    Two = auto()
    Three = auto()


@dataclass
class SingleEnum(IdlStruct):
    value: BasicEnum


@dataclass
class SingleNested(IdlStruct):
    value: SingleInt


@dataclass
@keylist(['a'])
class Keyed(IdlStruct):
    a: int
    b: int


@dataclass
class Keyed2(IdlStruct):
    a: int
    key(a)
    b: int


@dataclass
@keylist([])
class Keyless(IdlStruct):
    a: int
    b: int


@dataclass
class AllPrimitives(IdlStruct):
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


class EasyUnion(IdlUnion, discriminator=int):
    a: pt.case[1, int]
    b: pt.case[2, bool]


@dataclass
class SingleUnion(IdlStruct):
    value: EasyUnion
