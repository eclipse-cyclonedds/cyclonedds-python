import logging
from cyclonedds import core, domain, builtin
from cyclonedds.util import duration
from utils import EntityType

IGNORE_TOPICS = ["DCPSParticipant", "DCPSPublication", "DCPSSubscription"]


def builtin_observer(domain_id, dds_data, running):
    logging.info(f"builtin_observer({domain_id}) ...")

    domain_participant = domain.DomainParticipant(domain_id)
    waitset = core.WaitSet(domain_participant)

    rdp = builtin.BuiltinDataReader(domain_participant, builtin.BuiltinTopicDcpsParticipant)
    rcp = core.ReadCondition(
        rdp, core.SampleState.Any | core.ViewState.Any | core.InstanceState.Any)
    waitset.attach(rcp)

    rdw = builtin.BuiltinDataReader(domain_participant, builtin.BuiltinTopicDcpsPublication)
    rcw = core.ReadCondition(
        rdw, core.SampleState.Any | core.ViewState.Any | core.InstanceState.Any)
    waitset.attach(rcw)

    rdr = builtin.BuiltinDataReader(domain_participant, builtin.BuiltinTopicDcpsSubscription)
    rcr = core.ReadCondition(
        rdr, core.SampleState.Any | core.ViewState.Any | core.InstanceState.Any)
    waitset.attach(rcr)

    logging.info("")

    while running[0]:

        amount_triggered = 0
        try:
            amount_triggered = waitset.wait(duration(milliseconds=100))
        except:
            pass
        if amount_triggered == 0:
            continue

        for p in rdp.take(condition=rcp):
            if p.sample_info.sample_state == core.SampleState.NotRead and p.sample_info.instance_state == core.InstanceState.Alive:
                dds_data.add_domain_participant(domain_id, p)
            elif p.sample_info.instance_state == core.InstanceState.NotAliveDisposed:
                dds_data.remove_domain_participant(domain_id, p)

        for pub in rdw.take(condition=rcw):
            if pub.sample_info.sample_state == core.SampleState.NotRead and pub.sample_info.instance_state == core.InstanceState.Alive:
                if pub.topic_name not in IGNORE_TOPICS:
                    dds_data.add_endpoint(domain_id, pub, EntityType.WRITER)
            elif pub.sample_info.instance_state == core.InstanceState.NotAliveDisposed:
                dds_data.remove_endpoint(domain_id, pub)

        for sub in rdr.take(condition=rcr):
            if sub.sample_info.sample_state == core.SampleState.NotRead and sub.sample_info.instance_state == core.InstanceState.Alive:
                if sub.topic_name not in IGNORE_TOPICS:
                    dds_data.add_endpoint(domain_id, sub, EntityType.READER)
            elif sub.sample_info.instance_state == core.InstanceState.NotAliveDisposed:
                dds_data.remove_endpoint(domain_id, sub)

    logging.info(f"builtin_observer({domain_id}) ... DONE")
