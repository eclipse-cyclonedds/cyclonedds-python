import pytest

from cyclonedds.core import Entity, ReadCondition, SampleState, InstanceState, ViewState
from cyclonedds.util import isgoodentity

from  testtopics import Message


def test_readcondition_init(common_setup):
    rc = ReadCondition(common_setup.dr, SampleState.Any | InstanceState.Any | ViewState.Any)
    assert isgoodentity(rc)


def test_readcondition_get_mask(common_setup):
    mask = SampleState.Any | InstanceState.Any | ViewState.Any
    rc = ReadCondition(common_setup.dr, mask)

    assert rc.mask == rc.get_mask() == mask

    mask = SampleState.NotRead | InstanceState.NotAliveNoWriters | ViewState.Old

    assert rc.mask == rc.get_mask() != mask

    rc = ReadCondition(common_setup.dr, mask)

    assert rc.mask == rc.get_mask() == mask


def test_readcondition_get_reader(common_setup):
    rc = ReadCondition(common_setup.dr, SampleState.Any | InstanceState.Any | ViewState.Any)
    assert rc.get_datareader() == common_setup.dr


def test_readcondition_read(common_setup):
    rc = ReadCondition(common_setup.dr, SampleState.Any | ViewState.Any | InstanceState.NotAliveDisposed)

    assert not rc.triggered

    messages = [Message(message=f"Hi {i}!") for i in range(5)]
    for m in messages:
        common_setup.dw.write(m)

    received = common_setup.dr.read(N=5)

    assert messages == received

    common_setup.dw.dispose(messages[1])
    assert rc.triggered

    received = common_setup.dr.read(condition=rc)

    assert len(received) == 1 and received[0] == messages[1]


