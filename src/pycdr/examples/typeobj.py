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

from pycdr import cdr
from pycdr.types import int8, int16, uint16, map, sequence, array
from pycdr.type_object.builder import TypeObjectBuilder

@cdr
class Test2:
    a: int8
    b: str
    v: uint16


@cdr
class Test:
    a: int8
    b: int16
    c: str
    d: bool
    e: float
    f: Test2
    k: sequence[int, 12]
    l: sequence[str]
    m: array[bool, 3]


# The Typeobject is still a work in progress
t = TypeObjectBuilder()
print(t.to_typeobject(Test))
print(t.hash_of(Test, False))