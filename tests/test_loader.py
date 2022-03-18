from cyclonedds.internal import CycloneDDSLoaderException, load_cyclonedds
from cyclonedds.__library__ import library_path, in_wheel
from pytest_mock import MockerFixture
import pytest
import os


if in_wheel:
    pytest.skip("Loader tests are not needed in wheels: loadpath is static.", allow_module_level=True)


def gen_test_loader(loadlist):
    def load(path):
        loadlist.append(path)
        return None
    return load


def gen_joiner(sep):
    def joiner(*args):
        return sep.join(args)
    return joiner


def common_mocks(mocker: MockerFixture, platform: str, ext: str):
    loadlist = []
    mocker.patch("ctypes.util.find_library", new=lambda x: None)
    mocker.patch("cyclonedds.internal._load", new=gen_test_loader(loadlist))
    mocker.patch("platform.system", new=lambda: platform)
    mocker.patch("os.environ", new={"CYCLONEDDS_HOME": "env_canary", "PATH": ""})
    return loadlist


def test_loading_linux(mocker: MockerFixture):
    paths = common_mocks(mocker, "Linux", ".so")
    try:
        load_cyclonedds()
    except CycloneDDSLoaderException:
        pass

    assert paths == [
        f"env_canary{os.sep}lib{os.sep}libddsc.so",
        "libddsc.so",
        library_path
    ]


def test_loading_macos(mocker):
    paths = common_mocks(mocker, "Darwin", ".dylib")
    try:
        load_cyclonedds()
    except CycloneDDSLoaderException:
        pass

    assert paths == [
        f"env_canary{os.sep}lib{os.sep}libddsc.dylib",
        "libddsc.dylib",
        library_path
    ]


def test_loading_windows(mocker):
    paths = common_mocks(mocker, "Windows", ".dll")
    try:
        load_cyclonedds()
    except CycloneDDSLoaderException:
        pass

    assert paths == [
        f"env_canary{os.sep}bin{os.sep}ddsc.dll",
        "ddsc.dll",
        library_path
    ]
