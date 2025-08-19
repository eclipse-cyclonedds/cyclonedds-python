import pytest

from dataclasses import dataclass

from cyclonedds.idl import IdlStruct, IdlBitmask, IdlUnion, IdlEnum
from cyclonedds.idl._support import Buffer, Endianness
import cyclonedds.idl._machinery as mc
import cyclonedds.idl.types as tp


class A(IdlEnum):
    V1 = 0xca
    V2 = 0xef


@dataclass
class B(IdlBitmask):
    V1: bool
    V2: bool


@dataclass
class C(IdlStruct):
    A: tp.uint8
    B: tp.uint16


class D(IdlUnion, discriminator=bool):
    A: tp.case[True, tp.uint16]
    B: tp.default[tp.int8]



def test_all_machine_serializers():
    b = Buffer()
    b.set_endianness(Endianness.Little)

    m = mc.CharMachine()
    m.serialize(b, "a")
    m.serialize(b, "b")
    assert b.asbytes() == b"ab"

    m = mc.PrimitiveMachine(tp.uint8)
    b.zero_out()
    b.seek(0)
    m.serialize(b, 0xab)
    assert b.asbytes() == b"\xab"

    m2 = mc.SequenceMachine(m, add_size_header=False)
    b.zero_out()
    b.seek(0)
    m2.serialize(b, [0x0a, 0x0b])
    assert b.asbytes() == b"\x02\x00\x00\x00\x0a\x0b"

    m2 = mc.SequenceMachine(m, add_size_header=True)
    b.zero_out()
    b.seek(0)
    m2.serialize(b, [0x0a, 0x0b])
    assert b.asbytes() == b"\x06\x00\x00\x00\x02\x00\x00\x00\x0a\x0b"

    m2 = mc.ArrayMachine(m, 2, add_size_header=False)
    b.zero_out()
    b.seek(0)
    m2.serialize(b, [0x0a, 0x0b])
    assert b.asbytes() == b"\x0a\x0b"

    m2 = mc.ArrayMachine(m, 2, add_size_header=True)
    b.zero_out()
    b.seek(0)
    m2.serialize(b, [0x0a, 0x0b])
    assert b.asbytes() == b"\x02\x00\x00\x00\x0a\x0b"

    m2 = mc.PlainCdrV2SequenceOfPrimitiveMachine(tp.uint8)
    b.seek(0)
    m2.serialize(b, [0x0a, 0x0b])
    assert b.asbytes() == b"\x02\x00\x00\x00\x0a\x0b"

    m2 = mc.PlainCdrV2ArrayOfPrimitiveMachine(tp.uint8, 2)
    b.zero_out()
    b.seek(0)
    m2.serialize(b, [0x0a, 0x0b])
    assert b.asbytes() == b"\x0a\x0b"

    m2 = mc.ByteArrayMachine(3)
    b.zero_out()
    b.seek(0)
    m2.serialize(b, bytearray([1,2,3]))
    m2.serialize(b, b"\x03\x02\x01")
    assert b.asbytes() == b"\x01\x02\x03\x03\x02\x01"

    m2 = mc.EnumMachine(A)
    b.zero_out()
    b.seek(0)
    m2.serialize(b, A.V2)
    m2.serialize(b, A.V1)
    assert b.asbytes() == b"\xef\x00\x00\x00\xca\x00\x00\x00"

    m2 = mc.BitBoundEnumMachine(A, 8)
    b.zero_out()
    b.seek(0)
    m2.serialize(b, A.V2)
    m2.serialize(b, A.V1)
    assert b.asbytes() == b"\xef\xca"

    m2 = mc.BitBoundEnumMachine(A, 16)
    b.zero_out()
    b.seek(0)
    m2.serialize(b, A.V2)
    m2.serialize(b, A.V1)
    assert b.asbytes() == b"\xef\x00\xca\x00"

    m2 = mc.BitMaskMachine(B, 8)
    b.zero_out()
    b.seek(0)
    m2.serialize(b, B(True, False))
    m2.serialize(b, B(False, True))
    assert b.asbytes() == b"\x01\x02"

    m2 = mc.BitMaskMachine(B, 16)
    b.zero_out()
    b.seek(0)
    m2.serialize(b, B(True, False))
    m2.serialize(b, B(False, True))
    assert b.asbytes() == b"\x01\x00\x02\x00"

    m2 = mc.OptionalMachine(m, 0, True)
    b.zero_out()
    b.seek(0)
    m2.serialize(b, None)
    m2.serialize(b, 0x12)
    m2.serialize(b, 0)
    assert b.asbytes() == b"\x00\x01\x12\x01\x00"

    m2 = mc.StringMachine()
    b.zero_out()
    b.seek(0)
    m2.serialize(b, "ab")
    assert b.asbytes() == b"\x03\x00\x00\x00ab\x00"

    m3 = mc.StructMachine(C, {
        'A': mc.PrimitiveMachine(tp.uint8),
        'B': mc.PrimitiveMachine(tp.uint16)
    }, [])
    b.zero_out()
    b.seek(0)
    m3.serialize(b, C(0x0a, 0x0b))
    assert b.asbytes() == b"\x0a\x00\x0b\x00"

    m3 = mc.DelimitedCdrAppendableStructMachine(C, {
        'A': mc.PrimitiveMachine(tp.uint8),
        'B': mc.PrimitiveMachine(tp.uint16)
    }, [])
    b.zero_out()
    b.seek(0)
    m3.serialize(b, C(0x0a, 0x0b))
    assert b.asbytes() == b"\x04\x00\x00\x00\x0a\x00\x0b\x00"

    m3 = mc.PLCdrMutableStructMachine(C, [
        mc.MutableMember(
            'A', key=False, optional=True, lentype=mc.LenType.OneByte,
            must_understand=True, memberid=1, machine=mc.PrimitiveMachine(tp.uint8)
        ),
        mc.MutableMember(
            'B', key=False, optional=True, lentype=mc.LenType.TwoByte,
            must_understand=True, memberid=2, machine=mc.PrimitiveMachine(tp.uint16)
        )
    ], True)

    b.zero_out()
    b.seek(0)
    m3.serialize(b, C(0x0a, 0x0b))
    assert b.asbytes() == (
        b"\x0e\x00\x00\x00"
        b"\x01\x00\x00\x80"
        b"\x0a\x00\x00\x00"
        b"\x02\x00\x00\x90"
        b"\x0b\x00"
    )

    b.zero_out()
    b.seek(0)
    m3.serialize(b, C(None, 0x0b))
    assert b.asbytes() == (
        b"\x06\x00\x00\x00"
        b"\x02\x00\x00\x90"
        b"\x0b\x00"
    )

    b.zero_out()
    b.seek(0)
    m3.serialize(b, C(None, None))
    assert b.asbytes() == b"\x00\x00\x00\x00"

    m3 = mc.UnionMachine(D, mc.PrimitiveMachine(bool), {
        True: mc.PrimitiveMachine(tp.uint16),
    }, default_case=mc.PrimitiveMachine(tp.uint8))

    b.zero_out()
    b.seek(0)
    m3.serialize(b, D(A=0x1234))
    m3.serialize(b, D(B=0x77))
    assert b.asbytes() == b"\x01\x00\x34\x12\x00\x77"

    m3 = mc.DelimitedCdrAppendableUnionMachine(D, mc.PrimitiveMachine(bool), {
        True: mc.PrimitiveMachine(tp.uint16),
    }, default_case=mc.PrimitiveMachine(tp.uint8))

    b.zero_out()
    b.seek(0)
    m3.serialize(b, D(A=0x1234))
    m3.serialize(b, D(B=0x77))
    assert b.asbytes() == b"\x04\x00\x00\x00\x01\x00\x34\x12\x02\x00\x00\x00\x00\x77"




