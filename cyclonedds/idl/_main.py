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

from typing import Optional, cast, Any, Type, Union, ClassVar, Mapping, Dict, TypeVar, Tuple
from collections import defaultdict
from dataclasses import dataclass
from hashlib import md5
from enum import Enum

from ._support import Buffer, Endianness
from ._type_helper import get_origin, get_args, get_type_hints, Annotated
from . import types


@dataclass
class IdlField:
    name: dict
    type: Union[Type, str]
    annotations: dict


class IdlClassNamespace(dict):
    def __init__(self) -> None:
        super().__setitem__("__annotations__", {})
        super().__setitem__("__idl_annotations__", {})
        super().__setitem__("__idl_field_annotations__", {})

    def __getitem__(self, k):
        if not k in self and k in super().__getitem__("__annotations__"):
            idl_field_annotations = super().__getitem__("__idl_field_annotations__")

            if k not in idl_field_annotations:
                idl_field_annotations[k] = {}

            return IdlField(
                name=k,
                type=super().__getitem__("__annotations__")[k],
                annotations=idl_field_annotations[k]
            )

        return super().__getitem__(k)


class IDL:
    def __init__(self, datatype):
        self.buffer = Buffer()
        self.datatype = datatype
        self.machine = None
        self.keyless = None
        self.key_max_size = None
        self.idl_transformed_typename = self.datatype.__idl_typename__.replace(".", "::")

    def populate(self):
        if self.machine is None:
            from ._builder import Builder
            self.machine, self.keyless, self.key_max_size = Builder.build_machines(self.datatype)

    def serialize(self, object, buffer=None, endianness=None) -> bytes:
        if self.machine is None:
            self.populate()

        ibuffer = buffer or self.buffer
        ibuffer.seek(0)
        ibuffer.set_align_offset(0)
        ibuffer.set_endianness(endianness or Endianness.native())

        if ibuffer.endianness == Endianness.Big:
            ibuffer.write('b', 1, 0)
            ibuffer.write('b', 1, 0)
            ibuffer.write('b', 1, 0)
            ibuffer.write('b', 1, 0)
        else:
            ibuffer.write('b', 1, 0)
            ibuffer.write('b', 1, 1)
            ibuffer.write('b', 1, 0)
            ibuffer.write('b', 1, 0)

        ibuffer.set_align_offset(4)

        self.machine.serialize(ibuffer, object)
        a = ibuffer.asbytes() #.ljust((self.buffer._pos - 1) // 8 * 8 + 8, b'\0')
        return a

    def deserialize(self, data) -> object:
        if self.machine is None:
            self.populate()

        buffer = Buffer(data, align_offset=4) if not isinstance(data, Buffer) else data

        if buffer.tell() == 0:
            buffer.read('b', 1)
            v = buffer.read('b', 1)
            if v == 0:
                buffer.set_endianness(Endianness.Big)
            else:
                buffer.set_endianness(Endianness.Little)
            buffer.read('b', 1)
            buffer.read('b', 1)

        return self.machine.deserialize(buffer)

    def key(self, object) -> bytes:
        if self.machine is None:
            self.populate()

        self.buffer.seek(0)
        self.buffer.zero_out()
        self.buffer.set_align_offset(0)
        self.buffer.set_endianness(Endianness.Big)

        if self.keyless:
            return bytes()

        self.machine.serialize(self.buffer, object, for_key=True)

        return self.buffer.asbytes()

    def keyhash(self, object) -> bytes:
        if self.machine is None:
            self.populate()

        if self.key_max_size <= 16:
            return self.key(object).ljust(16, b'\0')

        m = md5()
        m.update(self.key(object))
        return m.digest()

    def cdr_key_machine(self, skip=False):
        if self.machine is None:
            self.populate()
        if self.keyless:
            return []

        return self.machine.cdr_key_machine_op(skip)


