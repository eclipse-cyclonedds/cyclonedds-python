from cyclonedds.idl import IdlStruct, IdlUnion, IdlEnum
from cyclonedds.idl.annotations import keylist, key
import cyclonedds.idl.types as pt

from enum import auto
from dataclasses import dataclass



@dataclass
class SingleInt(IdlStruct):
    value: int
    key("value")


@dataclass
class SingleString(IdlStruct):
    value: str
    key("value")


@dataclass
class SingleFloat(IdlStruct):
    value: float
    key("value")


@dataclass
class SingleBool(IdlStruct):
    value: bool
    key("value")


@dataclass
class SingleSequence(IdlStruct):
    value: pt.sequence[int]
    key("value")


@dataclass
class SingleArray(IdlStruct):
    value: pt.array[pt.uint16, 3]
    key("value")


@dataclass
class SingleUint16(IdlStruct):
    value: pt.uint16
    key("value")


@dataclass
class SingleBoundedSequence(IdlStruct):
    value: pt.sequence[int, 3]
    key("value")


@dataclass
class SingleBoundedString(IdlStruct):
    value: pt.bounded_str[10]
    key("value")


class BasicEnum(IdlEnum):
    One = auto()
    Two = auto()
    Three = auto()


@dataclass
class SingleEnum(IdlStruct):
    value: BasicEnum
    key("value")


@dataclass
class SingleNested(IdlStruct):
    value: SingleInt
    key("value")


@dataclass
@keylist(['a'])
class Keyed(IdlStruct):
    a: int
    b: int


@dataclass
class Keyed2(IdlStruct):
    a: int
    key("a")
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
    key("value")


typedef_a = pt.typedef['typedef_a', pt.uint32]
typedef_b = pt.typedef['typedef_b', pt.uint32]


class ContainSameTypes(IdlStruct):
    a: typedef_a
    b: typedef_b


alltypes = [
    SingleInt,
    SingleString,
    SingleFloat,
    SingleBool,
    SingleSequence,
    SingleArray,
    SingleUint16,
    SingleBoundedSequence,
    SingleBoundedString,
    SingleEnum,
    SingleNested,
    Keyed,
    Keyed2,
    Keyless,
    AllPrimitives,
    EasyUnion,
    SingleUnion,
    ContainSameTypes
]