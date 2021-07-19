from typing import Type
import pytest

from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.core import Qos, Policy
from cyclonedds.qos import DataWriterQos, PublisherQos

from testtopics import Message


def test_scoped_qos_apply(common_setup):
    with pytest.raises(TypeError):
        DomainParticipant(qos=Qos().topic())
    DomainParticipant(qos=Qos().domain_participant())

    with pytest.raises(TypeError):
        Topic(common_setup.dp, 'Message', Message, qos=Qos().domain_participant())
    Topic(common_setup.dp, 'Message', Message, qos=Qos().topic())

    with pytest.raises(TypeError):
        Publisher(common_setup.dp, qos=Qos().subscriber())
    Publisher(common_setup.dp, qos=Qos().publisher())

    with pytest.raises(TypeError):
        Subscriber(common_setup.dp, qos=Qos().publisher())
    Subscriber(common_setup.dp, qos=Qos().subscriber())

    with pytest.raises(TypeError):
        DataWriter(common_setup.pub, common_setup.tp, qos=Qos().datareader())
    DataWriter(common_setup.pub, common_setup.tp, qos=Qos().datawriter())

    with pytest.raises(TypeError):
        DataReader(common_setup.sub, common_setup.tp, qos=Qos().datawriter())
    DataReader(common_setup.sub, common_setup.tp, qos=Qos().datareader())


def test_scoped_qos_construct(common_setup):
    with pytest.raises(ValueError):
        DataWriterQos(
            Policy.Topicdata(b"hi!")
        )

    with pytest.raises(ValueError):
        PublisherQos(
            Policy.Liveliness.ManualByParticipant(120000)
        )

    next(iter(PublisherQos(
        Policy.Groupdata(b"hi!")
    ))) == Policy.Groupdata(b"hi!")

    next(iter(DataWriterQos(
        Policy.Userdata(b"hi!")
    ))) == Policy.Userdata(b"hi!")
