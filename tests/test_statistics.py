import pytest
import time

from cyclonedds.core import Statistics
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.sub import Subscriber, DataReader
from cyclonedds.pub import Publisher, DataWriter

from support_modules.testtopics import Message


def test_create_statistics():
    dp = DomainParticipant(0)
    tp = Topic(dp, "statistics", Message)
    dw = DataWriter(dp, tp)
    stat = Statistics(dw)
    print(f"stat = {stat}")
    assert stat.data


def test_refresh_statistics():
    dp = DomainParticipant(0)
    tp = Topic(dp, "statistics", Message)
    dw = DataWriter(dp, tp)
    stat = Statistics(dw)
    assert stat.data
    time.sleep(0.5)
    stat.refresh()
    assert stat.time != 0
