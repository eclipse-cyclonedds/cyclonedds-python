import pytest
from dataclasses import dataclass
from cyclonedds.idl import IdlBitmask, IdlStruct
from cyclonedds.idl.annotations import bit_bound, position, AnnotationException


@dataclass
class OneTest(IdlBitmask):
    a: bool
    b: bool
    c: bool


@dataclass
@bit_bound(20)
class TwoTest(IdlBitmask):
    a: bool
    position('a', 10)
    b: bool
    position('b', 1)


def test_bit_masks():
    assert OneTest(a=True, b=False, c=True).as_mask() == 0b101
    assert OneTest(a=False, b=True, c=False).as_mask() == 0b010
    assert TwoTest(a=True, b=True).as_mask() == ((1 << 10) | (1 << 1))

    with pytest.raises(AnnotationException):
        @bit_bound(4)
        class InvalidPosition(IdlBitmask):
            a: bool
            position('a', 4)

    with pytest.raises(AnnotationException):
        @bit_bound(80)
        class InvalidBitBound(IdlBitmask):
            pass

    with pytest.raises(TypeError):
        class InvalidDualUsage(IdlBitmask):
            a: bool
            b: bool
            position('b', 0)


@dataclass
class TypeWithBitmask(IdlStruct):
    a: OneTest
    b: TwoTest


def test_bit_mask_serialisation():
    instance = TypeWithBitmask(
        a=OneTest(False, True, True),
        b=TwoTest(True, False)
    )
    assert instance == TypeWithBitmask.deserialize(instance.serialize())
