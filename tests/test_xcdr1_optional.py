from dataclasses import dataclass
from typing import Optional

import pytest
import cyclonedds.idl.types as types

from cyclonedds.domain import DomainParticipant
from cyclonedds.idl import IdlStruct
from cyclonedds.idl.annotations import key
from cyclonedds.pub import DataWriter
from cyclonedds.qos import Policy, Qos
from cyclonedds.sub import DataReader
from cyclonedds.topic import Topic


@dataclass
class Xcdr1Optional(IdlStruct):
    value: Optional[types.int32]
    key: types.int32
    key("key")


@pytest.mark.parametrize("value", [None, 42])
def test_xcdr1_optional(value):
    qos = Qos(Policy.DataRepresentation(use_cdrv0_representation=True))

    dp = DomainParticipant(0)
    tp = Topic(dp, "Xcdr1Optional", Xcdr1Optional)
    dr = DataReader(dp, tp, qos=qos)
    dw = DataWriter(dp, tp, qos=qos)

    msg = Xcdr1Optional(value=value, key=1)
    dw.write(msg)
    assert dr.read_next() == msg
