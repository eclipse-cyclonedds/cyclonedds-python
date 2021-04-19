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

from .core import Entity, DDSException, Qos, ReadCondition, ViewState, InstanceState, SampleState
from .topic import Topic
from .sub import DataReader
from .internal import c_call, dds_c_t, SampleInfo
from .qos import _CQos


if TYPE_CHECKING:
    import cyclonedds


class _BuiltinTopicParticipantStruct(ct.Structure):
    _fields_ = [
        ('key', dds_c_t.guid),
        ('qos', dds_c_t.qos_p)
    ]


class _BuiltinTopicEndpointStruct(ct.Structure):
    _fields_ = [
        ('key', dds_c_t.guid),
        ('participant_key', dds_c_t.guid),
        ('participant_instance_handle', dds_c_t.instance_handle),
        ('topic_name', ct.c_char_p),
        ('type_name', ct.c_char_p),
        ('qos', dds_c_t.qos_p)
    ]


class BuiltinTopic(Topic):
    """ Represent a built-in CycloneDDS Topic by magic reference number. """
    def __init__(self, _ref, data_type):
        self._ref = _ref
        self.data_type = data_type

    def __del__(self):
        pass


@dataclass
class DcpsParticipant:
    """
    Data sample as returned when you subscribe to the BuiltinTopicDcpsParticipant topic.

    Attributes
    ----------
    key: uuid.UUID
        Unique participant identifier
    qos: Qos
        Qos policies associated with the participant.
    """

    struct_class: ClassVar[ct.Structure] = _BuiltinTopicParticipantStruct
    key: uuid.UUID
    qos: Qos

    @classmethod
    def from_struct(cls, struct: _BuiltinTopicParticipantStruct):
        return cls(key=struct.key.as_python_guid(), qos=_CQos.cqos_to_qos(struct.qos))


@dataclass
class DcpsEndpoint:
    """
    Data sample as returned when you subscribe to the BuiltinTopicDcpsTopic,
    BuiltinTopicDcpsPublication or BuiltinTopicDcpsSubscription topic.

    Attributes
    ----------
    key: uuid.UUID
        Unique identifier for the topic, publication or subscription endpoint.
    participant_key: uuid.UUID
        Unique identifier of the participant the endpoint belongs to.
    participant_instance_handle: int
        Instance handle
    topic_name: str
        Name of the associated topic.
    type_name: str
        Name of the type.
    qos: Qos
        Qos policies associated with the endpoint.
    """
    struct_class: ClassVar[ct.Structure] = _BuiltinTopicEndpointStruct
    key: uuid.UUID
    participant_key: uuid.UUID
    participant_instance_handle: int
    topic_name: str
    type_name: str
    qos: Qos

    @classmethod
    def from_struct(cls, struct: _BuiltinTopicEndpointStruct):
        return cls(
            key=struct.key.as_python_guid(),
            participant_key=struct.participant_key.as_python_guid(),
            participant_instance_handle=int(struct.participant_instance_handle),
            topic_name=bytes(struct.topic_name).decode('utf-8'),
            type_name=bytes(struct.type_name).decode('utf-8'),
            qos=_CQos.cqos_to_qos(struct.qos))