class IdlMeta(type):
    __idl__: ClassVar['IDL']
    __idl_typename__: ClassVar[str]
    __idl_annotations__: ClassVar[Dict[str, Any]]
    __idl_field_annotations__: ClassVar[Dict[str, Dict[str, Any]]]

    @classmethod
    def __prepare__(metacls, __name: str, __bases: Tuple[type, ...], **kwds: Any) -> Mapping[str, Any]:
        namespace: Dict[str, Any] = IdlClassNamespace()

        typename = None
        if "typename" in kwds:
            typename = kwds["typename"]
            del kwds["typename"]

        namespace.update(super().__prepare__(__name, __bases, **kwds))

        if typename:
            namespace["__idl_typename__"] = typename

        return namespace

    def __new__(metacls, name, bases, namespace, **kwds):
        new_cls = super().__new__(metacls, name, bases, dict(**namespace))

        if not "__idl_typename__" in namespace:
            new_cls.__idl_typename__ = name

        new_cls.__idl__ = IDL(new_cls)
        return new_cls

    def __repr__(cls):
        # Note, this is the _class_ repr
        return f"<IdlStruct:{cls.__name__} idl_typename='{cls.__idl_typename__}'" + \
               f"fields='{' '.join(str(k)+':'+str(v) for k,v in cls.__annotations__.items())}>"


def _union_default_finder(type, cases):
    if isinstance(type, Enum):
        # We assume the enum is well formatted and starts at 0. We will use an integer to encode.
        return -1

    if type == bool:
        if True not in cases:
            return True
        elif False not in cases:
            return False
        raise TypeError("No space in discriminated union for default value.")

    val, inc, end = {
        types.int8: (-1, -1, -128),
        types.int16: (-1, -1, -32768),
        types.int32: (-1, -1, -2147483648),
        types.int64: (-1, -1, -9223372036854775808),
        int: (-1, -1, -9223372036854775808),
        types.uint8: (0, 1, 255),
        types.uint16: (0, 1, 65535),
        types.uint32: (0, 1, 4294967295),
        types.uint64: (0, 1, 18446744073709551615),
    }.get(type, (None, None, None))

    if val is None:
        raise TypeError("Invalid discriminator type")

    while True:
        if val not in cases:
            return val
        if val == end:
            raise TypeError("No space in discriminated union for default value.")
        val += inc


class IdlUnionMeta(IdlMeta):
    __idl_discriminator__: Any
    __idl_discriminator_is_key__: bool
    __idl_cases__: Dict[Any, Any]
    __idl_default__: Optional[Tuple[Any, Any]]

    @classmethod
    def __prepare__(metacls, __name: str, __bases: Tuple[type, ...], **kwds: Any) -> Mapping[str, Any]:
        if not len(__bases):
            return super().__prepare__(__name, __bases, **kwds)

        discriminator_is_key = False

        if "discriminator" not in kwds:
            raise TypeError("Union class needs a 'discriminator=type'")

        if "discriminator_is_key" in kwds:
            discriminator_is_key = kwds["discriminator_is_key"]
            del kwds["discriminator_is_key"]

        discriminator = kwds["discriminator"]
        del kwds["discriminator"]

        namespace = super().__prepare__(__name, __bases, **kwds)
        namespace["__idl_discriminator__"] = discriminator
        namespace["__idl_discriminator_is_key__"] = discriminator_is_key
        return namespace

    def __new__(metacls, name, bases, namespace, **kwds):
        new_cls = super().__new__(metacls, name, bases, dict(**namespace))
        if not len(bases):
            return new_cls

        cases = {}
        default = None
        names = set()

        for name, _type in get_type_hints(new_cls, include_extras=True).items():
            origin = get_origin(_type)
            args = get_args(_type)

            if origin != Annotated or len(args) != 2:
                raise TypeError("Fields of a union need to be case or default.")

            holder = args[1]
            if type(holder) == tuple:
                # Edge case for python 3.6: bug in backport? TODO: investigate and report
                holder = holder[0]

            if isinstance(holder, types.case):
                for label in holder.labels:
                    if label in cases:
                        raise TypeError(f"Discriminator values must uniquely define a case, "
                                        f"but the case {label} occurred multiple times.")
                    cases[label] = (name, holder.subtype)
                    names.add(name)
            elif isinstance(holder, types.default):
                if default:
                    raise TypeError("A discriminated union can only have one default.")
                default = (name, holder.subtype)
                names.add(name)
            else:
                raise TypeError("Fields of a union need to be case or default.")

        new_cls.__idl_cases__ = cases
        new_cls.__idl_default__ = default
        new_cls.__idl_names__ = names
        new_cls.__idl_default_discriminator__ = _union_default_finder(namespace['__idl_discriminator__'], cases)

        return new_cls

    def __repr__(cls):
        # Note, this is the _class_ repr
        if not cls.__bases__:
            return f"<{cls.__name__}>"
        return f"<IdlUnion:{cls.__name__} idl_typename='{cls.__idl_typename__}' discriminator='{cls.__idl_discriminator__}' " + \
               f"fields='{' '.join(str(k)+':'+str(v) for k,v in cls.__annotations__.items())}>"



