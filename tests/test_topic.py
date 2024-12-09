import pytest

from cyclonedds.core import Entity
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.util import isgoodentity
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
from cyclonedds.qos import Policy, Qos
from dataclasses import dataclass

from support_modules.testtopics import Message


def test_create_topic():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message", Message)

    assert isgoodentity(tp)


def test_get_name():
    dp = DomainParticipant(0)
    tp = Topic(dp, 'MessageTopic', Message)

    assert tp.name == tp.get_name() == 'MessageTopic'


def test_get_type_name():
    dp = DomainParticipant(0)
    tp = Topic(dp, 'MessageTopic', Message)

    assert tp.typename == tp.get_type_name() == 'Message'


def filter(topic: Topic, sample: Message) -> bool:
    if "Filter" in sample.message:
        return False
    return True


def test_topic_filter():
    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message, qos=Qos(Policy.History.KeepLast(5)))
    tp.set_topic_filter(filter)
    dw = DataWriter(dp, tp)
    dr = DataReader(dp, tp)

    dw.write(Message("Nice Message"))
    dw.write(Message("Test Filtering"))
    dw.write(Message("Hello"))
    dw.write(Message("lower case filter"))

    data = str(dr.read(5))
    assert "Filter" not in data
    assert "filter" and "Hello" and "Nice" in data
