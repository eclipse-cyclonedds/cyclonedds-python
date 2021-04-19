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

from .machinery import build_machine, build_key_machine, Buffer, MaxSizeFinder

from hashlib import md5
from collections import defaultdict
from inspect import isclass


def module_prefix(cls):
    cls = cls.__class__ if not isclass(cls) else cls
    module = cls.__module__
    if module is None or module == str.__class__.__module__:
        return ""
    return module + "."


def qualified_name(instance):
    cls = instance.__class__ if not isclass(instance) else instance
    return module_prefix(cls) + cls.__name__


class CDR:
    defined_references = {}
    deferred_references = defaultdict(list)

    def resolve(self, type_name, instance):
        if '.' in qualified_name(self.datatype) and not '.' in type_name:
            # We got a local name, but we only deal in full paths
            type_name = module_prefix(self.datatype) + type_name

        if type_name not in self.defined_references:
            self.deferred_references[type_name].append(instance)
            return None
        return self.defined_references[type_name]

    @classmethod
    def refer(cls, type_name, object):
        for instance in cls.deferred_references[type_name]:
            instance.refer(object)
        del cls.deferred_references[type_name]
        cls.defined_references[type_name] = object

    def __init__(self, datatype, final=False, mutable=False, appendable=True, nested=False, autoid_hash=False, keylist=None):
        self.buffer = Buffer()
        self.datatype = datatype
        self.typename = qualified_name(datatype)
        self.final = final
        self.mutable = mutable
        self.appendable = appendable
        self.nested = nested
        self.autoid_hash = autoid_hash
        self.keylist = keylist

        self.machine = build_machine(self, datatype, True)
        self.key_machine = build_key_machine(self, keylist, datatype) if keylist else self.machine

        self.keyless = keylist is None

    def finalize(self):
        if not hasattr(self, 'key_max_size'):
            finder = MaxSizeFinder()
            self.key_machine.max_size(finder)
            self.key_max_size = finder.size

    def serialize(self, object, buffer=None) -> bytes:
        buffer = buffer or self.buffer.seek(0)
        self.machine.serialize(self.buffer, object)
        return self.buffer.asbytes()

    def deserialize(self, data) -> object:
        buffer = Buffer(data)
        return self.machine.deserialize(buffer)

    def key(self, object) -> bytes:
        self.buffer.seek(0)
        self.key_machine.serialize(self.buffer, object)
        return self.buffer.asbytes()

    def keyhash(self, object) -> bytes:
        if self.key_max_size <= 16:
            return self.key(object).ljust(16, b'\0')

        m = md5()
        m.update(self.key(object))
        return m.digest()


def proto_serialize(self, buffer=None):
    return self.cdr.serialize(self, buffer=buffer)


def proto_deserialize(cls, data):
    return cls.cdr.deserialize(data)