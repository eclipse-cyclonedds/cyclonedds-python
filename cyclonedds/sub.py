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

import ctypes as ct
import asyncio
import concurrent.futures
from typing import AsyncGenerator, List, Optional, TypeVar, Union, Generator, Generic, TYPE_CHECKING
import uuid

from .core import Entity, Listener, DDSException, WaitSet, ReadCondition, QueryCondition, SampleState, InstanceState, ViewState
from .domain import DomainParticipant
from .topic import Topic
from .internal import c_call, dds_c_t, InvalidSample
from .qos import _CQos, Qos, LimitedScopeQos, SubscriberQos, DataReaderQos
from .util import duration
from .builtin_types import DcpsEndpoint, endpoint_constructor, cqos_to_qos

from cyclonedds._clayer import ddspy_read, ddspy_take, ddspy_read_handle, ddspy_take_handle, ddspy_lookup_instance, ddspy_get_matched_publication_data


if TYPE_CHECKING:
    import cyclonedds


class Subscriber(Entity):
    def __init__(
            self,
            domain_participant: 'cyclonedds.domain.DomainParticipant',
            qos: Optional[Qos] = None,
            listener: Optional[Listener] = None):
        if not isinstance(domain_participant, DomainParticipant):
            raise TypeError(f"{domain_participant} is not a cyclonedds.domain.DomainParticipant.")

        if qos is not None:
            if isinstance(qos, LimitedScopeQos) and not isinstance(qos, SubscriberQos):
                raise TypeError(f"{qos} is not appropriate for a Subscriber")
            elif not isinstance(qos, Qos):
                raise TypeError(f"{qos} is not a valid qos object")

        if listener is not None:
            if not isinstance(listener, Listener):
                raise TypeError(f"{listener} is not a valid listener object.")

        cqos = _CQos.qos_to_cqos(qos) if qos else None
        try:
            super().__init__(
                self._create_subscriber(
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

    def notify_readers(self):
        ret = self._notify_readers(self._ref)
        if ret < 0:
            raise DDSException(ret, f"Occurred while reading data in {repr(self)}")

    @c_call("dds_create_subscriber")
    def _create_subscriber(self, domain_participant: dds_c_t.entity, qos: dds_c_t.qos_p,
                           listener: dds_c_t.listener_p) -> dds_c_t.entity:
        pass

    @c_call("dds_notify_readers")
    def _notify_readers(self, subsriber: dds_c_t.entity) -> dds_c_t.returnv:
        pass


_T = TypeVar('_T')

class DataReader(Entity, Generic[_T]):
    """Subscribe to a topic and read/take the data published to it.

    All returned samples are annotated with the :class:`sample.sample_info<cyclonedds.internal.SampleInfo>` attribute.
    """

    def __init__(
            self,
            subscriber_or_participant: Union['cyclonedds.sub.Subscriber', 'cyclonedds.domain.DomainParticipant'],
            topic: Topic[_T],
            qos: Optional[Qos] = None,
            listener: Optional[Listener] = None):
        """
        Parameters
        ----------
        subscriber_or_participant: cyclonedds.sub.Subscriber, cyclonedds.domain.DomainParticipant
            The subscriber to which this reader will be added. If you supply a DomainParticipant a subscriber
            will be created for you.
        builtin_topic: cyclonedds.builtin.BuiltinTopic
            Which Builtin Topic to subscribe to. This can be one of BuiltinTopicDcpsParticipant, BuiltinTopicDcpsTopic,
            BuiltinTopicDcpsPublication or BuiltinTopicDcpsSubscription. Please note that BuiltinTopicDcpsTopic will fail if
            you built CycloneDDS without Topic Discovery.
        qos: cyclonedds.core.Qos, optional = None
            Optionally supply a Qos.
        listener: cyclonedds.core.Listener = None
            Optionally supply a Listener.
        """
        if not isinstance(subscriber_or_participant, (Subscriber, DomainParticipant)):
            raise TypeError(f"{subscriber_or_participant} is not a cyclonedds.domain.DomainParticipant"
                            " or cyclonedds.sub.Subscriber.")

        if not isinstance(topic, Topic):
            raise TypeError(f"{topic} is not a cyclonedds.topic.Topic.")

        if qos is not None:
            if isinstance(qos, LimitedScopeQos) and not isinstance(qos, DataReaderQos):
                raise TypeError(f"{qos} is not appropriate for a DataReader")
            elif not isinstance(qos, Qos):
                raise TypeError(f"{qos} is not a valid qos object")

        if listener is not None:
            if not isinstance(listener, Listener):
                raise TypeError(f"{listener} is not a valid listener object.")

        cqos = _CQos.qos_to_cqos(qos) if qos else None
        try:
            super().__init__(
                self._create_reader(
                    subscriber_or_participant._ref,
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
        self._topic_ref = topic._ref
        self._next_condition = None
        self._keepalive_entities = [self.subscriber, topic]
        self._constructor = None

    @property
    def topic(self) -> Topic[_T]:
        return self._topic

    def read(self, N: int = 1, condition: Entity = None, instance_handle: int = None) -> List[_T]:
        """Read a maximum of N samples, non-blocking. Optionally use a read/query-condition to select which samples
        you are interested in.

        Reading samples does not remove them from the :class:`DataReader's<DataReader>` receive queue. So read
        methods may return the same sample in multiple calls.

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
        use_reader = self._ref
        use_mask = SampleState.Any | ViewState.Any | InstanceState.Any
        if isinstance(condition, ReadCondition):
            use_reader = condition.reader._ref
            use_mask = condition.mask
        elif isinstance(condition, QueryCondition):
            use_reader = condition._ref
            use_mask = condition.mask

        if instance_handle is not None:
            ret = ddspy_read_handle(use_reader, use_mask, N, instance_handle)
        else:
            ret = ddspy_read(use_reader, use_mask, N)

        if type(ret) == int:
            raise DDSException(ret, f"Occurred while reading data in {repr(self)}")

        samples = []
        for (data, info) in ret:
            if info.valid_data:
                samples.append(self._topic.data_type.deserialize(data))
                samples[-1].sample_info = info
            else:
                samples.append(InvalidSample(self._topic.data_type.deserialize_key(data), info))
        return samples

    def take(self, N: int = 1, condition: Entity = None, instance_handle: int = None) -> List[_T]:
        """Take a maximum of N samples, non-blocking. Optionally use a read/query-condition to select which samples
        you are interested in.

        Taking samples removes them from the :class:`DataReader's<DataReader>` receive queue. So take methods will
        not return the same sample more than once.

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
        use_reader = self._ref
        use_mask = SampleState.Any | ViewState.Any | InstanceState.Any
        if isinstance(condition, ReadCondition):
            use_reader = condition.reader._ref
            use_mask = condition.mask
        elif isinstance(condition, QueryCondition):
            use_reader = condition._ref
            use_mask = condition.mask

        if instance_handle is not None:
            ret = ddspy_take_handle(use_reader, use_mask, N, instance_handle)
        else:
            ret = ddspy_take(use_reader, use_mask, N)

        if type(ret) == int:
            raise DDSException(ret, f"Occurred while taking data in {repr(self)}")

        samples = []
        for (data, info) in ret:
            if info.valid_data:
                samples.append(self._topic.data_type.deserialize(data))
                samples[-1].sample_info = info
            else:
                samples.append(InvalidSample(self._topic.data_type.deserialize_key(data), info))
        return samples

    def read_next(self) -> Optional[_T]:
        """Shortcut method to read exactly one sample or return None.

        Raises
        ------
        DDSException
            If any error code is returned by the DDS API it is converted into an exception.
        """
        self._next_condition = self._next_condition or \
            ReadCondition(self, ViewState.Any | SampleState.NotRead | InstanceState.Alive)
        samples = self.read(condition=self._next_condition)
        if samples:
            return samples[0]
        return None

    def take_next(self) -> Optional[_T]:
        """Shortcut method to take exactly one sample or return None.

        Raises
        ------
        DDSException
            If any error code is returned by the DDS API it is converted into an exception.
        """
        self._next_condition = self._next_condition or \
            ReadCondition(self, ViewState.Any | SampleState.NotRead | InstanceState.Alive)
        samples = self.take(condition=self._next_condition)
        if samples:
            return samples[0]
        return None

    def read_iter(self, condition=None, timeout: int = None) -> Generator[_T, None, None]:
        """Shortcut method to iterate reading samples. Iteration will stop once the timeout you supply expires.
        Every time a sample is received the timeout is reset.

        Raises
        ------
        DDSException
            If any error code is returned by the DDS API it is converted into an exception.
        """
        waitset = WaitSet(self.participant)
        condition = condition or ReadCondition(self, ViewState.Any | InstanceState.Alive | SampleState.NotRead)
        waitset.attach(condition)
        timeout = timeout or duration(weeks=99999)

        while True:
            while True:
                a = self.read(condition=condition)
                if not a:
                    break
                yield a[0]
            if waitset.wait(timeout) == 0:
                break

    def read_one(self, condition=None, timeout: int = None) -> _T:
        """Shortcut method to block and take exactly one sample or raise a timeout"""
        sample = next(self.read_iter(condition=condition, timeout=timeout))
        if sample is None:
            raise TimeoutError()
        return sample

    def take_iter(self, condition=None, timeout: int = None) -> Generator[_T, None, None]:
        """Shortcut method to iterate taking samples. Iteration will stop once the timeout you supply expires.
        Every time a sample is received the timeout is reset.

        Raises
        ------
        DDSException
            If any error code is returned by the DDS API it is converted into an exception.
        """
        waitset = WaitSet(self.participant)
        condition = condition or ReadCondition(self, ViewState.Any | InstanceState.Alive | SampleState.NotRead)
        waitset.attach(condition)
        timeout = timeout or duration(weeks=99999)

        while True:
            while True:
                a = self.take(condition=condition)
                if not a:
                    break
                yield a[0]
            if waitset.wait(timeout) == 0:
                break

    def take_one(self, condition=None, timeout: int = None) -> _T:
        """Shortcut method to block and take exactly one sample or raise a timeout"""
        sample = next(self.take_iter(condition=condition, timeout=timeout))
        if sample is None:
            raise TimeoutError()
        return sample

    async def read_aiter(self, condition=None, timeout: int = None) -> AsyncGenerator[_T, None]:
        """Shortcut method to async iterate reading samples. Iteration will stop once the timeout you supply expires.
        Every time a sample is received the timeout is reset.

        Raises
        ------
        DDSException
            If any error code is returned by the DDS API it is converted into an exception.
        """
        waitset = WaitSet(self.participant)
        condition = condition or ReadCondition(self, ViewState.Any | InstanceState.Alive | SampleState.NotRead)
        waitset.attach(condition)
        timeout = timeout or duration(weeks=99999)

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            while True:
                while True:
                    a = self.read(condition=condition)
                    if not a:
                        break
                    yield a[0]
                result = await loop.run_in_executor(pool, waitset.wait, timeout)
                if result == 0:
                    break

    async def take_aiter(self, condition=None, timeout: int = None) -> AsyncGenerator[_T, None]:
        """Shortcut method to async iterate taking samples. Iteration will stop once the timeout you supply expires.
        Every time a sample is received the timeout is reset.

        Raises
        ------
        DDSException
            If any error code is returned by the DDS API it is converted into an exception.
        """
        waitset = WaitSet(self.participant)
        condition = condition or ReadCondition(self, ViewState.Any | InstanceState.Alive | SampleState.NotRead)
        waitset.attach(condition)
        timeout = timeout or duration(weeks=99999)

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            while True:
                while True:
                    a = self.take(condition=condition)
                    if not a:
                        break
                    yield a[0]
                result = await loop.run_in_executor(pool, waitset.wait, timeout)
                if result == 0:
                    break

    def wait_for_historical_data(self, timeout: int) -> bool:
        ret = self._wait_for_historical_data(self._ref, timeout)

        if ret == 0:
            return True
        elif ret == DDSException.DDS_RETCODE_TIMEOUT:
            return False
        raise DDSException(ret, f"Occured while waiting for historical data in {repr(self)}")

    def lookup_instance(self, sample: _T) -> Optional[int]:
        ret = ddspy_lookup_instance(self._ref, sample.serialize_key())
        if ret < 0:
            raise DDSException(ret, f"Occurred while lookup up instance from {repr(self)}")
        if ret == 0:
            return None
        return ret

    def get_matched_publications(self) -> List[int]:
        """Get instance handles of the data writers matching a reader.

        Raises
        ------
            DDSException: When the number of matching writers < 0.

        Returns
        -------
        List[int]:
            A list of instance handles of the matching data writers.
        """
        num_matched_pub = self._get_matched_publications(self._ref, None, 0)
        if num_matched_pub < 0:
            raise DDSException(num_matched_pub, f"Occurred when getting the number of matched publications of {repr(self)}")
        if num_matched_pub == 0:
            return []

        matched_pub_list = (dds_c_t.instance_handle * int(num_matched_pub))()
        matched_pub_list_pt = ct.cast(matched_pub_list, ct.POINTER(dds_c_t.instance_handle))

        ret = self._get_matched_publications(self._ref, matched_pub_list_pt, num_matched_pub)
        if ret >= 0:
            return [matched_pub_list[i] for i in range(ret)]

        raise DDSException(ret, f"Occurred when getting the matched publications of {repr(self)}")

    matched_pub = property(get_matched_publications)

    def get_matched_publication_data(self, handle) -> Optional['cyclonedds.builtin.DcpsEndpoint']:
        """Get a description of a writer matched with the provided reader.

        Parameters
        ----------
        handle: Int
            The instance handle of a writer.

        Returns
        -------
        DcpsEndpoint:
            The sample of the DcpsEndpoint built-in topic.
        """
        return ddspy_get_matched_publication_data(self._ref, handle, endpoint_constructor, cqos_to_qos)

    def get_liveliness_changed_status(self):
        """Get LIVELINESS_CHANGED status

        Raises
        ------
        DDSException

        Returns
        -------
        liveness_changed_status:
            The class 'liveness_changed_status' value.
        """
        status = dds_c_t.liveliness_changed_status()
        ret = self._get_liveliness_changed_status(self._ref, ct.byref(status))
        if ret == 0:
            return status
        raise DDSException(ret, f"Occurred when getting the liveliness changed status for {repr(self)}")

    def get_requested_deadline_missed_status(self):
        """Get REQUESTED DEALINE MISSED status

        Raises
        ------
        DDSException

        Returns
        -------
        requested_deadline_missed_status:
            The class 'requested_deadline_missed_status' value.
        """
        status = dds_c_t.requested_deadline_missed_status()
        ret = self._get_requested_deadline_missed_status(self._ref, ct.byref(status))
        if ret == 0:
            return status
        raise DDSException(ret, f"Occurred when getting the requested deadline missed status for {repr(self)}")

    def get_requested_incompatible_qos_status(self):
        """Get REQUESTED INCOMPATIBLE QOS status

        Raises
        ------
        DDSException

        Returns
        -------
        requested_incompatible_qos_status:
            The class 'requested_incompatible_qos_status' value.
        """
        status = dds_c_t.requested_incompatible_qos_status()
        ret = self._get_requested_incompatible_qos_status(self._ref, ct.byref(status))
        if ret == 0:
            return status
        raise DDSException(ret, f"Occurred when getting the requested incompatible qos status for {repr(self)}")

    def get_sample_lost_status(self):
        """Get SAMPLE LOST status

        Raises
        ------
        DDSException

        Returns
        -------
        sample_lost_status:
            The class 'sample_lost_status' value.
        """
        status = dds_c_t.sample_lost_status()
        ret = self._get_sample_lost_status(self._ref, ct.byref(status))
        if ret == 0:
            return status
        raise DDSException(ret, f"Occurred when getting the sample lost status for {repr(self)}")

    def get_sample_rejected_status(self):
        """Get SAMPLE REJECTED status

        Raises
        ------
        DDSException

        Returns
        -------
        sample_rejected_status:
            The class 'sample_rejected_status' value.
        """
        status = dds_c_t.sample_rejected_status()
        ret = self._get_sample_rejected_status(self._ref, ct.byref(status))
        if ret == 0:
            return status
        raise DDSException(ret, f"Occurred when getting the sample rejected status for {repr(self)}")

    def get_subscription_matched_status(self):
        """Get SUBSCRIPTION MATCHED status

        Raises
        ------
        DDSException

        Returns
        -------
        subscription_matched_status:
            The class 'subscription_matched_status' value.
        """
        status = dds_c_t.subscription_matched_status()
        ret = self._get_subscription_matched_status(self._ref, ct.byref(status))
        if ret == 0:
            return status
        raise DDSException(ret, f"Occurred when getting the subscription matched status for {repr(self)}")

    @c_call("dds_create_reader")
    def _create_reader(self, subscriber: dds_c_t.entity, topic: dds_c_t.entity, qos: dds_c_t.qos_p,
                       listener: dds_c_t.listener_p) -> dds_c_t.entity:
        pass

    @c_call("dds_reader_wait_for_historical_data")
    def _wait_for_historical_data(self, reader: dds_c_t.entity, max_wait: dds_c_t.duration) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_matched_publications")
    def _get_matched_publications(self, reader: dds_c_t.entity, handle: ct.POINTER(dds_c_t.instance_handle),
                                  size: ct.c_size_t) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_liveliness_changed_status")
    def _get_liveliness_changed_status(self, reader: dds_c_t.entity, status: ct.POINTER(dds_c_t.liveliness_changed_status)) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_requested_deadline_missed_status")
    def _get_requested_deadline_missed_status(self, reader: dds_c_t.entity, status: ct.POINTER(dds_c_t.requested_deadline_missed_status)) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_requested_incompatible_qos_status")
    def _get_requested_incompatible_qos_status(self, reader: dds_c_t.entity, status: ct.POINTER(dds_c_t.requested_incompatible_qos_status)) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_sample_lost_status")
    def _get_sample_lost_status(self, reader: dds_c_t.entity, status: ct.POINTER(dds_c_t.sample_lost_status)) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_sample_rejected_status")
    def _get_sample_rejected_status(self, reader: dds_c_t.entity, status: ct.POINTER(dds_c_t.sample_rejected_status)) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_subscription_matched_status")
    def _get_subscription_matched_status(self, reader: dds_c_t.entity, status: ct.POINTER(dds_c_t.subscription_matched_status)) -> dds_c_t.returnv:
        pass

__all__ = ["Subscriber", "DataReader"]
