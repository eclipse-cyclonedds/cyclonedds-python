import pytest

from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.sub import DataReader
from cyclonedds.pub import DataWriter

from support_modules.testtopics import KeyedArrayType


def test_keyed_type_alignment():
    dp = DomainParticipant()
    tp = Topic(dp, "Test", KeyedArrayType)
    dw = DataWriter(dp, tp)
    dr = DataReader(dp, tp)

    samp1 = KeyedArrayType(
        [-1] * 3,
        [-1] * 3,
        [-1] * 3,
        [-1] * 3,
        [-1] * 3,
        [-1] * 3
    )

    dw.write(samp1)
    samp2 = dr.read()[0]
    assert KeyedArrayType.__idl__.serialize_key_normalized(samp1) == KeyedArrayType.__idl__.serialize_key_normalized(samp2)
