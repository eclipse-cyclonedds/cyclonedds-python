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

from typing import Optional, Union, TYPE_CHECKING, List
import ctypes as ct
import uuid

from .internal import c_call, dds_c_t
from .core import Entity, DDSException, Listener
from .domain import DomainParticipant
from .topic import Topic
from .qos import _CQos, Qos, LimitedScopeQos, PublisherQos, DataWriterQos
from .builtin import DcpsEndpoint

from cyclonedds._clayer import ddspy_write, ddspy_write_ts, ddspy_dispose, ddspy_writedispose, ddspy_writedispose_ts, \
    ddspy_dispose_handle, ddspy_dispose_handle_ts, ddspy_register_instance, ddspy_unregister_instance,   \
    ddspy_unregister_instance_handle, ddspy_unregister_instance_ts, ddspy_unregister_instance_handle_ts, \
    ddspy_lookup_instance, ddspy_dispose_ts, ddspy_get_matched_subscription_data


if TYPE_CHECKING:
    import cyclonedds


class Publisher(Entity):
    def __init__(
            self,
            domain_participant: DomainParticipant,
            qos: Optional[Qos] = None,
            listener: Optional[Listener] = None):
        if not isinstance(domain_participant, DomainParticipant):
            raise TypeError(f"{domain_participant} is not a cyclonedds.domain.DomainParticipant.")

        if qos is not None:
            if isinstance(qos, LimitedScopeQos) and not isinstance(qos, PublisherQos):
                raise TypeError(f"{qos} is not appropriate for a Publisher")
            elif not isinstance(qos, Qos):
                raise TypeError(f"{qos} is not a valid qos object")

        if listener is not None:
            if not isinstance(listener, Listener):
                raise TypeError(f"{listener} is not a valid listener object.")

        cqos = _CQos.qos_to_cqos(qos) if qos else None
        try:
            super().__init__(
                self._create_publisher(
                    domain_participant._ref,
                    cqos,
                    listener._ref if listener else None
                ),
                listener=listener
            )
        finally:
            if cqos:
                _CQos.cqos_destroy(cqos)

        self._keepalive_entities = [self.participant]

    def suspend(self):
        ret = self._suspend(self._ref)
        if ret == 0:
            return
        raise DDSException(ret, f"Occurred while suspending {repr(self)}")

    def resume(self):
        ret = self._resume(self._ref)
        if ret == 0:
            return
        raise DDSException(ret, f"Occurred while resuming {repr(self)}")

    def wait_for_acks(self, timeout: int):
        ret = self._wait_for_acks(self._ref, timeout)
        if ret == 0:
            return True
        elif ret == DDSException.DDS_RETCODE_TIMEOUT:
            return False
        raise DDSException(ret, f"Occurred while waiting for acks from {repr(self)}")

    @c_call("dds_create_publisher")
    def _create_publisher(self, domain_participant: dds_c_t.entity, qos: dds_c_t.qos_p,
                          listener: dds_c_t.listener_p) -> dds_c_t.entity:
        pass

    @c_call("dds_suspend")
    def _suspend(self, publisher: dds_c_t.entity) -> dds_c_t.returnv:
        pass

    @c_call("dds_resume")
    def _resume(self, publisher: dds_c_t.entity) -> dds_c_t.returnv:
        pass

    @c_call("dds_wait_for_acks")
    def _wait_for_acks(self, publisher: dds_c_t.entity, timeout: dds_c_t.duration) -> dds_c_t.returnv:
        pass


