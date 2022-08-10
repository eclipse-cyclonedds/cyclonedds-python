import time
import re
from typing import List
from cyclonedds import core, domain, builtin, dynamic, util
from datetime import datetime, timedelta
from collections import defaultdict

from ..utils import LiveData
from ..idl import IdlType
from .ls_discoverables import DParticipant, DTopic, DPubSub
from .ps_discoverables import PApplication, PParticipant, PSystem


def ls_discovery(
    live: LiveData, domain_id: int, runtime: timedelta, topic: str
) -> List[DParticipant]:
    try:
        topic_re = re.compile(f"^{topic}$")
    except re.error:
        topic_re = re.compile(f"^{re.escape(topic)}$")

    dp = domain.DomainParticipant(domain_id)

    rdp = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsParticipant)
    rcp = core.ReadCondition(
        rdp, core.SampleState.NotRead | core.ViewState.Any | core.InstanceState.Alive
    )
    rdw = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsPublication)
    rcw = core.ReadCondition(
        rdw, core.SampleState.NotRead | core.ViewState.Any | core.InstanceState.Alive
    )
    rdr = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsSubscription)
    rcr = core.ReadCondition(
        rdr, core.SampleState.NotRead | core.ViewState.Any | core.InstanceState.Alive
    )

    participants = {}
    start = datetime.now()
    end = start + runtime
    while datetime.now() < end and not live.terminate:
        for p in rdp.take(N=20, condition=rcp):

            if p.key in participants:
                participants[p.key].sample = p
            else:
                participants[p.key] = DParticipant(sample=p, topics=[])
            if p.key == dp.guid:
                participants[p.key].is_self = True
            else:
                live.entities += 1

        for pub in rdw.take(N=20, condition=rcw):
            if pub.participant_key != dp.guid:
                live.entities += 1

            if not topic_re.match(pub.topic_name):
                continue

            pqos = pub.qos
            naming = None
            if core.Policy.EntityName in pqos:
                naming = pqos[core.Policy.EntityName]
                pqos = pqos - core.Qos(naming)

            if pub.participant_key in participants:
                par = participants[pub.participant_key]
            else:
                par = participants[pub.participant_key] = DParticipant(
                    sample=None, topics=[]
                )

            pub = DPubSub(endpoint=pub, qos=pqos, name=naming.name if naming else None)

            for topic in par.topics:
                if topic.name == pub.endpoint.topic_name:
                    topic.publications.append(pub)
                    break
            else:
                topic = DTopic(
                    name=pub.endpoint.topic_name, subscriptions=[], publications=[pub]
                )
                par.topics.append(topic)

        for sub in rdr.take(N=20, condition=rcr):
            if sub.participant_key != dp.guid:
                live.entities += 1

            if not topic_re.match(sub.topic_name):
                continue

            sqos = sub.qos
            naming = None
            if core.Policy.EntityName in sqos:
                naming = sqos[core.Policy.EntityName]
                sqos = sqos - core.Qos(naming)

            if sub.participant_key in participants:
                par = participants[sub.participant_key]
            else:
                par = participants[sub.participant_key] = DParticipant(
                    sample=None, topics=[]
                )

            sub = DPubSub(endpoint=sub, qos=sqos, name=naming.name if naming else None)

            for topic in par.topics:
                if topic.name == sub.endpoint.topic_name:
                    topic.subscriptions.append(sub)
                    break
            else:
                topic = DTopic(
                    name=sub.endpoint.topic_name, subscriptions=[sub], publications=[]
                )
                par.topics.append(topic)

        # yield thread
        time.sleep(0.01)

    live.result = list(participants.values())
    live.delivered = True


