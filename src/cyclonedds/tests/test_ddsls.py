import pytest
import json
import time
import signal
import os
import gc

import subprocess

from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from testtopics import Message
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
from cyclonedds.core import Qos, Policy, WaitSet, ReadCondition, ViewState, InstanceState, SampleState


# Helper functions

def run_ddsls(args, timeout=10):
    ddsls_process = subprocess.Popen(["python", "tools/ddsls.py"] + args,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     )

    try:
        stdout, stderr = ddsls_process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as e:
        ddsls_process.kill()
        raise e

    return {
        "stdout": stdout.decode(),
        "stderr": stderr.decode(),
        "status": ddsls_process.returncode
    }


def start_ddsls_watchmode(args):
    ddsls_process = subprocess.Popen(["python", "tools/ddsls.py", "--watch"] + args,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     )
    return ddsls_process


def stop_ddsls_watchmode(ddsls_process, timeout=10):
    ddsls_process.send_signal(signal.SIGINT)

    try:
        stdout, stderr = ddsls_process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as e:
        ddsls_process.kill()
        raise e

    return {
        "stdout": stdout.decode(),
        "stderr": stderr.decode(),
        "status": ddsls_process.returncode
    }


# Tests

def test_participant_empty():
    data = run_ddsls(["-t", "dcpsparticipant"])

    assert data["status"] == 0
    assert data["stdout"] == ""


def test_participant_empty_json():
    data = run_ddsls(["--json", "-t", "dcpsparticipant"])

    assert data["status"] == 0
    assert data["stdout"] == "[\n]\n"


def test_publication_empty():
    data = run_ddsls(["-t", "dcpspublication"])

    assert data["status"] == 0
    assert data["stdout"] == ""


def test_publication_empty_json():
    data = run_ddsls(["--json", "-t", "dcpspublication"])

    assert data["status"] == 0
    assert data["stdout"] == "[\n]\n"


def test_subscription_empty():
    data = run_ddsls(["-t", "dcpssubscription"])

    assert data["status"] == 0
    assert data["stdout"] == ""


def test_subscription_empty_json():
    data = run_ddsls(["--json", "-t", "dcpssubscription"])

    assert data["status"] == 0
    assert data["stdout"] == "[\n]\n"


def test_all_empty():
    data = run_ddsls(["-a"])

    assert data["status"] == 0
    assert data["stdout"] == ""


def test_all_empty_json():
    data = run_ddsls(["--json", "-a"])

    assert data["status"] == 0
    assert data["stdout"] == "[\n]\n"


def test_participant_reported():
    dp = DomainParticipant(0)
    time.sleep(0.5)

    data = run_ddsls(["-t", "dcpsparticipant"])

    time.sleep(0.5)

    assert str(dp.guid) in data["stdout"]


def test_participant_json_reported():
    dp = DomainParticipant(0)
    time.sleep(0.5)

    data = run_ddsls(["-t", "dcpsparticipant", "--json"])

    time.sleep(0.5)

    assert str(dp.guid) in data["stdout"]


def test_participant_watch_reported():
    ddsls = start_ddsls_watchmode(["-t", "dcpsparticipant"])

    time.sleep(0.5)

    dp = DomainParticipant(0)

    time.sleep(0.5)

    data = stop_ddsls_watchmode(ddsls)

    assert str(dp.guid) in data["stdout"]


def test_participant_json_watch_reported():
    ddsls = start_ddsls_watchmode(["--json", "-t", "dcpsparticipant"])

    time.sleep(0.5)

    dp = DomainParticipant(0)

    time.sleep(0.5)

    data = stop_ddsls_watchmode(ddsls)

    assert str(dp.guid) in data["stdout"]


def test_subscription_reported():
    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dr = DataReader(dp, tp)
    time.sleep(1)

    data = run_ddsls(["-t", "dcpssubscription"])

    assert str(dr.guid) in data["stdout"]
    assert str(dp.guid) in data["stdout"]
    assert tp.name in data["stdout"]
    assert tp.typename in data["stdout"]
    assert str(dr.get_qos()) in data["stdout"]


