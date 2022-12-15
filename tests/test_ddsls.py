import gc
import json
import time
import sys
import os
import pytest
import shutil
import asyncio
import tempfile
import concurrent
import subprocess

from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
from cyclonedds.core import Qos, Policy

from support_modules.testtopics import Message


if sys.platform.startswith("win"):
    pytest.skip("DDSLS is unstable on windows", allow_module_level=True)


# Helper functions

def run_ddsls(args, timeout=10):
    tmp_dir = tempfile.mkdtemp()
    process = subprocess.Popen([sys.executable, "-m", "cyclonedds.tools.ddsls"] + args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                                cwd=tmp_dir
                            )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as e:
        try:
            process.kill()
            shutil.rmtree(tmp_dir)
        except:
            # Observant readers will note that if the process is not killed
            # then we do not delete the temporary dir. This has a good reason:
            # When the process is stuck in an unkillable state and we try to remove
            # the directory, we will enter an infinite loop with permission errors on
            # windows.
            pass
        try:
            print("Ddsls command timeout")
            print("   attempting to pull from stdout:")
            process.stdout.close()
            print(process.stdout.read().decode().replace("\r", ""))
            print("   attempting to pull from stderr")
            process.stderr.close()
            print(process.stderr.read().decode().replace("\r", ""))
        except:
            pass
        raise e

    shutil.rmtree(tmp_dir)

    return {
        "stdout": stdout.decode().replace("\r", ""),
        "stderr": stderr.decode().replace("\r", ""),
        "status": process.returncode
    }


async def run_ddsls_async_watch(args, runtime, runner):
    loop = asyncio.get_event_loop_policy().get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        task = loop.run_in_executor(pool, run_ddsls, ["--watch", "--runtime", str(runtime)] + args)
        await asyncio.sleep(0.3)
        test = await runner()
        return (await task), test


def run_ddsls_watchmode(args, runner, runtime=5):
    loop = asyncio.get_event_loop_policy().get_event_loop()
    result = loop.run_until_complete(run_ddsls_async_watch(args, runtime, runner))
    return result


# Tests

def test_ddsls_participant_runs():
    data = run_ddsls(["-t", "dcpsparticipant"])
    assert data["status"] == 0


def test_ddsls_participant_runs_json():
    data = run_ddsls(["--json", "-t", "dcpsparticipant"])
    assert data["status"] == 0
    json.loads(data["stdout"])


def test_ddsls_publication_runs():
    data = run_ddsls(["-t", "dcpspublication"])
    assert data["status"] == 0


def test_ddsls_publication_runs_json():
    data = run_ddsls(["--json", "-t", "dcpspublication"])
    assert data["status"] == 0
    json.loads(data["stdout"])


def test_ddsls_subscription_runs():
    data = run_ddsls(["-t", "dcpssubscription"])
    assert data["status"] == 0


def test_ddsls_subscription_runs_json():
    data = run_ddsls(["--json", "-t", "dcpssubscription"])
    assert data["status"] == 0
    json.loads(data["stdout"])


def test_ddsls_all_runs():
    data = run_ddsls(["-a"])
    assert data["status"] == 0


def test_ddsls_all_runs_json():
    data = run_ddsls(["--json", "-a"])
    assert data["status"] == 0
    json.loads(data["stdout"])


def test_ddsls_participant_reported():
    dp = DomainParticipant(0)
    time.sleep(0.5)

    data = run_ddsls(["-t", "dcpsparticipant"])

    time.sleep(0.5)

    assert str(dp.guid) in data["stdout"]


def test_ddsls_participant_json_reported():
    dp = DomainParticipant(0)
    time.sleep(0.5)

    data = run_ddsls(["-t", "dcpsparticipant", "--json"])

    time.sleep(0.5)

    assert str(dp.guid) in data["stdout"]


def test_ddsls_participant_watch_reported():
    async def test_inner():
        dp = DomainParticipant(0)
        return dp

    data, dp = run_ddsls_watchmode(["-t", "dcpsparticipant"], test_inner, runtime=1)

    assert str(dp.guid) in data["stdout"]


