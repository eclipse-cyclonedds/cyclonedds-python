import pytest

from cyclonedds.core import Entity, GuardCondition
from cyclonedds.util import isgoodentity


def test_init_guardcondition(common_setup):
    gc = GuardCondition(common_setup.dp)
    assert isgoodentity(gc)


def test_set_guardcondition(common_setup):
    gc = GuardCondition(common_setup.dp)
    gc.set(True)
    gc.set(False)


def test_read_guardcondition(common_setup):
    gc = GuardCondition(common_setup.dp)

    gc.set(True)
    assert gc.read() == True
    assert gc.read() == True

    gc.set(False)
    assert gc.read() == False
    assert gc.read() == False


def test_take_guardcondition(common_setup):
    gc = GuardCondition(common_setup.dp)

    gc.set(True)
    assert gc.take() == True
    assert gc.take() == False

    gc.set(False)
    assert gc.take() == False
    assert gc.take() == False

