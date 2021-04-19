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
from setuptools import setup, find_packages


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


if sys.version_info < (3, 6):
    sys.exit("This package cannot be installed in Python version 3.5 or lower.")
elif sys.version_info < (3, 7):
    # We are in any Python 3.6 version
    REQUIRES = ['dataclasses==0.8', 'typing-extensions==3.7.4.3', 'typing-inspect==0.6.0']
elif sys.version_info < (3, 9):
    # We are in any Python 3.7 or 3.8 version
    REQUIRES = ['typing-extensions==3.7.4.3']
else:
    # We are in any Python 3.9 or 3.10 (maybe higher?) version, no requirements
    REQUIRES = []


setup(
    name='pycdr',
    version='0.1.5',
    description='Python CDR serialization',
    long_description=long_description,
    install_requires=REQUIRES,
    author='Thijs Miedema',
    author_email='thijs.miedema@adlinktech.com',
    long_description_content_type="text/markdown",
    url="https://github.com/thijsmie/cdds-py",
    project_urls={
        "Bug Tracker": "https://github.com/thijsmie/cdds-py/issues"
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
    packages=find_packages(exclude=("tests", "examples")),
    python_requires='>=3.6'
)