def test_ddsls_participant_json_watch_reported():
    async def test_inner():
        dp = DomainParticipant(0)
        return dp

    data, dp = run_ddsls_watchmode(["-t", "dcpsparticipant", "--json"], test_inner, runtime=1)

    assert str(dp.guid) in data["stdout"]


def test_ddsls_subscription_reported():
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


def test_ddsls_subscription_json_reported():
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


def test_ddsls_subscription_watch_reported():
    async def test_inner():
        dp = DomainParticipant(0)
        tp = Topic(dp, "MessageTopic", Message)
        dr = DataReader(dp, tp)
        return dp, tp, dr

    data, (dp, tp, dr) = run_ddsls_watchmode(["-t", "dcpssubscription"], test_inner, runtime=1)

    assert str(dr.guid) in data["stdout"]
    assert str(dp.guid) in data["stdout"]
    assert tp.name in data["stdout"]
    assert tp.typename in data["stdout"]
    assert str(dr.get_qos()) in data["stdout"]


def test_ddsls_subscription_json_watch_reported():
    async def test_inner():
        dp = DomainParticipant(0)
        tp = Topic(dp, "MessageTopic", Message)
        dr = DataReader(dp, tp)
        return dp, tp, dr

    data, (dp, tp, dr) = run_ddsls_watchmode(["-t", "dcpssubscription", "--json"], test_inner, runtime=1)
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



def test_ddsls_publication_reported():
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


def test_ddsls_publication_json_reported():
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


def test_ddsls_publication_watch_reported():
    async def test_inner():
        dp = DomainParticipant(0)
        tp = Topic(dp, "MessageTopic", Message)
        dw = DataWriter(dp, tp)
        return dp, tp, dw

    data, (dp, tp, dw) = run_ddsls_watchmode(["-t", "dcpspublication"], test_inner, runtime=1)

    assert str(dw.guid) in data["stdout"]
    assert str(dp.guid) in data["stdout"]
    assert tp.name in data["stdout"]
    assert tp.typename in data["stdout"]
    assert str(dw.get_qos()) in data["stdout"]


def test_ddsls_publication_json_watch_reported():
    async def test_inner():
        dp = DomainParticipant(0)
        tp = Topic(dp, "MessageTopic", Message)
        dw = DataWriter(dp, tp)
        return dp, tp, dw

    data, (dp, tp, dw) = run_ddsls_watchmode(["-t", "dcpspublication", "--json"], test_inner, runtime=1)
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


def test_ddsls_all_entities_reported():
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


def test_ddsls_all_entities_json_reported():
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


def test_ddsls_all_entities_watch_reported():
    async def test_inner():
        dp = DomainParticipant(0)
        tp = Topic(dp, "MessageTopic", Message)
        dw = DataWriter(dp, tp)
        dr = DataReader(dp, tp)
        return dp, tp, dw, dr

    data, (dp, tp, dw, dr) = run_ddsls_watchmode(["-a"], test_inner, runtime=2)

    assert str(dw.guid) in data["stdout"]
    assert str(dr.guid) in data["stdout"]
    assert str(dp.guid) in data["stdout"]
    assert tp.name in data["stdout"]
    assert tp.typename in data["stdout"]
    assert str(dw.get_qos()) in data["stdout"]
    assert str(dr.get_qos()) in data["stdout"]


def test_ddsls_all_entities_watch_json_reported():
    async def test_inner():
        dp = DomainParticipant(0)
        tp = Topic(dp, "MessageTopic", Message)
        dw = DataWriter(dp, tp)
        dr = DataReader(dp, tp)
        return dp, tp, dw, dr

    data, (dp, tp, dw, dr) = run_ddsls_watchmode(["-a", "--json"], test_inner, runtime=2)
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


