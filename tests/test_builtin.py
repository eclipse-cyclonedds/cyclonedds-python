import pytest

import cyclonedds.internal
from cyclonedds.domain import DomainParticipant
from cyclonedds.sub import Subscriber
from cyclonedds.topic import Topic
from cyclonedds.util import duration, isgoodentity
from cyclonedds.builtin import BuiltinDataReader, BuiltinTopicDcpsParticipant, BuiltinTopicDcpsSubscription, BuiltinTopicDcpsTopic

from support_modules.testtopics import Message

requires_dcps_topic = pytest.mark.skipif(
    not cyclonedds.internal.feature_topic_discovery, reason="Cannot use BuiltinTopicDcpsTopic since topic discovery is disabled."
)

def test_builtin_dcps_participant(manual_setup):
    dp = manual_setup.dp
    sub = Subscriber(dp)
    dr1 = BuiltinDataReader(sub, BuiltinTopicDcpsParticipant)
    dr2 = BuiltinDataReader(sub, BuiltinTopicDcpsSubscription)

    assert isgoodentity(dr1)
    assert isgoodentity(dr2)
    assert dr1.take_next().key == dp.guid
    msg = dr2.take(N=2)
    assert {msg[0].key, msg[1].key} == {dr1.guid, dr2.guid}


def test_builtin_dcps_participant_read_next(manual_setup):
    dp = manual_setup.dp
    sub = Subscriber(dp)
    dr1 = BuiltinDataReader(sub, BuiltinTopicDcpsParticipant)
    dr2 = BuiltinDataReader(sub, BuiltinTopicDcpsSubscription)

    assert isgoodentity(dr1)
    assert isgoodentity(dr2)
    assert dr1.read_next().key == dp.guid
    msg = dr2.take(N=2)
    assert {msg[0].key, msg[1].key} == {dr1.guid, dr2.guid}


def test_builtin_dcps_participant_iter(manual_setup):
    dp = manual_setup.dp
    sub = Subscriber(dp)
    dr1 = BuiltinDataReader(sub, BuiltinTopicDcpsParticipant)
    dr2 = BuiltinDataReader(sub, BuiltinTopicDcpsSubscription)

    assert isgoodentity(dr1)
    assert isgoodentity(dr2)

    for msg in dr1.read_iter(timeout=duration(milliseconds=10)):
        assert msg.key == dp.guid

    for msg in dr2.take_iter(timeout=duration(milliseconds=10)):
        assert msg.key in [dr1.guid, dr2.guid]


@requires_dcps_topic
def test_builtin_dcps_topic_read(manual_setup):
    dp = manual_setup.dp
    tdr = BuiltinDataReader(dp, BuiltinTopicDcpsTopic)
    tp = Topic(dp, 'MessageTopic', Message)

    # assert tp.typename == tp.get_type_name() == 'Message'

    assert isgoodentity(tdr)
    assert isgoodentity(tp)

    msg = tdr.read_one(timeout=duration(milliseconds=10))

    assert msg.topic_name == 'MessageTopic'
    assert msg.type_name == 'Message'


@requires_dcps_topic
def test_builtin_dcps_topic_take(manual_setup):
    dp = manual_setup.dp
    tdr = BuiltinDataReader(dp, BuiltinTopicDcpsTopic)

    tp = Topic(dp, 'MessageTopic', Message)

    assert isgoodentity(tdr)
    assert isgoodentity(tp)

    msg = tdr.take_one(timeout=duration(milliseconds=10))

    assert msg.topic_name == 'MessageTopic'
    assert msg.type_name == 'Message'

