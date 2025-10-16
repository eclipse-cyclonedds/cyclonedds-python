"""
 * Copyright(c) 2021 to 2022 ZettaScale Technology and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
"""

from enum import Enum, IntFlag, auto
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
    byte, case, default

from ._support import DataRepresentationFlags, DataTypeProperties

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
    def _scan_for_data_type_props(cls, _type, done) -> int:
        if id(_type) in done:
            return 0
        done.add(id(_type))

        # KEY is set by the caller
        if isinstance(_type, WrapOpt):
            return DataTypeProperties.DEFAULTS_TO_XCDR2 | cls._scan_for_data_type_props(_type.inner, done)
        elif isinstance(_type, typedef):
            return cls._scan_for_data_type_props(_type.subtype, done)
        elif isinstance(_type, sequence):
            return cls._scan_for_data_type_props(_type.subtype, done)
        elif isinstance(_type, array):
            return cls._scan_for_data_type_props(_type.subtype, done)
        elif get_origin(_type) == list:
            return cls._scan_for_data_type_props(get_args(_type)[0], done)
        elif get_origin(_type) == dict:
            # Maps not supported in the core yet, there's no CONTAINS_MAP bit
            return cls._scan_for_data_type_props(get_args(_type)[0], done) | cls._scan_for_data_type_props(get_args(_type)[1], done)
        elif isclass(_type) and issubclass(_type, IdlStruct):
            fields = get_extended_type_hints(_type)
            annotations = get_idl_annotations(_type)
            props = 0

            # Explicit setter
            if 'xcdrv2' in annotations:
                if annotations['xcdrv2']:
                    props |= DataTypeProperties.DISALLOWS_XCDR1
                else:
                    props |= DataTypeProperties.DISALLOWS_XCDR2
            if 'extensibility' in annotations and annotations['extensibility'] in ['appendable', 'mutable']:
                props |= DataTypeProperties.DEFAULTS_TO_XCDR2

            # Check for optionals or nested mutable/appendable
            for _, _ftype in fields.items():
                props |= cls._scan_for_data_type_props(_ftype, done)
            return props
        elif isclass(_type) and issubclass(_type, IdlUnion):
            fields = get_extended_type_hints(_type)
            annotations = get_idl_annotations(_type)
            props = 0

            # Explicit setter
            if 'xcdrv2' in annotations:
                if annotations['xcdrv2']:
                    props |= DataTypeProperties.DISALLOWS_XCDR1
                else:
                    props |= DataTypeProperties.DISALLOWS_XCDR2
            if 'extensibility' in annotations and annotations['extensibility'] in ['appendable', 'mutable']:
                props |= DataTypeProperties.DEFAULTS_TO_XCDR2

            for _, _ftype in fields.items():
                props |= cls._scan_for_data_type_props(_ftype.subtype, done)
            return props
        return 0

    # memberid is needed for XCDR1 optionals
    @classmethod
    def _machine_for_type(cls, _type, memberid_muflag, add_size_header, use_version_2):
        if _type in cls.easy_types:
            return cls.easy_types[_type]()
        elif _type in _type_code_align_size_default_mapping:
            return PrimitiveMachine(_type)
        elif isinstance(_type, WrapOpt):
            return OptionalMachine(cls._machine_for_type(_type.inner, None, add_size_header, use_version_2), memberid_muflag, use_version_2)
        elif isclass(_type) and issubclass(_type, Enum):
            if "bit_bound" in get_idl_annotations(_type) and use_version_2:
                return BitBoundEnumMachine(_type, get_idl_annotations(_type)["bit_bound"])
            return EnumMachine(_type)
        elif isclass(_type) and (issubclass(_type, IdlStruct) or issubclass(_type, IdlUnion)):
            return InstanceMachine(_type, use_version_2)
        elif isclass(_type) and (issubclass(_type, IdlBitmask)):
            return BitMaskMachine(_type, get_idl_annotations(_type)["bit_bound"])
        elif get_origin(_type) == list:
            return SequenceMachine(
                cls._machine_for_type(get_args(_type)[0], None, add_size_header, use_version_2),
                add_size_header=add_size_header
            )
        elif get_origin(_type) == dict:
            return MappingMachine(
                cls._machine_for_type(get_args(_type)[0], None, add_size_header, use_version_2),
                cls._machine_for_type(get_args(_type)[1], None, add_size_header, use_version_2)
            )
        elif isinstance(_type, typedef):
            return cls._machine_for_type(_type.subtype, memberid_muflag, add_size_header, use_version_2)
        elif isinstance(_type, array):
            submachine = cls._machine_for_type(_type.subtype, None, add_size_header, use_version_2)

            if isinstance(submachine, PrimitiveMachine):
                if submachine.type == uint8 or submachine.type == byte:
                    return ByteArrayMachine(_type.length)

                return PlainCdrV2ArrayOfPrimitiveMachine(submachine.type, _type.length)

            asubmachine = submachine
            while isinstance(asubmachine, ArrayMachine):
                asubmachine.add_size_header = False
                asubmachine = asubmachine.submachine

            if isinstance(asubmachine, (ByteArrayMachine, PlainCdrV2ArrayOfPrimitiveMachine, CharMachine)):
                add_size_header = False

            return ArrayMachine(
                submachine,
                size=_type.length,
                add_size_header=add_size_header
            )
        elif isinstance(_type, sequence):
            submachine = cls._machine_for_type(_type.subtype, None, add_size_header, use_version_2)

            if isinstance(submachine, PrimitiveMachine):
                return PlainCdrV2SequenceOfPrimitiveMachine(submachine.type, max_length=_type.max_length)

            if isinstance(submachine, (CharMachine)):
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
    def _get_xcdrv2_lentype(cls, machine: Machine) -> LenType:
        lentype = None
        if (isinstance(machine, PrimitiveMachine)
            or isinstance(machine, BitBoundEnumMachine)
            or isinstance(machine, BitMaskMachine)):
            lentype = {
                1: LenType.OneByte,
                2: LenType.TwoByte,
                4: LenType.FourByte,
                8: LenType.EightByte
            }[machine.size]
        elif isinstance(machine, CharMachine):
            lentype = LenType.OneByte
        elif isinstance(machine, EnumMachine):
            lentype = LenType.FourByte
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
        elif isinstance(machine, ArrayMachine):
            lentype = LenType.NextIntDualUseLen if machine.add_size_header else LenType.NextIntLen
        elif isinstance(machine, StringMachine):
            lentype = LenType.NextIntDualUseLen
        else:
            lentype = LenType.NextIntLen
        return lentype

    @classmethod
    def _machine_struct(cls, struct: Type[IdlStruct]) -> Tuple[Machine, bool]:
        fields = get_extended_type_hints(struct)
        annotations = get_idl_annotations(struct)
        field_annotations = get_idl_field_annotations(struct)

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

        for name, field_type in fields.items():
            assert struct.__idl__.get_member_id(name) >= 0

        v1_members = {}
        v2_members = {}
        for name, field_type in fields.items():
            mu = field_annotations.get(name, {}).get("must_understand", False)
            mid_mu = struct.__idl__.get_member_id(name) | ((1 << 31) if mu else 0)
            v1_members[name] = cls._machine_for_type(field_type, mid_mu, False, False)
            v2_members[name] = cls._machine_for_type(field_type, mid_mu, True, True)

        if extensibility is None:
            extensibility = "final"

        if extensibility == "final":
            v1_machine = StructMachine(struct, v1_members, keylist)
            v2_machine = StructMachine(struct, v2_members, keylist)
        elif extensibility == "appendable":
            v1_machine = StructMachine(struct, v1_members, keylist)
            v2_machine = DelimitedCdrAppendableStructMachine(struct, v2_members, keylist)
        elif extensibility == "mutable":
            v1_mutablemembers = []
            v2_mutablemembers = []

            for name, machine in v1_members.items():
                optional = False
                if isinstance(machine, OptionalMachine):
                    optional = True
                    machine = machine.submachine
                v1_mutablemembers.append(MutableMember(
                    name=name,
                    key=keylist and name in keylist,
                    optional=optional,
                    lentype=LenType.NextIntLen,
                    must_understand=field_annotations.get(name, {}).get("must_understand", False),
                    memberid=struct.__idl__.get_member_id(name),
                    machine=machine))
            v1_machine = PLCdrMutableStructMachine(struct, v1_mutablemembers, False)

            for name, machine in v2_members.items():
                optional = False
                if isinstance(machine, OptionalMachine):
                    optional = True
                    machine = machine.submachine
                v2_mutablemembers.append(MutableMember(
                    name=name,
                    key=keylist and name in keylist,
                    optional=optional,
                    lentype=cls._get_xcdrv2_lentype(machine),
                    must_understand=field_annotations.get(name, {}).get("must_understand", False),
                    memberid=struct.__idl__.get_member_id(name),
                    machine=machine))
            v2_machine = PLCdrMutableStructMachine(struct, v2_mutablemembers, True)

        return v1_machine, v2_machine, keyless

    @classmethod
    def _machine_union(cls, union: Type[IdlUnion]):
        annotations = get_idl_annotations(union)
        extensibility = annotations.get("extensibility")

        v1_cases = {}
        v2_cases = {}
        v1_default = None
        v2_default = None

        for _case in get_extended_type_hints(union).values():
            if isinstance(_case, default):
                v1_default = cls._machine_for_type(_case.subtype, None, False, False)
                v2_default = cls._machine_for_type(_case.subtype, None, True, True)
                continue

            if not isinstance(_case, case):
                continue

            v1_machine = cls._machine_for_type(_case.subtype, None, False, False)
            v2_machine = cls._machine_for_type(_case.subtype, None, True, True)

            for label in _case.labels:
                v1_cases[label] = v1_machine
                v2_cases[label] = v2_machine

        v1_discriminator = cls._machine_for_type(union.__idl_discriminator__, None, False, False)
        v2_discriminator = cls._machine_for_type(union.__idl_discriminator__, None, True, True)

        v1_machine = UnionMachine(union, v1_discriminator, v1_cases, v1_default)

        if extensibility is None or extensibility == "final":
            v2_machine = UnionMachine(union, v2_discriminator, v2_cases, v2_default)

        elif extensibility == "appendable":
            v2_machine = DelimitedCdrAppendableUnionMachine(union, v2_discriminator, v2_cases, v2_default)
        else:
            # mutable
            raise NotImplementedError()

        return v1_machine, v2_machine

    @classmethod
    def build_machines(cls, _type):
        if issubclass(_type, IdlUnion):
            v1_machine, v2_machine = cls._machine_union(_type)
            keyless = False
        elif issubclass(_type, IdlStruct):
            v1_machine, v2_machine, keyless = cls._machine_struct(_type)
        else:
            raise Exception(f"Cannot build for {_type}, not struct or union.")

        data_type_props = cls._scan_for_data_type_props(_type, set())
        if not keyless:
            data_type_props |= DataTypeProperties.CONTAINS_KEY

        supported_versions = DataRepresentationFlags.FLAG_XCDR1 | DataRepresentationFlags.FLAG_XCDR2
        if data_type_props & DataTypeProperties.DISALLOWS_XCDR1:
            supported_versions &= ~DataRepresentationFlags.FLAG_XCDR1
        if data_type_props & DataTypeProperties.DISALLOWS_XCDR2:
            supported_versions &= ~DataRepresentationFlags.FLAG_XCDR2
        if supported_versions == 0:
            raise Exception("Mutually incompatible restrictions on type")

        data_type_props &= ~DataTypeProperties.PYTHON_FLAGS_MASK
        if (data_type_props & DataTypeProperties.DEFAULTS_TO_XCDR2) != 0:
            default_version = 2 if supported_versions & DataRepresentationFlags.FLAG_XCDR2 else 1
        else:
            default_version = 1 if supported_versions & DataRepresentationFlags.FLAG_XCDR1 else 2        

        return v1_machine, v2_machine, data_type_props, supported_versions, default_version