def test_ddsls_write_to_file(tmp_path):
    dp = DomainParticipant(0)
    tp = Topic(dp, "MessageTopic", Message)
    dw = DataWriter(dp, tp)
    dr = DataReader(dp, tp)

    time.sleep(0.5)

    run_ddsls(["--json", "-a", "--filename", str(tmp_path / "test.json")])

    time.sleep(0.5)

    with open(tmp_path / "test.json") as f:
        data = json.load(f)

    assert str(dw.guid) in data["PUBLICATION"]["New"]
    assert str(dr.guid) in data["SUBSCRIPTION"]["New"]
    assert str(dp.guid) in data["PARTICIPANT"]["New"]
    assert tp.name in data["PUBLICATION"]["New"][str(dw.guid)]["topic_name"]
    assert tp.typename in data["PUBLICATION"]["New"][str(dw.guid)]["type_name"]
    assert tp.name in data["SUBSCRIPTION"]["New"][str(dr.guid)]["topic_name"]
    assert tp.typename in data["SUBSCRIPTION"]["New"][str(dr.guid)]["type_name"]


def test_ddsls_write_disposed_data_to_file(tmp_path):
    async def test_inner():
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
        await asyncio.sleep(1)

        del dp, tp, dw, dr
        gc.collect()
        await asyncio.sleep(1)
        return disposed_data

    procdata, disposed_data = run_ddsls_watchmode(["--json", "-a", "--filename", str(tmp_path / "test_disposed.json")],
                                           test_inner, runtime=2)

    assert procdata['status'] == 0

    with open(tmp_path / "test_disposed.json") as f:
        data = json.load(f)

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


def test_ddsls_domain_id():
    dp = DomainParticipant(0)
    dp1 = DomainParticipant(33)

    time.sleep(0.5)

    data = run_ddsls(["--id", "33", "-t", "dcpsparticipant"])

    time.sleep(0.5)

    assert str(dp.guid) not in data["stdout"]
    assert str(dp1.guid) in data["stdout"]


def test_ddsls_qos_change():
    async def test_inner():
        qos = Qos(Policy.OwnershipStrength(10),
                  Policy.Userdata("Old".encode()))
        dp = DomainParticipant(0)
        tp = Topic(dp, "MessageTopic", Message)
        dw = DataWriter(dp, tp, qos=qos)
        await asyncio.sleep(0.5)

        old_qos = dw.get_qos()
        await asyncio.sleep(0.5)

        new_qos = Qos(Policy.OwnershipStrength(20),
                      Policy.Userdata("New".encode()))
        dw.set_qos(new_qos)

        await asyncio.sleep(0.5)

        return dp, tp, dw, old_qos, new_qos

    data, (dp, tp, dw, old_qos, new_qos) = run_ddsls_watchmode(["-a"], test_inner, runtime=5)

    assert str(old_qos) in data["stdout"]
    for q in new_qos:
        assert str(q) in data["stdout"]
        assert f"{str(old_qos[q])} -> {str(q)}" in data["stdout"]


def test_ddsls_qos_change_in_verbose():
    async def test_inner():
        qos = Qos(Policy.OwnershipStrength(10),
                  Policy.Userdata("Old".encode()))
        dp = DomainParticipant(0)
        tp = Topic(dp, "MessageTopic", Message)
        dw = DataWriter(dp, tp, qos=qos)
        await asyncio.sleep(0.5)

        old_qos = dw.get_qos()
        await asyncio.sleep(0.5)

        new_qos = Qos(Policy.OwnershipStrength(20),
                      Policy.Userdata("New".encode()))
        dw.set_qos(new_qos)

        await asyncio.sleep(0.5)

        return dp, tp, dw, old_qos, new_qos

    data, (dp, tp, dw, old_qos, new_qos) = run_ddsls_watchmode(["-a", "--verbose"], test_inner, runtime=5)

    assert str(old_qos) in data["stdout"]
    for q in new_qos:
        assert str(q) in data["stdout"]
        assert f"{str(old_qos[q])} -> {str(q)}" in data["stdout"]
    assert str(dw.get_qos()) in data["stdout"]


# test error messages


def test_ddsls_file_open_error(tmp_path):
    data = run_ddsls(["--json", "-a", "--filename", f"{tmp_path}/this/path/denfinitely/doesnot/exist/ever"])
    assert f"Exception: Could not open file {tmp_path}/this/path/denfinitely/doesnot/exist/ever" in data["stderr"]
