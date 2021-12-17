import time

from ..rand_idl.context_containers import FullContext
from ..rand_idl.simplifier import SimplifyRStruct
from ..rand_idl.value import generate_random_instance
from ..utility.stream import Stream

from cyclonedds.core import DDSStatus
from cyclonedds.qos import Qos, Policy
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import DataWriter
from cyclonedds.util import duration
from cyclonedds._clayer import ddspy_calc_key


def check_py_pyc_key_equivalence(log: Stream, ctx: FullContext, typename: str, num_samples: int) -> bool:
    datatype = ctx.get_datatype(typename)
    if datatype.__idl__.keyless:
        return True

    for i in range(num_samples):
        sample = generate_random_instance(datatype, seed=i)

        try:
            py_key = datatype.__idl__.key(sample)
        except Exception as e:
            log.write_exception("python-key", e)
            return False

        try:
            pyc_key = ddspy_calc_key(datatype.__idl__, sample.serialize())
        except Exception as e:
            log.write_exception("pyc-key", e)
            return False

        if not py_key == pyc_key:
            log << "PY-PYC Keys do not match!" << log.endl << log.indent
            log << "Instance: " << sample << log.endl
            log << "Serialized Instance:" << log.endl << sample.serialize()
            log << "Python key:" << log.endl << py_key
            log << "PyC key:" << log.endl << pyc_key
            log << log.dedent
            return False

    return True


def check_py_c_key_equivalence(log: Stream, ctx: FullContext, typename: str, num_samples: int) -> bool:
    datatype = ctx.get_datatype(typename)
    if datatype.__idl__.keyless:
        return True

    samples = [generate_random_instance(datatype, seed=i) for i in range(num_samples)]

    # We need to make sure the samples all have unique keys to make sure that we agree
    # on sample ordering with C
    keysamples = {}
    for s in samples:
        keysamples[datatype.__idl__.key(s)] = s
    samples = list(keysamples.values())

    dp = DomainParticipant()
    tp = Topic(dp, typename, datatype)
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
            log << f"C-app did not communicate with Python:" << log.endl << log.indent
            log << ctx.c_app.last_error << log.endl
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
        log << log.dedent << "Example sample sent:" << log.endl << log.indent
        log << samples[0] << log.endl << samples[0].serialize()
        log << log.dedent
        return False

    if len(hashes) != len(samples):
        log << f"C-app did not return as many samples as were sent, stderr:" << log.endl << log.indent
        log << ctx.c_app.last_error << log.endl << log.dedent
        log << log.dedent << "Example sample sent:" << log.endl << log.indent
        log << samples[0] << log.endl << samples[0].serialize()
        success = False

    for i in range(min(len(hashes), len(samples))):
        c_key = hashes[i]
        py_key = datatype.__idl__.key(samples[i])

        if not py_key == c_key:
            log << "PY-C Keys do not match!" << log.endl << log.indent
            log << "Instance: " << samples[i] << log.endl
            log << "Serialized Instance:" << log.endl << samples[i].serialize()
            log << "Python key:" << log.endl << py_key
            log << "C key:" << log.endl << c_key
            log << log.dedent
            return False

    return success


def figure_minimal_error_reproducer_idl(ctx: FullContext, typename: str, num_samples: int):
    ctx = ctx.narrow_context_of(typename)
    struct = ctx.scope.topics[0]
    simplifier = SimplifyRStruct(struct)

    for test in simplifier.get_tests():
        nctx = ctx.narrow_context_of_entity(test)
        devnull = Stream()
        simplifier.report(check_py_c_key_equivalence(devnull, nctx, typename, num_samples))

    nctx = ctx.narrow_context_of_entity(simplifier.minimal_err_struct)
    return nctx.idl_file
