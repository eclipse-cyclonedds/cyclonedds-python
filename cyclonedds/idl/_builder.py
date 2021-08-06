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

from enum import Enum
from importlib import import_module
from inspect import isclass
from typing import Type, Optional, Union
from collections import defaultdict

from ._main import IdlStruct, IdlUnion
from ._support import MaxSizeFinder
from ._type_helper import Annotated, get_origin, get_args, get_type_hints
from ._machinery import NoneMachine, PrimitiveMachine, StringMachine, BytesMachine, ByteArrayMachine, UnionMachine, \
    ArrayMachine, SequenceMachine, InstanceMachine, MappingMachine, EnumMachine, StructMachine, OptionalMachine, CharMachine

from .types import array, bounded_str, sequence, primitive_types, NoneType, char


class Builder:
    easy_types = {
        char: CharMachine,
        str: StringMachine,
        bytes: BytesMachine,
        bytearray: ByteArrayMachine,
        NoneType: NoneMachine,
        None: NoneMachine
    }

    @classmethod
    def _machine_for_annotated_type(cls, _type):
        args = get_args(_type)
        if len(args) >= 2:
            holder = args[1]
            if type(holder) == tuple:
                # Edge case for python 3.6: bug in backport? TODO: investigate and report
                holder = holder[0]
            if isinstance(holder, array):
                return ArrayMachine(
                    cls._machine_for_type(holder.subtype),
                    size=holder.length
                )
            elif isinstance(holder, sequence):
                return SequenceMachine(
                    cls._machine_for_type(holder.subtype),
                    maxlen=holder.max_length
                )
            elif isinstance(holder, bounded_str):
                return StringMachine(
                    bound=holder.max_length
                )

        raise TypeError(f"{repr(_type)} is not valid in IDL classes because it cannot be encoded.")

    @classmethod
    def _machine_for_type(cls, _type):
        if _type in cls.easy_types:
            return cls.easy_types[_type]()
        elif _type in primitive_types:
            return PrimitiveMachine(_type)
        elif get_origin(_type) == Annotated:
            return cls._machine_for_annotated_type(_type)
        elif get_origin(_type) == Optional or (get_origin(_type) == Union and NoneType in get_args(_type)):
            return OptionalMachine(cls._machine_for_type(get_args(_type)[0]))
        elif isclass(_type) and issubclass(_type, Enum):
            return EnumMachine(_type)
        elif isclass(_type) and (issubclass(_type, IdlStruct) or issubclass(_type, IdlUnion)):
            return InstanceMachine(_type)
        elif get_origin(_type) == list:
            return SequenceMachine(
                cls._machine_for_type(get_args(_type)[0])
            )
        elif get_origin(_type) == dict:
            return MappingMachine(
                cls._machine_for_type(get_args(_type)[0]),
                cls._machine_for_type(get_args(_type)[1])
            )
        elif type(_type) == str:
            try:
                rname, rmodule = _type[::-1].split(".", 1)
                name, module = rname[::-1], rmodule[::-1]
                pymodule = import_module(module)
                return cls._machine_for_type(getattr(pymodule, name))
            except:
                pass

        raise TypeError(f"{repr(_type)} {get_origin(_type)} {get_args(_type)} is not valid in IDL classes because it cannot be encoded.")

    @classmethod
    def _machine_struct(cls, struct: Type[IdlStruct]):
        fields = get_type_hints(struct, include_extras=True)

        keylist = struct.__idl_annotations__.get("keylist")
        if not keylist:
            keylist = []
            for name, annotations in struct.__idl_field_annotations__.items():
                if "key" in annotations:
                    keylist.append(name)

            if not keylist:
                keylist = None

        members = {
            name: cls._machine_for_type(field_type)
            for name, field_type in fields.items()
        }
        return StructMachine(struct, members, keylist)

    @classmethod
    def _machine_union(cls, union: Type[IdlUnion]):
        discriminator = cls._machine_for_type(union.__idl_discriminator__)
        cases = {
            label: cls._machine_for_type(case_type)
            for label, (_, case_type) in union.__idl_cases__.items()
        }
        default = cls._machine_for_type(union.__idl_default__[1]) if union.__idl_default__ else None
        return UnionMachine(union, discriminator, cases, default)


    @classmethod
    def build_machines(cls, _type):
        if issubclass(_type, IdlUnion):
            machine = cls._machine_union(_type)
            keyless = False
        elif issubclass(_type, IdlStruct):
            machine = cls._machine_struct(_type)
            keyless = machine.keylist is None
        else:
            raise Exception(f"Cannot build for {_type}, not struct or union.")

        if not keyless:
            finder = MaxSizeFinder()
            machine.max_key_size(finder)
            size = finder.size
        else:
            size = 0

        return machine, keyless, size
