import os
import time
import sys
import asyncio
import subprocess
import concurrent.futures

from cyclonedds.core import Entity, WaitSet, QueryCondition, SampleState, ViewState, InstanceState
from cyclonedds.qos import Qos, Policy
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
from cyclonedds.util import duration

from test_c_compatibility_classes import replybytes
from random_instance import generate_random_instance
from cyclonedds._clayer import ddspy_calc_key



NUM_SAMPLES = 50
def test_c_compat(virtualenv_with_py_c_compat):
    qos = Qos(
        Policy.Reliability.Reliable(duration(seconds=10)),
        Policy.Durability.TransientLocal,
        Policy.DestinationOrder.BySourceTimestamp,
        Policy.History.KeepAll
    )

    sys.path.insert(0, os.path.join(virtualenv_with_py_c_compat.dir, "lib", "site-packages"))
    print(virtualenv_with_py_c_compat.dir)
    import fuzzymod

    test_success = True
    for name in virtualenv_with_py_c_compat.typenames:
        #time.sleep(0.3)
        print(f"Testing {name}.")

        datatype = getattr(fuzzymod, name)
        samples = [generate_random_instance(datatype, seed=i) for i in range(NUM_SAMPLES)]

        # We need to make sure the samples all have unique keys to make sure that we agree
        # on sample ordering with C
        keysamples = {}
        for s in samples:
            keysamples[datatype.__idl__.key(s)] = s
        samples = list(keysamples.values())

        subproc: subprocess.Popen = virtualenv_with_py_c_compat.run(
            ["republisher", name, str(len(samples))], stdout=subprocess.DEVNULL
        )
        try:
            dp = DomainParticipant()

            #time.sleep(0.2)
            rtp = Topic(dp, "replybytes", replybytes)
            rd = DataReader(dp, rtp, qos=qos)
            stp = Topic(dp, name, datatype)
            wr = DataWriter(dp, stp, qos=qos)

            for s in samples:
                wr.write(s)

            num_recv = 0
            recv = [None] * len(samples)
            for samp in rd.read_iter(timeout=duration(seconds=5)):
                if samp.reply_to != name:
                    continue

                if recv[samp.seq] is None:
                    num_recv += 1
                    recv[samp.seq] = samp

                if num_recv == len(samples):
                    break

            for i, samp in enumerate(recv):
                if not samp or \
                    not samp.data == ddspy_calc_key(datatype.__idl__, samples[i].serialize()) == datatype.__idl__.key(samples[i]) or \
                    not bytes(samp.keyhash) == datatype.__idl__.keyhash(samples[i]):
                    print(f"Failure for datatype {name}, sample index: {i}.")
                    print(f"Sample: {samples[i]}")
                    print(f"Serialized sample: {samples[i].serialize().hex(' ')}")
                    print(f"Received key:          {samp.data.hex(' ')}" if samp else "Did not receive keydata.")
                    print(f"KeyVM calculated key:  {ddspy_calc_key(datatype.__idl__, samples[i].serialize()).hex(' ')}")
                    print(f"Python calculated key: {datatype.__idl__.key(samples[i]).hex(' ')}")
                    print(f"Received keyhash: {bytes(samp.keyhash).hex(' ')}")
                    print(f"Python keyhash:   {datatype.__idl__.keyhash(samples[i]).hex(' ')}")
                    print()
                    test_success = False
                    break

            try:
                subproc.communicate(timeout=1.0)
                if not subproc.returncode == 0:
                    test_success = False
                    print(f"Republisher {name} returned non-zero exit code ({subproc.returncode})")
                    print()

            except subprocess.TimeoutExpired:
                subproc.kill()
                test_success = False
                print(f"Republisher {name} timeout expired")
                print()

        finally:
            try:
                # Ensure we never have a dangling subprocess
                subproc.kill()
            except:
                pass

    assert test_success
