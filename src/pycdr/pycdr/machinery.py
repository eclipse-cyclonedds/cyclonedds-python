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

from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Union
import struct
from inspect import isclass

from .types import ArrayHolder, BoundStringHolder, SequenceHolder, default, primitive_types, IdlUnion, NoneType
from .type_helper import Annotated, get_origin, get_args, get_type_hints


class Buffer:
    def __init__(self, bytes=None):
        self._bytes = bytearray(bytes) if bytes else bytearray(512)
        self._pos = 0
        self._size = len(self._bytes)
        self._alignc = '@'

    def seek(self, pos):
        self._pos = pos
        return self

    def ensure_size(self, size):
        if self._pos + size > self._size:
            old_bytes = self._bytes
            old_size = self._size
            self._size *= 2
            self._bytes = bytearray(self._size)
            self._bytes[0:old_size] = old_bytes

    def align(self, alignment):
        self._pos = (self._pos + alignment - 1) & ~(alignment - 1)
        return self

    def write(self, pack, size, value):
        self.ensure_size(size)
        struct.pack_into(self._alignc + pack, self._bytes, self._pos, value)
        self._pos += size
        return self

    def write_bytes(self, bytes):
        l = len(bytes)
        self.ensure_size(l)
        self._bytes[self._pos:self._pos+l] = bytes
        self._pos += l
        return self

    def read_bytes(self, length):
        b = bytes(self._bytes[self._pos:self._pos+length])
        self._pos += length
        return b

    def read(self, pack, size):
        v = struct.unpack_from(self._alignc + pack, buffer=self._bytes, offset=self._pos)
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


class Machine:
    """Given a type, serialize and deserialize"""
    def __init__(self, type):
        self.alignment = 1

    def serialize(self, buffer, value):
        pass

    def deserialize(self, buffer):
        pass

    def max_size(self, finder):
        pass


class NoneMachine(Machine):
    def __init__(self):
        self.alignment = 1

    def serialize(self, buffer, value):
        pass

    def deserialize(self, buffer):
        pass

    def max_size(self, finder):
        pass


class PrimitiveMachine(Machine):
    def __init__(self, type):
        self.type = type
        self.alignment, self.code = primitive_types[self.type]

    def serialize(self, buffer, value):
        buffer.align(self.alignment)
        buffer.write(self.code, self.alignment, value)

    def deserialize(self, buffer):
        buffer.align(self.alignment)
        return buffer.read(self.code, self.alignment)

    def max_size(self, finder: MaxSizeFinder):
        finder.increase(self.alignment, self.alignment)


class StringMachine(Machine):
    def __init__(self, bound=None):
        self.alignment = 4
        self.bound = bound

    def serialize(self, buffer, value):
        if self.bound and len(value) > self.bound:
            raise Exception("String longer than bound.")
        buffer.align(4)
        bytes = value.encode('utf-8')
        buffer.write('I', 4, len(bytes) + 1)
        buffer.write_bytes(bytes)
        buffer.write('b', 1, 0)

    def deserialize(self, buffer):
        buffer.align(4)
        numbytes = buffer.read('I', 4)
        bytes = buffer.read_bytes(numbytes - 1)
        buffer.read('b', 1)
        return bytes.decode('utf-8')

    def max_size(self, finder: MaxSizeFinder):
        if self.bound:
            finder.increase(self.bound + 5, 2)  # string size + length serialized (4) + null byte (1)
        else:
            finder.increase(2**64 - 1 + 5, 2)


class BytesMachine(Machine):
    def __init__(self, bound=None):
        self.alignment = 2
        self.bound = bound

    def serialize(self, buffer, value):
        if self.bound and len(value) > self.bound:
            raise Exception("Bytes longer than bound.")
        buffer.align(2)
        buffer.write('H', 2, len(value))
        buffer.write_bytes(value)

    def deserialize(self, buffer):
        buffer.align(2)
        numbytes = buffer.read('H', 2)
        return buffer.read_bytes(numbytes)

    def max_size(self, finder: MaxSizeFinder):
        if self.bound:
            finder.increase(self.bound + 3, 2)  # string size + length serialized (2)
        else:
            finder.increase(65535 + 3, 2)


class ByteArrayMachine(Machine):
    def __init__(self, size):
        self.alignment = 1
        self.size = size

    def serialize(self, buffer, value):
        if self.bound and len(value) != self.size:
            raise Exception("Incorrectly sized array.")

        buffer.write_bytes(value)

    def deserialize(self, buffer):
        return buffer.read_bytes(self.size)

    def max_size(self, finder: MaxSizeFinder):
        finder.increase(self.size, 1)


