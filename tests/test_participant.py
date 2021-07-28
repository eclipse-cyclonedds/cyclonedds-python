import pytest

from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.util import isgoodentity

from  testtopics import Message


def test_create_participant():
    dp = DomainParticipant(0)
    assert isgoodentity(dp)


def test_find_topic():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message", Message)

    assert isgoodentity(tp)
    
    xtp = dp.find_topic("Message")

    assert xtp.typename == tp.typename
    assert xtp.name == tp.name
