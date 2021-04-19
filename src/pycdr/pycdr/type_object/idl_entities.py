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

from pycdr import cdr
from pycdr.types import uint8, uint16, uint32, uint64, int16, int32, int64, float32, float64, char, \
    union, sequence, array, bound_str, default, case, optional, NoneType


TI_STRING8_SMALL = 0x70
TI_STRING8_LARGE = 0x71
TI_STRING16_SMALL = 0x72
TI_STRING16_LARGE = 0x73
TI_PLAIN_SEQUENCE_SMALL = 0x80
TI_PLAIN_SEQUENCE_LARGE = 0x81
TI_PLAIN_ARRAY_SMALL = 0x90
TI_PLAIN_ARRAY_LARGE = 0x91
TI_PLAIN_MAP_SMALL = 0xA0
TI_PLAIN_MAP_LARGE = 0xA1
TI_STRONGLY_CONNECTED_COMPONENT = 0xB0


# Primitive TKs
TK_NONE = 0x00
TK_BOOLEAN = 0x01
TK_BYTE = 0x02
TK_INT16 = 0x03
TK_INT32 = 0x04
TK_INT64 = 0x05
TK_UINT16 = 0x06
TK_UINT32 = 0x07
TK_UINT64 = 0x08
TK_FLOAT32 = 0x09
TK_FLOAT64 = 0x0A
TK_FLOAT128 = 0x0B
TK_CHAR8 = 0x10
TK_CHAR16 = 0x11

# String TKs
TK_STRING8 = 0x20
TK_STRING16 = 0x21

# Constructed/Named types
TK_ALIAS = 0x30

# Enumerated TKs
TK_ENUM = 0x40
TK_BITMASK = 0x41

# Structured TKs
TK_ANNOTATION = 0x50
TK_STRUCTURE = 0x51
TK_UNION = 0x52
TK_BITSET = 0x53

# Collection TKs
TK_SEQUENCE = 0x60
TK_ARRAY = 0x61
TK_MAP = 0x62


@cdr
class NameHash:
    hash: array[uint8, 4]


# @bit_bound(16)
# bitmask TypeFlag {
#     @position(0) IS_FINAL,        # F |
#     @position(1) IS_APPENDABLE,   # A |-  Struct, Union
#     @position(2) IS_MUTABLE,      # M |   (exactly one flag)
#     @position(3) IS_NESTED,       # N     Struct, Union
#     @position(4) IS_AUTOID_HASH   # H     Struct
# };

IS_FINAL = (1 << 0)
IS_APPENDABLE = (1 << 1)
IS_MUTABLE = (1 << 2)
IS_NESTED = (1 << 3)
IS_AUTOID_HASH = (1 << 4)

TypeFlag = uint16  # typedef

StructTypeFlag = TypeFlag  # All flags apply
UnionTypeFlag = TypeFlag  # All flags apply
CollectionTypeFlag = TypeFlag  # Unused. No flags apply
AnnotationTypeFlag = TypeFlag  # Unused. No flags apply
AliasTypeFlag = TypeFlag  # Unused. No flags apply
EnumTypeFlag = TypeFlag  # Unused. No flags apply
BitmaskTypeFlag = TypeFlag  # Unused. No flags apply
BitsetTypeFlag = TypeFlag  # Unused. No flags apply


SBound = uint8
SBoundSeq = sequence[SBound]
INVALID_SBOUND: SBound = 0


LBound = uint32
LBoundSeq = sequence[LBound]
INVALID_LBOUND: LBound = 0

EquivalenceHash = array[uint8, 14]


# @extensibility(FINAL) @nested
# union TypeObjectHashId switch (octet) {
#     case EK_COMPLETE:
#     case EK_MINIMAL:
#         EquivalenceHash  hash;
# };

EquivalenceKind = uint8  # typedef
EK_MINIMAL: EquivalenceKind = 0xf1
EK_COMPLETE: EquivalenceKind = 0xf2
EK_BOTH: EquivalenceKind = 0xf3


@union(uint8)
class TypeObjectHashId:
    hash: case[[EK_MINIMAL, EK_COMPLETE], EquivalenceHash]


TypeKind = uint8  # typedef

# @ bit_bound(16)
# bitmask MemberFlag {
# @position(0)  TRY_CONSTRUCT1,     # T1 | 00 = INVALID, 01 = DISCARD
# @position(1)  TRY_CONSTRUCT2,     # T2 | 10 = USE_DEFAULT, 11 = TRIM
# @position(2)  IS_EXTERNAL,        # X  StructMember, UnionMember, CollectionElement
# @position(3)  IS_OPTIONAL,        # O  StructMember
# @position(4)  IS_MUST_UNDERSTAND, # M  StructMember
# @position(5)  IS_KEY,             # K  StructMember, UnionDiscriminator
# @position(6)  IS_DEFAULT          # D  UnionMember, EnumerationLiteral
# };

TRY_CONSTRUCT1 = (1 << 0)
TRY_CONSTRUCT2 = (1 << 1)
IS_EXTERNAL = (1 << 2)
IS_OPTIONAL = (1 << 3)
IS_MUST_UNDERSTAND = (1 << 4)
IS_KEY = (1 << 5)
IS_DEFAULT = (1 << 6)

MemberFlag = uint16  # typedef

CollectionElementFlag = MemberFlag  # T1, T2, X
StructMemberFlag = MemberFlag  # T1, T2, O, M, K, X
UnionMemberFlag = MemberFlag  # T1, T2, D, X
UnionDiscriminatorFlag = MemberFlag  # T1, T2, K
EnumeratedLiteralFlag = MemberFlag  # D
AnnotationParameterFlag = MemberFlag  # Unused. No flags apply
AliasMemberFlag = MemberFlag  # Unused. No flags apply
BitflagFlag = MemberFlag  # Unused. No flags apply
BitsetMemberFlag = MemberFlag  # Unused. No flags apply


# @ extensibility(FINAL) @ nested
# struct StringSTypeDefn {
# SBound                  bound;
# };
@cdr
class StringSTypeDefn:
    bound: SBound


# @ extensibility(FINAL) @ nested
# struct StringLTypeDefn {
# LBound                  bound;
# };
@cdr
class StringLTypeDefn:
    bound: LBound


