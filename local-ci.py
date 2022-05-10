#!/usr/bin/env python
"""
 * Copyright(c) 2021 ZettaScale Technology and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause

This Python file runs steps like CI does for local development.
"""

import os
import sys
import argparse
import tempfile
import subprocess


def parse_arguments(args) -> argparse.Namespace:
    """
    Parse local-ci arguments, resulting namespace contains:
     * 'install', 'no-linter', 'no-tests', 'quiet', 'fuzzing'
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--install", action="store_true", default=False,
                        help="Reinstall the Cyclonedds package from script directory")

    parser.add_argument("--no-linter", action="store_true", default=False,
                        help="Disable flake8 linting on the Cyclonedds package.")

    parser.add_argument("--no-tests", action="store_true", default=False,
                        help="Disable pytest testsuite on the Cyclonedds package.")

    parser.add_argument("-q", "--quiet", action="store_true", default=False,
                        help="Suppress all tool output.")

    parser.add_argument("-f", "--fuzzing", action="store_true", default=False,
                        help="Run fuzzing.")

    return parser.parse_args(args)


def install(output):
    """Install CycloneDDS into active python env"""
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", os.path.abspath(os.path.dirname(__file__)) + "[dev]"],
        **output)


def linter(output):
    """Run flake8 linting"""
    # Linter - critical -
    subprocess.check_call(
        [sys.executable, "-m", "flake8", "--select=E9,F63,F7,F82", "--show-source"],
        cwd=os.path.abspath(os.path.dirname(__file__)),
        **output)

    # Linter - lax -
    subprocess.check_call(
        [sys.executable, "-m", "flake8", "--exit-zero"],
        cwd=os.path.abspath(os.path.dirname(__file__)),
        **output)


def tests(output, add_fuzzer):
    """Run tests with pytest"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        subprocess.check_call(
            [sys.executable, "-m", "pytest", os.path.abspath(os.path.dirname(__file__))] + (
                ["--fuzzing"] if add_fuzzer else []
            ),
            cwd=tmp_dir,
            **output)


if __name__ == "__main__":
    args = parse_arguments(sys.argv[1:])

    output = dict() if args.quiet else dict(stdout=sys.stdout, stderr=sys.stderr)

    if args.install:
        install(output)

    if not args.no_linter:
        linter(output)

    if not args.no_tests:
        tests(output, args.fuzzing)
