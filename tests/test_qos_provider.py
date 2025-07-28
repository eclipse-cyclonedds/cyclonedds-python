import pytest
import os
from pathlib import Path
from cyclonedds.core import DDSException
from cyclonedds.qos_provider import QosProvider
from cyclonedds.qos import (
    DataReaderQos, DataWriterQos, DomainParticipantQos, PublisherQos, Qos,
    SubscriberQos, TopicQos,
)


@pytest.fixture(scope="function")
def sysdef_file(tmp_path):
    q_str = """<dds>
      <qos_library name="qoslib01">
        <qos_profile name="qosprofile01">
          <datareader_qos>
            <history><kind>KEEP_LAST_HISTORY_QOS</kind><depth>5</depth></history>
          </datareader_qos>
          <datawriter_qos>
            <history><kind>KEEP_LAST_HISTORY_QOS</kind><depth>5</depth></history>
          </datawriter_qos>
          <topic_qos>
            <resource_limits><max_instances>5</max_instances></resource_limits>
          </topic_qos>
          <publisher_qos>
            <partition><name><element>part02</element></name></partition>
          </publisher_qos>
          <subscriber_qos>
            <partition><name><element>part01</element></name></partition>
          </subscriber_qos>
          <domain_participant_qos>
            <user_data><value>ZCBzdHJpbmcgZXhhbXBsZQ==</value></user_data>
          </domain_participant_qos>
        </qos_profile>
      </qos_library>
    </dds>"""
    tmp_file = (tmp_path / "sysdef_common_test.xml")
    assert tmp_file.write_text(q_str) != 0
    return tmp_file


def test_qos_provider_create(sysdef_file):
    qp0 = QosProvider(sysdef_file, "*::qosprofile01")
    wr_q = qp0.get_datawriter_qos("qoslib01::qosprofile01")
    assert isinstance(wr_q, DataWriterQos)
    qp1 = QosProvider("<dds></dds>")
    ret = True
    try:
        wr_q = qp1.get_datawriter_qos("qoslib01::qosprofile01")
    except DDSException:
        assert ret  # nothing to get from empty definition
        ret = False
    assert not ret


def test_qos_provider_get_topic(sysdef_file):
    qp = QosProvider(sysdef_file, "*::*")
    qs = Qos.fromdict({"ResourceLimits": {"max_instances": 5}}).topic()
    assert qp.get_topic_qos("qoslib01::qosprofile01") == qs


def test_qos_provider_get_subscriber(sysdef_file):
    qp = QosProvider(str(sysdef_file), "::::")
    qs = Qos.fromdict({"Partition": {"partitions": ["part01"]}}).subscriber()
    assert qp.get_subscriber_qos("qoslib01::qosprofile01") == qs


def test_qos_provider_get_publisher(sysdef_file):
    qp = QosProvider(str(sysdef_file), "::")
    qs = Qos.fromdict({"Partition": {"partitions": ["part02"]}}).publisher()
    assert qp.get_publisher_qos("qoslib01::qosprofile01") == qs


def test_qos_provider_get_datareader(sysdef_file):
    qp = QosProvider(str(sysdef_file).encode('utf-8'), "")
    qs = Qos.fromdict({"History": {"kind": "KeepLast", "depth": 5}}).datareader()
    assert qp.get_datareader_qos("qoslib01::qosprofile01") == qs


def test_qos_provider_get_datawriter(sysdef_file):
    qp = QosProvider(sysdef_file)
    qs = Qos.fromdict({"History": {"kind": "KeepLast", "depth": 5}}).datawriter()
    assert qp.get_datawriter_qos("qoslib01::qosprofile01") == qs


def test_qos_provider_get_participant(sysdef_file):
    qp = QosProvider(sysdef_file)
    qs = Qos.fromdict({"Userdata": {"data": "ZCBzdHJpbmcgZXhhbXBsZQ=="}}).domain_participant()
    assert qp.get_domain_participant_qos("qoslib01::qosprofile01") == qs
