import pytest

from cyclonedds.core import DDSException
from cyclonedds.domain import DomainParticipant
from cyclonedds.pub import Publisher
from cyclonedds.util import isgoodentity


def test_initialize_publisher():
    dp = DomainParticipant(0)
    pub = Publisher(dp)

    assert isgoodentity(pub)


def test_suspension():
    dp = DomainParticipant(0)
    pub = Publisher(dp)

    with pytest.raises(DDSException) as exc:
        pub.suspend()
    assert exc.value.code == DDSException.DDS_RETCODE_UNSUPPORTED

    with pytest.raises(DDSException) as exc:
        pub.resume()
    assert exc.value.code == DDSException.DDS_RETCODE_UNSUPPORTED
