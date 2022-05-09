from copy import deepcopy

from ..rand_idl.value import generate_random_instance

from ..rand_idl.context_containers import FullContext
from ..rand_idl.mutator import mutate, non_valid_mutation
from ..utility.stream import Stream
import time

from ..rand_idl.context_containers import FullContext
from ..rand_idl.value import generate_random_instance
from ..utility.stream import Stream

from cyclonedds.core import DDSStatus, DDSException
from cyclonedds.qos import Qos, Policy
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import DataWriter
from cyclonedds.util import duration



def check_mutation_assignability(log: Stream, ctx: FullContext, typename: str, num_samples: int) -> bool:
    narrow_ctx = ctx.narrow_context_of(typename)
    new_scope = deepcopy(narrow_ctx.scope)
    mutate(new_scope, typename)
    alt_ctx = FullContext(new_scope)

    datatype_a = ctx.get_datatype(typename)
    datatype_b = alt_ctx.get_datatype(typename)

    for i in range(num_samples):
        sample = generate_random_instance(datatype_a, i)

        try:
            bsample = datatype_b.deserialize(sample.serialize())
            assert datatype_b.__idl__.key(bsample) == datatype_a.__idl__.key(sample)
        except AssertionError:
            log << "Mutation failed, keys unequal" << log.endl << log.indent
            log << "A: " << datatype_a << log.endl
            log << "B: " << datatype_b << log.endl
            log << "sample: " << sample << log.endl
            log << log.dedent << "[Mutated IDL]:" << log.indent << log.endl
            log << alt_ctx.idl_file << log.endl
            log << log.dedent
            return False
        except Exception as e:
            log << "Mutation failed." << log.endl << log.indent
            log << "A: " << datatype_a << log.endl
            log << "B: " << datatype_b << log.endl
            log << "sample: " << sample << log.endl
            log.write_exception("mutated_deser", e)
            log << log.dedent << "[Mutated IDL]:" << log.indent << log.endl
            log << alt_ctx.idl_file << log.endl
            log << log.dedent
            return False

    for i in range(num_samples):
        sample = generate_random_instance(datatype_b, i)

        try:
            asample = datatype_a.deserialize(sample.serialize())
            assert datatype_b.__idl__.key(sample) == datatype_a.__idl__.key(asample)
        except AssertionError:
            log << "Mutation failed, keys unequal" << log.endl << log.indent
            log << "A: " << datatype_a << log.endl
            log << "B: " << datatype_b << log.endl
            log << "sample: " << sample << log.endl
            log << log.dedent << "[Mutated IDL]:" << log.indent << log.endl
            log << alt_ctx.idl_file << log.endl
            log << log.dedent
            return False

        except Exception as e:
            log << "Mutation failed." << log.endl << log.indent
            log << "A: " << datatype_a << log.endl
            log << "B: " << datatype_b << log.endl
            log << "sample: " << sample << log.endl
            log.write_exception("mutated_deser", e)
            log << log.dedent << "[Mutated IDL]:" << log.indent << log.endl
            log << alt_ctx.idl_file << log.endl
            log << log.dedent
            return False

    return True


