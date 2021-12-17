from cyclonedds.idl import IdlStruct, IdlUnion, IdlBitmask, IdlEnum
from cyclonedds.idl.annotations import key, mutable, appendable
from cyclonedds.idl.types import uint16, case, default

from dataclasses import dataclass


class XEnum(IdlEnum):
    V1 = 0
    V2 = 1


@dataclass
class XBitmask(IdlBitmask):
    V1: bool
    V2: bool


@appendable
class XUnion(IdlUnion, discriminator=uint16):
    A: case[0, XEnum]
    B: case[1, XBitmask]
    C: default[float]


@dataclass
@mutable
class XStruct(IdlStruct):
    A: XUnion
    k: int
    key('k')
