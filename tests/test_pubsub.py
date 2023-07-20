import pytest
import asyncio
import shutil
import concurrent
import subprocess
import json
import time
import sys
import tempfile

from cyclonedds.core import Qos, Policy


if sys.platform.startswith("win"):
    pytest.skip("DDSLS is unstable on windows", allow_module_level=True)


# Helper functions


message = "test\n 420\n [4,2,0]\n ['test','str','array','data','struct']\n [-1,183]\n ['test','string','sequence']"


def run_pubsub(args, text=message, timeout=10):
    tmp_dir = tempfile.mkdtemp()
    process = subprocess.Popen(
        [sys.executable, "-m", "cyclonedds.tools.pubsub"] + args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tmp_dir
    )

    try:
        if text:
            process.stdin.write(text.encode())
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
            print("Pubsub command timeout")
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
            print("DDSLS command timeout")
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


async def run_pubsub_ddsls_async(pubsub_args, ddsls_args, runtime):
    loop = asyncio.get_event_loop_policy().get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        pubsub_task = loop.run_in_executor(pool, run_pubsub, ["--runtime", str(runtime-1.5)] + pubsub_args)
        ddsls_task = loop.run_in_executor(pool, run_ddsls, ["--watch", "--runtime", str(runtime)] + ddsls_args)
        await asyncio.sleep(0.3)
        return (await pubsub_task), (await ddsls_task)


def run_pubsub_ddsls(pubsub_args, ddsls_args, runtime=5):
    loop = asyncio.get_event_loop_policy().get_event_loop()
    result = loop.run_until_complete(run_pubsub_ddsls_async(pubsub_args, ddsls_args, runtime))
    return result


# tests


def test_pubsub_empty():
    pubsub = run_pubsub(["-T", "test", "--runtime", "0.5"], text=None)
    assert pubsub["stdout"] == ""
    assert pubsub["status"] == 0


def test_pubsub_topics():
    pubsub = run_pubsub(["-T", "test", "--runtime", "0.5"])

    assert "String(seq=0, keyval='test')" in pubsub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]
    assert "IntArray(seq=2, keyval=[4, 2, 0])" in pubsub["stdout"]
    assert "StrArray(seq=3, keyval=['test', 'str', 'array', 'data', 'struct'])" in pubsub["stdout"]
    assert "IntSequence(seq=4, keyval=[-1, 183])" in pubsub["stdout"]
    assert "StrSequence(seq=5, keyval=['test', 'string', 'sequence'])" in pubsub["stdout"]
    assert pubsub["status"] == 0


def test_parse_qos():
    tests = \
    [
        (
            [
                "Reliability.Reliable 10000000",
                "Durability.TransientLocal",
                "History.KeepLast 10",
                "ResourceLimits 100 -1 100",
                "PresentationAccessScope.Topic True False",
                "Lifespan 1000000",
                "Deadline seconds=1",
                "LatencyBudget 10000000",
                "Ownership.Exclusive",
                "OwnershipStrength 20",
                "Liveliness.ManualByParticipant 100000",
                "TimeBasedFilter 100000",
                "Partition Hello, world",
                "TransportPriority 1",
                "DestinationOrder.BySourceTimestamp",
                "WriterDataLifecycle False",
                "ReaderDataLifecycle 10000000 10000000",
                "DurabilityService 100000 History.KeepLast 100, 2000, 1000, 1000",
                "Userdata HiUser",
                "Groupdata HiGroup",
                "Topicdata HiTopic"
            ],
            Qos(
                Policy.Reliability.Reliable(max_blocking_time=10000000),
                Policy.Durability.TransientLocal,
                Policy.History.KeepLast(depth=10),
                Policy.ResourceLimits(max_samples=100, max_instances=-1, max_samples_per_instance=100),
                Policy.PresentationAccessScope.Topic(coherent_access=True, ordered_access=False),
                Policy.Lifespan(lifespan=1000000),
                Policy.Deadline(deadline=1000000000),
                Policy.LatencyBudget(budget=10000000),
                Policy.Ownership.Exclusive,
                Policy.OwnershipStrength(strength=20),
                Policy.Liveliness.ManualByParticipant(lease_duration=100000),
                Policy.TimeBasedFilter(filter_time=100000),
                Policy.Partition(partitions=('Hello', 'world')),
                Policy.TransportPriority(priority=1),
                Policy.DestinationOrder.BySourceTimestamp,
                Policy.WriterDataLifecycle(autodispose=False),
                Policy.ReaderDataLifecycle(autopurge_nowriter_samples_delay=10000000, autopurge_disposed_samples_delay=10000000),
                Policy.DurabilityService(cleanup_delay=100000, history=Policy.History.KeepLast(depth=100),
                                            max_samples=2000, max_instances=1000, max_samples_per_instance=1000),
                Policy.Userdata(data=b'HiUser'),
                Policy.Groupdata(data=b'HiGroup'),
                Policy.Topicdata(data=b'HiTopic'),
            )
        )
    ]

    for (input, result) in tests:
        pubsub, ddsls = run_pubsub_ddsls(["-T", "test", "-q", ' '.join(input)],
                                         ["-a"],
                                         runtime=2)
        for policy in result:
            assert str(policy) in ddsls["stdout"]

        assert pubsub["status"] == 0


