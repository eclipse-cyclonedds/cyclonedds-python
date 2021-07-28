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

from os import path, listdir
from sys import exit


dir = path.abspath(path.join(path.dirname(__file__), ".libs"))
libs = [f for f in listdir(dir) if "idl" in f]

if not libs:
    exit(1)

print(path.join(dir, libs[0]), end="", flush=True)
exit(0)
