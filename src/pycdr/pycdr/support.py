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

import sys
import struct

from inspect import isclass
from dataclasses import dataclass
from enum import IntEnum, Enum, auto


class CdrKeyVMOpType(IntEnum):
    Done = 0
    StreamStatic = 1
    Stream2ByteSize = 2
    Stream4ByteSize = 3
    ByteSwap = 4
    RepeatStatic = 5
    Repeat2ByteSize = 6
    Repeat4ByteSize = 7
    EndRepeat = 8
    Union1Byte = 9
    Union2Byte = 10
    Union4Byte = 11
    Union8Byte = 12
    Jump = 13


@dataclass
class CdrKeyVmOp:
    type: CdrKeyVMOpType
    skip: bool
    size: int = 0
    value: int = 0
    align: int = 0


class Endianness(Enum):
    Little = auto()
    Big = auto()

    @staticmethod
    def native():
        return Endianness.Little if sys.byteorder == "little" else Endianness.Big


class Buffer:
    def __init__(self, bytes=None, align_offset=0):
        self._bytes = bytearray(bytes) if bytes else bytearray(512)
        self._pos = 0
        self._size = len(self._bytes)
        self._endian = '='
        self._align_offset = align_offset
        self.endianness = Endianness.native()

    def set_endianness(self, endianness):
        self.endianness = endianness
        if self.endianness == Endianness.Little:
            self._endian = "<"
        else:
            self._endian = ">"

    def zero_out(self):
        # As per testing (https://stackoverflow.com/questions/19671145)
        # Quickest way to zero is to re-alloc..
        self._bytes = bytearray(self._size)

    def set_align_offset(self, offset):
        self._align_offset = offset

    def seek(self, pos):
        self._pos = pos
        return self

    def tell(self):
        return self._pos

    def ensure_size(self, size):
        if self._pos + size > self._size:
            old_bytes = self._bytes
            old_size = self._size
            self._size *= 2
            self._bytes = bytearray(self._size)
            self._bytes[0:old_size] = old_bytes

    def align(self, alignment):
        self._pos = ((self._pos - self._align_offset + alignment - 1) & ~(alignment - 1)) + self._align_offset
        return self

    def write(self, pack, size, value):
        self.ensure_size(size)
        struct.pack_into(self._endian + pack, self._bytes, self._pos, value)
        self._pos += size
        return self

    def write_bytes(self, bytes):
        length = len(bytes)
        self.ensure_size(length)
        self._bytes[self._pos:self._pos+length] = bytes
        self._pos += length
        return self

    def read_bytes(self, length):
        b = bytes(self._bytes[self._pos:self._pos+length])
        self._pos += length
        return b

    def read(self, pack, size):
        v = struct.unpack_from(self._endian + pack, buffer=self._bytes, offset=self._pos)
        self._pos += size
        return v[0]

    def asbytes(self):
        return bytes(self._bytes[0:self._pos])


class MaxSizeFinder:
    def __init__(self):
        self.size = 0

    def align(self, alignment):
        self.size = (self.size + alignment - 1) & ~(alignment - 1)

    def increase(self, bytes, alignment):
        self.align(alignment)
        self.size += bytes


def module_prefix(cls):
    cls = cls.__class__ if not isclass(cls) else cls
    module = cls.__module__
    if module is None or module == str.__class__.__module__:
        return ""
    return module + "."


def qualified_name(instance, sep="."):
    cls = instance.__class__ if not isclass(instance) else instance
    return (module_prefix(cls) + cls.__name__).replace('.', sep)
