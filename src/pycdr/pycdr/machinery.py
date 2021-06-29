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

from .types import primitive_types
from .support import Buffer, MaxSizeFinder, CdrKeyVmOp, CdrKeyVMOpType


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

    def cdr_key_machine_op(self, skip):
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

    def cdr_key_machine_op(self, skip):
        return []


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

    def cdr_key_machine_op(self, skip):
        stream = [CdrKeyVmOp(CdrKeyVMOpType.StreamStatic, skip, self.alignment, align=self.alignment)]
        if not skip and not self.alignment == 1:
            stream += [CdrKeyVmOp(CdrKeyVMOpType.ByteSwap, skip, align=self.alignment)]
        return stream


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

    def cdr_key_machine_op(self, skip):
        return [CdrKeyVmOp(CdrKeyVMOpType.Stream4ByteSize, skip, 1, align=1)]


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

    def cdr_key_machine_op(self, skip):
        return [CdrKeyVmOp(CdrKeyVMOpType.Stream4ByteSize, skip, 1, align=1)]


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

    def cdr_key_machine_op(self, skip):
        return [CdrKeyVmOp(CdrKeyVMOpType.StreamStatic, skip, self.size, align=1)]


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

    def cdr_key_machine_op(self, skip):
        if isinstance(self.submachine, PrimitiveMachine):
            stream = [CdrKeyVmOp(
                CdrKeyVMOpType.StreamStatic,
                skip,
                self.submachine.alignment * self.size,
                align=self.submachine.alignment
            )]
            if not skip and self.submachine.alignment != 1:
                stream += [CdrKeyVmOp(CdrKeyVMOpType.ByteSwap, skip, align=self.submachine.alignment)]
            return stream

        subops = self.submachine.cdr_key_machine_op(skip)
        return [CdrKeyVmOp(CdrKeyVMOpType.RepeatStatic, skip, self.size, value=len(subops)+2)] + \
            subops + [CdrKeyVmOp(CdrKeyVMOpType.EndRepeat, skip, len(subops))]


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

    def cdr_key_machine_op(self, skip):
        if isinstance(self.submachine, PrimitiveMachine):
            stream = [CdrKeyVmOp(
                CdrKeyVMOpType.Stream2ByteSize,
                skip,
                self.submachine.alignment,
                align=self.submachine.alignment
            )]
            if not skip and self.submachine.alignment != 1:
                stream += [CdrKeyVmOp(CdrKeyVMOpType.ByteSwap, skip, align=self.submachine.alignment)]
            return stream

        subops = self.submachine.cdr_key_machine_op(skip)
        return [CdrKeyVmOp(CdrKeyVMOpType.Repeat2ByteSize, skip, value=len(subops)+2)] + \
            subops + [CdrKeyVmOp(CdrKeyVMOpType.EndRepeat, skip, len(subops))]


