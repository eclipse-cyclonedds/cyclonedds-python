from typing import Type, TypeVar, Sequence, Optional, Any, overload

_T = TypeVar("_T")

class array:
    @overload
    @classmethod
    def __class_getitem__(cls, item: Type[_T]) -> type[Sequence[_T]]: ...
    @overload
    @classmethod
    def __class_getitem__(cls, item: tuple[Type[_T], int]) -> type[Sequence[_T]]: ...

    def __init__(self, subtype: type, length: int) -> None: ...
    def __repr__(self) -> str: ...
    def __eq__(self, o: object) -> bool: ...
    def __hash__(self) -> int: ...


class sequence:
    @overload
    @classmethod
    def __class_getitem__(cls, item: Type[_T]) -> type[Sequence[_T]]: ...
    @overload
    @classmethod
    def __class_getitem__(cls, item: tuple[Type[_T], int]) -> type[Sequence[_T]]: ...

    def __init__(self, subtype: type, max_length: Optional[int] = None) -> None: ...
    def __repr__(self) -> str: ...
    def __eq__(self, o: object) -> bool: ...
    def __hash__(self) -> int: ...


class typedef:
    @overload
    @classmethod
    def __class_getitem__(cls, item: tuple[str, Type[_T]]) -> type[_T]: ...
    @overload
    @classmethod
    def __class_getitem__(cls, item: Type[_T]) -> type[_T]: ...

    def __init__(self, name: str, subtype: type) -> None: ...
    def __repr__(self) -> str: ...
    def __eq__(self, o: object) -> bool: ...
    def __hash__(self) -> int: ...
    def __call__(self, *args: Any, **kwds: Any) -> Any: ...
    @property
    def __idl_typename__(self) -> str: ...


class bounded_str:
    @overload
    @classmethod
    def __class_getitem__(cls, item: int) -> type[str]: ...

    def __init__(self, max_length: int) -> None: ...
    def __repr__(self) -> str: ...
    def __eq__(self, o: object) -> bool: ...
    def __hash__(self) -> int: ...


class ValidUnionHolder:
    pass


class case(ValidUnionHolder):
    @overload
    @classmethod
    def __class_getitem__(cls, item: tuple[int, Type[_T]]) -> type[Optional[_T]]: ...
    @overload
    @classmethod
    def __class_getitem__(cls, item: Type[_T]) -> type[Optional[_T]]: ...

    def __init__(self, discriminator_value: int | list[int], subtype: type) -> None: ...
    def __repr__(self) -> str: ...
    def __eq__(self, o: object) -> bool: ...
    def __hash__(self) -> int: ...


class default(ValidUnionHolder):
    @overload
    @classmethod
    def __class_getitem__(cls, item: Type[_T]) -> type[Optional[_T]]: ...

    def __init__(self, subtype: type) -> None: ...
    def __repr__(self) -> str: ...
    def __eq__(self, o: object) -> bool: ...
    def __hash__(self) -> int: ...


# IDL primitive type aliases
char = str
"""The C ``char`` datatype. In Python this is implemented as a single-character string."""

wchar = int
"""The C ``wchar`` datatype. Do not use, here for completeness."""

int8 = int
"""A signed 8 bit integer."""

int16 = int
"""A signed 16 bit integer."""

int32 = int
"""A signed 32 bit integer."""

int64 = int
"""A signed 64 bit integer."""

uint8 = int
"""An unsigned 8 bit integer."""

uint16 = int
"""An unsigned 16 bit integer."""

uint32 = int
"""An unsigned 32 bit integer."""

uint64 = int
"""An unsigned 64 bit integer."""

float32 = float
"""A 32bit floating point number. In typical C this is a regular ``float``."""

float64 = float
"""A 64bit floating point number. In typical C this is a regular ``float``."""

NoneType = type(None)
"""The NoneType, or a "void" type. This is not included in the OMG IDL spec or in the C library but it can be very useful."""
