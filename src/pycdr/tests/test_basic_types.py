import pytest
import test_classes as tc


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
        assert _type.cdr.keyhash(v1) == _type.cdr.keyhash(v2)


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
    assert tc.Keyed.cdr.keyhash(v1) == tc.Keyed.cdr.keyhash(v2)


def test_keyless():
    v1 = tc.Keyless(a=1, b=2)
    b = v1.serialize()
    v2 = tc.Keyless.deserialize(b)
    assert v1 == v2
    assert tc.Keyless.cdr.keyhash(v1) == tc.Keyless.cdr.keyhash(v2)


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