# @ extensibility(FINAL) @ nested
# struct PlainCollectionHeader {
# EquivalenceKind        equiv_kind;
# CollectionElementFlag  element_flags;
# };
@cdr
class PlainCollectionHeader:
    equiv_kind: EquivalenceKind
    element_flags: CollectionElementFlag


# @ extensibility(FINAL) @ nested
# struct PlainSequenceSElemDefn {
# PlainCollectionHeader  header;
# SBound                 bound;
# @external TypeIdentifier element_identifier;
# };
@cdr
class PlainSequenceSElemDefn:
    header: PlainCollectionHeader
    bound: SBound
    element_identifier: 'TypeIdentifier'


# @ extensibility(FINAL) @ nested
# struct PlainSequenceLElemDefn {
# PlainCollectionHeader  header;
# LBound                 bound;
# @external TypeIdentifier element_identifier;
# };
@cdr
class PlainSequenceLElemDefn:
    header: PlainCollectionHeader
    bound: LBound
    element_identifier: 'TypeIdentifier'


# @ extensibility(FINAL) @ nested
# struct PlainArraySElemDefn {
# PlainCollectionHeader  header;
# SBoundSeq              array_bound_seq;
# @external TypeIdentifier element_identifier;
# };
@cdr
class PlainArraySElemDefn:
    header: PlainCollectionHeader
    array_bound_seq: SBoundSeq
    element_identifier: 'TypeIdentifier'


# @ extensibility(FINAL) @ nested
# struct PlainArrayLElemDefn {
# PlainCollectionHeader  header;
# LBoundSeq              array_bound_seq;
# @external TypeIdentifier element_identifier;
# };
@cdr
class PlainArrayLElemDefn:
    header: PlainCollectionHeader
    array_bound_seq: LBoundSeq
    element_identifier: 'TypeIdentifier'


# @ extensibility(FINAL) @ nested
# struct PlainMapSTypeDefn {
# PlainCollectionHeader  header;
# SBound                 bound;
# @external TypeIdentifier element_identifier;
# CollectionElementFlag  key_flags;
# @external TypeIdentifier key_identifier;
# };
@cdr
class PlainMapSTypeDefn:
    header: PlainCollectionHeader
    bound: SBound
    element_identifier: 'TypeIdentifier'
    key_flags: CollectionElementFlag
    key_identifier: 'TypeIdentifier'


# @ extensibility(FINAL) @ nested
# struct PlainMapLTypeDefn {
# PlainCollectionHeader  header;
# LBound                 bound;
# @external TypeIdentifier element_identifier;
# CollectionElementFlag  key_flags;
# @external TypeIdentifier key_identifier;
# };
@cdr
class PlainMapLTypeDefn:
    header: PlainCollectionHeader
    bound: LBound
    element_identifier: 'TypeIdentifier'
    key_flags: CollectionElementFlag
    key_identifier: 'TypeIdentifier'


# # Used for Types that have cyclic depencencies with other types
# @ extensibility(APPENDABLE) @ nested
# struct StronglyConnectedComponentId {
# TypeObjectHashId sc_component_id; # Hash StronglyConnectedComponent
# long   scc_length; # StronglyConnectedComponent.length
# long   scc_index; # identify type in Strongly Connected Comp.
# };
@cdr
class StronglyConnectedComponentId:
    sc_component_id: TypeObjectHashId  # Hash StronglyConnectedComponent
    scc_length: int32  # StronglyConnectedComponent.length
    scc_index: int32  # identify type in Strongly Connected Comp.


# # Future extensibility
# @ extensibility(MUTABLE) @ nested
# struct ExtendedTypeDefn {
# # Empty. Available for future extension
# };
@cdr
class ExtendedTypeDefn:
    pass


# @ extensibility(FINAL) @ nested
# union TypeIdentifier switch(octet) {
# # == == == == == == Primitive types - use TypeKind == == == == ==
# # All primitive types fall here.
# # Commented-out because Unions cannot have cases with no member.
# /*
# case TK_NONE:
# case TK_BOOLEAN:
# case TK_BYTE_TYPE:
# case TK_INT16_TYPE:
# case TK_INT32_TYPE:
# case TK_INT64_TYPE:
# case TK_UINT8_TYPE:
# case TK_UINT16_TYPE:
# case TK_UINT32_TYPE:
# case TK_UINT64_TYPE:
# case TK_FLOAT32_TYPE:
# case TK_FLOAT64_TYPE:
# case TK_FLOAT128_TYPE:
# case TK_CHAR8_TYPE:
# case TK_CHAR16_TYPE:
# # No Value
# * /
# # == == == == == == Strings - use TypeIdentifierKind == == == ==
# case TI_STRING8_SMALL:
# case TI_STRING16_SMALL:
# StringSTypeDefn         string_sdefn;
# case TI_STRING8_LARGE:
# case TI_STRING16_LARGE:
# StringLTypeDefn         string_ldefn;
# # == == == == == == Plain collectios - use TypeIdentifierKind == == == == =
# case TI_PLAIN_SEQUENCE_SMALL:
# PlainSequenceSElemDefn  seq_sdefn;
# case TI_PLAIN_SEQUENCE_LARGE:
# PlainSequenceLElemDefn  seq_ldefn;
# case TI_PLAIN_ARRAY_SMALL:
# PlainArraySElemDefn     array_sdefn;
# case TI_PLAIN_ARRAY_LARGE:
# PlainArrayLElemDefn     array_ldefn;
# case TI_PLAIN_MAP_SMALL:
# PlainMapSTypeDefn       map_sdefn;
# case TI_PLAIN_MAP_LARGE:
# PlainMapLTypeDefn       map_ldefn;
# # == == == == == == Types that are mutually dependent on each other == =
# case TI_STRONGLY_CONNECTED_COMPONENT:
# StronglyConnectedComponentId  sc_component_id;
# # == == == == == == The remaining cases - use EquivalenceKind == == == == =
# case EK_COMPLETE:
# case EK_MINIMAL:
# EquivalenceHash         equivalence_hash;
# # == == == == == == == == == =  Future extensibility == == == == == ==
# # Future extensions
# default:
# ExtendedTypeDefn        extended_defn;
# };
@union(uint8)
class TypeIdentifier:
    # Note: this 'novalue' thing is actually not in the spec
    # However, I would argue the spec is wrong.
    novalue: case[
        [
            TK_NONE, TK_BOOLEAN, TK_BYTE, TK_INT16, TK_INT32,
            TK_INT64, TK_UINT16,  TK_UINT32, TK_UINT64,
            TK_FLOAT32, TK_FLOAT64, TK_CHAR8, TK_CHAR16
        ],
        NoneType
    ]
    string_sdefn: case[[TI_STRING8_SMALL, TI_STRING16_SMALL], StringSTypeDefn]
    string_ldefn: case[[TI_STRING8_LARGE, TI_STRING16_LARGE], StringLTypeDefn]
    seq_sdefn: case[TI_PLAIN_SEQUENCE_SMALL, PlainSequenceSElemDefn]
    seq_ldefn: case[TI_PLAIN_SEQUENCE_LARGE, PlainSequenceLElemDefn]
    array_sdefn: case[TI_PLAIN_ARRAY_SMALL, PlainArraySElemDefn]
    array_ldefn: case[TI_PLAIN_ARRAY_LARGE, PlainArrayLElemDefn]
    map_sdefn: case[TI_PLAIN_MAP_SMALL, PlainMapSTypeDefn]
    map_ldefn: case[TI_PLAIN_MAP_LARGE, PlainMapLTypeDefn]
    sc_component_id: case[TI_STRONGLY_CONNECTED_COMPONENT, StronglyConnectedComponentId]
    equivalence_hash: case[[EK_COMPLETE, EK_MINIMAL], EquivalenceHash]
    extended_defn: default[ExtendedTypeDefn]


