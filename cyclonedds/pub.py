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

from typing import Optional, Union, Generic, TypeVar, TYPE_CHECKING

from .internal import c_call, dds_c_t
from .core import Entity, DDSException, Listener
from .domain import DomainParticipant
from .topic import Topic
from .qos import _CQos, Qos, LimitedScopeQos, PublisherQos, DataWriterQos

from cyclonedds._clayer import ddspy_write, ddspy_write_ts, ddspy_dispose, ddspy_writedispose, ddspy_writedispose_ts, \
    ddspy_dispose_handle, ddspy_dispose_handle_ts, ddspy_register_instance, ddspy_unregister_instance,   \
    ddspy_unregister_instance_handle, ddspy_unregister_instance_ts, ddspy_unregister_instance_handle_ts, \
    ddspy_lookup_instance, ddspy_dispose_ts


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
        """
        This operation blocks the calling thread until either all data written by the publisher
        or writer is acknowledged by all matched reliable reader entities, or else the duration
        specified by the timeout parameter elapses, whichever happens first.

        Parameters
        ----------
        timeout
            The maximum number of nanoseconds to wait. Use the function :func:`duration<cyclonedds.util.duration>`
            to write that in a human readable format.
        """
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


_T = TypeVar('_T')

class DataWriter(Entity, Generic[_T]):
    def __init__(self,
                 publisher_or_participant: Union[DomainParticipant, Publisher],
                 topic: Topic[_T],
                 qos: Optional[Qos] = None,
                 listener: Optional[Listener] = None):
        if not isinstance(publisher_or_participant, (DomainParticipant, Publisher)):
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

        cqos = _CQos.cqos_create()
        ret = self._get_qos(self._ref, cqos)
        if ret == 0:
            data_repr_policy = _CQos._get_p_datarepresentation(cqos)
            if data_repr_policy is None or (data_repr_policy.use_cdrv0_representation and data_repr_policy.use_xcdrv2_representation):
                self._use_version_2 = None  # Use whatever is native to the datatype
            elif data_repr_policy.use_xcdrv2_representation:
                self._use_version_2 = True
            else:
                self._use_version_2 = False
        _CQos.cqos_destroy(cqos)

    @property
    def topic(self) -> Topic[_T]:
        return self._topic

    def write(self, sample: _T, timestamp: Optional[int] = None):
        """
        Parameters
        ----------
        sample
            The sample to write
        timestamp
            The sample's source_timestamp (in nanoseconds since the UNIX Epoch)
        """
        if not isinstance(sample, self.data_type):
            raise TypeError(f"{sample} is not of type {self.data_type}")

        ser = sample.serialize(use_version_2=self._use_version_2)
        ser = ser.ljust((len(ser) + 4 - 1) & ~(4 - 1), b'\0')

        if timestamp is not None:
            ret = ddspy_write_ts(self._ref, ser, timestamp)
        else:
            ret = ddspy_write(self._ref, ser)

        if ret < 0:
            raise DDSException(ret, f"Occurred while writing sample in {repr(self)}")

    def write_dispose(self, sample: _T, timestamp: Optional[int] = None):
        """
        Similar to :func:`write` but also marks the sample for disposal by setting its
        :class:`InstanceState<cyclonedds.core.InstanceState>` to `NotAliveDisposed`.

        Parameters
        ----------
        sample
            The sample to dispose
        timestamp
            The sample's source_timestamp (in nanoseconds since the UNIX Epoch)
        """
        ser = sample.serialize(use_version_2=self._use_version_2)
        ser = ser.ljust((len(ser) + 4 - 1) & ~(4 - 1), b'\0')

        if timestamp is not None:
            ret = ddspy_writedispose_ts(self._ref, ser, timestamp)
        else:
            ret = ddspy_writedispose(self._ref, ser)

        if ret < 0:
            raise DDSException(ret, f"Occurred while writedisposing sample in {repr(self)}")

    def dispose(self, sample: _T, timestamp: Optional[int] = None):
        """
        Marks the sample for disposal by setting its :class:`InstanceState<cyclonedds.core.InstanceState>` to
        `NotAliveDisposed`.

        Parameters
        ----------
        sample
            The sample to dispose
        timestamp
            The sample's source_timestamp (in nanoseconds since the UNIX Epoch)
        """
        ser = sample.serialize(use_version_2=self._use_version_2)
        ser = ser.ljust((len(ser) + 4 - 1) & ~(4 - 1), b'\0')

        if timestamp is not None:
            ret = ddspy_dispose_ts(self._ref, ser, timestamp)
        else:
            ret = ddspy_dispose(self._ref, ser)

        if ret < 0:
            raise DDSException(ret, f"Occurred while disposing in {repr(self)}")

    def dispose_instance_handle(self, handle: int, timestamp: Optional[int] = None):
        """
        Marks the instance and all samples associated wiht the given handle for disposal by setting their
        :class:`InstanceState<cyclonedds.core.InstanceState>` to `NotAliveDisposed`.

        Parameters
        ----------
        handle
            An instance handle received from :func:`register_instance` or :func:`lookup_instance`.
        timestamp
            The instance's source_timestamp (in nanoseconds since the UNIX Epoch)
        """
        if timestamp is not None:
            ret = ddspy_dispose_handle_ts(self._ref, handle, timestamp)
        else:
            ret = ddspy_dispose_handle(self._ref, handle)

        if ret < 0:
            raise DDSException(ret, f"Occurred while disposing in {repr(self)}")

    def register_instance(self, sample: _T) -> int:
        ser = sample.serialize(use_version_2=self._use_version_2)
        ser = ser.ljust((len(ser) + 4 - 1) & ~(4 - 1), b'\0')

        ret = ddspy_register_instance(self._ref, ser)
        if ret < 0:
            raise DDSException(ret, f"Occurred while registering instance in {repr(self)}")
        return ret

    def unregister_instance(self, sample: _T, timestamp: Optional[int] = None):
        """
        Parameters
        ----------
        sample
            The sample to unregister
        timestamp
            The timestamp used at registration (in nanoseconds since the UNIX Epoch)
        """
        ser = sample.serialize(use_version_2=self._use_version_2)
        ser = ser.ljust((len(ser) + 4 - 1) & ~(4 - 1), b'\0')

        if timestamp is not None:
            ret = ddspy_unregister_instance_ts(self._ref, ser, timestamp)
        else:
            ret = ddspy_unregister_instance(self._ref, ser)

        if ret < 0:
            raise DDSException(ret, f"Occurred while unregistering instance in {repr(self)}")

    def unregister_instance_handle(self, handle: int, timestamp: Optional[int] = None):
        """
        Parameters
        ----------
        handle
            An instance handle received from :func:`register_instance` or :func:`lookup_instance`.
        timestamp
            The timestamp used at registration (in nanoseconds since the UNIX Epoch)
        """
        if timestamp is not None:
            ret = ddspy_unregister_instance_handle_ts(self._ref, handle, timestamp)
        else:
            ret = ddspy_unregister_instance_handle(self._ref, handle)

        if ret < 0:
            raise DDSException(ret, f"Occurred while unregistering instance handle n {repr(self)}")

    def wait_for_acks(self, timeout: int) -> bool:
        """
        This operation blocks the calling thread until either all data written by the publisher
        or writer is acknowledged by all matched reliable reader entities, or else the duration
        specified by the timeout parameter elapses, whichever happens first.

        Parameters
        ----------
        timeout
            The maximum number of nanoseconds to wait. Use the function :func:`duration<cyclonedds.util.duration>`
            to write that in a human readable format.
        """
        ret = self._wait_for_acks(self._ref, timeout)
        if ret == 0:
            return True
        elif ret == Exception.DDS_RETCODE_TIMEOUT:
            return False
        raise DDSException(ret, f"Occurred while waiting for acks from {repr(self)}")

    def lookup_instance(self, sample: _T) -> Optional[int]:
        """
        This operation takes a sample and returns an instance handle to be used for subsequent operations.
        """
        ser = sample.serialize(use_version_2=self._use_version_2)
        ser = ser.ljust((len(ser) + 4 - 1) & ~(4 - 1), b'\0')

        ret = ddspy_lookup_instance(self._ref, ser)
        if ret < 0:
            raise DDSException(ret, f"Occurred while lookup up instance from {repr(self)}")
        if ret == 0:
            return None
        return ret

    @c_call("dds_create_writer")
    def _create_writer(self, publisher: dds_c_t.entity, topic: dds_c_t.entity, qos: dds_c_t.qos_p,
                       listener: dds_c_t.listener_p) -> dds_c_t.entity:
        pass

    @c_call("dds_wait_for_acks")
    def _wait_for_acks(self, publisher: dds_c_t.entity, timeout: dds_c_t.duration) -> dds_c_t.returnv:
        pass