class BuiltinDataReader(DataReader):
    """
    Builtin topics have sligtly different behaviour than normal topics, so you should use this BuiltinDataReader
    instead of the normal DataReader. They are identical in the rest of their functionality.
    """
    def __init__(self,
                 subscriber_or_participant: Union['cyclonedds.sub.Subscriber', 'cyclonedds.domain.DomainParticipant'],
                 builtin_topic: 'cyclonedds.builtin.BuiltinTopic',
                 qos: Optional['cyclonedds.core.Qos'] = None,
                 listener: Optional['cyclonedds.core.Listener'] = None) -> None:
        """Initialize the BuiltinDataReader

        Parameters
        ----------
        subscriber_or_participant: cyclonedds.sub.Subscriber, cyclonedds.domain.DomainParticipant
            The subscriber to which this reader will be added. If you supply a DomainParticipant a subscriber will be created for you.

        builtin_topic: cyclonedds.builtin.BuiltinTopic
            Which Builtin Topic to subscribe to. This can be one of BuiltinTopicDcpsParticipant, BuiltinTopicDcpsTopic,
            BuiltinTopicDcpsPublication or BuiltinTopicDcpsSubscription. Please note that BuiltinTopicDcpsTopic will fail if
            you built CycloneDDS without Topic Discovery.
        qos: cyclonedds.core.Qos, optional = None
            Optionally supply a Qos.
        listener: cyclonedds.core.Listener = None
            Optionally supply a Listener.
        """
        self._topic = builtin_topic
        self._N = 0
        self._sampleinfos = None
        self._pt_sampleinfos = None
        self._samples = None
        self._pt_samples = None
        self._pt_void_samples = None
        cqos = _CQos.qos_to_cqos(qos) if qos else None
        Entity.__init__(
            self,
            self._create_reader(
                subscriber_or_participant._ref,
                builtin_topic._ref,
                cqos,
                listener._ref if listener else None
            )
        )
        self._next_condition = ReadCondition(self, ViewState.Any | SampleState.NotRead | InstanceState.Any)
        if cqos:
            _CQos.cqos_destroy(cqos)

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

    def _convert_sampleinfo(self, sampleinfo: dds_c_t.sample_info):
        return SampleInfo(
            sampleinfo.sample_state,
            sampleinfo.view_state,
            sampleinfo.instance_state,
            sampleinfo.valid_data,
            sampleinfo.source_timestamp,
            sampleinfo.instance_handle,
            sampleinfo.publication_handle,
            sampleinfo.disposed_generation_count,
            sampleinfo.no_writers_generation_count,
            sampleinfo.sample_rank,
            sampleinfo.generation_rank,
            sampleinfo.absolute_generation_rank
        )

    def read(self, N: int = 1, condition: Union['cyclonedds.core.ReadCondition', 'cyclonedds.core.QueryCondition']=None):
        """Read a maximum of N samples, non-blocking. Optionally use a read/query-condition to select which samples
        you are interested in.

        Parameters
        ----------
        N: int
            The maximum number of samples to read.
        condition: cyclonedds.core.ReadCondition, cyclonedds.core.QueryCondition, optional
            Only read samples that satisfy the supplied condition.

        Raises
        ------
        DDSException
            If any error code is returned by the DDS API it is converted into an exception.
        """

        ref = condition._ref if condition else self._ref
        self._ensure_memory(N)

        ret = self._read(ref, self._pt_void_samples, self._pt_sampleinfos, N, N)

        if ret < 0:
            raise DDSException(ret, f"Occurred when calling read() in {repr(self)}")

        if ret == 0:
            return []

        return_samples = [self._topic.data_type.from_struct(self._samples[i]) for i in range(min(ret, N))]

        for i in range(min(ret, N)):
            return_samples[i].sample_info = self._convert_sampleinfo(self._sampleinfos[i])

        return return_samples

    def take(self, N: int = 1, condition=None):
        """Take a maximum of N samples, non-blocking. Optionally use a read/query-condition to select which samples
        you are interested in.

        Parameters
        ----------
        N: int
            The maximum number of samples to read.
        condition: cyclonedds.core.ReadCondition, cyclonedds.core.QueryCondition, optional
            Only take samples that satisfy the supplied condition.

        Raises
        ------
        DDSException
            If any error code is returned by the DDS API it is converted into an exception.
        """
        ref = condition._ref if condition else self._ref
        self._ensure_memory(N)

        ret = self._take(ref, self._pt_void_samples, self._pt_sampleinfos, N, N)

        if ret < 0:
            raise DDSException(ret, f"Occurred when calling take() in {repr(self)}")

        if ret == 0:
            return []

        return_samples = [self._topic.data_type.from_struct(self._samples[i]) for i in range(min(ret, N))]

        for i in range(min(ret, N)):
            return_samples[i].sample_info = self._convert_sampleinfo(self._sampleinfos[i])

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
"""Built-in topic, is published to when a new participants appear on the network."""

BuiltinTopicDcpsTopic = BuiltinTopic(_pseudo_handle + 2, DcpsEndpoint)
"""Built-in topic, is published to when a new topic appear on the network."""

BuiltinTopicDcpsPublication = BuiltinTopic(_pseudo_handle + 3, DcpsEndpoint)
"""Built-in topic, is published to when a publication happens."""

BuiltinTopicDcpsSubscription = BuiltinTopic(_pseudo_handle + 4, DcpsEndpoint)
"""Built-in topic, is published to when a subscription happens."""

__all__ = [
    "DcpsParticipant", "DcpsEndpoint", "BuiltinDataReader",
    "BuiltinTopicDcpsParticipant", "BuiltinTopicDcpsTopic",
    "BuiltinTopicDcpsPublication", "BuiltinTopicDcpsSubscription"
]