class DataWriter(Entity):
    def __init__(self,
                 publisher_or_participant: Union[DomainParticipant, Publisher],
                 topic: Topic,
                 qos: Optional[Qos] = None,
                 listener: Optional[Listener] = None):
        if not (isinstance(publisher_or_participant, DomainParticipant) or
                isinstance(publisher_or_participant, Publisher)):
            raise TypeError(f"{publisher_or_participant} is not a cyclonedds.domain.DomainParticipant"
                            " or cyclonedds.pub.Publisher.")

        if not isinstance(topic, Topic):
            raise TypeError(f"{topic} is not a cyclonedds.topic.Topic.")

        if qos is not None:
            if isinstance(qos, LimitedScopeQos) and not isinstance(qos, DataWriterQos):
                raise TypeError(f"{qos} is not appropriate for a DataWriter")
            elif not isinstance(qos, Qos):
                raise TypeError(f"{qos} is not a valid qos object")

        cqos = _CQos.qos_to_cqos(qos) if qos else None
        try:
            super().__init__(
                self._create_writer(
                    publisher_or_participant._ref,
                    topic._ref,
                    cqos,
                    listener._ref if listener else None
                ),
                listener=listener
            )
        finally:
            if cqos:
                _CQos.cqos_destroy(cqos)

        self._topic = topic
        self.data_type = topic.data_type
        self._keepalive_entities = [self.publisher, self.topic]
        self._constructor = None

    @property
    def topic(self) -> 'cyclonedds.topic.Topic':
        return self._topic

    def write(self, sample, timestamp=None):
        if not isinstance(sample, self.data_type):
            raise TypeError(f"{sample} is not of type {self.data_type}")

        if timestamp is not None:
            ret = ddspy_write_ts(self._ref, sample.serialize(), timestamp)
        else:
            ret = ddspy_write(self._ref, sample.serialize())

        if ret < 0:
            raise DDSException(ret, f"Occurred while writing sample in {repr(self)}")

    def write_dispose(self, sample, timestamp=None):
        if timestamp is not None:
            ret = ddspy_writedispose_ts(self._ref, sample.serialize(), timestamp)
        else:
            ret = ddspy_writedispose(self._ref, sample.serialize())

        if ret < 0:
            raise DDSException(ret, f"Occurred while writedisposing sample in {repr(self)}")

    def dispose(self, sample, timestamp=None):
        if timestamp is not None:
            ret = ddspy_dispose_ts(self._ref, sample.serialize(), timestamp)
        else:
            ret = ddspy_dispose(self._ref, sample.serialize())

        if ret < 0:
            raise DDSException(ret, f"Occurred while disposing in {repr(self)}")

    def dispose_instance_handle(self, handle, timestamp=None):
        if timestamp is not None:
            ret = ddspy_dispose_handle_ts(self._ref, handle, timestamp)
        else:
            ret = ddspy_dispose_handle(self._ref, handle)

        if ret < 0:
            raise DDSException(ret, f"Occurred while disposing in {repr(self)}")

    def register_instance(self, sample):
        ret = ddspy_register_instance(self._ref, sample.serialize())
        if ret < 0:
            raise DDSException(ret, f"Occurred while registering instance in {repr(self)}")
        return ret

    def unregister_instance(self, sample, timestamp: int = None):
        if timestamp is not None:
            ret = ddspy_unregister_instance_ts(self._ref, sample.serialize(), timestamp)
        else:
            ret = ddspy_unregister_instance(self._ref, sample.serialize())

        if ret < 0:
            raise DDSException(ret, f"Occurred while unregistering instance in {repr(self)}")

    def unregister_instance_handle(self, handle, timestamp: int = None):
        if timestamp is not None:
            ret = ddspy_unregister_instance_handle_ts(self._ref, handle, timestamp)
        else:
            ret = ddspy_unregister_instance_handle(self._ref, handle)

        if ret < 0:
            raise DDSException(ret, f"Occurred while unregistering instance handle n {repr(self)}")

    def wait_for_acks(self, timeout: int):
        ret = self._wait_for_acks(self._ref, timeout)
        if ret == 0:
            return True
        elif ret == Exception.DDS_RETCODE_TIMEOUT:
            return False
        raise DDSException(ret, f"Occurred while waiting for acks from {repr(self)}")

    def lookup_instance(self, sample):
        ret = ddspy_lookup_instance(self._ref, sample.serialize())
        if ret < 0:
            raise DDSException(ret, f"Occurred while lookup up instance from {repr(self)}")
        if ret == 0:
            return None
        return ret

    def get_matched_subscriptions(self) -> List[int]:
        """Get instance handles of the data readers matching a writer.

        Raises
        ------
            DDSException: When the number of matching readers < 0.

        Returns
        -------
        List[int]:
            A list of instance handles of the matching data readers.
        """
        num_matched_sub = self._get_matched_subscriptions(self._ref, None, 0)
        if num_matched_sub < 0:
            raise DDSException(num_matched_sub, f"Occurred when getting the number of matched subscriptions of {repr(self)}")
        if num_matched_sub == 0:
            return []

        matched_sub_list = (dds_c_t.instance_handle * int(num_matched_sub))()
        matched_sub_list_pt = ct.cast(matched_sub_list, ct.POINTER(dds_c_t.instance_handle))

        ret = self._get_matched_subscriptions(self._ref, matched_sub_list_pt, num_matched_sub)
        if ret >= 0:
            return [matched_sub_list[i] for i in range(ret)]

        raise DDSException(ret, f"Occurred when getting the matched subscriptions of {repr(self)}")

    matched_sub = property(get_matched_subscriptions)

    def _make_constructors(self):
        if self._constructor is not None:
            return
        
        def endpoint_constructor(keyhash, participant_keyhash, instance_handle, topic_name, type_name, qos):
            return DcpsEndpoint(
                key=uuid.UUID(bytes=keyhash),
                participant_key=uuid.UUID(bytes=participant_keyhash),
                participant_instance_handle=instance_handle,
                topic_name=topic_name,
                type_name=type_name,
                qos=qos
            )

        def cqos_to_qos(pointer):
            p = ct.cast(pointer, dds_c_t.qos_p)
            return _CQos.cqos_to_qos(p)
        
        self._constructor = endpoint_constructor
        self._cqos = cqos_to_qos

    def get_matched_subscription_data(self, handle) -> Optional['cyclonedds.builtin.DcpsEndpoint']:
        """Get a description of a reader matched with the provided writer

        Parameters
        ----------
        handle: Int
            The instance handle of a reader.

        Returns
        -------
        DcpsEndpoint:
            The sample of the DcpsEndpoint built-in topic.
        """
        self._make_constructors()
        return ddspy_get_matched_subscription_data(self._ref, handle, self._constructor, self._cqos)

    def get_liveliness_lost_status(self):
        """Get LIVELINESS_LOST status

        Raises
        ------
        DDSException

        Returns
        -------
        liveness_lost_status:
            The class 'liveness_lost_status' value.
        """
        status = dds_c_t.liveliness_lost_status()
        ret = self._get_liveliness_lost_status(self._ref, ct.byref(status))
        if ret == 0:
            return status
        raise DDSException(ret, f"Occurred when getting the liveliness lost status for {repr(self)}")

    def get_offered_deadline_missed_status(self):
        """Get OFFERED DEADLINE MISSED status

        Raises
        ------
        DDSException

        Returns
        -------
        offered_deadline_missed_status:
            The class 'offered_deadline_missed_status' value.
        """
        status = dds_c_t.offered_deadline_missed_status()
        ret = self._get_offered_deadline_missed_status(self._ref, ct.byref(status))
        if ret == 0:
            return status
        raise DDSException(ret, f"Occurred when getting the offered deadline missed status for {repr(self)}")

    def get_offered_incompatible_qos_status(self):
        """Get OFFERED INCOMPATIBLE QOS status

        Raises
        ------
        DDSException

        Returns
        -------
        offered_incompatible_qos_status:
            The class 'offered_incompatible_qos_status' value.
        """
        status = dds_c_t.offered_incompatible_qos_status()
        ret = self._get_offered_incompatible_qos_status(self._ref, ct.byref(status))
        if ret == 0:
            return status
        raise DDSException(ret, f"Occurred when getting the offered incompatible qos status for {repr(self)}")

    def get_publication_matched_status(self):
        """Get PUBLICATION MATCHED status

        Raises
        ------
        DDSException

        Returns
        -------
        publication_matched_status:
            The class 'publication_matched_status' value.
        """
        status = dds_c_t.publication_matched_status()
        ret = self._get_publication_matched_status(self._ref, ct.byref(status))
        if ret == 0:
            return status
        raise DDSException(ret, f"Occurred when getting the publication matched status for {repr(self)}")

    @c_call("dds_create_writer")
    def _create_writer(self, publisher: dds_c_t.entity, topic: dds_c_t.entity, qos: dds_c_t.qos_p,
                       listener: dds_c_t.listener_p) -> dds_c_t.entity:
        pass

    @c_call("dds_wait_for_acks")
    def _wait_for_acks(self, publisher: dds_c_t.entity, timeout: dds_c_t.duration) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_matched_subscriptions")
    def _get_matched_subscriptions(self, writer: dds_c_t.entity, handle: ct.POINTER(dds_c_t.instance_handle),
                                   size: ct.c_size_t) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_liveliness_lost_status")
    def _get_liveliness_lost_status(self, writer: dds_c_t.entity, status: ct.POINTER(dds_c_t.liveliness_lost_status)) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_offered_deadline_missed_status")
    def _get_offered_deadline_missed_status(self, writer: dds_c_t.entity, status: ct.POINTER(dds_c_t.offered_deadline_missed_status)) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_offered_incompatible_qos_status")
    def _get_offered_incompatible_qos_status(self, writer: dds_c_t.entity, status: ct.POINTER(dds_c_t.offered_incompatible_qos_status)) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_publication_matched_status")
    def _get_publication_matched_status(self, writer: dds_c_t.entity, status: ct.POINTER(dds_c_t.publication_matched_status)) -> dds_c_t.returnv:
        pass