TypeIdentifierSeq = sequence[TypeIdentifier]  # typedef

# # --- Annotation usage: ------

MemberId = uint32  # typedef

ANNOTATION_STR_VALUE_MAX_LEN = 128
ANNOTATION_SEC_VALUE_MAX_LEN = 128
MEMBER_NAME_MAX_LENGTH = 256
TYPE_NAME_MAX_LENGTH = 256

MemberName = bound_str[MEMBER_NAME_MAX_LENGTH]
QualifiedTypeName = bound_str[TYPE_NAME_MAX_LENGTH]


# @extensibility(MUTABLE) @nested
# struct ExtendedAnnotationParameterValue {
#     # Empty. Available for future extension
# };
@cdr
class ExtendedAnnotationParameterValue:
    pass


# /* Literal value of an annotation member: either the default value in its
#   * definition or the value applied in its usage.
#   */
# @extensibility(FINAL) @nested
# union AnnotationParameterValue switch (uint8_t) {
#     case TK_BOOLEAN:
#         boolean             boolean_value;
#     case TK_BYTE:
#         uint8_t               byte_value;
#     case TK_INT16:
#         short               int16_value;
#     case TK_UINT16:
#         unsigned short      uint16_value;
#     case TK_INT32:
#         long                int32_value;
#     case TK_UINT32:
#         unsigned long       uint32_value;
#     case TK_INT64:
#         long long           int64_value;
#     case TK_UINT64:
#         unsigned long long  uint64_value;
#     case TK_FLOAT32:
#         float               float32_value;
#     case TK_FLOAT64:
#         double              float64_value;
#     case TK_FLOAT128:
#         long double         float128_value;
#     case TK_CHAR8:
#         char                char_value;
#     case TK_CHAR16:
#         wchar               wchar_value;
#     case TK_ENUM:
#         long                enumerated_value;
#     case TK_STRING8:
#         string<ANNOTATION_STR_VALUE_MAX_LEN>  string8_value;
#     case TK_STRING16:
#         wstring<ANNOTATION_STR_VALUE_MAX_LEN> string16_value;
#     default:
#         ExtendedAnnotationParameterValue      extended_value;
# };
@union(uint8)
class AnnotationParameterValue:
    boolean_value: case[TK_BOOLEAN, bool]
    byte_value: case[TK_BYTE, uint8]
    int16_value: case[TK_INT16, int16]
    uint16_value: case[TK_UINT16, uint16]
    int32_value: case[TK_INT32, int32]
    uint32_value: case[TK_UINT32, uint32]
    int64_value: case[TK_INT64, int64]
    uint64_value: case[TK_UINT64, uint64]
    float32_value: case[TK_FLOAT32, float32]
    float64_value: case[TK_FLOAT64, float64]
    # Float128 not supported
    char_value: case[TK_CHAR8, char]
    # wchar not supported
    enum_value: case[TK_ENUM, int32]
    string_value: case[TK_STRING8, bound_str[ANNOTATION_STR_VALUE_MAX_LEN]]
    # string16 not supported
    extended_value: default[ExtendedAnnotationParameterValue]


# # The application of an annotation to some type or type member
# @extensibility(APPENDABLE) @nested
# struct AppliedAnnotationParameter {
#     NameHash                  paramname_hash;
#     AnnotationParameterValue  value;
# };
# # Sorted by AppliedAnnotationParameter.paramname_hash
# typedef sequence<AppliedAnnotationParameter> AppliedAnnotationParameterSeq;
@cdr
class AppliedAnnotationParameter:
    paramname_hash: NameHash
    value: AnnotationParameterValue


AppliedAnnotationParameterSeq = sequence[AppliedAnnotationParameter]


# @extensibility(APPENDABLE) @nested
# struct AppliedAnnotation {
#     TypeIdentifier                     annotation_typeid;
#     @optional AppliedAnnotationParameterSeq   param_seq;
# };
# # Sorted by AppliedAnnotation.annotation_typeid
# typedef sequence<AppliedAnnotation> AppliedAnnotationSeq;
@cdr
class AppliedAnnotation:
    annotation_typeid: TypeIdentifier
    param_seq: optional[AppliedAnnotationParameterSeq]


AppliedAnnotationSeq = sequence[AppliedAnnotation]


# # @verbatim(placement="<placement>", language="<lang>", text="<text>")
# @extensibility(FINAL) @nested
# struct AppliedVerbatimAnnotation {
#     string<32> placement;
#     string<32> language;
#     string     text;
# };
@cdr
class AppliedVerbatimAnnotation:
    placement: bound_str[32]
    language: bound_str[32]
    text: str


# # --- Aggregate types: ------------------------------------------------
# @extensibility(APPENDABLE) @nested
# struct AppliedBuiltinMemberAnnotations {
#     @optional string                  unit; # @unit("<unit>")
#     @optional AnnotationParameterValue min; # @min , @range
#     @optional AnnotationParameterValue max; # @max , @range
#     @optional string               hash_id; # @hash_id("<membername>")
# };
@cdr
class AppliedBuiltinMemberAnnotations:
    unit: optional[str]
    min: optional[AnnotationParameterValue]
    max: optional[AnnotationParameterValue]
    hash_id: optional[str]


