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

from .core import Qos
from .internal import dds_c_t
from .qos import _CQos

from cyclonedds.idl._typesupport.DDS.XTypes import TypeIdentifier

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


def cqos_to_qos(pointer):
    p = ct.cast(pointer, dds_c_t.qos_p)
    return _CQos.cqos_to_qos(p)

def participant_constructor(keybytes, qosobject, sampleinfo):
    s = DcpsParticipant(uuid.UUID(bytes=keybytes), qos=qosobject)
    s.sample_info = sampleinfo
    return s

def endpoint_constructor(keybytes, participant_keybytes, p_instance_handle, topic_name, type_name, qosobject, sampleinfo, typeid_bytes):
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
