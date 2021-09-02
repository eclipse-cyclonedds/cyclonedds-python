#!/usr/bin/env python
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
from skbuild import setup

# We sadly need this python dep at install time so we insert the current dir into the import path
dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, dir)
from republisher.fuzzy_idl_definition import random_idl_types


fuzzpath = os.path.join(dir, "src", "fuzzymod.idl")
idl, typenames = random_idl_types(seed=1, module="fuzzymod", number=100)

with open(fuzzpath, "w") as f:
    f.write(idl)


setup(
    name='republisher',
    packages=["republisher"],
    package_data={'': ['*.idl']},
    include_package_data=True,
    cmake_args=[
        "-DFUZZY_TYPES=" + ";".join(typenames)
    ],
    install_requires=[
        "cyclonedds"
    ]
)