# @extensibility(FINAL) @nested
# struct CommonStructMember {
#     MemberId                                   member_id;
#     StructMemberFlag                           member_flags;
#     TypeIdentifier                             member_type_id;
# };
@cdr
class CommonStructMember:
    member_id: MemberId
    member_flags: StructMemberFlag
    member_type_id: TypeIdentifier


# # COMPLETE Details for a member of an aggregate type
# @extensibility(FINAL) @nested
# struct CompleteMemberDetail {
#     MemberName                                 name;
#     @optional AppliedBuiltinMemberAnnotations  ann_builtin;
#     @optional AppliedAnnotationSeq             ann_custom;
# };
@cdr
class CompleteMemberDetail:
    name: MemberName
    ann_builtin: optional[AppliedBuiltinMemberAnnotations]
    ann_custom: optional[AppliedAnnotationSeq]


# # MINIMAL Details for a member of an aggregate type
# @extensibility(FINAL) @nested
# struct MinimalMemberDetail {
#     NameHash                                  name_hash;
# };
@cdr
class MinimalMemberDetail:
    name_hash: NameHash


# # Member of an aggregate type
# @extensibility(APPENDABLE) @nested
# struct CompleteStructMember {
#     CommonStructMember                         common;
#     CompleteMemberDetail                       detail;
# };
# # Ordered by the member_index
# typedef sequence<CompleteStructMember> CompleteStructMemberSeq;
@cdr
class CompleteStructMember:
    common: CommonStructMember
    detail: CompleteMemberDetail


CompleteStructMemberSeq = sequence[CompleteStructMember]


# # Member of an aggregate type
# @extensibility(APPENDABLE) @nested
# struct MinimalStructMember {
#     CommonStructMember                         common;
#     MinimalMemberDetail                        detail;
# };
# # Ordered by common.member_id
# typedef sequence<MinimalStructMember> MinimalStructMemberSeq;
@cdr
class MinimalStructMember:
    common: CommonStructMember
    detail: MinimalMemberDetail


MinimalStructMemberSeq = sequence[MinimalStructMember]


# @extensibility(APPENDABLE) @nested
# struct AppliedBuiltinTypeAnnotations {
#     @optional AppliedVerbatimAnnotation verbatim;  # @verbatim(...)
# };
@cdr
class AppliedBuiltinTypeAnnotations:
    verbatim: optional[AppliedVerbatimAnnotation]


# @extensibility(FINAL) @nested
# struct MinimalTypeDetail {
#     # Empty. Available for future extension
# };
@cdr
class MinimalTypeDetail:
    pass


# @extensibility(FINAL) @nested
# struct CompleteTypeDetail {
#       @optional AppliedBuiltinTypeAnnotations  ann_builtin;
#       @optional AppliedAnnotationSeq           ann_custom;
#       QualifiedTypeName                        type_name;
# };
@cdr
class CompleteTypeDetail:
    ann_builtin: AppliedBuiltinTypeAnnotations
    ann_custom: AppliedAnnotationSeq
    type_name: QualifiedTypeName


# @extensibility(APPENDABLE) @nested
# struct CompleteStructHeader {
#     TypeIdentifier                           base_type;
#     CompleteTypeDetail                       detail;
# };
@cdr
class CompleteStructHeader:
    base_type: TypeIdentifier
    detail: CompleteTypeDetail


# @extensibility(APPENDABLE) @nested
# struct MinimalStructHeader {
#     TypeIdentifier                           base_type;
#     MinimalTypeDetail                        detail;
# };
@cdr
class MinimalStructHeader:
    base_type: TypeIdentifier
    detail: MinimalTypeDetail


# @extensibility(FINAL) @nested
# struct CompleteStructType {
#     StructTypeFlag             struct_flags;
#     CompleteStructHeader       header;
#     CompleteStructMemberSeq    member_seq;
# };
@cdr
class CompleteStructType:
    struct_flags: StructTypeFlag
    header: CompleteStructHeader
    member_seq: CompleteStructMemberSeq


# @extensibility(FINAL) @nested
# struct MinimalStructType {
#     StructTypeFlag             struct_flags;
#     MinimalStructHeader        header;
#     MinimalStructMemberSeq     member_seq;
# };
@cdr
class MinimalStructType:
    struct_flags: StructTypeFlag
    header: MinimalStructHeader
    member_seq: MinimalStructMemberSeq


# # --- Union: ----------------------------------------------------------

# # Case labels that apply to a member of a union type
# # Ordered by their values
# typedef sequence<long> UnionCaseLabelSeq;
UnionCaseLabelSeq = sequence[int32]


# @extensibility(FINAL) @nested
# struct CommonUnionMember {
#     MemberId                    member_id;
#     UnionMemberFlag             member_flags;
#     TypeIdentifier              type_id;
#     UnionCaseLabelSeq           label_seq;
# };
@cdr
class CommonUnionMember:
    member_id: MemberId
    member_flags: UnionMemberFlag
    type_id: TypeIdentifier
    label_seq: UnionCaseLabelSeq


# # Member of a union type
# @extensibility(APPENDABLE) @nested
# struct CompleteUnionMember {
#     CommonUnionMember      common;
#     CompleteMemberDetail   detail;
# };
# # Ordered by member_index
# typedef sequence<CompleteUnionMember> CompleteUnionMemberSeq;
@cdr
class CompleteUnionMember:
    common: CommonUnionMember
    detail: CompleteMemberDetail


CompleteUnionMemberSeq = sequence[CompleteUnionMember]


# # Member of a union type
# @extensibility(APPENDABLE) @nested
# struct MinimalUnionMember {
#     CommonUnionMember   common;
#     MinimalMemberDetail detail;
# };
# # Ordered by MinimalUnionMember.common.member_id
# typedef sequence<MinimalUnionMember> MinimalUnionMemberSeq;
@cdr
class MinimalUnionMember:
    common: CommonUnionMember
    detail: MinimalMemberDetail


MinimalUnionMemberSeq = sequence[MinimalUnionMember]


# @extensibility(FINAL) @nested
# struct CommonDiscriminatorMember {
#     UnionDiscriminatorFlag       member_flags;
#     TypeIdentifier               type_id;
# };
@cdr
class CommonDiscriminatorMember:
    member_flags: UnionDiscriminatorFlag
    type_id: TypeIdentifier