def check_mutation_key(log: Stream, ctx: FullContext, typename: str, num_samples: int) -> bool:
    datatype_regular = ctx.get_datatype(typename)
    if datatype_regular.__idl__.keyless:
        return True

    narrow_ctx = ctx.narrow_context_of(typename)
    new_scope = deepcopy(narrow_ctx.scope)
    mutate(new_scope, typename)
    mutated_ctx = FullContext(new_scope)
    mutated_datatype = mutated_ctx.get_datatype(typename)

    if typename == "Zerepainam":
        print(mutated_ctx.idl_file)

    if narrow_ctx.idl_file[1:] == mutated_ctx.idl_file[1:]:
        return True

    samples = [generate_random_instance(mutated_datatype, seed=i) for i in range(num_samples)]

    # We need to make sure the samples all have unique keys to make sure that we agree
    # on sample ordering with C
    keysamples = {}
    for s in samples:
        keysamples[mutated_datatype.__idl__.key(s)] = s
    samples = list(keysamples.values())

    dp = DomainParticipant()
    tp = Topic(dp, typename, mutated_datatype)
    dw = DataWriter(dp, tp, qos=Qos(
        Policy.DataRepresentation(use_xcdrv2_representation=True),
        Policy.History.KeepLast(len(samples)),
        Policy.Reliability.Reliable(duration(seconds=2)),
        Policy.DestinationOrder.BySourceTimestamp
    ))
    dw.set_status_mask(DDSStatus.PublicationMatched)
    dw.take_status()

    ctx.c_app.run(typename, len(samples))

    now = time.time()
    while (dw.take_status() & DDSStatus.PublicationMatched) == 0:
        if time.time() - now > 4:
            # timeout if C app did not start up within 4 seconds
            ctx.c_app.result()
            log << f"C-app did not communicate with Mutated Python:" << log.endl << log.indent
            log << ctx.c_app.last_error << log.endl
            log << log.dedent << "[Mutated IDL]:" << log.indent << log.endl
            log << mutated_ctx.idl_file << log.endl
            log << log.dedent
            return False
        time.sleep(0.001)

    time.sleep(0.2)

    for sample in samples:
        dw.write(sample)
        time.sleep(0.002)

    hashes = ctx.c_app.result()
    success = True

    if not hashes:
        log << f"C-app did not return output, stderr:" << log.endl << log.indent
        log << ctx.c_app.last_error << log.endl
        log << f"stdout:" << log.endl
        log << ctx.c_app.last_out << log.endl
        log << log.dedent << "Example Mutated sample sent:" << log.endl << log.indent
        log << samples[0] << samples[0].serialize()
        log << log.dedent << "[Mutated IDL]:" << log.indent << log.endl
        log << mutated_ctx.idl_file << log.endl
        log << log.dedent
        return False

    if len(hashes) != len(samples):
        log << f"C-app did not return as many samples as were sent, stderr:" << log.endl << log.indent
        log << ctx.c_app.last_error << log.endl << log.dedent
        log << log.dedent << "Example Mutated sample sent:" << log.endl << log.indent
        log << samples[0] << samples[0].serialize()
        log << log.dedent << "[Mutated IDL]:" << log.indent << log.endl
        log << mutated_ctx.idl_file << log.endl
        log << log.dedent
        success = False

    for i in range(min(len(hashes), len(samples))):
        c_key = hashes[i]
        py_key = mutated_datatype.__idl__.key(samples[i])

        if not py_key == c_key:
            log << "Mutated PY-C Keys do not match!" << log.endl << log.indent
            log << "Instance: " << samples[i] << log.endl
            log << "Mutated Serialized Instance:" << log.endl << samples[i].serialize()
            log << "Mutated Python key:" << log.endl << py_key
            log << "C key:" << log.endl << c_key
            log << log.dedent << "[Mutated IDL]:" << log.indent << log.endl
            log << mutated_ctx.idl_file << log.endl
            log << log.dedent
            return False

    return success


def check_enforced_non_communication(log: Stream, ctx: FullContext, typename: str) -> bool:
    datatype_regular = ctx.get_datatype(typename)
    if datatype_regular.__idl__.keyless:
        return True

    narrow_ctx = ctx.narrow_context_of(typename)
    new_scope = deepcopy(narrow_ctx.scope)
    non_valid_mutation(new_scope, typename)
    mutated_ctx = FullContext(new_scope)
    mutated_datatype = mutated_ctx.get_datatype(typename)

    if narrow_ctx.idl_file[1:] == mutated_ctx.idl_file[1:]:
        # No mutation took place (only unions) just assume it is good
        return True

    dp = DomainParticipant()

    try:
        tp = Topic(dp, typename, mutated_datatype)
    except DDSException:
        # Sometimes the type gets so mangled (like empty structs/unions)
        # that it is not a valid topic type anymore. We'll consider this a
        # successful test.
        return True

    dw = DataWriter(dp, tp, qos=Qos(
        Policy.DataRepresentation(use_xcdrv2_representation=True),
        Policy.Reliability.Reliable(duration(seconds=2)),
        Policy.DestinationOrder.BySourceTimestamp
    ))
    dw.set_status_mask(DDSStatus.PublicationMatched)
    dw.take_status()

    ctx.c_app.run(typename, 1)

    now = time.time()
    while (dw.take_status() & DDSStatus.PublicationMatched) == 0:
        if time.time() - now > 0.5:
            ctx.c_app.process.kill()
            return True
        time.sleep(0.001)

    ctx.c_app.process.kill()

    log << f"C-app agreed to communicate with non-valid mutation" << log.endl << log.indent
    log << log.dedent << "[Mutated IDL]:" << log.indent << log.endl
    log << mutated_ctx.idl_file << log.endl
    log << log.dedent
    return False
