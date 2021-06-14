from cyclonedds.internal import CycloneDDSLoaderException, load_cyclonedds
from pytest_mock import MockerFixture


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
    mocker.patch("cyclonedds.internal._load", new=gen_test_loader(loadlist))
    mocker.patch("platform.system", new=lambda: platform)
    mocker.patch("os.path.join", new=gen_joiner("\\" if platform == "Windows" else "/"))
    mocker.patch("os.path.exists", new=lambda p: True)
    mocker.patch("os.listdir", new=lambda p: [f"libddsc_listdir_canary{ext}"])
    mocker.patch("os.path.dirname", new=lambda f: "dirname_canary")
    mocker.patch("os.environ", new={"CYCLONEDDS_HOME": "env_canary", "PATH": ""})
    return loadlist


def test_loading_linux(mocker: MockerFixture):
    paths = common_mocks(mocker, "Linux", ".so")
    try:
        load_cyclonedds()
    except CycloneDDSLoaderException:
        pass

    assert paths == [
        "dirname_canary/../cyclonedds.libs/libddsc_listdir_canary.so",
        "env_canary/lib/libddsc.so",
        "libddsc.so",
        "/lib/libddsc.so",
        "/lib64/libddsc.so",
        "/usr/lib/libddsc.so",
        "/usr/lib64/libddsc.so",
        "/usr/local/lib/libddsc.so",
        "/usr/local/lib64/libddsc.so",
    ]


def test_loading_macos(mocker):
    paths = common_mocks(mocker, "Darwin", ".dylib")
    try:
        load_cyclonedds()
    except CycloneDDSLoaderException:
        pass

    assert paths == [
        "dirname_canary/.dylibs/libddsc_listdir_canary.dylib",
        "env_canary/lib/libddsc.dylib",
        "libddsc.dylib",
        "/lib/libddsc.dylib",
        "/lib64/libddsc.dylib",
        "/usr/lib/libddsc.dylib",
        "/usr/lib64/libddsc.dylib",
        "/usr/local/lib/libddsc.dylib",
        "/usr/local/lib64/libddsc.dylib",
    ]


def test_loading_windows(mocker):
    paths = common_mocks(mocker, "Windows", ".dll")
    try:
        load_cyclonedds()
    except CycloneDDSLoaderException:
        pass

    assert paths == [
        "dirname_canary\\..\\cyclonedds.libs\\libddsc_listdir_canary.dll",
        "env_canary\\bin\\ddsc.dll",
        "ddsc.dll"
    ]
