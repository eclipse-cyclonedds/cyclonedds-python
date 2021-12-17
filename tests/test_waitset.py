import pytest

from cyclonedds.core import Entity, DDSException, WaitSet, ReadCondition, ViewState, InstanceState, SampleState
from cyclonedds.util import duration, isgoodentity

from support_modules.testtopics import Message


def test_waitset_initialize(common_setup):
    ws = WaitSet(common_setup.dp)

    assert isgoodentity(ws)


def test_waitset_attachment(common_setup):
    ws = WaitSet(common_setup.dp)
    rc = ReadCondition(common_setup.dr, ViewState.Any | InstanceState.Any | SampleState.Any)

    ws.attach(rc)
    assert ws.is_attached(rc)

    ws.detach(rc)
    assert not ws.is_attached(rc)


def test_waitset_illigal_op(common_setup):
    ws = WaitSet(common_setup.dp)

    with pytest.raises(DDSException) as exc:
        ws.attach(Entity(101))

    assert exc.value.code == DDSException.DDS_RETCODE_BAD_PARAMETER


def test_waitset_wait(common_setup):
    ws = WaitSet(common_setup.dp)

    rc1 = ReadCondition(common_setup.dr, ViewState.Any | InstanceState.Any | SampleState.Any)
    ws.attach(rc1)

    assert ws.wait(duration(milliseconds=5)) == 0

    common_setup.dw.write(Message(message="Hi!"))

    assert ws.wait(duration(seconds=1)) == 1

    rc2 = ReadCondition(common_setup.dr, ViewState.Any | InstanceState.Any | SampleState.NotRead)
    ws.attach(rc2)

    assert ws.wait(duration(seconds=1)) == 2