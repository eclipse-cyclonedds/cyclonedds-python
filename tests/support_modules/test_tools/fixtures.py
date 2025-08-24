import threading, os
from datetime import datetime
from typing import Optional, List

from cyclonedds.core import Qos, Policy
from cyclonedds.domain import Domain, DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.util import duration

from ..testtopics import Message


class DomainTag:
    def __init__(self, domain_id=0):
        self.d = Domain(domain_id, f"<Discovery><Tag>pytest_domain_{os.getpid()}</Tag></Discovery>")

class Common(DomainTag):
    def __init__(self, domain_id=0):
        super().__init__(domain_id)
        self.qos = Qos(Policy.Reliability.Reliable(duration(seconds=2)), Policy.History.KeepLast(10))

        self.dp = DomainParticipant(domain_id)
        self.tp = Topic(self.dp, 'Message', Message)
        self.pub = Publisher(self.dp)
        self.sub = Subscriber(self.dp)
        self.dw = DataWriter(self.pub, self.tp, qos=self.qos)
        self.dr = DataReader(self.sub, self.tp, qos=self.qos)
        self.msg = Message(message="hi")
        self.msg2 = Message(message="hi2")


class Manual(DomainTag):
    def __init__(self, domain_id=0):
        super().__init__(domain_id)
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


class HitPoint:
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


class FuzzingConfig:
    def __init__(
            self, *,
            num_types: int = 20,
            num_samples: int = 10,
            store_reproducers: bool = False,
            type_seed: int = 1,
            idl_file: Optional[str] = None,
            typenames: Optional[str] = None,
            skip_types: int = 0,
            mutation_failure_fatal: bool = False,
            xcdr_version: int = 2
        ) -> None:
        self.num_types: int = num_types
        self.num_samples: int = num_samples
        self.type_seed: int = type_seed
        self.store_reproducers: bool = store_reproducers
        self.idl_file: Optional[str] = idl_file
        self.typenames: Optional[List[str]] = None if typenames is None else typenames.split(',')
        self.skip_types: int = skip_types
        self.mutation_failure_fatal: bool = mutation_failure_fatal
        self.xcdr_version: int = xcdr_version
