import pytest

from cyclonedds.core import DDSException
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import Publisher, DataWriter
from cyclonedds.util import duration, isgoodentity

from testtopics import Message, MessageKeyed


def test_initialize_writer():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message", Message)
    pub = Publisher(dp)
    dw = DataWriter(pub, tp)

    assert isgoodentity(dw)


def test_writeto_writer():
    dp = DomainParticipant(0)
    tp = Topic(dp, "Message", Message)
    pub = Publisher(dp)
    dw = DataWriter(pub, tp)

    msg = Message(
        message="TestMessage"
    )

    dw.write(msg)
    assert dw.wait_for_acks(duration(seconds=1))


def test_writer_instance(common_setup):
    handle = common_setup.dw.register_instance(common_setup.msg)
    assert handle > 0
    common_setup.dw.write(common_setup.msg)
    common_setup.dw.unregister_instance(common_setup.msg)

def test_writer_instance_handle(common_setup):
    handle = common_setup.dw.register_instance(common_setup.msg)
    assert handle > 0
    common_setup.dw.write(common_setup.msg)
    common_setup.dw.unregister_instance_handle(handle)


def test_writer_writedispose(common_setup):
    common_setup.dw.write_dispose(common_setup.msg)


def test_writer_lookup(common_setup):
    keymsg1 = MessageKeyed(user_id=1, message="Hello!")
    keymsg2 = MessageKeyed(user_id=2, message="Hello!")
    print(MessageKeyed.__idl__.key(keymsg1), MessageKeyed.__idl__.key(keymsg2))
    dw = DataWriter(common_setup.dp, Topic(common_setup.dp, "keyed_hello_world", MessageKeyed))
    assert None == dw.lookup_instance(keymsg1)
    assert None == dw.lookup_instance(keymsg2)
    handle1 = dw.register_instance(keymsg1)
    handle2 = dw.register_instance(keymsg2)
    assert handle1 > 0 and handle2 > 0 and handle1 != handle2
    assert handle1 == dw.lookup_instance(keymsg1)
    assert handle2 == dw.lookup_instance(keymsg2)
