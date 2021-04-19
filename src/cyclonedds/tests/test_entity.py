import pytest

from cyclonedds.core import Entity, Listener, DDSException
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.util import isgoodentity

from  testtopics import Message


def test_create_entity():
    dp = DomainParticipant(0)

    assert isgoodentity(dp)


def test_delete_entity():
    dp = DomainParticipant(0)

    assert dp.get_participant() == dp

    reference = dp._ref
    del dp

    with pytest.raises(DDSException) as exc:
        Entity(reference).get_participant()
        
    # This test is weird, it can fail if other tests are also failing.
    # So if this test fails fix other tests first before spending any time here.
    assert exc.value.code == DDSException.DDS_RETCODE_PRECONDITION_NOT_MET


def test_get_parent():
    dp = DomainParticipant(0)

    assert dp.get_parent() == dp.parent == None

    tp = Topic(dp, 'Message', Message)

    assert isgoodentity(tp)
    assert tp.parent == tp.get_parent() == dp

    sub = Subscriber(dp)

    assert isgoodentity(sub)
    assert sub.parent == sub.get_parent() == dp

    pub = Publisher(dp)

    assert isgoodentity(pub)
    assert pub.parent == pub.get_parent() == dp

    dr = DataReader(sub, tp)

    assert isgoodentity(dr)
    assert dr.parent == dr.get_parent() == sub

    dw = DataWriter(pub, tp)

    assert isgoodentity(dw)
    assert dw.parent == dw.get_parent() == pub


def test_get_participant():
    dp = DomainParticipant(0)

    assert dp.participant == dp.get_participant() == dp

    tp = Topic(dp, "Message", Message)

    assert isgoodentity(tp)
    assert tp.participant == tp.get_participant() == dp

    sub = Subscriber(dp)

    assert isgoodentity(sub)
    assert sub.participant == sub.get_participant() == dp

    pub = Publisher(dp)

    assert isgoodentity(pub)
    assert pub.participant == pub.get_participant() == dp

    dr = DataReader(sub, tp)

    assert isgoodentity(dr)
    assert dr.participant == dr.get_participant() == dp

    dw = DataWriter(pub, tp)

    assert isgoodentity(dw)
    assert dw.participant == dw.get_participant() == dp


def test_get_children():
    dp = DomainParticipant(0)

    assert len(dp.children) == len(dp.get_children()) == 0

    tp = Topic(dp, "Message", Message)

    assert isgoodentity(tp)
    assert len(dp.children) == len(dp.get_children()) == 1
    assert dp.children[0] == dp.get_children()[0] == tp
    assert len(tp.children) == len(tp.get_children()) == 0

    sub = Subscriber(dp)

    assert isgoodentity(sub)
    assert len(dp.children) == len(dp.get_children()) == 2
    assert set(dp.children) == set([sub, tp])
    assert len(sub.children) == len(sub.get_children()) == 0

    pub = Publisher(dp)

    assert isgoodentity(pub)
    assert len(dp.children) == len(dp.get_children()) == 3
    assert set(dp.children) == set([pub, sub, tp])
    assert len(pub.children) == len(pub.get_children()) == 0

    dr = DataReader(sub, tp)

    assert isgoodentity(dr)
    assert set(dp.children) == set([pub, sub, tp])
    assert len(sub.children) == 1
    assert sub.children[0] == dr

    dw = DataWriter(pub, tp)

    assert isgoodentity(dw)
    assert set(dp.children) == set([pub, sub, tp])
    assert len(pub.children) == 1
    assert pub.children[0] == dw

    del dw
    del dr
    del pub
    del sub
    del tp

    assert len(dp.children) == len(dp.get_children()) == 0


def test_get_pubsub():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message", Message)
    sub = Subscriber(dp)
    pub = Publisher(dp)
    dr = DataReader(sub, tp)
    dw = DataWriter(pub, tp)

    assert dr.subscriber == dr.get_subscriber() == sub
    assert dw.publisher == dw.get_publisher() == pub

    with pytest.raises(DDSException) as exc:
        dp.get_subscriber()

    assert exc.value.code == DDSException.DDS_RETCODE_ILLEGAL_OPERATION


def test_get_listener():
    dp = DomainParticipant(0, listener=Listener())

    assert dp.get_listener()


def test_get_domainid():
    dp = DomainParticipant(2)
    assert dp.domainid == dp.get_domainid() == 2


def test_get_qos():
    dp = DomainParticipant(0)
    qos = dp.get_qos()
    assert qos == dp.get_qos()
    dp.set_qos(qos)


def test_set_listener():
    dp = DomainParticipant(0)
    dp.set_listener(Listener())


def test_retain_listener():
    m = lambda x, y: 0
    l = Listener(on_data_available=m)
    dp = DomainParticipant(0, listener=l)
    l = dp.get_listener()
    assert l.on_data_available == m


def test_get_guid():
    dp = DomainParticipant(0)
    dpa = DomainParticipant(1)
    
    assert dp.guid == dp.get_guid()
    assert dp.guid != dpa.guid