def ps_discovery(
    live: LiveData, domain_id: int, runtime: timedelta, show_self: bool, topic: str
) -> List[PApplication]:
    try:
        topic_re = re.compile(f"^{topic}$")
    except re.error:
        topic_re = re.compile(f"^{re.escape(topic)}$")

    dp = domain.DomainParticipant(domain_id)

    rdp = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsParticipant)
    rcp = core.ReadCondition(
        rdp, core.SampleState.NotRead | core.ViewState.Any | core.InstanceState.Alive
    )
    rdw = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsPublication)
    rcw = core.ReadCondition(
        rdw, core.SampleState.NotRead | core.ViewState.Any | core.InstanceState.Alive
    )
    rdr = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsSubscription)
    rcr = core.ReadCondition(
        rdr, core.SampleState.NotRead | core.ViewState.Any | core.InstanceState.Alive
    )

    applications = {}
    participants = {}

    hostname_get = core.Policy.Property("__Hostname", "")
    appname_get = core.Policy.Property("__ProcessName", "")
    pid_get = core.Policy.Property("__Pid", "")
    address_get = core.Policy.Property("__NetworkAddresses", "")

    start = datetime.now()
    end = start + runtime
    while datetime.now() < end and not live.terminate:
        for p in rdp.take(N=20, condition=rcp):
            if p.key == dp.guid and not show_self:
                continue

            hostname = (
                p.qos[hostname_get].value
                if p.qos[hostname_get] is not None
                else "Unknown"
            )
            appname = (
                p.qos[appname_get].value
                if p.qos[appname_get] is not None
                else "Unknown"
            )
            pid = p.qos[pid_get].value if p.qos[pid_get] is not None else "Unknown"
            address = (
                p.qos[address_get].value
                if p.qos[address_get] is not None
                else "Unknown"
            )

            key = f"{hostname}.{appname}.{pid}"
            name = (
                p.qos[core.Policy.EntityName].name
                if core.Policy.EntityName in p.qos
                else None
            )
            participant = PParticipant(name=name, key=p.key)
            live.entities += 1

            if p.key in participants:
                participant.topics = participants[p.key].topics

            participants[p.key] = participant

            if key in applications:
                applications[key].participants.append(participant)
            else:
                applications[key] = PApplication(
                    hostname=hostname,
                    appname=appname,
                    pid=pid,
                    addresses=address,
                    participants=[participant],
                )

        for pub in rdw.take(N=20, condition=rcw):
            if pub.participant_key == dp.guid:
                continue
            live.entities += 1

            if not topic_re.match(pub.topic_name):
                continue

            if pub.participant_key in participants:
                par = participants[pub.participant_key]
            else:
                par = participants[pub.participant_key] = DParticipant(
                    name=None, key=pub.participant_key
                )

            par.topics.add(pub.topic_name)

        for sub in rdr.take(N=20, condition=rcr):
            if sub.participant_key == dp.guid:
                continue
            live.entities += 1

            if not topic_re.match(sub.topic_name):
                continue

            if sub.participant_key in participants:
                par = participants[sub.participant_key]
            else:
                par = participants[sub.participant_key] = DParticipant(
                    name=None, key=sub.participant_key
                )

            par.topics.add(sub.topic_name)

        # yield thread
        time.sleep(0.01)

    live.result = PSystem(list(applications.values()))
    live.delivered = True


def type_discovery(
    live: LiveData, domain_id: int, runtime: timedelta, topic: str
) -> List[PApplication]:
    dp = domain.DomainParticipant(domain_id)

    rdw = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsPublication)
    rcw = core.ReadCondition(
        rdw, core.SampleState.NotRead | core.ViewState.Any | core.InstanceState.Alive
    )
    rdr = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsSubscription)
    rcr = core.ReadCondition(
        rdr, core.SampleState.NotRead | core.ViewState.Any | core.InstanceState.Alive
    )

    type_ids = set()
    participants = defaultdict(set)

    start = datetime.now()
    end = start + runtime
    while datetime.now() < end and not live.terminate:
        for pub in rdw.take(N=20, condition=rcw):
            if pub.topic_name == topic and pub.type_id is not None:
                type_ids.add(pub.type_id)
                participants[pub.type_id].add(pub.participant_key)
                live.entities += 1

        for sub in rdr.take(N=20, condition=rcr):
            if sub.topic_name == topic and sub.type_id is not None:
                type_ids.add(sub.type_id)
                participants[sub.type_id].add(sub.participant_key)
                live.entities += 1

        # yield thread
        time.sleep(0.01)

    data = []
    for type_id in type_ids:
        datatype, _ = dynamic.get_types_for_typeid(
            dp, type_id, util.duration(seconds=runtime.total_seconds())
        )
        data.append((datatype, IdlType.idl([datatype]), participants[type_id]))

    live.result = data
    live.delivered = True
