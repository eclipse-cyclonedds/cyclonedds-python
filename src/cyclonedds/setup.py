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
import logging
from setuptools import find_packages
from skbuild import setup

setup(
    name='cyclonedds',
    version='0.8.0',
    description='Cyclone DDS Python binding',
    author='Thijs Miedema',
    author_email='thijs.miedema@adlinktech.com',
    url="https://github.com/eclipse-cyclonedds/cyclonedds-python",
    project_urls={
        "Bug Tracker": "https://github.com/eclipse-cyclonedds/cyclonedds-python/issues"
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: Eclipse Public License 2.0 (EPL-2.0)",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent"
    ],
    install_requires=["pycdr"],
    packages=find_packages('.', exclude=("tests", "examples")),
    entry_points={
        "console_scripts": [
            "ddsls=cyclonedds.tools.ddsls:command",
            "pubsub=cyclonedds.tools.pubsub:command"
        ],
    },
    python_requires='>=3.6'
)
