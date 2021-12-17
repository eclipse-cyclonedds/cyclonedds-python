"""
 * Copyright(c) 2021 ADLINK Technology Limited and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
"""

import typing
if not typing.TYPE_CHECKING:
    class NewType:
        def __init__(self, name, tp):
            self.__name__ = name
            self.__supertype__ = tp

        def __call__(self, x):
            return x

        def __repr__(self):
            return self.__name__
    typing.NewType = NewType

from typing import NewType, Sequence, Optional, Type
from functools import reduce
from ._type_helper import Annotated


char = NewType("char", int)
wchar = NewType("wchar", int)
int8 = NewType("int8", int)
int16 = NewType("int16", int)
int32 = NewType("int32", int)
int64 = NewType("int64", int)
uint8 = NewType("uint8", int)
uint16 = NewType("uint16", int)
uint32 = NewType("uint32", int)
uint64 = NewType("uint64", int)
float32 = NewType("float32", float)
float64 = NewType("float64", float)
NoneType = type(None)

primitive_types = {
    wchar: (2, 'h'),
    int8: (1, 'b'),
    int16: (2, 'h'),
    int32: (4, 'i'),
    int64: (8, 'q'),
    uint8: (1, 'B'),
    uint16: (2, 'H'),
    uint32: (4, 'I'),
    uint64: (8, 'Q'),
    float32: (4, 'f'),
    float64: (8, 'd'),
    int: (8, 'q'),
    bool: (1, '?'),
    float: (8, 'd')
}


def _type_repr(obj):
    """Avoid printing <class 'int'>"""
    if isinstance(obj, type):
        if obj.__module__ == 'builtins':
            return obj.__qualname__
        return f'{obj.__module__}.{obj.__qualname__}'
    if obj is ...:
        return '...'
    return repr(obj)


class array:
    @classmethod
    def __class_getitem__(cls, tup):
        if type(tup) != tuple:
            tup = (tup,)

        if len(tup) != 2 or type(tup[1]) != int:
            raise TypeError("An array takes two arguments: an element type and a constant length.")
        return Annotated[Sequence[tup[0]], cls(*tup)]

    def __init__(self, subtype: Type, length: int):
        self.subtype: Type = subtype
        self.length: int = length

    def __repr__(self) -> str:
        return f"array[{_type_repr(self.subtype)}, {self.length}]"

    def __eq__(self, o: object) -> bool:
        return isinstance(o, array) and o.subtype == self.subtype and o.length == self.length

    def __hash__(self) -> int:
        return (241813571056069 * self.length) ^ hash(self.subtype)

    __str__ = __repr__


class sequence:
    @classmethod
    def __class_getitem__(cls, tup):
        if type(tup) != tuple:
            tup = (tup,)

        if len(tup) not in [1, 2] or (len(tup) == 2 and type(tup[1]) != int):
            raise TypeError("A sequence takes a subtype and an optional maximum length.")
        if len(tup) > 1 and (tup[1] <= 0 or tup[1] > 65535):
            return TypeError("Sequence max length should be between 0 and 65536.")
        return Annotated[Sequence[tup[0]], cls(*tup)]

    def __init__(self, subtype: Type, max_length: Optional[int] = None) -> None:
        self.subtype: Type = subtype
        self.max_length: Optional[int] = max_length

    def __repr__(self) -> str:
        if self.max_length:
            return f"sequence[{_type_repr(self.subtype)}, {self.max_length}]"
        else:
            return f"sequence[{_type_repr(self.subtype)}]"

    def __eq__(self, o: object) -> bool:
        return isinstance(o, sequence) and o.subtype == self.subtype and o.max_length == self.max_length

    def __hash__(self) -> int:
        if self.max_length:
            return (406820761152607 * self.max_length) ^ hash(self.subtype)
        else:
            return 406820761152609 ^ hash(self.subtype)

    __str__ = __repr__


class typedef:
    @classmethod
    def __class_getitem__(cls, tup):
        if type(tup) != tuple:
            tup = (tup,)

        if len(tup) != 2:
            raise TypeError("A typedef takes a name and real type as argument.")

        rtype = tup[1]
        while _th.get_origin(rtype) == _th.Annotated:
            rtype = _th.get_args(rtype)[0]
        return _th.Annotated[rtype, cls(*tup)]

    def __init__(self, name: str, subtype: type) -> None:
        self.name: str = name
        self.subtype: type = subtype

    def __repr__(self) -> str:
        return f"typedef[{self.name}, {_type_repr(self.subtype)}]"

    def __eq__(self, o: object) -> bool:
        return (isinstance(o, typedef) and o.subtype == self.subtype)

    def __hash__(self) -> int:
        return hash(self.name) ^ hash(self.subtype)

    def __call__(self, *args: _typing.Any, **kwds: _typing.Any) -> _typing.Any:
        return self.subtype(*args, **kwds)

    @property
    def __idl_typename__(self):
        return self.name

    __str__ = __repr__


class bounded_str:
    @classmethod
    def __class_getitem__(cls, tup):
        if type(tup) != tuple:
            tup = (tup,)

        if len(tup) != 1 or type(tup[0]) != int:
            raise TypeError("A bounded str takes one argument, a maximum length.")
        if tup[0] <= 0:
            return TypeError("Bound string max length should be bigger than 0.")
        return Annotated[str, cls(*tup)]

    def __init__(self, max_length: int) -> None:
        self.max_length: int = max_length

    def __repr__(self) -> str:
        return f"bounded_str[{self.max_length}]"

    def __eq__(self, o: object) -> bool:
        return isinstance(o, bounded_str) and o.max_length == self.max_length

    def __hash__(self) -> int:
        return 277146416319491 * self.max_length

    __str__ = __repr__


class ValidUnionHolder:
    pass


class case(ValidUnionHolder):
    @classmethod
    def __class_getitem__(cls, tup):
        if type(tup) != tuple:
            tup = (tup,)

        if len(tup) != 2:
            raise TypeError("A case takes two arguments: the discriminator value(s) and the type.")
        return Annotated[Optional[tup[1]], cls(*tup)]

    def __init__(self, discriminator_value, subtype: Type) -> None:
        self.labels = discriminator_value if type(discriminator_value) == list else [discriminator_value]
        self.subtype = subtype

    def __repr__(self) -> str:
        return f"case[{self.labels}, {_type_repr(self.subtype)}]"

    def __eq__(self, o: object) -> bool:
        return isinstance(o, case) and o.subtype == self.subtype and \
               o.labels == self.labels

    def __hash__(self) -> int:
        return (545464105755071 * reduce((lambda x, y: hash(x ^ (y * 11))), self.labels)) ^ hash(self.subtype)

    __str__ = __repr__


class default(ValidUnionHolder):
    @classmethod
    def __class_getitem__(cls, tup):
        if type(tup) != tuple:
            tup = (tup,)

        if len(tup) != 1:
            raise TypeError("A default takes one arguments: the type.")
        return Annotated[Optional[tup[0]], cls(*tup)]

    def __init__(self, subtype: Type) -> None:
        self.subtype: Type = subtype

    def __repr__(self) -> str:
        return f"default[{_type_repr(self.subtype)}]"

    def __eq__(self, o: object) -> bool:
        return isinstance(o, default) and o.subtype == self.subtype

    def __hash__(self) -> int:
        return 438058395842377 ^ hash(self.subtype)

    __str__ = __repr__