def test_subscription_json_reported():
    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dr = DataReader(dp, tp)
    time.sleep(1)

    data = run_ddsls(["--json", "-t", "dcpssubscription"])
    json_data = json.loads(data["stdout"])

    assert str(dr.guid) in data["stdout"]
    assert str(dp.guid) in data["stdout"]
    assert tp.name in data["stdout"]
    assert tp.typename in data["stdout"]

    reader_check = False
    for sample in json_data:
        for val in sample["value"]:
            if val["key"] == str(dr.guid):
                assert (dr.get_qos()).asdict() == val["qos"]
                reader_check = True
    assert reader_check


def test_subscription_watch_reported():
    ddsls = start_ddsls_watchmode(["-t", "dcpssubscription"])

    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dr = DataReader(dp, tp)

    time.sleep(1)

    data = stop_ddsls_watchmode(ddsls)

    assert str(dr.guid) in data["stdout"]
    assert str(dp.guid) in data["stdout"]
    assert tp.name in data["stdout"]
    assert tp.typename in data["stdout"]
    assert str(dr.get_qos()) in data["stdout"]


def test_subscription_json_watch_reported():
    ddsls = start_ddsls_watchmode(["--json", "-t", "dcpssubscription"])

    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dr = DataReader(dp, tp)

    time.sleep(1)

    data = stop_ddsls_watchmode(ddsls)
    json_data = json.loads(data["stdout"])

    assert str(dr.guid) in data["stdout"]
    assert str(dp.guid) in data["stdout"]
    assert tp.name in data["stdout"]
    assert tp.typename in data["stdout"]

    reader_check = False
    for sample in json_data:
        for val in sample["value"]:
            if val["key"] == str(dr.guid):
                assert (dr.get_qos()).asdict() == val["qos"]
                reader_check = True
    assert reader_check


def test_publication_reported():
    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dw = DataWriter(dp, tp)
    time.sleep(1)

    data = run_ddsls(["-t", "dcpspublication"])

    assert str(dw.guid) in data["stdout"]
    assert str(dp.guid) in data["stdout"]
    assert tp.name in data["stdout"]
    assert tp.typename in data["stdout"]
    assert str(dw.get_qos()) in data["stdout"]


def test_publication_json_reported():
    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dw = DataWriter(dp, tp)
    time.sleep(1)

    data = run_ddsls(["--json", "-t", "dcpspublication"])
    json_data = json.loads(data["stdout"])

    assert str(dw.guid) in data["stdout"]
    assert str(dp.guid) in data["stdout"]
    assert tp.name in data["stdout"]
    assert tp.typename in data["stdout"]

    writer_check = False
    for sample in json_data:
        for val in sample["value"]:
            if val["key"] == str(dw.guid):
                assert (dw.get_qos()).asdict() == val["qos"]
                writer_check = True
    assert writer_check


def test_publication_watch_reported():
    ddsls = start_ddsls_watchmode(["-t", "dcpspublication"])

    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dw = DataWriter(dp, tp)

    time.sleep(1)

    data = stop_ddsls_watchmode(ddsls)

    assert str(dw.guid) in data["stdout"]
    assert str(dp.guid) in data["stdout"]
    assert tp.name in data["stdout"]
    assert tp.typename in data["stdout"]
    assert str(dw.get_qos()) in data["stdout"]


def test_publication_json_watch_reported():
    ddsls = start_ddsls_watchmode(["--json", "-t", "dcpspublication"])

    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dw = DataWriter(dp, tp)

    time.sleep(1)

    data = stop_ddsls_watchmode(ddsls)
    json_data = json.loads(data["stdout"])

    assert str(dw.guid) in data["stdout"]
    assert str(dp.guid) in data["stdout"]
    assert tp.name in data["stdout"]
    assert tp.typename in data["stdout"]

    writer_check = False
    for sample in json_data:
        for val in sample["value"]:
            if val["key"] == str(dw.guid):
                assert (dw.get_qos()).asdict() == val["qos"]
                writer_check = True
    assert writer_check