# # Member of a union type
# @extensibility(APPENDABLE) @nested
# struct CompleteDiscriminatorMember {
#     CommonDiscriminatorMember                common;
#     @optional AppliedBuiltinTypeAnnotations  ann_builtin;
#     @optional AppliedAnnotationSeq           ann_custom;
# };
@cdr
class CompleteDiscriminatorMember:
    common: CommonDiscriminatorMember
    ann_builtin: AppliedBuiltinTypeAnnotations
    ann_custom: AppliedAnnotationSeq


# # Member of a union type
# @extensibility(APPENDABLE) @nested
# struct MinimalDiscriminatorMember {
#     CommonDiscriminatorMember   common;
# };
@cdr
class MinimalDiscriminatorMember:
    common: CommonDiscriminatorMember


# @extensibility(APPENDABLE) @nested
# struct CompleteUnionHeader {
#     CompleteTypeDetail          detail;
# };
@cdr
class CompleteUnionHeader:
    detail: CompleteTypeDetail


# @extensibility(APPENDABLE) @nested
# struct MinimalUnionHeader {
#     MinimalTypeDetail           detail;
# };
@cdr
class MinimalUnionHeader:
    detail: MinimalTypeDetail


# @extensibility(FINAL) @nested
# struct CompleteUnionType {
#     UnionTypeFlag                union_flags;
#     CompleteUnionHeader          header;
#     CompleteDiscriminatorMember  discriminator;
#     CompleteUnionMemberSeq       member_seq;
# };
@cdr
class CompleteUnionType:
    union_flags: UnionTypeFlag
    header: CompleteUnionHeader
    discriminator: CompleteDiscriminatorMember
    member_seq: CompleteUnionMemberSeq


# @extensibility(FINAL) @nested
# struct MinimalUnionType {
#     UnionTypeFlag                union_flags;
#     MinimalUnionHeader           header;
#     MinimalDiscriminatorMember   discriminator;
#     MinimalUnionMemberSeq        member_seq;
# };
@cdr
class MinimalUnionType:
    union_flags: UnionTypeFlag
    header: MinimalUnionHeader
    discriminator: MinimalDiscriminatorMember
    member_seq: MinimalUnionMemberSeq


# # --- Annotation: ----------------------------------------------------
# @extensibility(FINAL) @nested
# struct CommonAnnotationParameter {
#     AnnotationParameterFlag      member_flags;
#     TypeIdentifier               member_type_id;
# };
@cdr
class CommonAnnotationParameter:
    member_flags: AnnotationParameterFlag
    member_type_id: TypeIdentifier


# # Member of an annotation type
# @extensibility(APPENDABLE) @nested
# struct CompleteAnnotationParameter {
#     CommonAnnotationParameter  common;
#     MemberName                 name;
#     AnnotationParameterValue   default_value;
# };
# # Ordered by CompleteAnnotationParameter.name
# typedef
# sequence<CompleteAnnotationParameter> CompleteAnnotationParameterSeq;
@cdr
class CompleteAnnotationParameter:
    common: CommonAnnotationParameter
    name: MemberName
    default_value: AnnotationParameterValue


CompleteAnnotationParameterSeq = sequence[CompleteAnnotationParameter]


# @extensibility(APPENDABLE) @nested
# struct MinimalAnnotationParameter {
#     CommonAnnotationParameter  common;
#     NameHash                   name_hash;
#     AnnotationParameterValue   default_value;
# };
# # Ordered by MinimalAnnotationParameter.name_hash
# typedef
# sequence<MinimalAnnotationParameter> MinimalAnnotationParameterSeq;
@cdr
class MinimalAnnotationParameter:
    common: CommonAnnotationParameter
    name_hash: NameHash
    default_value: AnnotationParameterValue


MinimalAnnotationParameterSeq = sequence[MinimalAnnotationParameter]


# @extensibility(APPENDABLE) @nested
# struct CompleteAnnotationHeader {
#     QualifiedTypeName         annotation_name;
# };
@cdr
class CompleteAnnotationHeader:
    annotation_name: QualifiedTypeName


# @extensibility(APPENDABLE) @nested
# struct MinimalAnnotationHeader {
#     # Empty. Available for future extension
# };
@cdr
class MinimalAnnotationHeader:
    pass


# @extensibility(FINAL) @nested
# struct CompleteAnnotationType {
#     AnnotationTypeFlag             annotation_flag;
#     CompleteAnnotationHeader       header;
#     CompleteAnnotationParameterSeq member_seq;
# };
@cdr
class CompleteAnnotationType:
    annotation_flag: AnnotationTypeFlag
    header: CompleteAnnotationHeader
    member_seq: CompleteAnnotationParameterSeq


# @extensibility(FINAL) @nested
# struct MinimalAnnotationType {
#     AnnotationTypeFlag             annotation_flag;
#     MinimalAnnotationHeader        header;
#     MinimalAnnotationParameterSeq  member_seq;
# };
@cdr
class MinimalAnnotationType:
    annotation_flag: AnnotationTypeFlag
    header: MinimalAnnotationHeader
    member_seq: MinimalAnnotationParameterSeq


# # --- Alias: ----------------------------------------------------------

# @extensibility(FINAL) @nested
# struct CommonAliasBody {
#     AliasMemberFlag       related_flags;
#     TypeIdentifier        related_type;
# };
@cdr
class CommonAliasBody:
    related_flags: AliasMemberFlag
    related_type: TypeIdentifier


# @extensibility(APPENDABLE) @nested
# struct CompleteAliasBody {
#     CommonAliasBody       common;
#     @optional AppliedBuiltinMemberAnnotations  ann_builtin;
#     @optional AppliedAnnotationSeq             ann_custom;
# };
@cdr
class CompleteAliasBody:
    common: CommonAliasBody
    ann_builtin: optional[AppliedBuiltinMemberAnnotations]
    ann_custom: optional[AppliedAnnotationSeq]


# @extensibility(APPENDABLE) @nested
# struct MinimalAliasBody {
#     CommonAliasBody       common;
# };
@cdr
class MinimalAliasBody:
    common: CommonAliasBody


# @extensibility(APPENDABLE) @nested
# struct CompleteAliasHeader {
#     CompleteTypeDetail    detail;
# };
@cdr
class CompleteAliasHeader:
    detail: CompleteTypeDetail


