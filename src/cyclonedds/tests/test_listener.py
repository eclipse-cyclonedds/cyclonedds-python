import pytest

from cyclonedds.core import Listener, Qos, Policy
from cyclonedds.util import duration, timestamp


def test_on_data_available(manual_setup, hitpoint):
    class L(Listener):
        def on_data_available(self, _):
            hitpoint.hit()

    manual_setup.dr(listener=L())
    manual_setup.dw().write(manual_setup.msg)

    assert hitpoint.was_hit()


def test_data_available_listeners(manual_setup, hitpoint_factory):
    hpf = hitpoint_factory

    class MyListener(Listener):
        def __init__(self):
            super().__init__()
            self.hitpoint_data_available = hpf()
            self.hitpoint_pub_matched = hpf()
            self.hitpoint_sub_matched = hpf()

        def on_data_available(self, reader):
            self.hitpoint_data_available.hit()

        def on_publication_matched(self, writer,status):
            self.hitpoint_pub_matched.hit()

        def on_subscription_matched(self, reader, status):
            self.hitpoint_sub_matched.hit()

    domain_participant_listener = MyListener()
    manual_setup.dp.listener = domain_participant_listener

    publisher_listener = MyListener()
    manual_setup.pub(listener=publisher_listener)

    subscriber_listener = MyListener()
    manual_setup.sub(listener=subscriber_listener)

    datawriter_listener = MyListener()
    datawriter = manual_setup.dw(listener=datawriter_listener)

    datareader_listener = MyListener()
    manual_setup.dr(listener=datareader_listener)

    datawriter.write(manual_setup.msg)

    #  Assertions, _only_ datawriter should publication match,
    # _only_ datareader should subscriber match and receive data

    assert datawriter_listener.hitpoint_pub_matched.was_hit()
    assert datareader_listener.hitpoint_sub_matched.was_hit()
    assert datareader_listener.hitpoint_data_available.was_hit()

    assert domain_participant_listener.hitpoint_pub_matched.was_not_hit()
    assert domain_participant_listener.hitpoint_sub_matched.was_not_hit()
    assert domain_participant_listener.hitpoint_data_available.was_not_hit()

    assert publisher_listener.hitpoint_pub_matched.was_not_hit()
    assert publisher_listener.hitpoint_sub_matched.was_not_hit()
    assert publisher_listener.hitpoint_data_available.was_not_hit()

    assert subscriber_listener.hitpoint_pub_matched.was_not_hit()
    assert subscriber_listener.hitpoint_sub_matched.was_not_hit()
    assert subscriber_listener.hitpoint_data_available.was_not_hit()

    assert datawriter_listener.hitpoint_sub_matched.was_not_hit()
    assert datawriter_listener.hitpoint_data_available.was_not_hit()

    assert datareader_listener.hitpoint_pub_matched.was_not_hit()


def test_on_offered_deadline_missed(manual_setup, hitpoint):
    class MyListener(Listener):
        def on_offered_deadline_missed(self, writer, status):
            hitpoint.hit(data=timestamp.now())

    wqos = Qos(Policy.Deadline(duration(seconds=0.2)))
    datawriter = manual_setup.dw(qos=wqos, listener=MyListener())
    manual_setup.dr()

    write_time = timestamp.now()
    datawriter.write(manual_setup.msg)

    assert hitpoint.was_hit()
    delay = hitpoint.data - write_time
    assert delay >= duration(seconds=0.2)  


def test_on_offered_incompatible_qos(manual_setup, hitpoint):
    class MyListener(Listener):
        def on_offered_incompatible_qos(self, writer, status):
            hitpoint.hit()

    wqos = Qos(Policy.Durability.Volatile)
    rqos = Qos(Policy.Durability.Transient)

    datawriter = manual_setup.dw(qos=wqos, listener=MyListener())
    manual_setup.dr(qos=rqos)

    datawriter.write(manual_setup.msg)

    assert hitpoint.was_hit()


def test_on_requested_incompatible_qos(manual_setup, hitpoint):
    class MyListener(Listener):
        def on_requested_incompatible_qos(self, writer, status):
            hitpoint.hit()

    wqos = Qos(Policy.Durability.Volatile)
    rqos = Qos(Policy.Durability.Transient)

    manual_setup.dr(qos=rqos, listener=MyListener())
    datawriter = manual_setup.dw(qos=wqos)

    datawriter.write(manual_setup.msg)

    assert hitpoint.was_hit()


def test_liveliness(manual_setup, hitpoint_factory):
    handler = hitpoint_factory()
    alive = hitpoint_factory()
    notalive = hitpoint_factory()

    class MyListenerWriter(Listener):
        def on_liveliness_lost(self, writer, status):
            handler.hit(data=timestamp.now())

    class MyListenerReader(Listener):
        def on_liveliness_changed(self, reader, status):
            if status.alive_count == 1:
                alive.hit(data=status.alive_count_change)
            else:
                notalive.hit(data=status.alive_count_change)

    qos = Qos(
        Policy.Liveliness.ManualByTopic(duration(seconds=0.2)),
        Policy.Ownership.Exclusive
    )

    manual_setup.tp(qos=qos)
    manual_setup.dr(listener=MyListenerReader())
    datawriter = manual_setup.dw(listener=MyListenerWriter())

    write_time = timestamp.now()
    datawriter.write(manual_setup.msg)

    assert handler.was_hit()
    assert handler.data - write_time >= duration(seconds=0.2)
    assert alive.was_hit() and alive.data == 1
    assert notalive.was_hit() and notalive.data == -1


def test_on_requested_deadline_missed(manual_setup, hitpoint):
    class MyListener(Listener):
        def on_requested_deadline_missed(self, reader, status):
            hitpoint.hit(data=timestamp.now())

    qos = Qos(Policy.Deadline(duration(seconds=0.2)))
    datawriter = manual_setup.dw(qos=qos)
    manual_setup.dr(qos=qos, listener=MyListener())

    write_time = timestamp.now()
    datawriter.write(manual_setup.msg)

    assert hitpoint.was_hit()
    assert hitpoint.data - write_time >= duration(seconds=0.2)


def test_on_sample_rejected(manual_setup, hitpoint):
    class MyListener(Listener):
        def on_sample_rejected(self, reader, status):
            hitpoint.hit()

    qos = Qos(Policy.ResourceLimits(max_samples=1))

    datawriter = manual_setup.dw()
    manual_setup.dr(qos=qos, listener=MyListener())

    datawriter.write(manual_setup.msg)
    assert hitpoint.was_not_hit()

    datawriter.write(manual_setup.msg2)
    assert hitpoint.was_hit()


def test_on_sample_lost(manual_setup, hitpoint):
    class MyListener(Listener):
        def on_sample_lost(self, reader, status):
            hitpoint.hit()

    qos = Qos(Policy.DestinationOrder.BySourceTimestamp)

    datawriter = manual_setup.dw(qos=qos)
    datareader = manual_setup.dr(qos=qos, listener=MyListener())

    t1 = timestamp.now()
    t2 = t1 + duration(seconds=1)

    datawriter.write(manual_setup.msg, timestamp=t2)
    datareader.take()
    datawriter.write(manual_setup.msg, timestamp=t1)

    assert hitpoint.was_hit()


