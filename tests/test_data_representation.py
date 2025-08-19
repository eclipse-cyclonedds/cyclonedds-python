import pytest

from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.sub import DataReader
from cyclonedds.pub import DataWriter
from cyclonedds.qos import Qos, Policy
from cyclonedds.core import DDSException


from support_modules.testtopics import XMessage, Message


def test_data_representation_writer_v0_match():
    qos = Qos(Policy.DataRepresentation(use_cdrv0_representation=True))

    dp = DomainParticipant(0)
    tp = Topic(dp, "Message", Message)
    dr = DataReader(dp, tp, qos=qos)
    dw = DataWriter(dp, tp, qos=qos)

    assert dw._use_version_2 == False

    msg = Message("Hello")
    dw.write(msg)
    assert dr.read_next() == msg


def test_data_representation_writer_v0_notdefault():
    qos = Qos(Policy.DataRepresentation(use_cdrv0_representation=True))

    dp = DomainParticipant(0)
    tp = Topic(dp, "XMessage", XMessage)
    dr = DataReader(dp, tp, qos=qos)
    dw = DataWriter(dp, tp, qos=qos)

    assert dw._use_version_2 == False

    msg = XMessage("Hello")
    dw.write(msg)
    assert dr.read_next() == msg


def test_data_representation_writer_v2_match():
    qos = Qos(Policy.DataRepresentation(use_xcdrv2_representation=True))

    dp = DomainParticipant(0)
    tp = Topic(dp, "XMessage", XMessage)
    dr = DataReader(dp, tp, qos=qos)
    dw = DataWriter(dp, tp, qos=qos)

    assert dw._use_version_2 == True

    msg = XMessage("Hello")
    dw.write(msg)
    assert dr.read_next() == msg


def test_data_representation_writer_v0_v2_unmatch():
    qosv0 = Qos(Policy.DataRepresentation(use_cdrv0_representation=True))
    qosv2 = Qos(Policy.DataRepresentation(use_xcdrv2_representation=True))

    dp = DomainParticipant(0)
    tp = Topic(dp, "Message", Message)
    dr = DataReader(dp, tp, qos=qosv0)
    dw = DataWriter(dp, tp, qos=qosv2)

    msg = Message("Hello")
    dw.write(msg)
    assert dr.read_next() == None


def test_data_representation_writer_v2_v0_unmatch():
    qosv0 = Qos(Policy.DataRepresentation(use_cdrv0_representation=True))
    qosv2 = Qos(Policy.DataRepresentation(use_xcdrv2_representation=True))

    dp = DomainParticipant(0)
    tp = Topic(dp, "Message", Message)
    dr = DataReader(dp, tp, qos=qosv2)
    dw = DataWriter(dp, tp, qos=qosv0)

    msg = Message("Hello")
    dw.write(msg)
    assert dr.read_next() == None


def test_data_representation_writer_dualreader_match():
    qosv0 = Qos(Policy.DataRepresentation(use_cdrv0_representation=True))
    qosv2 = Qos(Policy.DataRepresentation(use_xcdrv2_representation=True))
    qosv0v2 = Qos(Policy.DataRepresentation(use_cdrv0_representation=True, use_xcdrv2_representation=True))

    dp = DomainParticipant(0)
    tp = Topic(dp, "Message", Message)
    dr = DataReader(dp, tp, qos=qosv0v2)
    dwv0 = DataWriter(dp, tp, qos=qosv0)
    dwv2 = DataWriter(dp, tp, qos=qosv2)

    msg1 = Message("Hello")
    dwv0.write(msg1)
    assert dr.read_next() == msg1

    msg2 = Message("Hi!")
    dwv2.write(msg2)
    assert dr.read_next() == msg2

