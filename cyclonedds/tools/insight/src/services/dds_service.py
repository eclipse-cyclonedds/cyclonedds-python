import dds_data

import logging
import time
from cyclonedds import core, domain, builtin, dynamic, util, internal


class Listener(core.Listener):

    def on_inconsistent_topic(self, reader, status) -> None:
        logging.info("on_inconsistent_topic")

    # def on_data_available(self, reader) -> None:
    #     logging.info("on_data_available", reader)
    #     if reader:
    #         cond = core.ReadCondition(
    #             reader, core.SampleState.Any | core.ViewState.Any | core.InstanceState.Any
    #         )
    #         for sample in reader.take(N=20, condition=cond):
    #             logging.info("")
    #             logging.info(sample)
    #             logging.info(sample.sample_info)

    def on_liveliness_lost(self, writer, status) -> None:
        logging.info("on_liveliness_lost")

    def on_liveliness_changed(self, reader, status) -> None:
        logging.info("on_liveliness_changed, alive_count: " + str(status.alive_count))

    def on_offered_deadline_missed(self, writer, status) -> None:
        logging.info("on_offered_deadline_missed")

    def on_offered_incompatible_qos(self, writer, status) -> None:
        logging.info("xxxxxxxxxxxxxxx on_offered_incompatible_qos")

    def on_data_on_readers(self, subscriber) -> None:
        logging.info("on_data_on_readers")

    def on_sample_lost(self, writer, status) -> None:
        logging.info("on_sample_lost")

    def on_sample_rejected(self, reader, status) -> None:
        logging.info("on_sample_rejected")

    def on_requested_deadline_missed(self, reader, status) -> None:
        logging.info("on_requested_deadline_missed")

    def on_requested_incompatible_qos(self, reader, status) -> None:
        logging.info("xxxxxxxxxxxx   on_requested_incompatible_qos")

    def on_publication_matched(self, writer, status) -> None:
        logging.info("on_publication_matched")

    def on_subscription_matched(self, reader, status) -> None:
        logging.info("on_subscription_matched")


def builtin_observer(domain_id, dds_data, running):
    logging.info(f"builtin_observer({domain_id}) ...")

    dds_data.add_domain(domain_id)

    domain_participant = domain.DomainParticipant(domain_id)

    listener_participant = Listener()
    listener_pub= Listener()
    listener_sub = Listener()

    rdp = builtin.BuiltinDataReader(domain_participant, builtin.BuiltinTopicDcpsParticipant)#, listener=listener_participant)
    rcp = core.ReadCondition(
        rdp, core.SampleState.Any | core.ViewState.Any | core.InstanceState.Any
    )

    rdw = builtin.BuiltinDataReader(domain_participant, builtin.BuiltinTopicDcpsPublication)#, listener=listener_pub)
    rcw = core.ReadCondition(
        rdw, core.SampleState.Any | core.ViewState.Any | core.InstanceState.Any
    )
    rdr = builtin.BuiltinDataReader(domain_participant, builtin.BuiltinTopicDcpsSubscription)#, listener=listener_sub)
    rcr = core.ReadCondition(
        rdr, core.SampleState.Any | core.ViewState.Any | core.InstanceState.Any
    )

    hostname_get = core.Policy.Property("__Hostname", "")
    appname_get = core.Policy.Property("__ProcessName", "")
    pid_get = core.Policy.Property("__Pid", "")
    address_get = core.Policy.Property("__NetworkAddresses", "")

    logging.info("")

    while running[0]:

        time.sleep(1)

        for p in rdp.take(N=20, condition=rcp):
            #logging.info(p.sample_info)
            if p.sample_info.sample_state == core.SampleState.NotRead and p.sample_info.instance_state == core.InstanceState.Alive:
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
                logging.info("Found Participant: " + str(p))
                logging.debug("Qos: " + str(p.qos))
                dds_data.add_domain_participant(domain_id, p)#DdsData.Participant(p.key, hostname, appname, pid, address))
            elif p.sample_info.instance_state == core.InstanceState.NotAliveDisposed:
                logging.info("Removed Participant: " + str(p.key))
                dds_data.remove_domain_participant(domain_id, p)#DdsData.Participant(p.key, "", "",  "",  ""))

        for pub in rdw.take(N=20, condition=rcw):
            #logging.info(pub.sample_info)
            if pub.sample_info.sample_state == core.SampleState.NotRead and pub.sample_info.instance_state == core.InstanceState.Alive:
                logging.info("pub.pariticpantkey: " + str(pub.participant_key))
                logging.debug("pub.qos: " + str(pub.qos))
                print(type(pub), "<------------------------------")
                dds_data.add_endpoint(domain_id, pub)

            elif pub.sample_info.instance_state == core.InstanceState.NotAliveDisposed:
                logging.info("pub removed: " + str(pub.participant_key))
                dds_data.remove_endpoint(domain_id, pub)

        for sub in rdr.take(N=20, condition=rcr):

            # logging.info(sub.sample_info)
            if sub.sample_info.sample_state == core.SampleState.NotRead and sub.sample_info.instance_state == core.InstanceState.Alive:
                logging.info("Found subscriber participant: " + str(sub.participant_key) + "on topic: " + str(sub.topic_name))
                print(type(sub), "<-----------sub-------------------")
                print(str(sub))
                dds_data.add_endpoint(domain_id, sub)

            elif sub.sample_info.instance_state == core.InstanceState.NotAliveDisposed:
                logging.info("Removed subscriber participant:" + str(sub.participant_key))
                dds_data.remove_endpoint(domain_id, sub)

    logging.info(f"builtin_observer({domain_id}) ... DONE")
