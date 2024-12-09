import pytest
import random

from cyclonedds.core import DDSException
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.util import duration, isgoodentity
from cyclonedds.sub import DataReader
from cyclonedds.core import Qos, Policy

from support_modules.testtopics import Message, MessageKeyed


def test_initialize_writer():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message", Message)
    pub = Publisher(dp)
    dw = DataWriter(pub, tp)

    assert isgoodentity(dw)


def test_writeto_writer():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message", Message)
    pub = Publisher(dp)
    dw = DataWriter(pub, tp)

    msg = Message(
        message="TestMessage"
    )

    dw.write(msg)
    assert dw.wait_for_acks(duration(seconds=1))


def test_writer_instance():
    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageKeyed", MessageKeyed)
    pub = Publisher(dp)
    dw = DataWriter(pub, tp)

    msg = MessageKeyed(user_id=1, message="Hello")

    handle = dw.register_instance(msg)
    assert handle > 0
    dw.write(msg)
    dw.unregister_instance(msg)


def test_writer_instance_handle():
    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageKeyed", MessageKeyed)
    pub = Publisher(dp)
    dw = DataWriter(pub, tp)

    msg = MessageKeyed(user_id=1, message="Hello")

    handle = dw.register_instance(msg)
    assert handle > 0
    dw.write(msg)
    dw.unregister_instance_handle(handle)


def test_writer_writedispose():
    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageKeyed", MessageKeyed)
    pub = Publisher(dp)
    dw = DataWriter(pub, tp)

    msg = MessageKeyed(user_id=1, message="Hello")

    dw.write_dispose(msg)


def test_writer_lookup():
    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageKeyed", MessageKeyed)
    pub = Publisher(dp)
    dw = DataWriter(pub, tp)

    keymsg1 = MessageKeyed(user_id=1000, message="Hello!")
    keymsg2 = MessageKeyed(user_id=2000, message="Hello!")
    assert None == dw.lookup_instance(keymsg1)
    assert None == dw.lookup_instance(keymsg2)
    handle1 = dw.register_instance(keymsg1)
    handle2 = dw.register_instance(keymsg2)
    assert handle1 > 0 and handle2 > 0 and handle1 != handle2
    assert handle1 == dw.lookup_instance(keymsg1)
    assert handle2 == dw.lookup_instance(keymsg2)


def test_get_matched_subscriptions():
    dp = DomainParticipant(0)
    tp = Topic(dp, f"Message{random.randint(1000000,9999999)}", Message)
    dw = DataWriter(dp, tp)

    rand_dr = random.randint(0, 20)
    dr = []
    for i in range(rand_dr):
        dr.append(DataReader(dp, tp))

    matched = dw.get_matched_subscriptions()
    assert len(matched) == rand_dr


def test_get_matched_subscription_data():
    dp = DomainParticipant(0)
    tp = Topic(dp, f"Message{random.randint(1000000,9999999)}", Message)
    dr = DataReader(dp, tp)
    dw = DataWriter(dp, tp)

    matched_handles = dw.get_matched_subscriptions()
    for handle in matched_handles:
        matched_data = dw.get_matched_subscription_data(handle)
        print(f"matched data = {matched_data.key}")
        assert matched_data is not None
