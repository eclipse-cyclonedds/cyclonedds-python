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
from typing import Union, AnyStr, Callable, Optional, Generic, Type, TypeVar, TYPE_CHECKING

from .internal import DDS, c_call, c_callable, dds_c_t
from .core import Entity, DDSException, Listener
from .qos import _CQos, Qos, LimitedScopeQos, TopicQos
from .idl import IdlStruct, IdlUnion

from cyclonedds._clayer import ddspy_topic_create


if TYPE_CHECKING:
    import cyclonedds


_S = TypeVar("_S", bound=Union[IdlStruct, IdlUnion])

class Sample(ct.Structure):
    _fields_ = [
        ('usample', ct.c_void_p),
        ('usample_size', ct.c_size_t)
    ]

_filter_fn = c_callable(ct.c_bool, [ct.POINTER(Sample), ct.c_void_p])


class Topic(Entity, Generic[_S]):
    """Representing a Topic"""

    def __init__(
            self,
            domain_participant: 'cyclonedds.domain.DomainParticipant',
            topic_name: AnyStr,
            data_type: Type[_S],
            qos: Optional[Qos] = None,
            listener: Optional[Listener] = None):
        if qos is not None:
            if isinstance(qos, LimitedScopeQos) and not isinstance(qos, TopicQos):
                raise TypeError(f"{qos} is not appropriate for a Topic")
            elif not isinstance(qos, Qos):
                raise TypeError(f"{qos} is not a valid qos object")

        if listener is not None:
            if not isinstance(listener, Listener):
                raise TypeError(f"{listener} is not a valid listener object.")

        if not hasattr(data_type, "__idl__"):
            raise TypeError(f"{data_type} is not an idl type.")

        self.data_type = data_type
        data_type.__idl__.populate()
        data_type.__idl__.fill_type_data()

        cqos = _CQos.qos_to_cqos(qos) if qos else None
        try:
            super().__init__(
                ddspy_topic_create(
                    domain_participant._ref,
                    topic_name,
                    data_type,
                    cqos,
                    listener._ref if listener else None
                ),
                listener=listener
            )
        finally:
            if cqos:
                _CQos.cqos_destroy(cqos)

        self._keepalive_entities = [self.participant]

    def get_name(self, max_size=256) -> str:
        name = (ct.c_char * max_size)()
        name_pt = ct.cast(name, ct.c_char_p)
        ret = self._get_name(self._ref, name_pt, max_size)
        if ret < 0:
            raise DDSException(ret, f"Occurred while fetching a topic name for {repr(self)}")
        return bytes(name).split(b'\0', 1)[0].decode("ASCII")

    name = property(get_name, doc="Get topic name")

    def get_type_name(self, max_size=256) -> str:
        name = (ct.c_char * max_size)()
        name_pt = ct.cast(name, ct.c_char_p)
        ret = self._get_type_name(self._ref, name_pt, max_size)
        if ret < 0:
            raise DDSException(ret, f"Occurred while fetching a topic type name for {repr(self)}")
        return bytes(name).split(b'\0', 1)[0].decode("ASCII")

    typename = property(get_type_name, doc="Get topic type name")

    def set_topic_filter(self, callable: Callable[['cyclonedds.topic', Sample], bool]):
        """Sets a filter and filter argument on a topic.

        Parameters
        ----------
        callable : filter
            The filter function used to filter topic samples.
        topic: Topic
            The topic to set the filter function.
        Sample: Sample
            The sample that needs to be checked whether to be filtered.

        Returns
        -------
        bool
            Whether this sample is filtered.
        """
        if callable is None:
            return self._set_topic_filter(self._ref, None, None)

        def call(csample, args):
            return callable(self, self.data_type.deserialize(
                ct.string_at(csample[0].usample, csample[0].usample_size)))

        self._topic_filter = _filter_fn(call)
        self._set_topic_filter(self._ref, self._topic_filter, None)

    def set_c_topic_filter(self, c_callable):
        self._c_topic_filter = c_callable
        self._set_topic_filter(self._ref, self._c_topic_filter, None)

    def get_inconsistent_topic_status(self):
        """Get INCONSISTENT_TOPIC status

        Raises
        ------
        DDSException:
            If any error code is returned by the DDS API it is converted into an exception.

        Returns
        -------
        inconsistent_topic_status:
            The class 'inconsistent_topic_status` value.
        """
        status = dds_c_t.inconsistent_topic_status()
        ret = self._get_inconsistent_topic_status(self._ref, ct.byref(status))
        if ret == 0:
            return status
        raise DDSException(ret, f"Occurred when getting the inconsistent topic status for {repr(self)}")

    


    @c_call("dds_get_name")
    def _get_name(self, topic: dds_c_t.entity, name: ct.c_char_p, size: ct.c_size_t) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_type_name")
    def _get_type_name(self, topic: dds_c_t.entity, name: ct.c_char_p, size: ct.c_size_t) -> dds_c_t.returnv:
        pass

    @c_call("dds_set_topic_filter_and_arg")
    def _set_topic_filter(self, topic: dds_c_t.entity, callback: _filter_fn, args: ct.c_void_p) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_inconsistent_topic_status")
    def _get_inconsistent_topic_status(self, topic: dds_c_t.entity, status: ct.POINTER(dds_c_t.inconsistent_topic_status)) -> dds_c_t.returnv:
        pass
