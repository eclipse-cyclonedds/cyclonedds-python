import pytest

from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.util import isgoodentity

from support_modules.testtopics import Message


def test_create_participant():
    dp = DomainParticipant(0)
    assert isgoodentity(dp)