# @extensibility(APPENDABLE) @nested
# struct MinimalAliasHeader {
#     # Empty. Available for future extension
# };
@cdr
class MinimalAliasHeader:
    pass


# @extensibility(FINAL) @nested
# struct CompleteAliasType {
#     AliasTypeFlag         alias_flags;
#     CompleteAliasHeader   header;
#     CompleteAliasBody     body;
# };
@cdr
class CompleteAliasType:
    alias_flags: AliasTypeFlag
    header: CompleteAliasHeader
    body: CompleteAliasBody


# @extensibility(FINAL) @nested
# struct MinimalAliasType {
#     AliasTypeFlag         alias_flags;
#     MinimalAliasHeader    header;
#     MinimalAliasBody      body;
# };
@cdr
class MinimalAliasType:
    alias_flags: AliasTypeFlag
    header: MinimalAliasHeader
    body: MinimalAliasBody


# # --- Collections: ----------------------------------------------------
# @extensibility(FINAL) @nested
# struct CompleteElementDetail {
#     @optional AppliedBuiltinMemberAnnotations  ann_builtin;
#     @optional AppliedAnnotationSeq             ann_custom;
# };
@cdr
class CompleteElementDetail:
    ann_builtin: AppliedBuiltinMemberAnnotations
    ann_custom: AppliedAnnotationSeq


# @extensibility(FINAL) @nested
# struct CommonCollectionElement {
#     CollectionElementFlag     element_flags;
#     TypeIdentifier            type;
# };
@cdr
class CommonCollectionElement:
    element_flags: CollectionElementFlag
    type: TypeIdentifier


# @extensibility(APPENDABLE) @nested
# struct CompleteCollectionElement {
#     CommonCollectionElement   common;
#     CompleteElementDetail     detail;
# };
@cdr
class CompleteCollectionElement:
    common: CommonCollectionElement
    detail: CompleteElementDetail


# @extensibility(APPENDABLE) @nested
# struct MinimalCollectionElement {
#     CommonCollectionElement   common;
# };
@cdr
class MinimalCollectionElement:
    common: CommonCollectionElement


# @extensibility(FINAL) @nested
# struct CommonCollectionHeader {
#     LBound                    bound;
# };
@cdr
class CommonCollectionHeader:
    bound: LBound


# @extensibility(APPENDABLE) @nested
# struct CompleteCollectionHeader {
#     CommonCollectionHeader        common;
#     @optional CompleteTypeDetail  detail; # not present for anonymous
# };
@cdr
class CompleteCollectionHeader:
    common: CommonCollectionHeader
    detail: optional[CompleteTypeDetail]  # not present for anonymous


# @extensibility(APPENDABLE) @nested
# struct MinimalCollectionHeader {
#     CommonCollectionHeader        common;
# };
@cdr
class MinimalCollectionHeader:
    common: CommonCollectionHeader


# # --- Sequence: ------------------------------------------------------
# @extensibility(FINAL) @nested
# struct CompleteSequenceType {
#     CollectionTypeFlag         collection_flag;
#     CompleteCollectionHeader   header;
#     CompleteCollectionElement  element;
# };
@cdr
class CompleteSequenceType:
    collection_flag: CollectionTypeFlag
    header: CompleteCollectionHeader
    element: CompleteCollectionElement


# @extensibility(FINAL) @nested
# struct MinimalSequenceType {
#     CollectionTypeFlag         collection_flag;
#     MinimalCollectionHeader    header;
#     MinimalCollectionElement   element;
# };
@cdr
class MinimalSequenceType:
    collection_flag: CollectionTypeFlag
    header: MinimalCollectionHeader
    element: MinimalCollectionElement


# # --- Array: ------------------------------------------------------
# @extensibility(FINAL) @nested
# struct CommonArrayHeader {
#     LBoundSeq           bound_seq;
# };
@cdr
class CommonArrayHeader:
    bound_seq: LBoundSeq


# @extensibility(APPENDABLE) @nested
# struct CompleteArrayHeader {
#     CommonArrayHeader   common;
#     CompleteTypeDetail  detail;
# };
@cdr
class CompleteArrayHeader:
    common: CommonArrayHeader
    detail: CompleteTypeDetail


# @extensibility(APPENDABLE) @nested
# struct MinimalArrayHeader {
#     CommonArrayHeader   common;
# };
@cdr
class MinimalArrayHeader:
    common: CommonArrayHeader


# @extensibility(APPENDABLE) @nested
# struct CompleteArrayType  {
#     CollectionTypeFlag          collection_flag;
#     CompleteArrayHeader         header;
#     CompleteCollectionElement   element;
# };
@cdr
class CompleteArrayType:
    collection_flag: CollectionTypeFlag
    header: CompleteArrayHeader
    element: CompleteCollectionElement


# @extensibility(FINAL) @nested
# struct MinimalArrayType  {
#     CollectionTypeFlag         collection_flag;
#     MinimalArrayHeader         header;
#     MinimalCollectionElement   element;
# };
@cdr
class MinimalArrayType:
    collection_flag: CollectionTypeFlag
    header: MinimalArrayHeader
    element: MinimalCollectionElement


# # --- Map: ------------------------------------------------------
# @extensibility(FINAL) @nested
# struct CompleteMapType {
#     CollectionTypeFlag            collection_flag;
#     CompleteCollectionHeader      header;
#     CompleteCollectionElement     key;
#     CompleteCollectionElement     element;
# };
@cdr
class CompleteMapType:
    collection_flag: CollectionTypeFlag
    header: CompleteCollectionHeader
    key: CompleteCollectionElement
    element: CompleteCollectionElement


# @extensibility(FINAL) @nested
# struct MinimalMapType {
#     CollectionTypeFlag          collection_flag;
#     MinimalCollectionHeader     header;
#     MinimalCollectionElement    key;
#     MinimalCollectionElement    element;
# };
@cdr
class MinimalMapType:
    collection_flag: CollectionTypeFlag
    header: MinimalCollectionHeader
    key: MinimalCollectionElement
    element: MinimalCollectionElement


# # --- Enumeration: ----------------------------------------------------
BitBound = uint16


# # Constant in an enumerated type
# @extensibility(APPENDABLE) @nested
# struct CommonEnumeratedLiteral {
#     long                     value;
#     EnumeratedLiteralFlag    flags;
# };
@cdr
class CommonEnumeratedLiteral:
    value: int32
    flags: EnumeratedLiteralFlag


