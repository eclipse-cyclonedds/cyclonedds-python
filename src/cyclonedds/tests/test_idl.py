import sys
import pytest

from cyclonedds.idl import compile


@pytest.mark.skipif(sys.version_info >= (3, 10), reason="The import mechanism on Python 3.10 has changed, needs looking into.")
def test_compile_idl(tmp_path):
    file = tmp_path / "test.idl"
    file.write_text("""module test { struct TestData { string data; }; };""")
    types = compile(file)
    t = types[0].TestData(data="Hi!")
