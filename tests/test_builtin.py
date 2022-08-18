import pytest

from cyclonedds.domain import DomainParticipant
from cyclonedds.sub import Subscriber
from cyclonedds.topic import Topic
from cyclonedds.util import duration, isgoodentity
from cyclonedds.builtin import BuiltinDataReader, BuiltinTopicDcpsParticipant, BuiltinTopicDcpsSubscription, BuiltinTopicDcpsTopic

from support_modules.testtopics import Message



def test_builtin_dcps_participant():
    dp = DomainParticipant(0)
    sub = Subscriber(dp)
    dr1 = BuiltinDataReader(sub, BuiltinTopicDcpsParticipant)
    dr2 = BuiltinDataReader(sub, BuiltinTopicDcpsSubscription)

    assert isgoodentity(dr1)
    assert isgoodentity(dr2)
    assert dr1.take_next().key == dp.guid
    msg = dr2.take(N=2)
    assert {msg[0].key, msg[1].key} == {dr1.guid, dr2.guid}


def test_builtin_dcps_participant_read_next():
    dp = DomainParticipant(0)
    sub = Subscriber(dp)
    dr1 = BuiltinDataReader(sub, BuiltinTopicDcpsParticipant)
    dr2 = BuiltinDataReader(sub, BuiltinTopicDcpsSubscription)

    assert isgoodentity(dr1)
    assert isgoodentity(dr2)
    assert dr1.read_next().key == dp.guid
    msg = dr2.take(N=2)
    assert {msg[0].key, msg[1].key} == {dr1.guid, dr2.guid}


def test_builtin_dcps_participant_iter():
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


def test_builtin_dcps_topic_read():
    dp = DomainParticipant(0)
    tdr = BuiltinDataReader(dp, BuiltinTopicDcpsTopic)

    tp = Topic(dp, 'MessageTopic', Message)

    # assert tp.typename == tp.get_type_name() == 'Message'

    assert isgoodentity(tdr)
    assert isgoodentity(tp)

    msg = tdr.read_one(timeout=duration(milliseconds=10))

    assert msg.topic_name == 'MessageTopic'
    assert msg.type_name == 'Message'


def test_builtin_dcps_topic_take():
    dp = DomainParticipant(0)
    tdr = BuiltinDataReader(dp, BuiltinTopicDcpsTopic)

    tp = Topic(dp, 'MessageTopic', Message)

    assert isgoodentity(tdr)
    assert isgoodentity(tp)

    msg = tdr.take_one(timeout=duration(milliseconds=10))

    assert msg.topic_name == 'MessageTopic'
    assert msg.type_name == 'Message'

