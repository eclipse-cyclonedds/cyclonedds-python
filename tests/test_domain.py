import pytest

from cyclonedds.domain import Domain, DomainParticipant


def test_domain_initialize():
    domain = Domain(1)

def test_domain_lookup():
    domain = Domain(1)
    dp = DomainParticipant(1)

    pc = domain.get_participants()
    assert len(pc) == 1 and pc[0] == dp