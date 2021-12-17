import pytest

from cyclonedds.core import Entity, DDSStatus

from support_modules.testtopics import Message


def test_communication_basic_read(common_setup):
    msg = Message(message="Hi!")
    common_setup.dw.write(msg)
    result = common_setup.dr.read()

    assert len(result) == 1
    assert result[0] == msg


def test_communication_basic_take(common_setup):
    msg = Message(message="Hi!")
    common_setup.dw.write(msg)
    result = common_setup.dr.take()

    assert len(result) == 1
    assert result[0] == msg


def test_communication_order(common_setup):
    msg1 = Message(message="Hi1!")
    msg2 = Message(message="Hi2!")
    common_setup.dw.write(msg1)
    common_setup.dw.write(msg2)
    result = common_setup.dr.read(N=2)
    
    assert len(result) == 2
    assert result[0] == msg1
    assert result[1] == msg2


def test_communication_read_nodestroys(common_setup):
    msg = Message(message="Hi!")
    common_setup.dw.write(msg)
    common_setup.dr.read()
    result = common_setup.dr.read()

    assert len(result) == 1
    assert result[0] == msg


def test_communication_take_destroys(common_setup):
    msg = Message(message="Hi!")
    common_setup.dw.write(msg)
    result1 = common_setup.dr.read()
    result2 = common_setup.dr.take()
    result3 = common_setup.dr.read()

    assert len(result1) == 1
    assert len(result2) == 1
    assert len(result3) == 0
    assert result1[0] == result2[0] == msg


def test_communication_status_mask(common_setup):
    common_setup.dr.set_status_mask(DDSStatus.SubscriptionMatched)
    status = common_setup.dr.read_status()
    assert status == DDSStatus.SubscriptionMatched

    del common_setup.dw

    status = common_setup.dr.get_status_changes()
    assert (status & DDSStatus.SubscriptionMatched) > 0

    status = common_setup.dr.take_status()
    assert (status & DDSStatus.SubscriptionMatched) > 0