def test_all_entities_reported():
    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dw = DataWriter(dp, tp)
    dr = DataReader(dp, tp)
    time.sleep(1)

    data = run_ddsls(["-a"])

    assert str(dw.guid) in data["stdout"]
    assert str(dr.guid) in data["stdout"]
    assert str(dp.guid) in data["stdout"]
    assert tp.name in data["stdout"]
    assert tp.typename in data["stdout"]
    assert str(dw.get_qos()) in data["stdout"]
    assert str(dr.get_qos()) in data["stdout"]


def test_all_entities_json_reported():
    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dw = DataWriter(dp, tp)
    dr = DataReader(dp, tp)
    time.sleep(1)

    data = run_ddsls(["--json", "-a"])
    json_data = json.loads(data["stdout"])

    assert str(dw.guid) in data["stdout"]
    assert str(dr.guid) in data["stdout"]
    assert str(dp.guid) in data["stdout"]
    assert tp.name in data["stdout"]
    assert tp.typename in data["stdout"]

    writer_check, reader_check = False, False
    for sample in json_data:
        for val in sample["value"]:
            if val["key"] == str(dw.guid):
                assert (dw.get_qos()).asdict() == val["qos"]
                writer_check = True
            if val["key"] == str(dr.guid):
                assert (dr.get_qos()).asdict() == val["qos"]
                reader_check = True
    assert reader_check and writer_check


def test_all_entities_watch_reported():
    ddsls = start_ddsls_watchmode(["-a"])

    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dw = DataWriter(dp, tp)
    dr = DataReader(dp, tp)

    time.sleep(1)

    data = stop_ddsls_watchmode(ddsls)

    assert str(dw.guid) in data["stdout"]
    assert str(dr.guid) in data["stdout"]
    assert str(dp.guid) in data["stdout"]
    assert tp.name in data["stdout"]
    assert tp.typename in data["stdout"]
    assert str(dw.get_qos()) in data["stdout"]
    assert str(dr.get_qos()) in data["stdout"]


def test_all_entities_watch_json_reported():
    ddsls = start_ddsls_watchmode(["--json", "-a"])

    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dw = DataWriter(dp, tp)
    dr = DataReader(dp, tp)

    time.sleep(1)

    data = stop_ddsls_watchmode(ddsls)
    json_data = json.loads(data["stdout"])

    assert str(dw.guid) in data["stdout"]
    assert str(dr.guid) in data["stdout"]
    assert str(dp.guid) in data["stdout"]
    assert tp.name in data["stdout"]
    assert tp.typename in data["stdout"]

    writer_check, reader_check = False, False
    for sample in json_data:
        for val in sample["value"]:
            if val["key"] == str(dw.guid):
                assert (dw.get_qos()).asdict() == val["qos"]
                writer_check = True
            if val["key"] == str(dr.guid):
                assert (dr.get_qos()).asdict() == val["qos"]
                reader_check = True
    assert reader_check and writer_check


def test_write_to_file(tmp_path):
    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dw = DataWriter(dp, tp)
    dr = DataReader(dp, tp)

    time.sleep(0.5)

    run_ddsls(["--json", "-a", "--filename", tmp_path/"test.json"])

    time.sleep(0.5)

    data = json.load(open(tmp_path/"test.json",))

    assert str(dw.guid) in data["PUBLICATION"]["New"]
    assert str(dr.guid) in data["SUBSCRIPTION"]["New"]
    assert str(dp.guid) in data["PARTICIPANT"]["New"]
    assert tp.name in data["PUBLICATION"]["New"][str(dw.guid)]["topic_name"]
    assert tp.typename in data["PUBLICATION"]["New"][str(dw.guid)]["type_name"]
    assert tp.name in data["SUBSCRIPTION"]["New"][str(dr.guid)]["topic_name"]
    assert tp.typename in data["SUBSCRIPTION"]["New"][str(dr.guid)]["type_name"]

    os.remove(tmp_path/"test.json")


