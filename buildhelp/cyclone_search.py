"""
 * Copyright(c) 2022 ZettaScale Technology and others
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
import platform
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class FoundCycloneResult:
    home: Path
    library_path: Path
    include_path: Path
    binary_path: Path
    ddsc_library: Path
    idlc_executable: Optional[Path]
    idlc_library: Optional[Path]
    security_libs: List[Path]


def first_or_none(alist):
    alist = list(alist)
    if alist:
        return alist[0]


def good_directory(directory: Path):
    dir = directory.resolve()
    if not dir.exists():
        return

    include_path = dir / 'include'
    bindir = dir / 'bin'

    if not include_path.exists() or not bindir.exists():
        return

    libdir = dir / 'lib'
    if not libdir.exists():
        libdir = dir / 'lib64'
        if not libdir.exists():
            return None

    if platform.system() == 'Windows':
        ddsc_library = bindir / "ddsc.dll"
    elif platform.system() == 'Darwin':
        ddsc_library = libdir / "libddsc.dylib"
    else:
        ddsc_library = libdir / "libddsc.so"

    if not ddsc_library.exists():
        return None

    idlc_executable = first_or_none(bindir.glob("idlc*"))
    idlc_library = first_or_none(libdir.glob('libcycloneddsidl*')) or first_or_none(bindir.glob("cycloneddsidl*"))
    security_libs = list(libdir.glob("*dds_security_*")) + list(bindir.glob("*dds_security_*"))

    return FoundCycloneResult(
        home=dir,
        include_path=include_path,
        library_path=libdir,
        binary_path=bindir,
        ddsc_library=ddsc_library,
        idlc_executable=idlc_executable,
        idlc_library=idlc_library,
        security_libs=security_libs
    )


def search_cyclone_pathlike(pathlike, upone=False):
    for path in pathlike.split(os.pathsep):
        if upone:
            return good_directory(Path(path) / '..')
        else:
            return good_directory(Path(path))


def find_cyclonedds() -> Optional[FoundCycloneResult]:
    if "STANDALONE_WHEELS" in os.environ:
        dir = good_directory(Path(__file__).parent.parent / "cyclonedds-build")
        if dir:
            return dir
    if "CYCLONEDDS_HOME" in os.environ:
        dir = good_directory(Path(os.environ["CYCLONEDDS_HOME"]))
        if dir:
            return dir
    if "CycloneDDS_ROOT" in os.environ:
        dir = good_directory(Path(os.environ["CMAKE_CycloneDDS_ROOT"]))
        if dir:
            return dir
    if "CycloneDDS_ROOT" in os.environ:
        dir = good_directory(Path(os.environ["CycloneDDS_ROOT"]))
        if dir:
            return dir
    if "CMAKE_PREFIX_PATH" in os.environ:
        dir = search_cyclone_pathlike(os.environ["CMAKE_PREFIX_PATH"])
        if dir:
            return dir
    if "CMAKE_LIBRARY_PATH" in os.environ:
        dir = search_cyclone_pathlike(os.environ["CMAKE_LIBRARY_PATH"])
        if dir:
            return dir
    if platform.system() != "Windows" and "LIBRARY_PATH" in os.environ:
        dir = search_cyclone_pathlike(os.environ["LIBRARY_PATH"], upone=True)
        if dir:
            return dir
    if platform.system() != "Windows" and "LD_LIBRARY_PATH" in os.environ:
        dir = search_cyclone_pathlike(os.environ["LD_LIBRARY_PATH"], upone=True)
        if dir:
            return dir
    if platform.system() == "Windows" and "PATH" in os.environ:
        dir = search_cyclone_pathlike(os.environ["PATH"], upone=True)
        if dir:
            return dir

