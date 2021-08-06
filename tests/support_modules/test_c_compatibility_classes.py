from dataclasses import dataclass

from cyclonedds.idl import IdlStruct
from cyclonedds.idl.types import uint32, array, uint8
from cyclonedds.idl.annotations import key


@dataclass
class replybytes(IdlStruct, typename="py_c_compat.replybytes"):
    reply_to: str
    key(reply_to)
    seq: uint32
    key(seq)
    data: bytes
    keyhash: array[uint8, 16]


