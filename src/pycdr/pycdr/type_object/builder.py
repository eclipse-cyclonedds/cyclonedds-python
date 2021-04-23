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

from .idl_entities import CompleteStructType, CompleteTypeDetail, CompleteTypeObject, EK_BOTH, EK_COMPLETE, IS_AUTOID_HASH, \
    IS_NESTED, PlainSequenceSElemDefn, TK_NONE, TypeObject, CompleteStructMember, EK_MINIMAL, CommonStructMember, \
    CompleteMemberDetail, CompleteStructHeader, PlainSequenceLElemDefn, PlainCollectionHeader, PlainArrayLElemDefn, \
    PlainArraySElemDefn, StringSTypeDefn, StringLTypeDefn, TypeIdentifier, IS_FINAL, IS_APPENDABLE, IS_MUTABLE, \
    TypeObjectContainer

from dataclasses import fields, is_dataclass
from enum import Enum
from pycdr.types import char, wchar, int8, int16, int32, int64, uint8, uint16, uint32, uint64, float32, float64, \
    ArrayHolder, BoundStringHolder, IdlUnion, SequenceHolder
from pycdr.type_helper import Annotated, get_origin, get_args
from pycdr.main import CDR
from hashlib import md5
from inspect import isclass

from .idl_entities import TK_BOOLEAN, TK_BYTE, TK_INT16, TK_INT32, TK_INT64, TK_UINT16, TK_UINT32, TK_UINT64, TK_FLOAT32, \
    TK_FLOAT64, TK_CHAR8, TK_CHAR16
from .util import uint32_max, uint8_max


