import time
from typing import Any
from cyclonedds import qos, domain, sub, topic

from ..utils import LiveData


def subscribe(
    live: LiveData,
    domain_id: int,
    topic_name: str,
    datatype: Any,
    topicqos: qos.Qos,
    readerqos: qos.Qos,
):
    dp = domain.DomainParticipant(domain_id)
    tp = topic.Topic(dp, topic_name, datatype, qos=topicqos)
    rd = sub.DataReader(dp, tp, qos=readerqos)

    while not live.terminate:
        for data in rd.take(N=20):
            live.printables.put(data, block=True)

        # yield thread
        time.sleep(0.01)

    live.delivered = True
