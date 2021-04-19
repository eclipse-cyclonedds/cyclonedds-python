from pycdr import cdr


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