def test_parse_qos_compatible_expressions():
    tests = [
                (
                    [
                        "Reliability.Reliable 10,",
                        "History.KeepLast: 10",
                        "ResourceLimits 100, -1 100",
                        "PresentationAccessScope.Topic 1 no",
                        "liFespAn seconds=1000;days=12",
                        "deadline seconds=1",
                        "WriterDataLifecycle off"
                    ],
                    [
                        Policy.Reliability.Reliable(max_blocking_time=10),
                        Policy.History.KeepLast(depth=10),
                        Policy.ResourceLimits(max_samples=100, max_instances=-1, max_samples_per_instance=100),
                        Policy.PresentationAccessScope.Topic(coherent_access=True, ordered_access=False),
                        Policy.Lifespan(lifespan=1037800000000000),
                        Policy.Deadline(deadline=1000000000),
                        Policy.WriterDataLifecycle(autodispose=False)
                    ]
                )
            ]

    for (input, result) in tests:
        pubsub, ddsls = run_pubsub_ddsls(["-T", "test", "-q", ' '.join(input)],
                                         ["-a"],
                                         runtime=2)
        for policy in result:
            assert str(policy) in ddsls["stdout"]

        assert pubsub["status"] == 0


def test_multiple_qoses():
    pubsub, ddsls = run_pubsub_ddsls(["-T", "test", "--qos", "Durability.TransientLocal", "Userdata HelloWorld"],
                                     ["-a"],
                                     runtime=2)

    assert "Userdata(data=b'HelloWorld')" in ddsls["stdout"]
    assert "Durability.TransientLocal" in ddsls["stdout"]

    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]
    assert pubsub["status"] == 0


def test_qos_special_cases():
    pubsub, ddsls = run_pubsub_ddsls(["-T", "test", "--qos", "PresentationAccessScope.Topic:", "True, False",
                                      "Partition", "test, parti, 33",
                                      "DurabilityService", "seconds=1, history.keeplast 10, 100, 10, 10",
                                      "Topicdata", "helloTopic"],
                                     ["-a"],
                                     runtime=2)

    assert "PresentationAccessScope.Topic(coherent_access=True, ordered_access=False)" in ddsls["stdout"]
    assert "Partition(partitions=('test', 'parti', '33'))" in ddsls["stdout"]
    assert "DurabilityService(cleanup_delay=1000000000, history=Policy.History.KeepLast(depth=10), \
max_samples=100, max_instances=10, max_samples_per_instance=10)" in ddsls["stdout"]
    assert "Topicdata(data=b'helloTopic')" in ddsls["stdout"]

    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]
    assert pubsub["status"] == 0


def test_topic_qos():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "topic",
                                          "--qos", "Durability.TransientLocal"],
                                         ["-t", "dcpspublication"], runtime=2)

    assert "Durability.TransientLocal" in ddsls_pub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]
    assert pubsub["status"] == 0

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "topic",
                                          "--qos", "Durability.TransientLocal"],
                                         ["-t", "dcpssubscription"], runtime=2)

    assert "Durability.TransientLocal" in ddsls_sub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]
    assert pubsub["status"] == 0


