from cyclonedds.idl import idl
from cyclonedds.idl.types import array, int16, int32, int64


@idl
class Message:
    message: str


@idl
class MessageAlt:
    user_id: int
    message: str


@idl(keylist="user_id")
class MessageKeyed:
    user_id: int
    message: str


@idl(keylist=["arr1a", "arr2a", "arr3a", "arr4a"])
class KeyedArrayType:
    arr1a: array[str, 3]
    arr1b: array[str, 3]
    arr2a: array[int64, 3]
    arr2b: array[int16, 3]
    arr3a: array[int32, 3]
    arr3b: array[int64, 3]
