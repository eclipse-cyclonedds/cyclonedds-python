import pytest

from cyclonedds.domain import DomainParticipant
from cyclonedds.sub import Subscriber
from cyclonedds.util import duration, isgoodentity
from cyclonedds.builtin import BuiltinDataReader, BuiltinTopicDcpsParticipant, BuiltinTopicDcpsSubscription



def test_builtin_dcps_participant():
    dp = DomainParticipant(0)
    sub = Subscriber(dp)
    dr1 = BuiltinDataReader(sub, BuiltinTopicDcpsParticipant)
    dr2 = BuiltinDataReader(sub, BuiltinTopicDcpsSubscription)

    assert isgoodentity(dr1)
    assert isgoodentity(dr2)
    assert dr1.take_next().key == dp.guid
    msg = dr2.take(N=2)
    assert [msg[0].key, msg[1].key] == [dr1.guid, dr2.guid] or \
           [msg[0].key, msg[1].key] == [dr2.guid, dr1.guid]


def test_builtin_dcps_participant():
    dp = DomainParticipant(0)
    sub = Subscriber(dp)
    dr1 = BuiltinDataReader(sub, BuiltinTopicDcpsParticipant)
    dr2 = BuiltinDataReader(sub, BuiltinTopicDcpsSubscription)

    assert isgoodentity(dr1)
    assert isgoodentity(dr2)
    assert dr1.read_next().key == dp.guid
    msg = dr2.take(N=2)
    assert [msg[0].key, msg[1].key] == [dr1.guid, dr2.guid] or \
           [msg[0].key, msg[1].key] == [dr2.guid, dr1.guid]


def test_builtin_dcps_participant():
    dp = DomainParticipant(0)
    sub = Subscriber(dp)
    dr1 = BuiltinDataReader(sub, BuiltinTopicDcpsParticipant)
    dr2 = BuiltinDataReader(sub, BuiltinTopicDcpsSubscription)

    assert isgoodentity(dr1)
    assert isgoodentity(dr2)

    for msg in dr1.read_iter(timeout=duration(milliseconds=10)):
        assert msg.key == dp.guid

    for msg in dr2.take_iter(timeout=duration(milliseconds=10)):
        msg.key in [dr1.guid, dr2.guid]
