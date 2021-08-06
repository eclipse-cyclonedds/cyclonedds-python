from dataclasses import dataclass

from cyclonedds.idl import IdlStruct
from cyclonedds.idl.annotations import keylist
from cyclonedds.idl.types import array, int16, int32, int64


@dataclass
class Message(IdlStruct):
    message: str


@dataclass
class MessageAlt(IdlStruct):
    user_id: int
    message: str


@dataclass
@keylist(["user_id"])
class MessageKeyed(IdlStruct):
    user_id: int
    message: str


@dataclass
@keylist(["arr1a", "arr2a", "arr3a", "arr4a"])
class KeyedArrayType(IdlStruct):
    arr1a: array[str, 3]
    arr1b: array[str, 3]
    arr2a: array[int64, 3]
    arr2b: array[int16, 3]
    arr3a: array[int32, 3]
    arr3b: array[int64, 3]