def test_write_disposed_data_to_file(tmp_path):
    ddsls = start_ddsls_watchmode(["--json", "-a", "-w", "--filename", tmp_path/"test_disposed.json"])

    time.sleep(0.5)

    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dw = DataWriter(dp, tp)
    dr = DataReader(dp, tp)

    disposed_data = {
        "dp.guid": str(dp.guid),
        "tp.name": tp.name,
        "tp.typename": tp.typename,
        "dw.guid": str(dw.guid),
        "dr.guid": str(dr.guid)
    }
    time.sleep(0.5)

    del dp, tp, dw, dr
    gc.collect()
    time.sleep(1)

    stop_ddsls_watchmode(ddsls)

    time.sleep(0.5)

    data = json.load(open(tmp_path/"test_disposed.json",))

    dw_guid = disposed_data["dw.guid"]
    dr_guid = disposed_data["dr.guid"]

    assert disposed_data["dp.guid"] not in data["PARTICIPANT"]["New"]
    assert disposed_data["dp.guid"] in data["PARTICIPANT"]["Disposed"]
    assert dw_guid not in data["PUBLICATION"]["New"]
    assert dw_guid in data["PUBLICATION"]["Disposed"]
    assert dr_guid not in data["SUBSCRIPTION"]["New"]
    assert dr_guid in data["SUBSCRIPTION"]["Disposed"]
    assert disposed_data["tp.name"] == data["PUBLICATION"]["Disposed"][dw_guid]["topic_name"]
    assert disposed_data["tp.name"] == data["SUBSCRIPTION"]["Disposed"][dr_guid]["topic_name"]
    assert disposed_data["tp.typename"] == data["PUBLICATION"]["Disposed"][dw_guid]["type_name"]
    assert disposed_data["tp.typename"] == data["SUBSCRIPTION"]["Disposed"][dr_guid]["type_name"]

    os.remove(tmp_path/"test_disposed.json")


def test_domain_id():
    dp = DomainParticipant(0)
    dp1 = DomainParticipant(33)

    time.sleep(0.5)

    data = run_ddsls(["--id", "33", "-t", "dcpsparticipant"])

    time.sleep(0.5)

    assert str(dp.guid) not in data["stdout"]
    assert str(dp1.guid) in data["stdout"]


def test_qos_change():
    ddsls = start_ddsls_watchmode(["-a"])

    qos = Qos(Policy.OwnershipStrength(10),
              Policy.Userdata("Old".encode()))
    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dw = DataWriter(dp, tp, qos=qos)
    time.sleep(0.5)

    old_qos = dw.get_qos()
    time.sleep(0.5)

    new_qos = Qos(Policy.OwnershipStrength(20),
                  Policy.Userdata("New".encode()))
    dw.set_qos(new_qos)

    time.sleep(0.5)

    data = stop_ddsls_watchmode(ddsls)

    assert str(old_qos) in data["stdout"]
    for q in new_qos:
        assert str(q) in data["stdout"]
        assert f"{str(old_qos[q])} -> {str(q)}" in data["stdout"]


def test_qos_change_in_verbose():
    ddsls = start_ddsls_watchmode(["-a", "--verbose"])

    qos = Qos(Policy.OwnershipStrength(10),
              Policy.Userdata("Old".encode()))
    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dw = DataWriter(dp, tp, qos=qos)
    time.sleep(0.5)

    old_qos = dw.get_qos()
    time.sleep(0.5)

    new_qos = Qos(Policy.OwnershipStrength(20),
                  Policy.Userdata("New".encode()))
    dw.set_qos(new_qos)

    time.sleep(0.5)

    data = stop_ddsls_watchmode(ddsls)

    assert str(old_qos) in data["stdout"]
    for q in new_qos:
        assert str(q) in data["stdout"]
        assert f"{str(old_qos[q])} -> {str(q)}" in data["stdout"]
    assert str(dw.get_qos()) in data["stdout"]
