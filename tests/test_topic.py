import pytest

from cyclonedds.core import Entity
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.util import isgoodentity

from  testtopics import Message


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

    assert tp.typename == tp.get_type_name() == 'testtopics::message::Message'
