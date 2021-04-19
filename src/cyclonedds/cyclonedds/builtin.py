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

import uuid
import ctypes as ct
from dataclasses import dataclass
from typing import Optional, Union, ClassVar, TYPE_CHECKING

from .core import Entity, DDSException, Qos
from .topic import Topic
from .sub import DataReader
from .internal import c_call, dds_c_t


# The TYPE_CHECKING variable will always evaluate to False, incurring no runtime costs
# But the import here allows your static type checker to resolve fully qualified cyclonedds names
if TYPE_CHECKING:
    import cyclonedds


class _builtintopic_participant(ct.Structure):
    _fields_ = [
        ('key', dds_c_t.guid),
        ('qos', dds_c_t.qos_p)
    ]


class _builtintopic_endpoint(ct.Structure):
    _fields_ = [
        ('key', dds_c_t.guid),
        ('participant_key', dds_c_t.guid),
        ('participant_instance_handle', dds_c_t.instance_handle),
        ('topic_name', ct.c_char_p),
        ('type_name', ct.c_char_p),
        ('qos', dds_c_t.qos_p)
    ]


class BuiltinTopic(Topic):
    def __init__(self, _ref, data_type):
        Entity.__init__(self, _ref)
        self.data_type = data_type


@dataclass
class DcpsParticipant:
    struct_class: ClassVar[ct.Structure] = _builtintopic_participant
    key: uuid
    qos: Qos

    @classmethod
    def from_struct(cls, struct: _builtintopic_participant):
        return cls(key=struct.key.as_python_guid(), qos=Qos(_reference=struct.qos))


@dataclass
class DcpsEndpoint:
    struct_class: ClassVar[ct.Structure] = _builtintopic_endpoint
    key: uuid.UUID
    participant_key: uuid.UUID
    participant_instance_handle: int
    topic_name: str
    type_name: str
    qos: Qos

    @classmethod
    def from_struct(cls, struct: _builtintopic_endpoint):
        return cls(
            key=struct.key.as_python_guid(),
            participant_key=struct.participant_key.as_python_guid(),
            participant_instance_handle=int(struct.participant_instance_handle),
            topic_name=bytes(struct.topic_name).decode('utf-8'),
            type_name=bytes(struct.type_name).decode('utf-8'),
            qos=Qos(_reference=struct.qos))


class BuiltinDataReader(DataReader):
    def __init__(self,
                 subscriber_or_participant: Union['cyclonedds.sub.Subscriber', 'cyclonedds.domain.DomainParticipant'],
                 builtin_topic: 'cyclonedds.topic.BuiltinTopic',
                 qos: Optional['cyclonedds.core.Qos'] = None,
                 listener: Optional['cyclonedds.core.Listener'] = None):
        self._topic = builtin_topic
        self._N = 0
        self._sampleinfos = None
        self._pt_sampleinfos = None
        self._samples = None
        self._pt_samples = None
        self._pt_void_samples = None
        Entity.__init__(
            self,
            self._create_reader(
                subscriber_or_participant._ref,
                builtin_topic._ref,
                qos._ref if qos else None,
                listener._ref if listener else None
            )
        )

    def _ensure_memory(self, N):
        if N <= self._N:
            return
        self._sampleinfos = (dds_c_t.sample_info * N)()
        self._pt_sampleinfos = ct.cast(self._sampleinfos, ct.POINTER(dds_c_t.sample_info))
        self._samples = (self._topic.data_type.struct_class * N)()
        self._pt_samples = (ct.POINTER(self._topic.data_type.struct_class) * N)()
        for i in range(N):
            self._pt_samples[i] = ct.pointer(self._samples[i])
        self._pt_void_samples = ct.cast(self._pt_samples, ct.POINTER(ct.c_void_p))

    def read(self, N=1, condition=None):
        ref = condition._ref if condition else self._ref
        self._ensure_memory(N)

        ret = self._read(ref, self._pt_void_samples, self._pt_sampleinfos, N, N)

        if ret < 0:
            raise DDSException(ret, f"Occurred when calling read() in {repr(self)}")

        if ret == 0:
            return []

        return_samples = [self._topic.data_type.from_struct(self._samples[i]) for i in range(min(ret, N))]

        return return_samples

    def take(self, N=1, condition=None):
        ref = condition._ref if condition else self._ref
        self._ensure_memory(N)

        ret = self._take(ref, self._pt_void_samples, self._pt_sampleinfos, N, N)

        if ret < 0:
            raise DDSException(ret, f"Occurred when calling take() in {repr(self)}")

        if ret == 0:
            return []

        return_samples = [self._topic.data_type.from_struct(self._samples[i]) for i in range(min(ret, N))]

        return return_samples

    @c_call("dds_read")
    def _read(self, reader: dds_c_t.entity, buffer: ct.POINTER(ct.c_void_p), sample_info: ct.POINTER(dds_c_t.sample_info),
              buffer_size: ct.c_size_t, max_samples: ct.c_uint32) -> dds_c_t.returnv:
        pass

    @c_call("dds_take")
    def _take(self, reader: dds_c_t.entity, buffer: ct.POINTER(ct.c_void_p), sample_info: ct.POINTER(dds_c_t.sample_info),
              buffer_size: ct.c_size_t, max_samples: ct.c_uint32) -> dds_c_t.returnv:
        pass


_pseudo_handle = 0x7fff0000
BuiltinTopicDcpsParticipant = BuiltinTopic(_pseudo_handle + 1, DcpsParticipant)
BuiltinTopicDcpsTopic = BuiltinTopic(_pseudo_handle + 2, DcpsEndpoint)
BuiltinTopicDcpsPublication = BuiltinTopic(_pseudo_handle + 3, DcpsEndpoint)
BuiltinTopicDcpsSubscription = BuiltinTopic(_pseudo_handle + 4, DcpsEndpoint)