# # Constant in an enumerated type
# @extensibility(APPENDABLE) @nested
# struct CompleteEnumeratedLiteral {
#     CommonEnumeratedLiteral  common;
#     CompleteMemberDetail     detail;
# };
# # Ordered by EnumeratedLiteral.common.value
# typedef sequence<CompleteEnumeratedLiteral> CompleteEnumeratedLiteralSeq;
@cdr
class CompleteEnumeratedLiteral:
    common: CommonEnumeratedLiteral
    detail: CompleteMemberDetail


CompleteEnumeratedLiteralSeq = sequence[CompleteEnumeratedLiteral]


# # Constant in an enumerated type
# @extensibility(APPENDABLE) @nested
# struct MinimalEnumeratedLiteral {
#     CommonEnumeratedLiteral  common;
#     MinimalMemberDetail      detail;
# };
# # Ordered by EnumeratedLiteral.common.value
# typedef sequence<MinimalEnumeratedLiteral> MinimalEnumeratedLiteralSeq;
@cdr
class MinimalEnumeratedLiteral:
    common: CommonEnumeratedLiteral
    detail: MinimalMemberDetail


MinimalEnumeratedLiteralSeq = sequence[MinimalEnumeratedLiteral]


# @extensibility(FINAL) @nested
# struct CommonEnumeratedHeader {
#     BitBound                bit_bound;
# };
@cdr
class CommonEnumeratedHeader:
    bit_bound: BitBound


# @extensibility(APPENDABLE) @nested
# struct CompleteEnumeratedHeader {
#     CommonEnumeratedHeader  common;
#     CompleteTypeDetail      detail;
# };
@cdr
class CompleteEnumeratedHeader:
    common: CommonEnumeratedHeader
    detail: CompleteTypeDetail


# @extensibility(APPENDABLE) @nested
# struct MinimalEnumeratedHeader {
#     CommonEnumeratedHeader  common;
# };
@cdr
class MinimalEnumeratedHeader:
    common: CommonEnumeratedHeader


# # Enumerated type
# @extensibility(FINAL) @nested
# struct CompleteEnumeratedType  {
#     EnumTypeFlag                    enum_flags; # unused
#     CompleteEnumeratedHeader        header;
#     CompleteEnumeratedLiteralSeq    literal_seq;
# };
@cdr
class CompleteEnumeratedType:
    enum_flags: EnumTypeFlag  # unused
    header: CompleteEnumeratedHeader
    literal_seq: CompleteEnumeratedLiteralSeq


# # Enumerated type
# @extensibility(FINAL) @nested
# struct MinimalEnumeratedType  {
#     EnumTypeFlag                  enum_flags; # unused
#     MinimalEnumeratedHeader       header;
#     MinimalEnumeratedLiteralSeq   literal_seq;
# };
@cdr
class MinimalEnumeratedType:
    enum_flags: EnumTypeFlag  # unused
    header: MinimalEnumeratedHeader
    literal_seq: MinimalEnumeratedLiteralSeq


# # --- Bitmask: --------------------------------------------------------
# # Bit in a bit mask
# @extensibility(FINAL) @nested
# struct CommonBitflag {
#     unsigned short         position;
#     BitflagFlag            flags;
# };
@cdr
class CommonBitflag:
    position: uint16
    flags: BitflagFlag


# @extensibility(APPENDABLE) @nested
# struct CompleteBitflag {
#     CommonBitflag          common;
#     CompleteMemberDetail   detail;
# };
# # Ordered by Bitflag.position
# typedef sequence<CompleteBitflag> CompleteBitflagSeq;
@cdr
class CompleteBitflag:
    common: CommonBitflag
    detail: CompleteMemberDetail


CompleteBitflagSeq = sequence[CompleteBitflag]


# @extensibility(APPENDABLE) @nested
# struct MinimalBitflag {
#     CommonBitflag        common;
#     MinimalMemberDetail  detail;
# };
# # Ordered by Bitflag.position
# typedef sequence<MinimalBitflag> MinimalBitflagSeq;
@cdr
class MinimalBitflag:
    common: CommonBitflag
    detail: MinimalMemberDetail


MinimalBitflagSeq = sequence[MinimalBitflag]


# @extensibility(FINAL) @nested
# struct CommonBitmaskHeader {
#     BitBound             bit_bound;
# };
@cdr
class CommonBitmaskHeader:
    bit_bound: BitBound


CompleteBitmaskHeader = CompleteEnumeratedHeader
MinimalBitmaskHeader = MinimalEnumeratedHeader


# @extensibility(APPENDABLE) @nested
# struct CompleteBitmaskType {
#     BitmaskTypeFlag          bitmask_flags; # unused
#     CompleteBitmaskHeader    header;
#     CompleteBitflagSeq       flag_seq;
# };
@cdr
class CompleteBitmaskType:
    bitmask_flags: BitmaskTypeFlag  # unused
    header: CompleteBitmaskHeader
    flag_seq: CompleteBitflagSeq


# @extensibility(APPENDABLE) @nested
# struct MinimalBitmaskType {
#     BitmaskTypeFlag          bitmask_flags; # unused
#     MinimalBitmaskHeader     header;
#     MinimalBitflagSeq        flag_seq;
# };
@cdr
class MinimalBitmaskType:
    bitmask_flags: BitmaskTypeFlag  # unused
    header: MinimalBitmaskHeader
    flag_seq: MinimalBitflagSeq


# # --- Bitset: ----------------------------------------------------------
# @extensibility(FINAL) @nested
# struct CommonBitfield {
#     unsigned short        position;
#     BitsetMemberFlag      flags;
#     uint8_t                 bitcount;
#     TypeKind              holder_type; # Must be primitive integer type
# };
@cdr
class CommonBitfield:
    position: uint16
    flags: BitsetMemberFlag
    bitcount: uint8
    holder_type: TypeKind  # Must be primitive integer type


# @extensibility(APPENDABLE) @nested
# struct CompleteBitfield {
#     CommonBitfield           common;
#     CompleteMemberDetail     detail;
# };
# # Ordered by Bitfield.position
# typedef sequence<CompleteBitfield> CompleteBitfieldSeq;
@cdr
class CompleteBitfield:
    common: CommonBitfield
    detail: CompleteMemberDetail


