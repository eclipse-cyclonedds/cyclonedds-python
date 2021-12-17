import pytest

from cyclonedds.core import Entity, ReadCondition, SampleState, InstanceState, ViewState
from cyclonedds.util import isgoodentity
from cyclonedds.topic import Topic
from cyclonedds.sub import DataReader
from cyclonedds.pub import DataWriter

from support_modules.testtopics import Message, MessageKeyed


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
    tp = Topic(common_setup.dp, "hi_sayer", MessageKeyed)
    dr = DataReader(common_setup.dp, tp)
    dw = DataWriter(common_setup.dp, tp)
    rc = ReadCondition(dr, SampleState.Any | ViewState.Any | InstanceState.NotAliveDisposed)

    assert not rc.triggered

    messages = [MessageKeyed(user_id=i, message=f"Hi {i}!") for i in range(5)]
    for m in messages:
        dw.write(m)

    received = dr.read(N=5)

    assert messages == received

    dw.dispose(messages[1])
    assert rc.triggered

    received = dr.read(condition=rc)

    assert len(received) == 1 and received[0] == messages[1]


def test_condition_cleanup(common_setup):
    reader = DataReader(common_setup.dp, common_setup.tp)
    condition = ReadCondition(reader, 1234)

    del reader
    import gc
    gc.collect()

    del condition