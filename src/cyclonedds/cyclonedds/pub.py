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

from typing import Optional, TYPE_CHECKING

from .internal import c_call, dds_c_t
from .core import Entity, DDSException
from .qos import _CQos

from ddspy import ddspy_write, ddspy_write_ts, ddspy_dispose, ddspy_writedispose, ddspy_writedispose_ts, \
    ddspy_dispose_handle, ddspy_dispose_handle_ts, ddspy_register_instance, ddspy_unregister_instance,   \
    ddspy_unregister_instance_handle, ddspy_unregister_instance_ts, ddspy_unregister_instance_handle_ts, \
    ddspy_lookup_instance, ddspy_dispose_ts


if TYPE_CHECKING:
    import cyclonedds


class Publisher(Entity):
    def __init__(
            self,
            domain_participant: 'cyclonedds.domain.DomainParticipant',
            qos: Optional['cyclonedds.core.Qos'] = None,
            listener: Optional['cyclonedds.core.Listener'] = None):
        cqos = _CQos.qos_to_cqos(qos) if qos else None
        super().__init__(
            self._create_publisher(
                domain_participant._ref,
                cqos,
                listener._ref if listener else None
            ),
            listener=listener
        )
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
    def __init__(self, publisher: 'cyclonedds.pub.Publisher', topic: 'cyclonedds.topic.Topic', qos=None, listener=None):
        cqos = _CQos.qos_to_cqos(qos) if qos else None
        super().__init__(
            self._create_writer(
                publisher._ref,
                topic._ref,
                cqos,
                listener._ref if listener else None
            ),
            listener=listener
        )

        self._topic_ref = topic._ref
        if cqos:
            _CQos.cqos_destroy(cqos)

        self._keepalive_entities = [self.publisher, self.topic]

    @property
    def topic(self) -> 'cyclonedds.topic.Topic':
        return self.get_entity(self._topic_ref)

    def write(self, sample, timestamp=None):
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

    @c_call("dds_create_writer")
    def _create_writer(self, publisher: dds_c_t.entity, topic: dds_c_t.entity, qos: dds_c_t.qos_p,
                       listener: dds_c_t.listener_p) -> dds_c_t.entity:
        pass

    @c_call("dds_wait_for_acks")
    def _wait_for_acks(self, publisher: dds_c_t.entity, timeout: dds_c_t.duration) -> dds_c_t.returnv:
        pass
