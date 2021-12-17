import pytest

from cyclonedds.core import Entity, QueryCondition, SampleState, InstanceState, ViewState
from cyclonedds.util import isgoodentity

from support_modules.testtopics import Message


def test_querycondition_init(common_setup):
    qc = QueryCondition(
        common_setup.dr,
        SampleState.Any | InstanceState.Any | ViewState.Any, 
        lambda x: False
    )
    assert isgoodentity(qc)


def test_querycondition_get_mask(common_setup):
    mask = SampleState.Any | InstanceState.Any | ViewState.Any
    qc = QueryCondition(common_setup.dr, mask, lambda x: False)

    assert qc.mask == qc.get_mask() == mask

    mask = SampleState.NotRead | InstanceState.NotAliveNoWriters | ViewState.Old

    assert qc.mask == qc.get_mask() != mask

    qc = QueryCondition(common_setup.dr, mask, lambda x: False)

    assert qc.mask == qc.get_mask() == mask


def test_querycondition_get_reader(common_setup):
    qc = QueryCondition(common_setup.dr, SampleState.Any | InstanceState.Any | ViewState.Any, lambda x: False)
    assert qc.get_datareader() == common_setup.dr


# @pytest.mark.xfail(reason="TODO: implement typeless serdata")
def test_querycondition_read(common_setup):
    qc = QueryCondition(
        common_setup.dr,
        SampleState.Read | ViewState.Any | InstanceState.Any,
        lambda msg: msg.message.startswith("Goodbye")
    )

    assert not qc.triggered

    messages = [Message(message=f"Hi {i}!") for i in range(5)] + [Message(message="Goodbye")]
    for m in messages:
        common_setup.dw.write(m)

    common_setup.dr.read(N=5)
    assert not qc.triggered

    common_setup.dr.read(N=6)
    assert qc.triggered

    received = common_setup.dr.read(condition=qc)

    assert len(received) == 1 and received[0] == messages[5]
