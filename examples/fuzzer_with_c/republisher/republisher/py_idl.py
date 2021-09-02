import os
import sys
import shutil
import tempfile
import subprocess


# Make sure we have idlpy
from cyclonedds.__idlc__ import idlpy_lib


dir = os.path.abspath(os.path.dirname(__file__))


class ManualCleanupDir:
    def __init__(self, dir) -> None:
        self.dir = dir

    def cleanup(self):
        shutil.rmtree(self.dir)


def compile_and_add_to_path(file):
    t = tempfile.mkdtemp()
    p = subprocess.Popen(["idlc", "-l", idlpy_lib, file], cwd=t)
    sys.path.insert(0, t)
    p.communicate()
    return ManualCleanupDir(t)