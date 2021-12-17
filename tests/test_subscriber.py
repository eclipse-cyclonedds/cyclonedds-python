import pytest

from cyclonedds.domain import DomainParticipant
from cyclonedds.sub import Subscriber
from cyclonedds.util import isgoodentity


def test_subscriber_initialize():
    dp = DomainParticipant(0)
    sub = Subscriber(dp)

    assert isgoodentity(sub)


def test_subscriber_wrong_usage_errors():
    dp = DomainParticipant(0)

    with pytest.raises(TypeError):
        Subscriber(False)

    with pytest.raises(TypeError):
        Subscriber(dp, qos=False)

    with pytest.raises(TypeError):
        Subscriber(dp, listener=False)


@pytest.mark.xfail
def test_subscriber_notify_readers():
    """This will fail, notify_readers is not yet implemented on the C side."""
    dp = DomainParticipant(0)
    sub = Subscriber(dp)
    sub.notify_readers()