class TypeObjectBuilder:
    def __init__(self):
        self.type_objects_minimal = {}
        self._hash_of_minimal = {}
        self.type_objects_complete = {}
        self._hash_of_complete = {}

        self.simple_types = {
            bool: TK_BOOLEAN,
            int: TK_INT64,
            float: TK_FLOAT64,
            char: TK_CHAR8,
            wchar: TK_CHAR16,
            int8: TK_CHAR8,
            int16: TK_INT16,
            int32: TK_INT32,
            int64: TK_INT64,
            uint8: TK_BYTE,
            uint16: TK_UINT16,
            uint32: TK_UINT32,
            uint64: TK_UINT64,
            float32: TK_FLOAT32,
            float64: TK_FLOAT64
        }

    def simple_types_only(self, _type):
        if _type in self.simple_types.keys():
            return True
        if _type is str:
            return True
        if get_origin(_type) == Annotated:
            _, holder = get_args(_type)
            if isinstance(holder, ArrayHolder) or isinstance(holder, SequenceHolder):
                return self.simple_types_only(holder.type)
            elif isinstance(holder, BoundStringHolder):
                return True
        return False

    def type_identifier_sequence_of(self, _type, bound, minimal):
        equiv_kind = EK_BOTH if self.simple_types_only(_type) else (EK_MINIMAL if minimal else EK_COMPLETE)

        if bound <= uint8_max:
            return TypeIdentifier(seq_sdefn=PlainSequenceSElemDefn(
                header=PlainCollectionHeader(
                    equiv_kind=equiv_kind,
                    element_flags=0,  # TODO
                ),
                bound=bound,
                element_identifier=self.type_identifier_resolve(_type, minimal)
            ))
        else:
            return TypeIdentifier(seq_ldefn=PlainSequenceLElemDefn(
                header=PlainCollectionHeader(
                    equiv_kind=equiv_kind,
                    element_flags=0,  # TODO
                ),
                bound=bound,
                element_identifier=self.type_identifier_resolve(_type, minimal)
            ))

    def type_identifier_array_of(self, _type, bound, minimal):
        equiv_kind = EK_BOTH if self.simple_types_only(_type) else (EK_MINIMAL if minimal else EK_COMPLETE)

        if bound <= uint8_max:
            return TypeIdentifier(array_sdefn=PlainArraySElemDefn(
                header=PlainCollectionHeader(
                    equiv_kind=equiv_kind,
                    element_flags=0,  # TODO
                ),
                array_bound_seq=[bound],
                element_identifier=self.type_identifier_resolve(_type, minimal)
            ))
        else:
            return TypeIdentifier(array_ldefn=PlainArrayLElemDefn(
                header=PlainCollectionHeader(
                    equiv_kind=equiv_kind,
                    element_flags=0,  # TODO
                ),
                array_bound_seq=[bound],
                element_identifier=self.type_identifier_resolve(_type, minimal)
            ))

    def type_identifier_string(self, bound):
        if bound <= uint8_max:
            return TypeIdentifier(string_sdefn=StringSTypeDefn(bound=bound))
        else:
            return TypeIdentifier(string_ldefn=StringLTypeDefn(bound=bound))

    def type_identifier_resolve(self, _type, minimal):
        if _type in self.simple_types:
            return TypeIdentifier(discriminator=self.simple_types[_type])
        elif _type is str:
            return self.type_identifier_string(uint32_max)
        elif get_origin(_type) == Annotated:
            _, holder = get_args(_type)
            if isinstance(holder, ArrayHolder):
                return self.type_identifier_array_of(holder.type, holder.length, minimal)
            elif isinstance(holder, SequenceHolder):
                return self.type_identifier_sequence_of(holder.type, holder.max_length or uint32_max, minimal)
            elif isinstance(holder, BoundStringHolder):
                return self.type_identifier_string(holder.max_length)
        else:
            print(_type)
            return TypeIdentifier(
                discriminator=EK_MINIMAL if minimal else EK_COMPLETE,
                value=self.hash_of(_type, minimal)
            )

    def register_typeobj(self, datatype, typeobj, minimal):
        data = TypeObjectContainer(type_object=typeobj).serialize()

        f = md5()
        f.update(data)
        hash = f.digest()[:14]

        if minimal:
            self.type_objects_minimal[hash] = typeobj
            self._hash_of_minimal[id(datatype)] = hash
        else:
            self.type_objects_complete[hash] = typeobj
            self._hash_of_complete[id(datatype)] = hash

    def hash_of(self, datatype, minimal):
        if minimal:
            if id(datatype) in self._hash_of_minimal:
                return self._hash_of_minimal[id(datatype)]

            self.to_typeobject(datatype, minimal)
            return self._hash_of_minimal[id(datatype)]
        else:
            if id(datatype) in self._hash_of_complete:
                return self._hash_of_complete[id(datatype)]

            self.to_typeobject(datatype, minimal)
            return self._hash_of_complete[id(datatype)]

    def struct_to_typeobject_complete(self, struct):
        members = []
        member_id = 0
        for field in fields(struct):
            members.append(CompleteStructMember(
                common=CommonStructMember(
                    member_id=member_id,
                    member_flags=0,   # TODO
                    member_type_id=self.type_identifier_resolve(field.type, False)
                ),
                detail=CompleteMemberDetail(
                    name=field.name,
                    ann_builtin=None,  # TODO
                    ann_custom=[]   # TODO
                )
            ))
            member_id += 1

        typeobj = TypeObject(
            complete=CompleteTypeObject(
                struct_type=CompleteStructType(
                    struct_flags=(IS_FINAL if struct.cdr.final else 0) |
                                 (IS_MUTABLE if struct.cdr.mutable else 0) |
                                 (IS_APPENDABLE if struct.cdr.appendable else 0) |
                                 (IS_NESTED if struct.cdr.nested else 0) |
                                 (IS_AUTOID_HASH if struct.cdr.autoid_hash else 0),
                    header=CompleteStructHeader(
                        base_type=(
                            self.type_identifier_resolve(struct.__base__, False) if struct.__base__ != object
                            else TypeIdentifier(discriminator=TK_NONE)
                        ),
                        detail=CompleteTypeDetail(
                            ann_builtin=None,  # TODO
                            ann_custom=[],   # TODO
                            type_name=struct.cdr.typename
                        )
                    ),
                    member_seq=members
                )
            )
        )

        self.register_typeobj(struct, typeobj, False)
        return typeobj

    def to_typeobject(self, _type, minimal=False):
        if isclass(_type) and issubclass(_type, IdlUnion):
            return self.union_to_typeobject(_type)
        elif isinstance(_type, Enum):
            return self.enum_to_typeobject(_type)
        elif is_dataclass(_type) and hasattr(_type, 'cdr') and isinstance(_type.cdr, CDR):
            return self.struct_to_typeobject_complete(_type)
        raise Exception(f"Can't convert object {object} to typeobject")
