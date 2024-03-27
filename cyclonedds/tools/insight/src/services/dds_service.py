import dds_data

import logging
import time
from cyclonedds import core, domain, builtin, dynamic, util, internal

IGNORE_TOPICS = ["DCPSParticipant", "DCPSPublication", "DCPSSubscription"]


def builtin_observer(domain_id, dds_data, running):
    logging.info(f"builtin_observer({domain_id}) ...")

    dds_data.add_domain(domain_id)

    domain_participant = domain.DomainParticipant(domain_id)

    rdp = builtin.BuiltinDataReader(domain_participant, builtin.BuiltinTopicDcpsParticipant)
    rcp = core.ReadCondition(
        rdp, core.SampleState.Any | core.ViewState.Any | core.InstanceState.Any
    )

    rdw = builtin.BuiltinDataReader(domain_participant, builtin.BuiltinTopicDcpsPublication)
    rcw = core.ReadCondition(
        rdw, core.SampleState.Any | core.ViewState.Any | core.InstanceState.Any
    )
    rdr = builtin.BuiltinDataReader(domain_participant, builtin.BuiltinTopicDcpsSubscription)
    rcr = core.ReadCondition(
        rdr, core.SampleState.Any | core.ViewState.Any | core.InstanceState.Any
    )

    logging.info("")

    while running[0]:

        time.sleep(1)

        for p in rdp.take(N=20, condition=rcp):
            #logging.info(p.sample_info)
            if p.sample_info.sample_state == core.SampleState.NotRead and p.sample_info.instance_state == core.InstanceState.Alive:

                logging.info("Found Participant: " + str(p))
                logging.debug("Qos: " + str(p.qos))
                dds_data.add_domain_participant(domain_id, p)
            elif p.sample_info.instance_state == core.InstanceState.NotAliveDisposed:
                logging.info("Removed Participant: " + str(p.key))
                dds_data.remove_domain_participant(domain_id, p)

        for pub in rdw.take(N=20, condition=rcw):
            #logging.info(pub.sample_info)
            if pub.sample_info.sample_state == core.SampleState.NotRead and pub.sample_info.instance_state == core.InstanceState.Alive:
                #logging.info("pub.pariticpantkey: " + str(pub.participant_key))
                #logging.debug("pub.qos: " + str(pub.qos))
                if pub.topic_name not in IGNORE_TOPICS:
                    dds_data.add_endpoint(domain_id, pub, True)

            elif pub.sample_info.instance_state == core.InstanceState.NotAliveDisposed:
                #logging.info("pub removed: " + str(pub.participant_key))
                dds_data.remove_endpoint(domain_id, pub)

        for sub in rdr.take(N=20, condition=rcr):

            # logging.info(sub.sample_info)
            if sub.sample_info.sample_state == core.SampleState.NotRead and sub.sample_info.instance_state == core.InstanceState.Alive:
                #logging.info("Found subscriber participant: " + str(sub.participant_key) + "on topic: " + str(sub.topic_name))
                #print(str(sub))
                if sub.topic_name not in IGNORE_TOPICS:
                    dds_data.add_endpoint(domain_id, sub, False)

            elif sub.sample_info.instance_state == core.InstanceState.NotAliveDisposed:
                #logging.info("Removed subscriber participant:" + str(sub.participant_key))
                dds_data.remove_endpoint(domain_id, sub)

    logging.info(f"builtin_observer({domain_id}) ... DONE")
