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
from pycdr.types import int8, int16, uint16, map, sequence, array, union, case, default
import cyclonedds.core
from ddspy import ddspy_calc_key
from dataclasses import fields


@cdr(keylist=["a", "v"])
class Test:
    a: int8
    b: str
    v: uint16


@cdr(keylist=["a", "b"])
class Test2:
    a: int8
    b: str
    v: uint16

@union(int16)
class AU:
    a: case[-1, int8]
    b: case[1, array[int8, 2]]
    c: default[str]

@cdr(keylist=["k"])
class AUS:
    a: int
    k: AU
    v: float

@union(bool)
class AU1:
    a: case[True, int8]
    b: case[False, sequence[float, 8]]

@cdr(keylist=["k"])
class AU1S:
    a: sequence[int]
    k: AU1
    v: float
"""
tests = [
    Test(a=2, b="blah", v=8888),
    Test2(a=-1, b="klsjdfkljdljfd8ie8e8e8", v=818),
    Test2(a=-1, b="", v=818),
    AUS(a=100, k=AU(a=12), v=0.891),
    AUS(a=-100, k=AU(b=[9,121]), v=1.831),
    AUS(a=0, k=AU(c="lksdflkjdkf"), v=3.822),
    AU1S(a=[], k=AU1(a=8), v=8182.8),
    AU1S(a=[1,2,0,-1999], k=AU1(b=[0.1, 8.1]), v=66468.12),
]
"""
tests = [ AU1S(a=[], k=AU1(a=8), v=8182.8)]
def keyformat(key):
    return ' '.join('{:02x}'.format(x) for x in key)


for test in tests:
    data = test.serialize()
    pykey = test.cdr.key(test)
    vmkey = ddspy_calc_key(test.cdr, data)
    if pykey != vmkey:
        print("Failed:", test)
        print("py key:", keyformat(pykey))
        print("vm key:", keyformat(vmkey))
        print("vm ops:")
        for op in test.cdr.cdr_key_machine():
            print(f"\t{op}")
        print("data:", keyformat(data))
