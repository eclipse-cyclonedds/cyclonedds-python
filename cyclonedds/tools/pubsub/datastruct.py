"""
 * Copyright(c) 2021 to 2022 ZettaScale Technology and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
"""

from dataclasses import dataclass

from cyclonedds.idl import IdlStruct
from cyclonedds.idl.types import array, sequence
from cyclonedds.idl.annotations import key


@dataclass
class Integer(IdlStruct):
    seq: int
    keyval: int
    key("seq")
    key("keyval")

    @classmethod
    def postfix(cls):
        return "integer"


@dataclass
class String(IdlStruct):
    seq: int
    keyval: str
    key("seq")
    key("keyval")

    @classmethod
    def postfix(cls):
        return "string"


@dataclass
class IntArray(IdlStruct):
    seq: int
    keyval: array[int, 3]
    key("seq")
    key("keyval")

    @staticmethod
    def size():
        return 3

    @classmethod
    def postfix(cls):
        return "int_array"


@dataclass
class StrArray(IdlStruct):
    seq: int
    keyval: array[str, 5]
    key("seq")
    key("keyval")

    @staticmethod
    def size():
        return 5

    @classmethod
    def postfix(cls):
        return "str_array"


@dataclass
class IntSequence(IdlStruct):
    seq: int
    keyval: sequence[int]
    key("seq")
    key("keyval")

    @classmethod
    def postfix(cls):
        return "int_sequence"


@dataclass
class StrSequence(IdlStruct):
    seq: int
    keyval: sequence[str, 100]  # max 100 string elements
    key("seq")
    key("keyval")

    @classmethod
    def postfix(cls):
        return "str_sequence"


datatypes = [Integer, String, IntArray, StrArray, IntSequence, StrSequence]
