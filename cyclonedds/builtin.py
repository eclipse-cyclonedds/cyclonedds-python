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

import uuid
import ctypes as ct
from dataclasses import dataclass
from typing import Optional, Union, TYPE_CHECKING

from .core import Entity, DDSException, Qos, ReadCondition, ViewState, InstanceState, SampleState
from .topic import Topic
from .sub import DataReader
from .internal import dds_c_t
from .qos import _CQos

from cyclonedds._clayer import ddspy_read_participant, ddspy_take_participant, ddspy_read_endpoint, ddspy_take_endpoint, ddspy_read_topic, ddspy_take_topic
from cyclonedds.idl._typesupport.DDS.XTypes import TypeIdentifier


if TYPE_CHECKING:
    import cyclonedds


class BuiltinTopic(Topic):
    """Represent a built-in CycloneDDS Topic by magic reference number."""

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

    key: uuid.UUID
    qos: Qos


@dataclass
class DcpsTopic:
    """
    Data sample as returned when you subscribe to the BuiltinTopicDcpsTopic topic.

    Attributes
    ----------
    key:
        Unique identifier for the topic, publication or subscription endpoint.
    topic_name:
        Name of the associated topic.
    type_name:
        Name of the type.
    qos:
        Qos policies associated with the endpoint.
    typeid:
        Complete XTypes TypeIdentifier of the type, can be None.
    """

    key: uuid.UUID
    topic_name: str
    type_name: str
    qos: Qos
    type_id: Optional[TypeIdentifier]


@dataclass
class DcpsEndpoint:
    """
    Data sample as returned when you subscribe to the BuiltinTopicDcpsPublication or
    BuiltinTopicDcpsSubscription topic.

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
    typeid: TypeIdentifier, optional
        Complete XTypes TypeIdentifier of the type, can be None.
    """

    key: uuid.UUID
    participant_key: uuid.UUID
    participant_instance_handle: int
    topic_name: str
    type_name: str
    qos: Qos
    type_id: Optional[TypeIdentifier]


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
            The subscriber to which this reader will be added. If you supply a DomainParticipant
            a subscriber will be created for you.

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

        cqos = _CQos.qos_to_cqos(qos) if qos else None
        Entity.__init__(
            self,
            self._create_reader(
                subscriber_or_participant._ref,
                builtin_topic._ref,
                cqos,
                listener._ref if listener else None
            ),
            listener=listener
        )
        self._next_condition = ReadCondition(self, ViewState.Any | SampleState.NotRead | InstanceState.Any)
        if cqos:
            _CQos.cqos_destroy(cqos)
        self._make_constructors()
        self._keepalive_entities = [self.subscriber]

    def _make_constructors(self):
        def participant_constructor(keybytes, qosobject, sampleinfo):
            s = DcpsParticipant(uuid.UUID(bytes=keybytes), qos=qosobject)
            s.sample_info = sampleinfo
            return s

        def endpoint_constructor(keybytes, participant_keybytes, p_instance_handle, topic_name, type_name,
                                 qosobject, sampleinfo, typeid_bytes):
            ident = None
            if typeid_bytes is not None:
                try:
                    ident = TypeIdentifier.deserialize(typeid_bytes, has_header=False, use_version_2=True)
                except Exception:
                    pass

            s = DcpsEndpoint(
                uuid.UUID(bytes=keybytes),
                uuid.UUID(bytes=participant_keybytes),
                p_instance_handle,
                topic_name,
                type_name,
                qosobject,
                ident
            )
            s.sample_info = sampleinfo
            return s

        def topic_constructor(keybytes, topic_name, type_name, qosobject, sampleinfo, typeid_bytes):
            ident = None
            if typeid_bytes is not None:
                try:
                    ident = TypeIdentifier.deserialize(typeid_bytes, has_header=False, use_version_2=True)
                except Exception:
                    pass

            s = DcpsTopic(
                uuid.UUID(bytes=keybytes),
                topic_name,
                type_name,
                qosobject,
                ident
            )
            s.sample_info = sampleinfo
            return s

        def cqos_to_qos(pointer):
            p = ct.cast(pointer, dds_c_t.qos_p)
            return _CQos.cqos_to_qos(p)

        if self._topic == BuiltinTopicDcpsParticipant:
            self._readfn = ddspy_read_participant
            self._takefn = ddspy_take_participant
            self._constructor = participant_constructor
        elif self._topic == BuiltinTopicDcpsTopic:
            self._readfn = ddspy_read_topic
            self._takefn = ddspy_take_topic
            self._constructor = topic_constructor
        else:
            self._readfn = ddspy_read_endpoint
            self._takefn = ddspy_take_endpoint
            self._constructor = endpoint_constructor
        self._cqos_conv = cqos_to_qos

    def read(self, N: int = 1,
             condition: Union['cyclonedds.core.ReadCondition', 'cyclonedds.core.QueryCondition'] = None):
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
        ret = self._readfn(ref, N, self._constructor, self._cqos_conv)

        if type(ret) == int:
            raise DDSException(ret, f"Occurred when calling read() in {repr(self)}")

        return ret

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
        ret = self._takefn(ref, N, self._constructor, self._cqos_conv)

        if type(ret) == int:
            raise DDSException(ret, f"Occurred when calling read() in {repr(self)}")

        return ret


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
