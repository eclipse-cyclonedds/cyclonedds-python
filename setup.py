#!/usr/bin/env python

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
import sys
from pathlib import Path
from setuptools import setup, Extension, find_packages

this_directory = Path(__file__).resolve().parent
sys.path.insert(0, str(this_directory / 'buildhelp'))

from cyclone_search import find_cyclonedds
from build_ext import build_ext, Library
from bdist_wheel import bdist_wheel


with open(this_directory / 'README.md', encoding='utf-8') as f:
    long_description = f.read()


if "BUILDING_SDIST" not in os.environ:
    cyclone = find_cyclonedds()

    if not cyclone:
        print("Could not locate cyclonedds. Try to set CYCLONEDDS_HOME or CMAKE_PREFIX_PATH")
        import sys
        sys.exit(1)


    with open(this_directory / 'cyclonedds' / '__library__.py', "w", encoding='utf-8') as f:
        f.write("in_wheel = False\n")
        f.write(f"library_path = '{cyclone.ddsc_library}'")


    ext_modules = [
        Extension('cyclonedds._clayer', [
                'clayer/cdrkeyvm.c',
                'clayer/pysertype.c',
                'clayer/typeser.c'
            ],
            include_dirs=[
                str(cyclone.include_path),
                str(this_directory / "clayer")
            ],
            libraries=['ddsc'],
            library_dirs=[
                str(cyclone.library_path),
                str(cyclone.binary_path),
            ]
        )
    ]

    if cyclone.idlc_library:
        ext_modules += [
            Library('cyclonedds._idlpy', [
                    'idlpy/src/context.c',
                    'idlpy/src/generator.c',
                    'idlpy/src/naming.c',
                    'idlpy/src/ssos.c',
                    'idlpy/src/types.c',
                    'idlpy/src/util.c'
                ],
                include_dirs=[
                    str(cyclone.include_path),
                    str(this_directory / "idlpy" / "include")
                ],
                libraries=['ddsc', 'cycloneddsidl'],
                library_dirs=[
                    str(cyclone.library_path),
                    str(cyclone.binary_path)
                ]
            )
        ]
else:
    ext_modules=[]


setup(
    name='cyclonedds',
    version='0.9.0',
    description='Eclipse Cyclone DDS Python binding',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Eclipse Cyclone DDS Committers',
    maintainer='Thijs Miedema',
    maintainer_email='thijs.miedema@adlinktech.com',
    url="https://cyclonedds.io",
    project_urls={
        "Documentation": "https://cyclonedds.io/docs",
        "Source Code": "https://github.com/eclipse-cyclonedds/cyclonedds-python",
        "Bug Tracker": "https://github.com/eclipse-cyclonedds/cyclonedds-python/issues"
    },
    license="EPL-2.0, BSD-3-Clause",
    platforms=["Windows", "Linux", "Mac OS-X", "Unix"],
    keywords=[
        "eclipse", "cyclone", "dds", "pub", "sub",
        "pubsub", "iot", "cyclonedds", "cdr", "omg",
        "idl", "middleware", "ros"
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: Eclipse Public License 2.0 (EPL-2.0)",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent"
    ],
    packages=find_packages(".", include=("cyclonedds", "cyclonedds.*")),
    package_data={
        "cyclonedds": ["*.so", "*.dylib", "*.dll", "idlc*", "*py.typed"],
        "cyclonedds.idl": ["py.typed"]
    },
    ext_modules=ext_modules,
    cmdclass={
        'bdist_wheel': bdist_wheel,
        'build_ext': build_ext,
    },
    entry_points={
        "console_scripts": [
            "ddsls=cyclonedds.tools.ddsls:command",
            "pubsub=cyclonedds.tools.pubsub:command"
        ],
    },
    python_requires='>=3.7',
    install_requires=[
        "typing-inspect>=0.6;python_version<'3.7'",
        "typing-extensions>=3.7;python_version<'3.9'"
    ],
    extras_require={
        "dev": [
            "pytest>=6.2",
            "pytest-cov",
            "pytest-mock",
            "flake8",
            "flake8-bugbear",
            "twine"
        ],
        "docs": [
            "Sphinx>=4.0.0",
            "sphinx-rtd-theme>=0.5.2"
        ]
    },
    zip_safe=False
)
