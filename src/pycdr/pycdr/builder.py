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

from enum import Enum
from inspect import isclass
from collections import defaultdict

from .support import qualified_name, module_prefix, MaxSizeFinder
from .type_helper import Annotated, get_origin, get_args, get_type_hints
from .types import ArrayHolder, BoundStringHolder, SequenceHolder, primitive_types, IdlUnion, NoneType
from .machinery import NoneMachine, PrimitiveMachine, StringMachine, BytesMachine, ByteArrayMachine, UnionMachine, \
    ArrayMachine, SequenceMachine, InstanceMachine, MappingMachine, EnumMachine, StructMachine, InstanceKeyMachine, \
    UnionKeyMachine


class BuildDefer(Exception):
    def __init__(self, wait_for) -> None:
        self.wait_for = wait_for


class Builder:
    easy_types = {
        str: StringMachine,
        bytes: BytesMachine,
        bytearray: ByteArrayMachine,
        NoneType: NoneMachine
    }

    defined_classes = {}
    deferred_classes = defaultdict(set)
    generic_deferred_classes = set()

    @classmethod
    def missing_report_for(cls, _type):
        if _type in cls.generic_deferred_classes:
            return ['[unknown]']

        missing = []
        for name, types in cls.deferred_classes.items():
            for _itype in types:
                if _itype == _type:
                    missing.append(name)
                    break
        return missing

    @classmethod
    def _machine_for_cdrclass(cls, module_prefix, _type, key):
        if type(_type) != str:
            qn = qualified_name(_type)
        else:
            if '.' not in _type:
                qn = module_prefix + _type
            else:
                qn = _type

        if qn in cls.defined_classes:
            if key:
                return InstanceKeyMachine(cls.defined_classes[qn])
            else:
                return InstanceMachine(cls.defined_classes[qn])
        raise BuildDefer(qn)

    @classmethod
    def _machine_for_annotated_type(cls, module_prefix, _type, key):
        args = get_args(_type)
        if len(args) >= 2:
            holder = args[1]
            if type(holder) == tuple:
                # Edge case for python 3.6: bug in backport? TODO: investigate and report
                holder = holder[0]
            if isinstance(holder, ArrayHolder):
                return ArrayMachine(
                    cls._machine_for_type(module_prefix, holder.type, key),
                    size=holder.length
                )
            elif isinstance(holder, SequenceHolder):
                return SequenceMachine(
                    cls._machine_for_type(module_prefix, holder.type, key),
                    maxlen=holder.max_length
                )
            elif isinstance(holder, BoundStringHolder):
                return StringMachine(
                    bound=holder.max_length
                )

        raise TypeError(f"{repr(_type)} is not valid in CDR classes because it cannot be encoded.")

    @classmethod
    def _machine_for_type(cls, module_prefix, _type, key):
        if _type in cls.easy_types:
            return cls.easy_types[_type]()
        elif _type in primitive_types:
            return PrimitiveMachine(_type)
        elif get_origin(_type) == Annotated:
            return cls._machine_for_annotated_type(module_prefix, _type, key)
        elif isclass(_type) and issubclass(_type, Enum):
            return EnumMachine(_type)
        elif type(_type) == str or (isclass(_type) and hasattr(_type, 'cdr')):
            return cls._machine_for_cdrclass(module_prefix, _type, key)
        elif get_origin(_type) == list:
            return SequenceMachine(
                cls._machine_for_type(module_prefix, get_args(_type)[0], key)
            )
        elif get_origin(_type) == dict:
            return MappingMachine(
                cls._machine_for_type(module_prefix, get_args(_type)[0], key),
                cls._machine_for_type(module_prefix, get_args(_type)[1], key)
            )
        raise TypeError(f"{repr(_type)} is not valid in CDR classes because it cannot be encoded.")

    @classmethod
    def _machine_struct(cls, module_prefix, _type, key):
        try:
            fields = get_type_hints(_type, include_extras=True)
        except NameError as e:
            key = e.args[0].split('\'')[1]
            if '.' not in key:
                raise BuildDefer(module_prefix + key)
            else:
                raise BuildDefer(key)

        if _type.cdr.keylist is None:
            _type.cdr.keylist = fields.keys()  # here .keys() gives dict keys

        members = {
            name: cls._machine_for_type(module_prefix, field_type, key)
            for name, field_type in fields.items()
            if not key or name in _type.cdr.keylist
        }
        return StructMachine(_type, members)

    @classmethod
    def _machine_union(cls, module_prefix, _type, key):
        discriminator = cls._machine_for_type(module_prefix, _type._discriminator, key)
        cases = {
            label: cls._machine_for_type(module_prefix, case_type, key)
            for label, (_, case_type) in _type._cases.items()
        }
        default = cls._machine_for_type(module_prefix, _type._default[1], key) if _type._default else None

        if key:
            return UnionKeyMachine(_type, discriminator, cases, default)
        return UnionMachine(_type, discriminator, cases, default)

    @classmethod
    def _process_deferral(cls, qn, _type):
        cls.defined_classes[qn] = _type

        for deferral in cls.deferred_classes[qn]:
            cls.build_machine(deferral)

        for deferral in cls.generic_deferred_classes:
            cls.build_machine(deferral)

        del cls.deferred_classes[qn]

    @classmethod
    def build_machine(cls, _type):
        mp = module_prefix(_type)
        qn = qualified_name(_type)

        if qn not in cls.defined_classes.keys():
            cls._process_deferral(qn, _type)

        try:
            if issubclass(_type, IdlUnion):
                machine = cls._machine_union(mp, _type, False)
                key_machine = cls._machine_union(mp, _type, True)
            else:
                machine = cls._machine_struct(mp, _type, False)
                key_machine = cls._machine_struct(mp, _type, True)
        except BuildDefer as e:
            cls.deferred_classes[e.wait_for].add(_type)
            return

        _type.cdr.machine = machine
        _type.cdr.key_machine = key_machine

        finder = MaxSizeFinder()
        key_machine.max_size(finder)
        _type.cdr.key_max_size = finder.size

        if _type in cls.generic_deferred_classes:
            cls.generic_deferred_classes.remove(_type)
