"""
 * Copyright(c) 2025 ZettaScale Technology and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
"""

import ctypes as ct
from typing import Any, Optional

from .core import DDSException
from .internal import DDS, c_call, dds_c_t, qos_kind
from .qos import (
    DataReaderQos, DataWriterQos, DomainParticipantQos, PublisherQos, Qos,
    SubscriberQos, TopicQos, _CQos,
)


class QosProvider(DDS):
    """
    Representing QosProvider
    """

    _qos_provider: dds_c_t.qos_provider_p

    def __init__(
            self,
            path: Any,
            scope: Optional[str] = ""):
        bpath = path
        if not isinstance(path, str) and not isinstance(path, bytes):
            bpath = path.__str__().encode('utf-8')
        elif isinstance(path, str):
            bpath = path.encode('utf-8')
        bscope = scope.encode('utf-8')
        self._qos_provider = dds_c_t.qos_provider_p(0)
        ret = self._create_qos_provider_scope(
            bpath, ct.byref(self._qos_provider), bscope
        )
        if ret < 0 or not self._qos_provider:
            raise DDSException(ret, f"Occured when initialize {repr(self)}")

    def _get_qos_kind(self, key: str, kind: qos_kind) -> Qos:
        bkey = key.encode('utf-8')
        cqos = dds_c_t.qos_p(0)
        ret = self._qos_provider_get_qos(
            self._qos_provider, kind, bkey, ct.byref(cqos)
        )
        if ret < 0:
            raise DDSException(ret, f"Occured trying to get_topic_qos {repr(self)}")
        return _CQos.cqos_to_qos(cqos)

    def get_datawriter_qos(self, key: str = "") -> 'DataWriterQos':
        return self._get_qos_kind(key, qos_kind.DDS_WRITER_QOS).datawriter()

    def get_datareader_qos(self, key: str = "") -> 'DataReaderQos':
        return self._get_qos_kind(key, qos_kind.DDS_READER_QOS).datareader()

    def get_domain_participant_qos(self, key: str = "") -> 'DomainParticipantQos':
        return self._get_qos_kind(key, qos_kind.DDS_PARTICIPANT_QOS).domain_participant()

    def get_publisher_qos(self, key: str = "") -> 'PublisherQos':
        return self._get_qos_kind(key, qos_kind.DDS_PUBLISHER_QOS).publisher()

    def get_subscriber_qos(self, key: str = "") -> 'SubscriberQos':
        return self._get_qos_kind(key, qos_kind.DDS_SUBSCRIBER_QOS).subscriber()

    def get_topic_qos(self, key: str = "") -> 'TopicQos':
        return self._get_qos_kind(key, qos_kind.DDS_TOPIC_QOS).topic()

    def __del__(self) -> None:
        self._delete_qos_provider(self._qos_provider)

    @c_call("dds_create_qos_provider_scope")
    def _create_qos_provider_scope(
        self, path: ct.c_char_p, provider: ct.POINTER(dds_c_t.qos_provider_p),
        scope: ct.c_char_p
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_delete_qos_provider")
    def _delete_qos_provider(
        self, provider: dds_c_t.qos_provider_p
    ) -> None:
        pass

    @c_call("dds_qos_provider_get_qos")
    def _qos_provider_get_qos(
        self, provider: dds_c_t.qos_provider_p, qos_type: dds_c_t.qos_kind,
        key: ct.c_char_p, qos: ct.POINTER(dds_c_t.qos_p)
    ) -> dds_c_t.returnv:
        pass
