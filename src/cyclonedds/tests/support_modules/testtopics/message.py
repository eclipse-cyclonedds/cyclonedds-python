from pycdr import cdr
from pycdr.types import array, int16, int32, int64


@cdr
class Message:
    message: str


@cdr
class MessageAlt:
    user_id: int
    message: str


@cdr(keylist="user_id")
class MessageKeyed:
    user_id: int
    message: str


@cdr(keylist=["arr1a", "arr2a", "arr3a", "arr4a"])
class KeyedArrayType:
    arr1a: array[str, 3]
    arr1b: array[str, 3]
    arr2a: array[int64, 3]
    arr2b: array[int16, 3]
    arr3a: array[int32, 3]
    arr3b: array[int64, 3]
