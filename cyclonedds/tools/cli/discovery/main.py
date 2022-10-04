from dataclasses import dataclass
import time
import re
from typing import List
from cyclonedds import core, domain, builtin, dynamic, util, internal
from datetime import datetime, timedelta
from collections import defaultdict

from ..utils import LiveData
from ..idl import IdlType
from .ls_discoverables import DParticipant, DTopic, DPubSub
from .ps_discoverables import PApplication, PParticipant, PSystem
from .type_discoverables import DiscoveredType, TypeDiscoveryData


def ls_discovery(
    live: LiveData, domain_id: int, runtime: timedelta, topic: str, show_qos: bool
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

    if internal.feature_topic_discovery:
        rdt = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsTopic)
        rct = core.ReadCondition(
            rdt,
            core.SampleState.NotRead | core.ViewState.Any | core.InstanceState.Alive,
        )

    participants = {}
    topic_qos = {}
    start = datetime.now()
    end = start + runtime
    while datetime.now() < end and not live.terminate:
        for p in rdp.take(N=20, condition=rcp):
            if p.key in participants:
                participants[p.key].sample = p
            else:
                participants[p.key] = DParticipant(
                    sample=p, topics=[], show_qos=show_qos
                )
            if p.key == dp.guid:
                participants[p.key].is_self = True
            else:
                live.entities += 1

        if internal.feature_topic_discovery:
            for t in rdt.take(N=20, condition=rct):
                if not topic_re.match(t.topic_name):
                    continue

                for participant in participants.values():
                    for topic in participant.topics:
                        if topic.name == t.topic_name:
                            topic.qos = t.qos
                            break

                topic_qos[t.topic_name] = t.qos

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
                    sample=None, topics=[], show_qos=show_qos
                )

            pub = DPubSub(endpoint=pub, qos=pqos, name=naming.name if naming else None)

            for topic in par.topics:
                if topic.name == pub.endpoint.topic_name:
                    topic.publications.append(pub)
                    break
            else:
                topic = DTopic(
                    name=pub.endpoint.topic_name,
                    subscriptions=[],
                    publications=[pub],
                    show_qos=show_qos,
                    qos=topic_qos.get(pub.endpoint.topic_name, core.Qos()),
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
                    sample=None, topics=[], show_qos=show_qos
                )

            sub = DPubSub(endpoint=sub, qos=sqos, name=naming.name if naming else None)

            for topic in par.topics:
                if topic.name == sub.endpoint.topic_name:
                    topic.subscriptions.append(sub)
                    break
            else:
                topic = DTopic(
                    name=sub.endpoint.topic_name,
                    subscriptions=[sub],
                    publications=[],
                    show_qos=show_qos,
                    qos=topic_qos.get(sub.endpoint.topic_name, core.Qos()),
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

    if internal.feature_topic_discovery:
        rdt = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsTopic)
        rct = core.ReadCondition(
            rdt,
            core.SampleState.NotRead | core.ViewState.Any | core.InstanceState.Alive,
        )

    discovery_data = TypeDiscoveryData()

    start = datetime.now()
    end = start + runtime
    while datetime.now() < end and not live.terminate:
        for t in rdt.take(N=20, condition=rct):
            if t.topic_name == topic:
                discovery_data.topic_qosses.append(t.qos)

        for pub in rdw.take(N=20, condition=rcw):
            if pub.topic_name == topic:
                if pub.type_id is not None:
                    discovery_data.add_type_id(str(pub.participant_key), pub.type_id)
                discovery_data.writer_qosses.append(pub.qos)
                live.entities += 1

        for sub in rdr.take(N=20, condition=rcr):
            if sub.topic_name == topic:
                if sub.type_id is not None:
                    discovery_data.add_type_id(str(sub.participant_key), sub.type_id)
                discovery_data.reader_qosses.append(sub.qos)
                live.entities += 1

        # yield thread
        time.sleep(0.01)

    for type_id, discovered_type in discovery_data.types.items():
        datatype, all_nested_datatypes = dynamic.get_types_for_typeid(
            dp, type_id, util.duration(seconds=runtime.total_seconds())
        )

        discovered_type.code = IdlType.idl([datatype])
        discovered_type.dtype = datatype
        discovered_type.nested_dtypes = all_nested_datatypes

    live.result = discovery_data
    live.delivered = True