CompleteBitfieldSeq = sequence[CompleteBitfield]


# @extensibility(APPENDABLE) @nested
# struct MinimalBitfield {
#     CommonBitfield       common;
#     NameHash             name_hash;
# };
# # Ordered by Bitfield.position
# typedef sequence<MinimalBitfield> MinimalBitfieldSeq;
@cdr
class MinimalBitfield:
    common: CommonBitfield
    name_hash: NameHash


MinimalBitfieldSeq = sequence[MinimalBitfield]


# @extensibility(APPENDABLE) @nested
# struct CompleteBitsetHeader {
#     CompleteTypeDetail   detail;
# };
@cdr
class CompleteBitsetHeader:
    detail: CompleteTypeDetail


# @extensibility(APPENDABLE) @nested
# struct MinimalBitsetHeader {
#     # Empty. Available for future extension
# };
@cdr
class MinimalBitsetHeader:
    pass


# @extensibility(APPENDABLE) @nested
# struct CompleteBitsetType  {
#     BitsetTypeFlag         bitset_flags; # unused
#     CompleteBitsetHeader   header;
#     CompleteBitfieldSeq    field_seq;
# };
@cdr
class CompleteBitsetType:
    bitset_flags: BitsetTypeFlag  # unused
    header: CompleteBitsetHeader
    field_seq: CompleteBitfieldSeq


# @extensibility(APPENDABLE) @nested
# struct MinimalBitsetType  {
#     BitsetTypeFlag       bitset_flags; # unused
#     MinimalBitsetHeader  header;
#     MinimalBitfieldSeq   field_seq;
# };
@cdr
class MinimalBitsetType:
    bitset_flags: BitsetTypeFlag  # unused
    header: MinimalBitsetHeader
    field_seq: MinimalBitfieldSeq


# # --- Type Object: ---------------------------------------------------
# # The types associated with each case selection must have extensibility
# # kind APPENDABLE or MUTABLE so that they can be extended in the future

# @extensibility(MUTABLE) @nested
# struct CompleteExtendedType {
#     # Empty. Available for future extension
# };
@cdr
class CompleteExtendedType:
    pass


# @extensibility(FINAL)     @nested
# union CompleteTypeObject switch (uint8_t) {
#     case TK_ALIAS:
#         CompleteAliasType      alias_type;
#     case TK_ANNOTATION:
#         CompleteAnnotationType annotation_type;
#     case TK_STRUCTURE:
#         CompleteStructType     struct_type;
#     case TK_UNION:
#         CompleteUnionType      union_type;
#     case TK_BITSET:
#         CompleteBitsetType     bitset_type;
#     case TK_SEQUENCE:
#         CompleteSequenceType   sequence_type;
#     case TK_ARRAY:
#         CompleteArrayType      array_type;
#     case TK_MAP:
#         CompleteMapType        map_type;
#     case TK_ENUM:
#         CompleteEnumeratedType enumerated_type;
#     case TK_BITMASK:
#         CompleteBitmaskType    bitmask_type;

#     # ===================  Future extensibility  ============
#     default:
#         CompleteExtendedType   extended_type;
# };
@union(uint8)
class CompleteTypeObject:
    alias_type: case[TK_ALIAS, CompleteAliasType]
    annotation_type: case[TK_ANNOTATION, CompleteAnnotationType]
    struct_type: case[TK_STRUCTURE, CompleteStructType]
    union_type: case[TK_UNION, CompleteUnionType]
    bitset_type: case[TK_BITSET, CompleteBitsetType]
    sequence_type: case[TK_SEQUENCE, CompleteSequenceType]
    array_type: case[TK_ARRAY, CompleteArrayType]
    map_type: case[TK_MAP, CompleteMapType]
    enumerated_type: case[TK_ENUM, CompleteEnumeratedType]
    bitmask_type: case[TK_BITMASK, CompleteBitmaskType]
    extended_type: default[CompleteExtendedType]


# @extensibility(MUTABLE) @nested
# struct MinimalExtendedType {
#     # Empty. Available for future extension
# };
@cdr
class MinimalExtendedType:
    pass


# @extensibility(FINAL)     @nested
# union MinimalTypeObject switch (uint8_t) {
#     case TK_ALIAS:
#         MinimalAliasType       alias_type;
#     case TK_ANNOTATION:
#         MinimalAnnotationType  annotation_type;
#     case TK_STRUCTURE:
#         MinimalStructType      struct_type;
#     case TK_UNION:
#         MinimalUnionType       union_type;
#     case TK_BITSET:
#         MinimalBitsetType      bitset_type;
#     case TK_SEQUENCE:
#         MinimalSequenceType    sequence_type;
#     case TK_ARRAY:
#         MinimalArrayType       array_type;
#     case TK_MAP:
#         MinimalMapType         map_type;
#     case TK_ENUM:
#         MinimalEnumeratedType  enumerated_type;
#     case TK_BITMASK:
#         MinimalBitmaskType     bitmask_type;

#     # ===================  Future extensibility  ============
#     default:
#         MinimalExtendedType    extended_type;
# };
@union(uint8)
class MinimalTypeObject:
    alias_type: case[TK_ALIAS, MinimalAliasType]
    annotation_type: case[TK_ANNOTATION, MinimalAnnotationType]
    struct_type: case[TK_STRUCTURE, MinimalStructType]
    union_type: case[TK_UNION, MinimalUnionType]
    bitset_type: case[TK_BITSET, MinimalBitsetType]
    sequence_type: case[TK_SEQUENCE, MinimalSequenceType]
    array_type: case[TK_ARRAY, MinimalArrayType]
    map_type: case[TK_MAP, MinimalMapType]
    enumerated_type: case[TK_ENUM, MinimalEnumeratedType]
    bitmask_type: case[TK_BITMASK, MinimalBitmaskType]
    extended_type: default[MinimalExtendedType]


# @extensibility(APPENDABLE)  @nested
# union TypeObject switch (uint8_t) { # EquivalenceKind
# case EK_COMPLETE:
#     CompleteTypeObject   complete;
# case EK_MINIMAL:
#     MinimalTypeObject    minimal;
# };
@union(uint8)
class TypeObject:
    complete: case[EK_COMPLETE, CompleteTypeObject]
    minimal: case[EK_MINIMAL, MinimalTypeObject]


@cdr
class TypeObjectContainer:
    type_object: TypeObject
