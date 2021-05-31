import pytest
import threading

from cyclonedds.core import Qos, Policy
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.util import duration

# Allow the import of support modules for tests
import os.path as p
import sys
sys.path.append(p.join(p.abspath(p.dirname(__file__)), "support_modules/"))

from testtopics import Message

class Common:
    def __init__(self, domain_id=0):
        self.qos = Qos(Policy.Reliability.Reliable(duration(seconds=2)), Policy.History.KeepLast(10))

        self.dp = DomainParticipant(domain_id)
        self.tp = Topic(self.dp, 'Message', Message)
        self.pub = Publisher(self.dp)
        self.sub = Subscriber(self.dp)
        self.dw = DataWriter(self.pub, self.tp, qos=self.qos)
        self.dr = DataReader(self.sub, self.tp, qos=self.qos)
        self.msg = Message(message="hi")
        self.msg2 = Message(message="hi2")

global domain_id_counter
domain_id_counter = 0

@pytest.fixture
def common_setup():
    # Ensuring a unique domain id for each setup ensures parellization options
    global domain_id_counter
    domain_id_counter += 1
    return Common(domain_id=domain_id_counter)


class Manual:
    def __init__(self, domain_id=0):
        self.qos = Qos(Policy.Reliability.Reliable(duration(seconds=2)), Policy.History.KeepLast(10))

        self.dp = DomainParticipant(domain_id)
        self._tp = None
        self._pub = None
        self._sub = None
        self._dw = None
        self._dr = None
        self.msg = Message(message="hi")
        self.msg2 = Message(message="hi2")

    def tp(self, qos=None, listener=None):
        self._tp = Topic(self.dp, 'Message', Message, qos=qos, listener=listener)
        return self._tp

    def pub(self, qos=None, listener=None):
        self._pub = Publisher(self.dp, qos=qos, listener=listener)
        return self._pub

    def sub(self, qos=None, listener=None):
        self._sub = Subscriber(self.dp, qos=qos, listener=listener)
        return self._sub

    def dw(self, qos=None, listener=None):
        self._dw = DataWriter(
            self._pub if self._pub else self.pub(),
            self._tp if self._tp else self.tp(),
            qos=qos, listener=listener)
        return self._dw

    def dr(self, qos=None, listener=None):
        self._dr = DataReader(
            self._sub if self._sub else self.sub(),
            self._tp if self._tp else self.tp(),
            qos=qos, listener=listener)
        return self._dr


@pytest.fixture
def manual_setup():
    # Ensuring a unique domain id for each setup ensures parellization options
    global domain_id_counter
    domain_id_counter += 1
    return Manual(domain_id=domain_id_counter)


class HitPoint():
    def __init__(self) -> None:
        self.hp = threading.Event()
        self.data = None

    def was_hit(self, timeout=10.0):
        return self.hp.wait(timeout)

    def was_not_hit(self, timeout=0.5):
        return not self.hp.wait(timeout)

    def hit(self, data=None):
        self.data = data
        self.hp.set()


@pytest.fixture
def hitpoint():
    return HitPoint()


@pytest.fixture
def hitpoint_factory():
    return HitPoint