class UnionMachine(Machine):
    def __init__(self, type, discriminator_machine, labels_submachines, default_case=None):
        self.type = type
        self.labels_submachines = labels_submachines
        self.alignment = max(s.alignment for s in labels_submachines.values())
        self.alignment = max(self.alignment, discriminator_machine.alignment)
        self.discriminator = discriminator_machine
        self.default = default_case

    def serialize(self, buffer, union):
        try:
            if union.discriminator is None:
                self.discriminator.serialize(buffer, union._default_val)
                self.default.serialize(buffer, union.value)
            else:
                self.discriminator.serialize(buffer, union.discriminator)
                self.labels_submachines[union.discriminator].serialize(buffer, union.value)
        except Exception as e:
            raise Exception(f"Failed to encode union, {self.type}, value is {union.value}") from e

    def deserialize(self, buffer):
        label = self.discriminator.deserialize(buffer)

        if label not in self.labels_submachines:
            label = None
            contents = self.default.deserialize(buffer)
        else:
            contents = self.labels_submachines[label].deserialize(buffer)

        return self.type(discriminator=label, value=contents)

    def max_size(self, finder: MaxSizeFinder):
        self.discriminator.max_size(finder)
        pre_size = finder.size
        sizes = []

        for submachine in self.labels_submachines.values():
            finder.size = pre_size
            submachine.max_size(finder)
            sizes.append(finder.size - pre_size)

        if self.default:
            finder.size = pre_size
            self.default.max_size(finder)
            sizes.append(finder.size - pre_size)

        finder.size = pre_size + max(sizes)

    def cdr_key_machine_op(self, skip):
        headers = []
        opsets = []
        union_type = {
            1: CdrKeyVMOpType.Union1Byte,
            2: CdrKeyVMOpType.Union2Byte,
            4: CdrKeyVMOpType.Union4Byte,
            8: CdrKeyVMOpType.Union8Byte
        }[self.discriminator.alignment]

        buffer = Buffer(bytes=self.discriminator.alignment)

        value_skip = skip or self.type._is_key

        for label, submachine in self.labels_submachines.items():
            buffer.seek(0)
            self.discriminator.serialize(buffer, label)
            buffer.seek(0)
            value = buffer.read({1: 'B', 2: 'H', 4: 'I', 8: 'Q'}[self.discriminator.alignment], self.discriminator.alignment)
            headers.append(CdrKeyVmOp(union_type, skip, value=value))
            opsets.append(submachine.cdr_key_machine_op(value_skip))

        lens = [len(o) + 2 for o in opsets]

        if self.default is not None:
            opsets.append(self.discriminator.cdr_key_machine_op(skip) + self.default.cdr_key_machine_op(value_skip))
            lens.append(len(opsets[-1]))
        else:
            lens[-1] -= 1

        jumps = [sum(lens[i:]) for i in range(len(lens))]

        for i in range(len(headers)):
            if i != len(opsets)-1:
                opsets[i].append(CdrKeyVmOp(CdrKeyVMOpType.Jump, skip, size=jumps[i+1]+1))
            headers[i].size = lens[i]
            opsets[i] = [headers[i]] + opsets[i]

        return sum(opsets, [])


class UnionKeyMachine(UnionMachine):
    def serialize(self, buffer, union):
        if not self.type._is_key:
            super().serialize(buffer, union)
            return

        try:
            if union.discriminator is None:
                self.discriminator.serialize(buffer, union._default_val)
            else:
                self.discriminator.serialize(buffer, union.discriminator)
        except Exception as e:
            raise Exception(f"Failed to encode union, {self.type}, value is {union.value}") from e


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

        for _i in range(num):
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

    def cdr_key_machine_op(self, skip):
        raise NotImplementedError()


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
            except Exception as e:
                raise Exception(f"Failed to encode member {member}, value is {getattr(value, member)}") from e

    def deserialize(self, buffer):
        valuedict = {}
        for member, machine in self.members_machines.items():
            valuedict[member] = machine.deserialize(buffer)
        return self.type(**valuedict)

    def max_size(self, finder):
        for m in self.members_machines.values():
            m.max_size(finder)

    def cdr_key_machine_op(self, skip):
        return sum(
            (
                m.cdr_key_machine_op(skip or name not in self.type.cdr.keylist)
                for name, m in self.members_machines.items()
            ),
            []
        )


class InstanceMachine(Machine):
    def __init__(self, object):
        self.type = object
        self.alignment = 1

    def serialize(self, buffer, value):
        return self.type.cdr.machine.serialize(buffer, value)

    def deserialize(self, buffer):
        return self.type.cdr.machine.deserialize(buffer)

    def max_size(self, finder):
        if hasattr(self.type.cdr, 'key_max_size'):
            return self.type.cdr.key_max_size
        else:
            # If we get here the object can contain itself
            # Size can be infinite
            return 1_000_000_000

    def cdr_key_machine_op(self, skip):
        return self.type.cdr.machine.cdr_key_machine_op(skip)


class InstanceKeyMachine(InstanceMachine):
    def serialize(self, buffer, value):
        return value.cdr.key_machine.serialize(buffer, value)

    def deserialize(self, buffer):
        raise NotImplementedError()


class EnumMachine(Machine):
    def __init__(self, enum):
        self.enum = enum

    def serialize(self, buffer, value):
        buffer.write("I", 4, value.value)

    def deserialize(self, buffer):
        return self.enum(buffer.read("I", 4))

    def max_size(self, finder: MaxSizeFinder):
        finder.increase(4, 4)

    def cdr_key_machine_op(self, skip):
        stream = [CdrKeyVmOp(CdrKeyVMOpType.StreamStatic, skip, 4, align=4)]
        if not skip:
            stream += [CdrKeyVmOp(CdrKeyVMOpType.ByteSwap, skip, align=4)]
        return stream
