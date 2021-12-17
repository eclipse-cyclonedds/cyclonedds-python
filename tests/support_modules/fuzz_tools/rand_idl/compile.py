from pathlib import Path
import subprocess
import traceback
import importlib
import tempfile
import sys


def compile_idl(idl_text, module):
    tdir = tempfile.TemporaryDirectory()
    directory = Path(tdir.name).resolve()
    idl_file = directory / "_fuzzytypes.idl"

    with open(idl_file, "w") as f:
        f.write(idl_text)

    compiler = subprocess.Popen(
        ['idlc', '-l', 'py', str(idl_file)],
        cwd=directory,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = compiler.communicate()

    if stdout or stderr:
        print("IDLC stdout:", stdout.decode())
        print("IDLC stderr:", stderr.decode())

    sys.path.insert(0, str(directory))
    try:
        imported = importlib.import_module(module)
    except ImportError:
        print("Failed to import IDL generated module")
        raise
    finally:
        sys.path.pop(0)

    return imported, tdir