def test_topic_multiple_qoses():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "topic",
                                          "--qos", "Durability.TransientLocal", "ResourceLimits", "100, 10, 10"],
                                         ["-t", "dcpspublication"], runtime=2)

    assert "Durability.TransientLocal" in ddsls_pub["stdout"]
    assert "ResourceLimits(max_samples=100, max_instances=10, max_samples_per_instance=10)" in ddsls_pub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]
    assert pubsub["status"] == 0

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "topic",
                                          "--qos", "Durability.TransientLocal", "ResourceLimits", "100, 10, 10"],
                                         ["-t", "dcpssubscription"], runtime=2)

    assert "Durability.TransientLocal" in ddsls_sub["stdout"]
    assert "ResourceLimits(max_samples=100, max_instances=10, max_samples_per_instance=10)" in ddsls_sub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]
    assert pubsub["status"] == 0


def test_publisher_qos():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "publisher",
                                          "-q", "PresentationAccessScope.Instance", "False, True"],
                                         ["-t", "dcpspublication"], runtime=2)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" in ddsls_pub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]
    assert pubsub["status"] == 0

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "publisher",
                                          "-q", "PresentationAccessScope.Instance", "False, True"],
                                         ["-t", "dcpssubscription"], runtime=2)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" not in ddsls_sub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]
    assert pubsub["status"] == 0


def test_publisher_multiple_qoses():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "publisher",
                                          "-q", "PresentationAccessScope.Instance", "False, True",
                                          "Groupdata", "TestPublisherQos"],
                                         ["-t", "dcpspublication"], runtime=2)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" in ddsls_pub["stdout"]
    assert "Groupdata(data=b'TestPublisherQos')" in ddsls_pub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]
    assert pubsub["status"] == 0

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "publisher",
                                          "-q", "PresentationAccessScope.Instance", "False, True",
                                          "Groupdata", "TestPublisherQos"],
                                         ["-t", "dcpssubscription"], runtime=2)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" not in ddsls_sub["stdout"]
    assert "Groupdata(data=b'TestPublisherQos')" not in ddsls_sub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]
    assert pubsub["status"] == 0


def test_subscriber_qos():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "subscriber",
                                          "-q", "PresentationAccessScope.Instance", "False, True"],
                                         ["-t", "dcpspublication"], runtime=2)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" not in ddsls_pub["stdout"]
    assert pubsub["status"] == 0

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "subscriber",
                                          "-q", "PresentationAccessScope.Instance", "False, True"],
                                         ["-t", "dcpssubscription"], runtime=2)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" in ddsls_sub["stdout"]
    assert pubsub["status"] == 0


def test_subscriber_multiple_qoses():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "subscriber",
                                          "-q", "PresentationAccessScope.Instance", "False, True",
                                          "Groupdata", "TestSubscriberQos"],
                                         ["-t", "dcpspublication"], runtime=2)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" not in ddsls_pub["stdout"]
    assert "Groupdata(data=b'TestSubscriberQos')" not in ddsls_pub["stdout"]
    assert pubsub["status"] == 0

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "subscriber",
                                          "-q", "PresentationAccessScope.Instance", "False, True",
                                          "Groupdata", "TestSubscriberQos"],
                                         ["-t", "dcpssubscription"], runtime=2)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" in ddsls_sub["stdout"]
    assert "Groupdata(data=b'TestSubscriberQos')" in ddsls_sub["stdout"]
    assert pubsub["status"] == 0


def test_writer_qos():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "datawriter",
                                          "--qos", "Durability.TransientLocal"],
                                         ["-t", "dcpspublication"], runtime=2)

    assert "Durability.TransientLocal" in ddsls_pub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]
    assert pubsub["status"] == 0

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "datawriter",
                                          "--qos", "Durability.TransientLocal"],
                                         ["-t", "dcpssubscription"], runtime=2)

    assert "Durability.TransientLocal" not in ddsls_sub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]
    assert pubsub["status"] == 0


