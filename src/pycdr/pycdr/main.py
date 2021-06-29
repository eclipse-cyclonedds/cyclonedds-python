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

from hashlib import md5

from .support import Buffer, Endianness, qualified_name
from .builder import Builder


class CDR:
    def __init__(self, datatype, final=True, mutable=False, appendable=False, nested=False,
                 autoid_hash=False, keylist=None):
        self.buffer = Buffer()
        self.datatype = datatype
        self.typename = qualified_name(datatype, sep='::')
        self.final = final
        self.mutable = mutable
        self.appendable = appendable
        self.nested = nested
        self.autoid_hash = autoid_hash

        self.keylist = keylist
        self.keyless = keylist is not None and len(keylist) == 0

        self.machine = None
        self.key_machine = None

        datatype.cdr = self
        Builder.build_machine(datatype)

    def serialize(self, object, buffer=None, endianness=None) -> bytes:
        if self.machine is None:
            report = ', '.join(Builder.missing_report_for(self.datatype))
            raise Exception(f"{self.typename} is relies on unknown types {report}.")

        ibuffer = buffer or self.buffer.seek(0)
        if endianness is not None:
            ibuffer.set_endianness(endianness)

        if ibuffer.endianness == Endianness.Big:
            ibuffer.write('b', 1, 0)
            ibuffer.write('b', 1, 0)
            ibuffer.write('b', 1, 0)
            ibuffer.write('b', 1, 0)
        else:
            ibuffer.write('b', 1, 0)
            ibuffer.write('b', 1, 1)
            ibuffer.write('b', 1, 0)
            ibuffer.write('b', 1, 0)
        ibuffer.set_align_offset(4)

        self.machine.serialize(ibuffer, object)
        return ibuffer.asbytes()

    def deserialize(self, data) -> object:
        if self.machine is None:
            raise Exception(f"{self.typename} relies on unknown types {', '.join(Builder.missing_report_for(self.datatype))}.")

        buffer = Buffer(data, align_offset=4) if not isinstance(data, Buffer) else data

        if buffer.tell() == 0:
            buffer.read('b', 1)
            v = buffer.read('b', 1)
            if v == 0:
                buffer.set_endianness(Endianness.Big)
            else:
                buffer.set_endianness(Endianness.Little)
            buffer.read('b', 1)
            buffer.read('b', 1)

        return self.machine.deserialize(buffer)

    def key(self, object) -> bytes:
        self.buffer.seek(0)
        self.buffer.zero_out()
        self.buffer.set_align_offset(0)
        self.buffer.set_endianness(Endianness.Big)

        self.key_machine.serialize(self.buffer, object)

        b = self.buffer.asbytes()
        return b.ljust(16, b'\0')

    def keyhash(self, object) -> bytes:
        if self.key_max_size <= 16:
            return self.key(object)

        m = md5()
        m.update(self.key(object))
        return m.digest()

    def cdr_key_machine(self, skip=False):
        return self.machine.cdr_key_machine_op(skip)


def proto_serialize(self, buffer=None, endianness=None):
    return self.cdr.serialize(self, buffer=buffer, endianness=endianness)


def proto_deserialize(cls, data):
    return cls.cdr.deserialize(data)
