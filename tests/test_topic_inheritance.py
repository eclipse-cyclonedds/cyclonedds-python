import asyncio
import pytest

import cyclonedds.idl as idl
import cyclonedds.idl.annotations as annotate

from dataclasses import dataclass
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
from cyclonedds.util import duration


@dataclass
@annotate.mutable
@annotate.autoid("sequential")
class Base(idl.IdlStruct, typename="Hierarchy.Base"):
    fieldA: str


@dataclass
@annotate.mutable
@annotate.autoid("sequential")
class Derived(Base, typename="Hierarchy.Derived"):
    fieldB: str


@pytest.mark.asyncio
async def test_base_topic():
    '''
    Creates a publisher and a subscriber of the Base topic and checks if the
    update sent by the publisher is received by the subscriber.
    '''
    base = Base(fieldA='Lorem')
    tasks = [
        _subscriber(Base),
        _publisher(Base, base),
    ]
    results = await asyncio.gather(*tasks)
    assert results[0] == results[1]


@pytest.mark.asyncio
async def test_derived_topic():
    '''
    Creates a publisher and a subscriber of the Derived topic and checks if the
    update sent by the publisher is received by the subscriber.
    '''
    derived = Derived(
        fieldA='Ipsum',
        fieldB='Dolor')

    tasks = [
        _subscriber(Derived),
        _publisher(Derived, derived),
    ]

    results = await asyncio.gather(*tasks)
    assert results[0] == results[1]


@pytest.mark.asyncio
async def test_base_and_derived_topics():
    '''
    Creates publishers and a subscribers of the Base and Derived topics and
    checks if the updates sent by the publishers are received by the
    subscribers.
    '''
    base = Base(fieldA='Lorem')
    derived = Derived(
        fieldA='Ipsum',
        fieldB='Dolor')

    tasks = [
        # This should not be necessary. I suspect there is a bug in CycloneDDS
        _subscriber(Base),
        _publisher(Base, base),

        # This is the part of the test that really matters
        _subscriber(Derived),
        _publisher(Derived, derived),
    ]

    results = await asyncio.gather(*tasks)
    assert results[0] == results[1]
    assert results[2] == results[3]


async def _publisher(topicClass, value, timeout=2):
    '''
    Publishes an update with a given value.
    '''
    participant = DomainParticipant(0)
    topic = Topic(participant, topicClass.__name__, topicClass)
    writer = DataWriter(participant, topic)
    writer.write(value)
    await asyncio.sleep(timeout)
    return value


async def _subscriber(topicClass, timeout=2):
    '''
    Receives an update. Raises an exception if no update is received within a
    given timeout.
    '''
    participant = DomainParticipant(0)
    topic = Topic(participant, topicClass.__name__, topicClass)
    reader = DataReader(participant, topic)
    async for update in reader.read_aiter(timeout=duration(seconds=timeout)):
        return update
