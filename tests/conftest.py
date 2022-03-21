import os
import sys
import pytest
from pathlib import Path

# Remove working dir to avoid importing the un-installed cyclonedds install
try:
    sys.path.remove(os.getcwd())
except:
    pass

# Allow the import of support modules for tests
sys.path.append(str(Path(__file__).resolve().parent))

from support_modules.test_tools.fixtures import Common, Manual, HitPoint, FuzzingConfig


global domain_id_counter
domain_id_counter = 0

@pytest.fixture
def common_setup() -> Common:
    # Ensuring a unique domain id for each setup ensures parellization options
    global domain_id_counter
    domain_id_counter += 1
    return Common(domain_id=domain_id_counter)


@pytest.fixture
def manual_setup() -> Manual:
    # Ensuring a unique domain id for each setup ensures parellization options
    global domain_id_counter
    domain_id_counter += 1
    return Manual(domain_id=domain_id_counter)


@pytest.fixture
def hitpoint():
    return HitPoint()


@pytest.fixture
def hitpoint_factory():
    return HitPoint


# Fuzzing testsuite

def pytest_addoption(parser):
    parser.addoption("--fuzzing", action="store", nargs='*', type=str, help="You can specify FuzzingConfig parameters: num_types=12 num_samples=11 store_reproducers=True")


def pytest_runtest_setup(item):
    if 'fuzzing' in item.keywords and item.config.getoption("fuzzing") is None:
        pytest.skip("need --fuzzing option to run this test")


@pytest.fixture
def fuzzing_config(pytestconfig) -> FuzzingConfig:
    assert "fuzzing" in pytestconfig.option
    data = {}
    for arg in pytestconfig.getoption("fuzzing"):
        name, value = arg.split('=')
        if name in ["num_types", "num_samples", "type_seed", "skip_types"]:
            value = int(value)
        elif name in ["store_reproducers", "mutation_failure_fatal"]:
            value = bool(value)
        elif name in ["idl_file", "typenames"]:
            pass
        else:
            raise ValueError(f"Unknown config item {name}")
        data[name] = value
    return FuzzingConfig(**data)