class ArrayMachine(Machine):
    def __init__(self, submachine, size):
        self.size = size
        self.submachine = submachine
        self.alignment = submachine.alignment

    def serialize(self, buffer, value):
        assert len(value) == self.size

        for v in value:
            self.submachine.serialize(buffer, v)

    def deserialize(self, buffer):
        return [self.submachine.deserialize(buffer) for i in range(self.size)]

    def max_size(self, finder: MaxSizeFinder):
        if self.size == 0:
            return

        finder.align(self.alignment)
        pre_size = finder.size
        self.submachine.max_size(finder)
        post_size = finder.size

        size = post_size - pre_size
        size = (size + self.alignment - 1) & ~(self.alignment - 1)
        finder.size = pre_size + self.size * size


class SequenceMachine(Machine):
    def __init__(self, submachine, maxlen=None):
        self.submachine = submachine
        self.alignment = 2
        self.maxlen = maxlen

    def serialize(self, buffer, value):
        if self.maxlen is not None:
            assert len(value) <= self.maxlen

        buffer.align(2)
        buffer.write('H', 2, len(value))

        for v in value:
            self.submachine.serialize(buffer, v)

    def deserialize(self, buffer):
        buffer.align(2)
        num = buffer.read('H', 2)
        return [self.submachine.deserialize(buffer) for i in range(num)]

    def max_size(self, finder: MaxSizeFinder):
        if self.maxlen == 0:
            return

        finder.align(self.alignment)
        pre_size = finder.size
        self.submachine.max_size(finder)
        post_size = finder.size

        size = post_size - pre_size
        size = (size + self.alignment - 1) & ~(self.alignment - 1)
        finder.size = pre_size + (self.maxlen if self.maxlen else 65535) * size + 2


class UnionMachine(Machine):
    def __init__(self, type, discriminator_machine, labels_submachines, default=None):
        self.type = type
        self.labels_submachines = labels_submachines
        self.alignment = max(s.alignment for s in labels_submachines.values())
        self.alignment = max(self.alignment, discriminator_machine.alignment)
        self.discriminator = discriminator_machine
        self.default = default

    def serialize(self, buffer, union):
        try:
            if union.discriminator is None:
                self.discriminator.serialize(buffer, union._default_val)
                self.default.serialize(buffer, union.value)
            else:
                self.discriminator.serialize(buffer, union.discriminator)
                self.labels_submachines[union.discriminator].serialize(buffer, union.value)
        except:
            raise Exception(f"Failed to encode union, {self.type}, value is {union.value}")

    def deserialize(self, buffer):
        label = self.disciminator.deserialize(buffer)

        if label not in self.labels_submachines:
            contents = self.default.deserialize(buffer)
        else:
            contents = self.labels_submachines[label].deserialize(buffer)

        return self.type(**{label: contents})

    def max_size(self, finder: MaxSizeFinder):
        self.discriminator.max_size(finder)
        pre_size = finder.size
        sizes = []

        for submachine in self.labels_submachines.values():
            finder.size = pre_size
            submachine.max_size(finder)
            sizes.append(finder.size - pre_size)

        if default:
            finder.size = pre_size
            default.max_size(finder)
            sizes.append(finder.size - pre_size)

        finder.size = pre_size + max(sizes)


class MappingMachine(Machine):
    def __init__(self, key_machine, value_machine):
        self.key_machine = key_machine
        self.value_machine = value_machine
        self.alignment = 2

    def serialize(self, buffer, values):
        buffer.align(2)
        buffer.write('H', 2, len(values))

        for key, value in values.items():
            self.key_machine.serialize(buffer, key)
            self.value_machine.serialize(buffer, value)

    def deserialize(self, buffer):
        ret = {}
        buffer.align(2)
        num = buffer.read('H', 2)

        for i in range(num):
            key = self.key_machine.deserialize(buffer)
            value = self.value_machine.deserialize(buffer)
            ret[key] = value

        return ret

    def max_size(self, finder: MaxSizeFinder):
        finder.increase(2, 2)

        pre_size = finder.size
        self.key_machine.max_size(finder)
        self.value_machine.max_size(finder)
        post_size = finder.size

        finder.size = pre_size + (post_size - pre_size) * 65535


