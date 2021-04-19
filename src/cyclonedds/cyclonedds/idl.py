"""
 * Copyright(c) 2021 ADLINK Technology Limited and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
"""

import os
import sys
import platform
import tempfile
import importlib
import subprocess
from importlib.abc import MetaPathFinder


if "CYCLONEDDS_HOME" in os.environ:
    home = os.environ["CYCLONEDDS_HOME"]
    idlc = os.path.join(home, "bin", "idlc")
else:
    # Hopefully they are on the PATH
    if platform.system() == "Windows":
        idlc = "idlc.exe"
    else:
        idlc = "idlc"


def run_idlc(arg, dir):
    path = os.path.abspath(arg)
    proc = subprocess.Popen([idlc, "-l", "py", path], cwd=dir)
    proc.communicate()


def compile(idl_path):
    dir = tempfile.mkdtemp()
    run_idlc(idl_path, dir)
    module = os.listdir(dir)[0]

    sys.path.insert(0, dir)

    if module.endswith('.py'):
        module = module[:-3]

    module = importlib.import_module(module)
    sys.path.pop(0)
    return module


class JITIDL(MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if path is None or path == "":
            path = [os.getcwd()]  # top level import --

        # We are always only interested in the toplevel module
        if "." in fullname:
            name, *children = fullname.split(".")
        else:
            name = fullname

        loc_idl = None
        for entry in path:
            filename_idl = os.path.join(entry, name + ".idl")

            if os.path.exists(filename_idl):
                # IDL file located
                loc_idl = filename_idl

        if loc_idl:
            # We have found an idl file but we did not find a python module
            dir = os.path.dirname(loc_idl)
            run_idlc(loc_idl, dir)

        # Even if we have compiled the idl module we will let the normal python
        # system handle the import.
        return None


def enable_jit():
    sys.meta_path.insert(0, JITIDL())
