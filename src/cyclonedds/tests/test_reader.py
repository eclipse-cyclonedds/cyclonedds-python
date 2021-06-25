import pytest

from cyclonedds.domain import Domain, DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.util import duration, isgoodentity


from  testtopics import Message

def test_reader_initialize():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message", Message)
    sub = Subscriber(dp)
    dr = DataReader(sub, tp)

    assert isgoodentity(dr)
    
def test_reader_initialize_direct():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message", Message)
    dr = DataReader(dp, tp)

    assert isgoodentity(dr)


def test_reader_read():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message__DONOTPUBLISH", Message)
    sub = Subscriber(dp)
    dr = DataReader(sub, tp)

    assert len(dr.read()) == 0


def test_reader_take():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message__DONOTPUBLISH", Message)
    sub = Subscriber(dp)
    dr = DataReader(sub, tp)

    assert len(dr.take()) == 0


def test_reader_waitforhistoricaldata():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message__DONOTPUBLISH", Message)
    sub = Subscriber(dp)
    dr = DataReader(sub, tp)

    assert dr.wait_for_historical_data(duration(milliseconds=5))


def test_reader_resizebuffer():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message__DONOTPUBLISH", Message)
    sub = Subscriber(dp)
    dr = DataReader(sub, tp)

    assert len(dr.read(N=100)) == 0
    assert len(dr.read(N=200)) == 0
    assert len(dr.read(N=100)) == 0


def test_reader_invalid():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message__DONOTPUBLISH", Message)
    sub = Subscriber(dp)
    dr = DataReader(sub, tp)

    with pytest.raises(TypeError):
        dr.read(-1)

    with pytest.raises(TypeError):
        dr.take(-1)


def test_reader_readnext_takenext():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message__DONOTPUBLISH", Message)
    sub = Subscriber(dp)
    pub = Publisher(dp)
    dr = DataReader(sub, tp)
    dw = DataWriter(pub, tp)

    msg = Message("Hello")
    dw.write(msg)

    assert dr.read_next() == msg
    assert dr.read_next() is None
    dw.write(msg)
    assert dr.take_next() == msg
    assert dr.take_next() is None


def test_reader_readiter():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message", Message)
    sub = Subscriber(dp)
    pub = Publisher(dp)
    dr = DataReader(sub, tp)
    dw = DataWriter(pub, tp)

    msg = Message("Hello")
    dw.write(msg)

    read = False

    for msgr in dr.read_iter(timeout=duration(milliseconds=10)):
        assert not read
        assert msg == msgr
        read = True


def test_reader_takeiter():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message", Message)
    sub = Subscriber(dp)
    pub = Publisher(dp)
    dr = DataReader(sub, tp)
    dw = DataWriter(pub, tp)

    msg = Message("Hello")
    dw.write(msg)

    read = False

    for msgr in dr.take_iter(timeout=duration(milliseconds=10)):
        assert not read
        assert msg == msgr
        read = True


def _make_reader_without_saving_deps():
    tp = Topic(DomainParticipant(0), "Message", Message)
    return DataReader(Subscriber(tp.participant), tp)


def test_reader_keepalive_parents():
    dr = _make_reader_without_saving_deps()

    msg = Message("Hello")
    dw = DataWriter(dr.participant, dr.topic).write(msg)

    assert dr.read_next() == msg