def test_writer_multiple_qoses():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "datawriter",
                                          "--qos", "Durability.TransientLocal", "TransportPriority", "10"],
                                         ["-t", "dcpspublication"], runtime=2)

    assert "Durability.TransientLocal" in ddsls_pub["stdout"]
    assert "TransportPriority(priority=10)" in ddsls_pub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]
    assert pubsub["status"] == 0

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "datawriter",
                                          "--qos", "Durability.TransientLocal", "TransportPriority", "10"],
                                         ["-t", "dcpssubscription"], runtime=2)

    assert "Durability.TransientLocal" not in ddsls_sub["stdout"]
    assert "TransportPriority(priority=10)" not in ddsls_sub["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]
    assert pubsub["status"] == 0


def test_reader_qos():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "datareader",
                                          "--qos", "Durability.TransientLocal"],
                                         ["-t", "dcpspublication"], runtime=2)

    assert "Durability.TransientLocal" not in ddsls_pub["stdout"]
    assert pubsub["status"] == 0

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "datareader",
                                          "--qos", "Durability.TransientLocal"],
                                         ["-t", "dcpssubscription"], runtime=2)

    assert "Durability.TransientLocal" in ddsls_sub["stdout"]
    assert pubsub["status"] == 0


def test_reader_multiple_qoses():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "datareader",
                                          "--qos", "Durability.TransientLocal", "LatencyBudget", "10"],
                                         ["-t", "dcpspublication"], runtime=2)

    assert "Durability.TransientLocal" not in ddsls_pub["stdout"]
    assert "LatencyBudget(budget=10)" not in ddsls_pub["stdout"]
    assert pubsub["status"] == 0

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "datareader",
                                          "--qos", "Durability.TransientLocal", "LatencyBudget", "10"],
                                         ["-t", "dcpssubscription"], runtime=2)

    assert "Durability.TransientLocal" in ddsls_sub["stdout"]
    assert "LatencyBudget(budget=10)" in ddsls_sub["stdout"]
    assert pubsub["status"] == 0


def test_qos_help():
    pubsub = run_pubsub(["--qoshelp"])
    assert "Available QoS and usage" in pubsub["stdout"]
    assert "--qos Reliability.BestEffort" in pubsub["stdout"]
    assert "--qos Reliability.Reliable [max_blocking_time<integer>]" in pubsub["stdout"]
    assert "--qos Partition [partitions<Sequence[str]>]" in pubsub["stdout"]
    assert "--qos DurabilityService [cleanup_delay<integer>], [History.KeepAll / History.KeepLast [depth<integer>]], \
[max_samples<integer>], [max_instances<integer>], [max_samples_per_instance<integer>]" in pubsub["stdout"]

    assert pubsub["status"] == 0


def test_write_to_file(tmp_path):
    pubsub = run_pubsub(["-T", "test", "--filename", str(tmp_path / "test_pubsub.json"), "--runtime", "0.5"],
                        text=message+"\nhello\n[]")

    time.sleep(0.5)

    with open(tmp_path / "test_pubsub.json") as f:
        data = json.load(f)

    assert "string" == data["sequence 0"]["type"]
    assert "test" == data["sequence 0"]["keyval"]
    assert "integer" == data["sequence 1"]["type"]
    assert 420 == data["sequence 1"]["keyval"]
    assert "int_array" == data["sequence 2"]["type"]
    assert [4, 2, 0] == data["sequence 2"]["keyval"]
    assert "str_array" == data["sequence 3"]["type"]
    assert ['test', 'str', 'array', 'data', 'struct'] == data["sequence 3"]["keyval"]
    assert "int_sequence" == data["sequence 4"]["type"]
    assert [-1, 183] == data["sequence 4"]["keyval"]
    assert "str_sequence" == data["sequence 5"]["type"]
    assert ['test', 'string', 'sequence'] == data["sequence 5"]["keyval"]
    assert "string" == data["sequence 6"]["type"]
    assert "hello" == data["sequence 6"]["keyval"]
    assert "int_sequence" == data["sequence 7"]["type"]
    assert [] == data["sequence 7"]["keyval"]
    assert pubsub["status"] == 0


# test error messages


def test_not_applicable_entity_qos():
    pubsub, ddsls = run_pubsub_ddsls(["-T", "test",
                                      "--qos", "WriterDataLifecycle", "False",
                                      "-eqos", "subscriber"],
                                     ["-a"], runtime=2)

    assert ("InapplicableQosWarning: The Policy.WriterDataLifecycle(autodispose=False) is not applicable for subscriber"
            in pubsub["stderr"])
    assert "WriterDataLifecycle(autodispose=False)" not in ddsls["stdout"]
    assert "Integer(seq=1, keyval=420)" in pubsub["stdout"]


