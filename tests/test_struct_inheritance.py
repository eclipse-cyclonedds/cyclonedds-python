from dataclasses import dataclass
from cyclonedds.idl import IdlStruct


@dataclass
class A(IdlStruct):
    fa: int


@dataclass
class B(A):
    fb: int


def test_inheritance():
    v = B(fa=1, fb=2)
    assert v == B.deserialize(v.serialize())
