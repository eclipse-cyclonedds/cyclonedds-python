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
from inspect import isclass
from typing import Tuple, Type, Union

from . import IdlStruct, IdlUnion, IdlBitmask
from ._type_helper import get_origin, get_args
from ._type_normalize import get_idl_annotations, get_idl_field_annotations, get_extended_type_hints, WrapOpt
from ._machinery import Machine, NoneMachine, PrimitiveMachine, StringMachine, BytesMachine, ByteArrayMachine, UnionMachine, \
    ArrayMachine, SequenceMachine, InstanceMachine, MappingMachine, EnumMachine, StructMachine, OptionalMachine, CharMachine, \
    PLCdrMutableStructMachine, DelimitedCdrAppendableStructMachine, MutableMember, DelimitedCdrAppendableUnionMachine, \
    PlainCdrV2ArrayOfPrimitiveMachine, PlainCdrV2SequenceOfPrimitiveMachine, LenType, BitMaskMachine, BitBoundEnumMachine

from .types import array, bounded_str, sequence, _type_code_align_size_default_mapping, NoneType, char, typedef, uint8, \
    case, default


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
    def _machine_for_type(cls, _type, add_size_header):
        if _type in cls.easy_types:
            return cls.easy_types[_type]()
        elif _type in _type_code_align_size_default_mapping:
            return PrimitiveMachine(_type)
        elif isinstance(_type, WrapOpt):
            return OptionalMachine(cls._machine_for_type(_type.inner, add_size_header))
        elif isclass(_type) and issubclass(_type, Enum):
            if "bit_bound" in get_idl_annotations(_type) and add_size_header:
                return BitBoundEnumMachine(_type, get_idl_annotations(_type)["bit_bound"])
            return EnumMachine(_type)
        elif isclass(_type) and (issubclass(_type, IdlStruct) or issubclass(_type, IdlUnion)):
            return InstanceMachine(_type)
        elif isclass(_type) and (issubclass(_type, IdlBitmask)):
            return BitMaskMachine(_type, get_idl_annotations(_type)["bit_bound"])
        elif get_origin(_type) == list:
            return SequenceMachine(
                cls._machine_for_type(get_args(_type)[0], add_size_header),
                add_size_header=add_size_header
            )
        elif get_origin(_type) == dict:
            return MappingMachine(
                cls._machine_for_type(get_args(_type)[0], add_size_header),
                cls._machine_for_type(get_args(_type)[1], add_size_header)
            )
        elif isinstance(_type, typedef):
            return cls._machine_for_type(_type.subtype, add_size_header)
        elif isinstance(_type, array):
            submachine = cls._machine_for_type(_type.subtype, add_size_header)

            if isinstance(submachine, PrimitiveMachine):
                if submachine.type == uint8:
                    return ByteArrayMachine(_type.length)

                return PlainCdrV2ArrayOfPrimitiveMachine(submachine.type, _type.length)

            asubmachine = submachine
            while isinstance(asubmachine, ArrayMachine):
                asubmachine.add_size_header = False
                asubmachine = asubmachine.submachine

            # TODO: remove Enum and Bitmask here when C also has those
            if isinstance(asubmachine, (ByteArrayMachine, PlainCdrV2ArrayOfPrimitiveMachine, CharMachine, EnumMachine, BitBoundEnumMachine, BitMaskMachine)):
                add_size_header = False

            return ArrayMachine(
                submachine,
                size=_type.length,
                add_size_header=add_size_header
            )
        elif isinstance(_type, sequence):
            submachine = cls._machine_for_type(_type.subtype, add_size_header)

            if isinstance(submachine, PrimitiveMachine):
                return PlainCdrV2SequenceOfPrimitiveMachine(submachine.type, max_length=_type.max_length)

            # TODO: remove Enum and Bitmask here when C also has those
            if isinstance(submachine, (CharMachine, EnumMachine, BitBoundEnumMachine, BitMaskMachine)):
                add_size_header = False

            return SequenceMachine(
                submachine,
                maxlen=_type.max_length,
                add_size_header=add_size_header
            )
        elif isinstance(_type, bounded_str):
            return StringMachine(
                bound=_type.max_length
            )

        raise TypeError(f"{_type} is not valid in IDL classes because it cannot be encoded.")

    @classmethod
    def _machine_struct(cls, struct: Type[IdlStruct]) -> Tuple[Machine, bool]:
        fields = get_extended_type_hints(struct)
        annotations = get_idl_annotations(struct)
        field_annotations = get_idl_field_annotations(struct)

        use_version_2 = annotations.get('xcdrv2', False)

        keylist = annotations.get("keylist")
        if not keylist:
            keylist = []
            for name, f_annotations in field_annotations.items():
                if "key" in f_annotations:
                    keylist.append(name)

            if not keylist:
                keylist = None

        keyless = keylist is None or len(keylist) == 0

        extensibility = annotations.get("extensibility")

        members = {
            name: cls._machine_for_type(field_type, use_version_2)
            for name, field_type in fields.items()
        }

        if extensibility:
            if extensibility == "appendable":
                return DelimitedCdrAppendableStructMachine(
                    struct, members, keylist
                ), keyless
            elif extensibility == "mutable":
                mutablemembers = []

                for name, machine in members.items():
                    optional = False
                    if isinstance(machine, OptionalMachine):
                        optional = True
                        machine = machine.submachine

                    lentype = None
                    if isinstance(machine, PrimitiveMachine):
                        lentype = {
                            1: LenType.OneByte,
                            2: LenType.TwoByte,
                            4: LenType.FourByte,
                            8: LenType.EightByte
                        }[machine.size]
                    elif isinstance(machine, PlainCdrV2SequenceOfPrimitiveMachine):
                        if machine.size == 1:
                            lentype = LenType.NextIntDualUseLen
                        elif machine.size == 4:
                            lentype = LenType.NextIntDualUse4Len
                        elif machine.size == 8:
                            lentype = LenType.NextIntDualUse8Len
                        else:
                            lentype = LenType.NextIntLen
                    elif isinstance(machine, SequenceMachine):
                        lentype = LenType.NextIntDualUseLen
                    else:
                        lentype = LenType.NextIntLen

                    mutablemembers.append(MutableMember(
                        name=name,
                        key=not keylist or name in keylist,
                        optional=optional,
                        lentype=lentype,
                        must_understand=field_annotations.get(name, {}).get("must_understand", False),
                        memberid=struct.__idl__.get_member_id(name),
                        machine=machine
                    ))

                return PLCdrMutableStructMachine(
                    struct, mutablemembers
                ), keyless

        return StructMachine(struct, members, keylist), keyless

    @classmethod
    def _machine_union(cls, union: Type[IdlUnion]):
        annotations = get_idl_annotations(union)
        extensibility = annotations.get("extensibility")
        use_version_2 = annotations.get('xcdrv2', False)

        cases = {}
        _default = None
        for _case in get_extended_type_hints(union).values():
            if isinstance(_case, default):
                _default = cls._machine_for_type(_case.subtype, use_version_2)
                continue

            if not isinstance(_case, case):
                continue

            for label in _case.labels:
                cases[label] = cls._machine_for_type(_case.subtype, use_version_2)

        discriminator = cls._machine_for_type(union.__idl_discriminator__, use_version_2)

        if extensibility is None or extensibility == "final":
            return UnionMachine(union, discriminator, cases, _default)

        elif extensibility == "appendable":
            return DelimitedCdrAppendableUnionMachine(union, discriminator, cases, _default)
        else:
            # mutable
            raise NotImplementedError()

    @classmethod
    def build_machines(cls, _type):
        if issubclass(_type, IdlUnion):
            machine = cls._machine_union(_type)
            keyless = False
        elif issubclass(_type, IdlStruct):
            machine, keyless = cls._machine_struct(_type)
        else:
            raise Exception(f"Cannot build for {_type}, not struct or union.")

        return machine, keyless