def test_incompatible_qos():
    pubsub, ddsls_pub = run_pubsub_ddsls(["-T", "test", "-eqos", "subscriber",
                                          "--qos", "PresentationAccessScope.Instance", "False, True"],
                                         ["-t", "dcpspublication"], runtime=2)
    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" not in ddsls_pub["stdout"]
    assert "The Qos requested for subscription is incompatible with the Qos offered by publication" in pubsub["stderr"]

    pubsub, ddsls_sub = run_pubsub_ddsls(["-T", "test", "-eqos", "subscriber",
                                          "--qos", "PresentationAccessScope.Instance", "False, True"],
                                         ["-t", "dcpssubscription"], runtime=2)

    assert "PresentationAccessScope.Instance(coherent_access=False, ordered_access=True)" in ddsls_sub["stdout"]
    assert "The Qos requested for subscription is incompatible with the Qos offered by publication" in pubsub["stderr"]

    assert "Integer(seq=1, keyval=420)" not in pubsub["stdout"]
    assert "String" not in pubsub["stdout"]
    assert "IntArray" not in pubsub["stdout"]
    assert "StrArray" not in pubsub["stdout"]
    assert "IntSequence" not in pubsub["stdout"]
    assert "StrSequence" not in pubsub["stdout"]


def test_qos_policy_error():
    pubsub = run_pubsub(["-T", "test", "-q", "Hello"])
    assert "No such policy policy.hello" in pubsub["stderr"]


def test_multiple_qos_policy_error():
    pubsub = run_pubsub(["-T", "test", "-q", "Durability.TransientLocal", "Durability.TransientLocal"])
    assert "ValueError: Multiple Qos policies of type Durability" in pubsub["stderr"]


def test_qos_policy_arguments_error():
    pubsub = run_pubsub(["-T", "test", "-q", "History.KeepLast", "hey"])
    assert "ValueError: invalid literal for int()" in pubsub["stderr"]

    pubsub = run_pubsub(["-T", "test", "-q", "WriterDataLifecycle", "sure"])
    assert "Invalid boolean sure" in pubsub["stderr"]


def test_qos_policy_arguments_number_error():
    pubsub = run_pubsub(["-T", "test", "-q", "History.KeepAll", "10"])
    assert "No such policy policy.10" in pubsub["stderr"]

    pubsub = run_pubsub(["-T", "test", "-q", "History.KeepLast"])
    assert "Exception: Unexpected end of arguments" in pubsub["stderr"]

    pubsub = run_pubsub(["-T", "test", "-q", "History.KeepLast", "10", "20"])
    assert "Exception: No such policy policy.20" in pubsub["stderr"]


def test_subqos_error():
    pubsub = run_pubsub(["-T", "test", "-q", "DurabilityService", "100"])
    assert "Exception: Unexpected end of arguments" in pubsub["stderr"]

    pubsub = run_pubsub(["-T", "test", "-q", "DurabilityService", "100, ResourceLimits 1, 10, 10"])
    assert "Exception: DurabilityService takes a History policy" in pubsub["stderr"]


def test_incompatible_qos_value():
    pubsub = run_pubsub(["-T", "test", "-q", "DurabilityService", "10, History.KeepLast 20, 30, 40, 50"])
    assert "Exception: The arguments inputted are considered invalid for cyclonedds" in pubsub["stderr"]


def test_input_data_error_msg():
    new_msg = "[1,'hello',2]"
    pubsub = run_pubsub(["-T", "test"], text=new_msg)
    assert "Exception: TypeError: Element type inconsistent" in pubsub["stderr"]


def test_select_eqos_without_qos_definitions():
    pubsub = run_pubsub(["-T", "test", "-eqos", "all"])
    assert "The following argument is required: -q/--qos" in pubsub["stderr"]

    pubsub = run_pubsub(["-T", "test", "-eqos", "topic"])
    assert "The following argument is required: -q/--qos" in pubsub["stderr"]


def test_file_open_error(tmp_path):
    data = run_ddsls(["--json", "-a", "--filename", f"{tmp_path}/this/path/denfinitely/doesnot/exist/ever"])
    assert f"Exception: Could not open file {tmp_path}/this/path/denfinitely/doesnot/exist/ever" in data["stderr"]


def test_input_syntax_error():
    pubsub = run_pubsub(["-T", "test"], text="[2,3,")
    assert "Input unrecognizable" in pubsub["stderr"]