class IdlStruct(metaclass=IdlMeta):
    def serialize(self, buffer=None, endianness=None):
        return self.__idl__.serialize(self, buffer=buffer, endianness=endianness)

    @classmethod
    def deserialize(cls, data):
        return cls.__idl__.deserialize(data)


class IdlUnion(metaclass=IdlUnionMeta):
    def __init__(self, **kwargs):
        self.__active = None
        self.__discriminator = None
        self.__value = None

        if len(kwargs) == 2 and 'discriminator' in kwargs and 'value' in kwargs:
            self.set(kwargs['discriminator'], kwargs['value'])
        elif len(kwargs) == 1:
            for key, value in kwargs.items():
                self.__setattr__(key, value)
        else:
            raise ValueError("Can only set one field of union.")

    def __setattr__(self, name: str, value: Any) -> None:
        if name not in self.__idl_names__:
            return super().__setattr__(name, value)

        if self.__idl_default__ and self.__idl_default__[0] == name:
            if self.__active:
                super().__setattr__(self.__active, None)

            self.__active = name
            self.__discriminator = None
            self.__value = value
            return super().__setattr__(name, value)

        for label, case in self.__idl_cases__.items():
            if case[0] == name:
                if self.__active:
                    super().__setattr__(self.__active, None)

                self.__active = name
                self.__discriminator = label
                self.__value = value
                return super().__setattr__(name, value)

        raise Exception("Programmer error, should not get here.")

    def __getattr__(self, name: str) -> Any:
        if name in self.__idl_names__ and not self.__active == name:
            raise AttributeError("Tried to get inactive case on union")
        return super().__getattribute__(name)

    def set(self, discriminator, value):
        if discriminator not in self.__idl_cases__:
            if self.__active:
                super().__setattr__(self.__active, None)

            self.__active = self.__idl_default__[0]
            self.__discriminator = discriminator
            self.__value = value
            return super().__setattr__(self.__idl_default__[0], value)
        else:
            case = self.__idl_cases__[discriminator]
            if self.__active:
                super().__setattr__(self.__active, None)

            self.__active = case[0]
            self.__discriminator = discriminator
            self.__value = value
            return super().__setattr__(case[0], value)

    def get(self):
        return self.__discriminator, self.__value

    @property
    def discriminator(self):
        return self.__discriminator

    @property
    def value(self):
        return self.__value

    def __repr__(self):
        return f"{self.__class__.__name__}[Union]{self.get()}"

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.get() == other.get()

    def serialize(self, buffer=None, endianness=None):
        return self.__idl__.serialize(self, buffer=buffer, endianness=endianness)

    @classmethod
    def deserialize(cls, data):
        return cls.__idl__.deserialize(data)

