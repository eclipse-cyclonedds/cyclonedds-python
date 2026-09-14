from dataclasses import dataclass

import pytest
import support_modules.test_classes as tc

from cyclonedds.idl import IdlStruct
from cyclonedds.idl.annotations import appendable, mutable


@dataclass
class KeylessFinal(IdlStruct):
    value: int = 0


@dataclass
@appendable
class KeylessAppendable(IdlStruct):
    value: int = 0


@dataclass
@mutable
class KeylessMutable(IdlStruct):
    value: int = 0


single_test_data = [
    (tc.SingleInt, (1, 1000, 9128919)),
    (tc.SingleString, ("", "Hello, World!", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")),
    (tc.SingleFloat, (0.0, -1000000000, 1.02)),
    (tc.SingleBool, (True, False)),
    (tc.SingleSequence, ([], [1,2,3], [0, 1] * 100)),
    (tc.SingleArray, ([0, 1, 2],)),
    (tc.SingleUint16, (0, 65535)),
    (tc.SingleBoundedSequence, ([], [1], [1,1], [100, 1, 1])),
    (tc.SingleBoundedString, ("123456789", "llsllë", "")),
    (tc.SingleEnum, (tc.BasicEnum.One, tc.BasicEnum.Two, tc.BasicEnum.Three)),
    (tc.SingleNested, (tc.SingleInt(1),))
]


@pytest.mark.parametrize("_type,values", single_test_data)
def test_simple_datatypes(_type, values):
    for value in values:
        v1 = _type(value=value)
        b = v1.serialize()
        v2 = _type.deserialize(b)
        assert v1 == v2
        assert _type.__idl__.serialize_key_normalized(v1) == _type.__idl__.serialize_key_normalized(v2)


def test_all_primitives():
    v1 = tc.AllPrimitives()
    b = v1.serialize()
    v2 = tc.AllPrimitives.deserialize(b)
    assert v1 == v2


def test_keyed():
    v1 = tc.Keyed(a=1, b=2)
    b = v1.serialize()
    v2 = tc.Keyed.deserialize(b)
    assert v1 == v2
    assert tc.Keyed.__idl__.serialize_key_normalized(v1) == tc.Keyed.__idl__.serialize_key_normalized(v2)
    assert tc.Keyed.__idl__.serialize_key(v1) == bytes.fromhex('01 00 00 00 00 00 00 00')


def test_keyed2():
    v1 = tc.Keyed2(a=1, b=2)
    b = v1.serialize()
    v2 = tc.Keyed2.deserialize(b)
    assert v1 == v2
    assert tc.Keyed2.__idl__.serialize_key_normalized(v1) == tc.Keyed2.__idl__.serialize_key_normalized(v2)
    assert tc.Keyed.__idl__.serialize_key(v2) == bytes.fromhex('01 00 00 00 00 00 00 00')


def test_keyless():
    v1 = tc.Keyless(a=1, b=2)
    b = v1.serialize()
    v2 = tc.Keyless.deserialize(b)
    assert v1 == v2
    assert tc.Keyless.__idl__.serialize_key_normalized(v1) == tc.Keyless.__idl__.serialize_key_normalized(v2)


@pytest.mark.parametrize("keyless_type", [KeylessFinal, KeylessAppendable, KeylessMutable])
@pytest.mark.parametrize("use_version_2", [False, True])
def test_keyless_serialized_key_has_no_payload(keyless_type, use_version_2):
    sample = keyless_type(value=42)

    # Public key serialization includes only the representation header.
    serialized_key = sample.serialize_key(use_version_2=use_version_2)
    assert len(serialized_key) == 4
    assert keyless_type.deserialize_key(serialized_key) == keyless_type()

    # The payload used by the C layer is empty, for both definition-order and
    # normalized key serialization.
    assert keyless_type.__idl__.serialize_key(sample, use_version_2=use_version_2) == b""
    assert keyless_type.__idl__.serialize_key_normalized(sample, use_version_2=use_version_2) == b""
    assert keyless_type.__idl__.deserialize_key(
        b"", has_header=False, use_version_2=use_version_2
    ) == keyless_type()

    # Ordinary data serialization remains unchanged.
    assert keyless_type.deserialize(
        sample.serialize(use_version_2=use_version_2)
    ) == sample


def test_simple_union():
    values = [
        tc.SingleUnion(value=tc.EasyUnion(a=1)),
        tc.SingleUnion(value=tc.EasyUnion(a=2)),
        tc.SingleUnion(value=tc.EasyUnion(a=3)),
        tc.SingleUnion(value=tc.EasyUnion(b=True))
    ]
    for v1 in values:
        b = v1.serialize()
        v2 = tc.SingleUnion.deserialize(b)
        assert v1 == v2
