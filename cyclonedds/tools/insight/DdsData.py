# This Python file uses the following encoding: utf-8

from dataclasses import dataclass

@dataclass
class Application:
    id: str
    participants = []
    #hostname_get = core.Policy.Property("__Hostname", "")
    #appname_get = core.Policy.Property("__ProcessName", "")
    #pid_get = core.Policy.Property("__Pid", "")
    #address_get = core.Policy.Property("__NetworkAddresses", "")


@dataclass
class Domain:
    id: int
    participants = []

    def add_participant(self, participant):
        self.participants.append(participant)


@dataclass
class Participant:
    id: str
    hostname: str
    appname: str
    pid: str
    address: str

    #hostname_get = core.Policy.Property("__Hostname", "")
    #appname_get = core.Policy.Property("__ProcessName", "")
    #pid_get = core.Policy.Property("__Pid", "")
    #address_get = core.Policy.Property("__NetworkAddresses", "")

    topics = []

    def add_topic(self):
        print("add topic")

@dataclass
class Topic:
    name: str
    qos: str

    publisher = []
    subscriber = []

@dataclass
class Publisher:
    qos: str
    writer: str

@dataclass
class Writer:
    qos: str

@dataclass
class Subscriber:
    qos: str
    reader: str

@dataclass
class Reader:
    qos: str

class DdsData:

    domains = []

    def __init__(self):
        pass

    def add_domain(self, domain_id: int):
        for domain in self.domains:
            if domain.id == domain_id:
                # Already known domain
                return

        self.domains.append(Domain(id=domain_id))

    def add_domain_participant(self, domain_id, participant):
        for domain in self.domains:
            if domain.id == domain_id:
                domain.add_participant(participant)





