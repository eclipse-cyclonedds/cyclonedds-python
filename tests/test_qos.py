import pytest
import itertools
from cyclonedds.qos import Policy, Qos, _CQos, TopicQos


some_qosses = [
    Qos(Policy.Reliability.BestEffort),
    Qos(Policy.Reliability.Reliable(22)),
    Qos(Policy.Durability.Volatile),
    Qos(Policy.Durability.TransientLocal),
    Qos(Policy.Durability.Transient),
    Qos(Policy.Durability.Persistent),
    Qos(Policy.History.KeepAll),
    Qos(Policy.History.KeepLast(10)),
    Qos(Policy.ResourceLimits(3, 4, 5)),
    Qos(Policy.PresentationAccessScope.Instance(False, True)),
    Qos(Policy.PresentationAccessScope.Topic(True, True)),
    Qos(Policy.PresentationAccessScope.Group(False, False)),
    Qos(Policy.Lifespan(12001)),
    Qos(Policy.Deadline(2129981)),
    Qos(Policy.LatencyBudget(1337)),
    Qos(Policy.Ownership.Shared),
    Qos(Policy.Ownership.Exclusive),
    Qos(Policy.OwnershipStrength(8)),
    Qos(Policy.Liveliness.Automatic(898989)),
    Qos(Policy.Liveliness.ManualByParticipant(898989)),
    Qos(Policy.Liveliness.ManualByTopic(898989)),
    Qos(Policy.TimeBasedFilter(999900999)),
    Qos(Policy.Partition(["a", "b", "8isdfijsdifij3e8"])),
    Qos(Policy.TransportPriority(9)),
    Qos(Policy.DestinationOrder.ByReceptionTimestamp),
    Qos(Policy.DestinationOrder.BySourceTimestamp),
    Qos(Policy.WriterDataLifecycle(False)),
    Qos(Policy.ReaderDataLifecycle(7, 9)),
    Qos(Policy.DurabilityService(12, Policy.History.KeepAll, 99, 88, 77)),
    Qos(Policy.DurabilityService(112, Policy.History.KeepLast(66), 199, 188, 177)),
    Qos(Policy.IgnoreLocal.Nothing),
    Qos(Policy.IgnoreLocal.Participant),
    Qos(Policy.IgnoreLocal.Process),
    Qos(Policy.Userdata(b"1298129891lsakdjflksadjflas")),
    Qos(Policy.Groupdata(b"\0ksdlfkjsldkfj")),
    Qos(Policy.Topicdata(b"\n\nrrlskdjflsdj")),
    Qos(Policy.Userdata(b"1298129891lsakdjflksadjflas"),
        Policy.Groupdata(b"\0ksdlfkjsldkfj"),
        Policy.Topicdata(b"\n\nrrlskdjflsdj")),
    Qos(Policy.Property("a", "bs")),
    Qos(Policy.BinaryProperty("a", b"bs")),
    Qos(Policy.Property("a", "bs"), Policy.Property("b", "cs")),
    Qos(Policy.TypeConsistency.AllowTypeCoercion(True, False, True, False, True)),
    Qos(Policy.TypeConsistency.AllowTypeCoercion(False, False, False, True, True)),
    Qos(Policy.TypeConsistency.AllowTypeCoercion(True, True, False, False, False)),
    Qos(Policy.TypeConsistency.DisallowTypeCoercion(True)),
    Qos(Policy.TypeConsistency.DisallowTypeCoercion(False)),
    Qos(Policy.DataRepresentation(use_cdrv0_representation=True)),
    Qos(Policy.DataRepresentation(use_xcdrv2_representation=True)),
    Qos(Policy.DataRepresentation(use_cdrv0_representation=True, use_xcdrv2_representation=True)),
    Qos(Policy.EntityName("dihydrogenmonoxide"))
]

qos_pairs = list(itertools.combinations(some_qosses, 2))

def to_c_and_back(qos):
    cqos = _CQos.qos_to_cqos(qos)
    nqos = _CQos.cqos_to_qos(cqos)
    _CQos.cqos_destroy(cqos)
    return nqos


def test_qos_ops():
    for qos in some_qosses:
        assert qos == to_c_and_back(qos)
        assert qos == Qos.fromdict(qos.asdict())
        for policy in qos:
            assert policy in qos
        repr(qos)
        qos.domain_participant()
        qos.subscriber()
        qos.publisher()
        qos.topic()
        qos.datawriter()
        qos.datareader()
        assert qos - qos == Qos()
        assert qos + qos == qos


def test_qos_inequality():
    for qos1, qos2 in qos_pairs:
        assert qos1 != qos2


def test_qos_lookup():
    qos = Qos(Policy.Durability.Volatile)
    assert qos[Policy.Durability] == Policy.Durability.Volatile
    qos = Qos(Policy.History.KeepLast(20))
    assert qos[Policy.History] == Policy.History.KeepLast(20)
    assert qos[Policy.History.KeepLast] == Policy.History.KeepLast(20)


def test_qos_inheritance():
    qos = Qos(Policy.Durability.Volatile)
    qos2 = Qos(Policy.Deadline(10), base=qos)
    qos3 = Qos(Policy.Durability.Transient, base=qos)
    assert qos2 == Qos(Policy.Durability.Volatile, Policy.Deadline(10)) == Qos(Policy.Deadline(10), Policy.Durability.Volatile)
    assert qos3 == Qos(Policy.Durability.Transient)
    assert qos3 != Qos()
    assert qos3 != Qos(Policy.Durability.Volatile)


def test_qos_raise_wrong_usage():
    with pytest.raises(NotImplementedError):
        Policy()

    with pytest.raises(NotImplementedError):
        Policy.Durability()

    with pytest.raises(TypeError):
        Policy.Durability.Persistent()

    with pytest.raises(TypeError):
        Qos(1)

    with pytest.raises(ValueError):
        Qos(
            Policy.Durability.Persistent,
            Policy.Durability.Volatile
        )

    with pytest.raises(ValueError):
        Qos(
            Policy.Property("a", "b"),
            Policy.Property("a", "c")
        )

    with pytest.raises(ValueError):
        Qos.fromdict({"Durability": {}})

