import os
import sys
import pytest
import threading
from datetime import datetime

# Allow the import of support modules for tests
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), "support_modules/"))

# Remove working dir to avoid importing the un-installed cyclonedds install
try:
    sys.path.remove(os.getcwd())
except:
    pass

from cyclonedds.core import Qos, Policy
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.util import duration

from testtopics import Message
from virtual_test_env import VirtualEnvWithPyCCompat


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
        self.creation = datetime.now()

    def was_hit(self, timeout=10.0):
        return self.hp.wait(timeout)

    def was_not_hit(self, timeout=0.5):
        return not self.hp.wait(timeout)

    def hit(self, data=None):
        self.data = data
        self.hittime = datetime.now()
        self.hp.set()

    def time_to_hit(self):
        return self.hittime - self.creation


@pytest.fixture
def hitpoint():
    return HitPoint()


@pytest.fixture
def hitpoint_factory():
    return HitPoint


@pytest.fixture(scope="session")
def virtualenv_with_py_c_compat():
    return VirtualEnvWithPyCCompat()