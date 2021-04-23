import pytest

from cyclonedds.domain import DomainParticipant
from cyclonedds.sub import Subscriber
from cyclonedds.util import isgoodentity


def test_initialize_subscriber():
    dp = DomainParticipant(0)
    sub = Subscriber(dp)

    assert isgoodentity(sub)