class StructMachine(Machine):
    def __init__(self, object, members_machines):
        self.type = object
        self.members_machines = members_machines

    def serialize(self, buffer, value):
        #  We use the fact here that dicts retain their insertion order
        #  This is guaranteed from python 3.7 but no existing python 3.6 implementation
        #  breaks this guarantee.

        for member, machine in self.members_machines.items():
            try:
                machine.serialize(buffer, getattr(value, member))
            except:
                raise Exception(f"Failed to encode member {member}, value is {getattr(value, member)}")

    def deserialize(self, buffer):
        valuedict = {}
        for member, machine in self.members_machines.items():
            valuedict[member] = machine.deserialize(buffer)
        return self.type(**valuedict)

    def max_size(self, finder):
        for k, m in self.members_machines.items():
            m.max_size(finder)


class InstanceMachine(Machine):
    def __init__(self, object):
        self.type = object
        self.alignment = 1

    def serialize(self, buffer, value):
        if value is None:
            print(f"Skipping the {self.type} object for now.")
            return
        return value.serialize(buffer)

    def deserialize(self, buffer):
        return self.type.deserialize(buffer)

    def max_size(self, finder):
        self.type.cdr.machine.max_size(finder)


class DeferredInstanceMachine(Machine):
    def __init__(self, object_type_name, cdr):
        self.alignment = 1
        self.object_type_name = object_type_name
        self.type = cdr.resolve(object_type_name, self)

    def refer(self, type):
        self.type = type

    def serialize(self, buffer, value):
        return value.serialize(buffer)

    def deserialize(self, buffer):
        if not self.type:
            raise TypeError(f"Deferred type {self.object_type_name} was never defined.")
        return self.type.deserialize(buffer)

    def max_size(self, finder):
        if not self.type:
            raise TypeError(f"Deferred type {self.object_type_name} was never defined.")
        self.type.cdr.machine.max_size(finder)


class EnumMachine(Machine):
    def __init__(self, enum):
        self.enum = enum

    def serialize(self, buffer, value):
        buffer.write("I", 4, int(value))

    def deserialize(self, buffer):
        return self.enum(buffer.read("I", 4))

    def max_size(self, finder: MaxSizeFinder):
        finder.increase(4, 4)


def build_machine(cdr, _type, top=False) -> Machine:
    if type(_type) == str:
        return DeferredInstanceMachine(_type, cdr)
    if _type == str:
        return StringMachine()
    elif _type in primitive_types:
        return PrimitiveMachine(_type)
    elif _type == bytes:
        return BytesMachine()
    elif _type == NoneType:
        return NoneMachine()
    elif get_origin(_type) == Annotated:
        args = get_args(_type)
        if len(args) >= 2:
            holder = args[1]
            if isinstance(holder, ArrayHolder):
                return ArrayMachine(
                    build_machine(cdr, holder.type),
                    size=holder.length
                )
            elif isinstance(holder, SequenceHolder):
                return SequenceMachine(
                    build_machine(cdr, holder.type),
                    maxlen=holder.max_length
                )
            elif isinstance(holder, BoundStringHolder):
                return StringMachine(
                    bound=holder.max_length
                )
    elif get_origin(_type) == Union and len(get_args(_type)) == 2 and get_args(_type)[1] == NoneType:
        # TODO
        return build_machine(cdr, get_args(_type)[0])
    elif get_origin(_type) == list:
        return SequenceMachine(
            build_machine(cdr, get_args(_type)[0])
        )
    elif get_origin(_type) == dict:
        return MappingMachine(
            build_machine(cdr, get_args(_type)[0]),
            build_machine(cdr, get_args(_type)[1])
        )
    elif isclass(_type) and issubclass(_type, IdlUnion):
        return UnionMachine(
            _type,
            build_machine(cdr, _type._discriminator),
            {dv: build_machine(cdr, tp) for dv, (_, tp) in _type._cases.items()},
            default=build_machine(cdr, _type._default[1]) if _type._default else None
        )
    elif isclass(_type) and issubclass(_type, Enum):
        return EnumMachine(_type)
    elif isclass(_type) and is_dataclass(_type) and hasattr(_type, 'cdr'):
        return InstanceMachine(_type)
    elif isclass(_type) and is_dataclass(_type) and top:
        _fields = get_type_hints(_type, include_extras=True)
        _members = { k: build_machine(cdr, v) for k,v in _fields.items()}
        return StructMachine(_type, _members)

    print(get_origin(_type), get_args(_type))
    raise TypeError(f"{_type} is not valid in CDR classes because it cannot be encoded.")


def build_key_machine(cdr, keys, cls) -> Machine:
    _fields = get_type_hints(cls, include_extras=True)
    _members = { k: build_machine(cdr, v) for k,v in _fields.items()}
    return StructMachine(cls, _members)