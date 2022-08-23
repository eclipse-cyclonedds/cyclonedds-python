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

from argparse import ArgumentError
import uuid
import asyncio
import concurrent
import ctypes as ct
from weakref import WeakValueDictionary
from typing import Any, Callable, Dict, Optional, List, TYPE_CHECKING

from .internal import c_call, c_callable, dds_infinity, dds_c_t, DDS
from .qos import Qos, Policy, _CQos


if TYPE_CHECKING:
    import cyclonedds


class DDSException(Exception):
    """This exception is thrown when a return code from the underlying C api indicates non-valid use of the API.
    Print the exception directly or convert it to string for a detailed description.

    Attributes
    ----------
    code: int
        One of the ``DDS_RETCODE_`` constants that indicates the type of error.
    msg: str
        A human readable description of where the error occurred
    """

    DDS_RETCODE_OK = 0  # Success
    DDS_RETCODE_ERROR = -1  # Non specific error
    DDS_RETCODE_UNSUPPORTED = -2  # Feature unsupported
    DDS_RETCODE_BAD_PARAMETER = -3  # Bad parameter value
    DDS_RETCODE_PRECONDITION_NOT_MET = -4  # Precondition for operation not met
    DDS_RETCODE_OUT_OF_RESOURCES = (
        -5
    )  # When an operation fails because of a lack of resources
    DDS_RETCODE_NOT_ENABLED = -6  # When a configurable feature is not enabled
    DDS_RETCODE_IMMUTABLE_POLICY = (
        -7
    )  # When an attempt is made to modify an immutable policy
    DDS_RETCODE_INCONSISTENT_POLICY = (
        -8
    )  # When a policy is used with inconsistent values
    DDS_RETCODE_ALREADY_DELETED = (
        -9
    )  # When an attempt is made to delete something more than once
    DDS_RETCODE_TIMEOUT = -10  # When a timeout has occurred
    DDS_RETCODE_NO_DATA = -11  # When expected data is not provided
    DDS_RETCODE_ILLEGAL_OPERATION = (
        -12
    )  # When a function is called when it should not be
    DDS_RETCODE_NOT_ALLOWED_BY_SECURITY = (
        -13
    )  # When credentials are not enough to use the function

    error_message_mapping = {
        DDS_RETCODE_OK: ("DDS_RETCODE_OK", "Success"),
        DDS_RETCODE_ERROR: ("DDS_RETCODE_ERROR", "Non specific error"),
        DDS_RETCODE_UNSUPPORTED: ("DDS_RETCODE_UNSUPPORTED", "Feature unsupported"),
        DDS_RETCODE_BAD_PARAMETER: ("DDS_RETCODE_BAD_PARAMETER", "Bad parameter value"),
        DDS_RETCODE_PRECONDITION_NOT_MET: (
            "DDS_RETCODE_PRECONDITION_NOT_MET",
            "Precondition for operation not met",
        ),
        DDS_RETCODE_OUT_OF_RESOURCES: (
            "DDS_RETCODE_OUT_OF_RESOURCES",
            "Operation failed because of a lack of resources",
        ),
        DDS_RETCODE_NOT_ENABLED: (
            "DDS_RETCODE_NOT_ENABLED",
            "A configurable feature is not enabled",
        ),
        DDS_RETCODE_IMMUTABLE_POLICY: (
            "DDS_RETCODE_IMMUTABLE_POLICY",
            "An attempt was made to modify an immutable policy",
        ),
        DDS_RETCODE_INCONSISTENT_POLICY: (
            "DDS_RETCODE_INCONSISTENT_POLICY",
            "A policy with inconsistent values was used",
        ),
        DDS_RETCODE_ALREADY_DELETED: (
            "DDS_RETCODE_ALREADY_DELETED",
            "An attempt was made to delete something more than once",
        ),
        DDS_RETCODE_TIMEOUT: ("DDS_RETCODE_TIMEOUT", "A timeout has occurred"),
        DDS_RETCODE_NO_DATA: ("DDS_RETCODE_NO_DATA", "Expected data is not provided"),
        DDS_RETCODE_ILLEGAL_OPERATION: (
            "DDS_RETCODE_ILLEGAL_OPERATION",
            "A function was called when it should not be",
        ),
        DDS_RETCODE_NOT_ALLOWED_BY_SECURITY: (
            "DDS_RETCODE_NOT_ALLOWED_BY_SECURITY",
            "Insufficient credentials supplied to use the function",
        ),
    }

    def __init__(self, code: int, msg: str = None, **kwargs) -> None:
        """Initialize a DDSException. Code should be one of the DDS_RETCODE_* constants."""
        self.code = code
        self.msg = msg or ""
        super().__init__(**kwargs)

    def __str__(self) -> str:
        if self.code in self.error_message_mapping:
            msg = self.error_message_mapping[self.code]
            return f"[{msg[0]}] {msg[1]}. {self.msg}"
        return f"[DDSException] Got an unexpected error code '{self.code}'. {self.msg}"

    def __repr__(self) -> str:
        return str(self)


class Entity(DDS):
    """
    Base class for all entities in the DDS API. The lifetime of the underlying
    DDS API object is linked to the lifetime of the Python entity object.

    Attributes
    ----------
    subscriber
                 If this entity is associated with a DataReader retrieve it.
                 It is read-only. This is a proxy for get_subscriber().
    publisher
                 If this entity is associated with a Publisher retrieve it.
                 It is read-only. This is a proxy for get_publisher().
    datareader
                 If this entity is associated with a DataReader retrieve it.
                 It is read-only. This is a proxy for get_datareader().
    guid:        uuid.UUID
                 Return the globally unique identifier for this entity.
                 It is read-only. This is a proxy for get_guid().
    status_mask
                 The status mask for this entity. It is a set of bits formed
                 from ``DDSStatus``. This is a proxy for get/set_status_mask().
    parent
                 The entity that is this entities parent. For example: the subscriber for a
                 datareader, the participant for a topic.
                 It is read-only. This is a proxy for get_parent().
    participant
                 Get the participant for any entity, will only fail for a ``Domain``.
                 It is read-only. This is a proxy for get_participant().
    children
                 Get a list of children belonging to this entity. It is the opposite as ``parent``.
                 It is read-only. This is a proxy for get_children().
    domain_id
                 Get the id of the domain this entity belongs to.
    """

    _entities: Dict[dds_c_t.entity, "Entity"] = WeakValueDictionary()

    def __init__(self, ref: int, listener: "Listener" = None) -> None:
        """Initialize an Entity. You should never need to initialize an Entity manually.

        Parameters
        ----------
        ref: int
            The reference id as returned by the DDS API.
        listener: Listener
            Listener for this entity. We retain the python object to avoid it being garbage collected if the listener
            goes out of scope but the entity doesn't. If we don't the python function will be freed, causing C to call
            into freed memory -> segfault.

        Raises
        ------
        DDSException
            If an invalid reference id is passed to this function this means instantiation of some other object failed.
        """
        if ref < 0:
            raise DDSException(
                ref,
                f"Occurred upon initialisation of a {self.__class__.__module__}.{self.__class__.__name__}",
            )
        super().__init__(ref)
        self._entities[self._ref] = self
        self._listener = listener

    def __del__(self) -> None:
        if not hasattr(self, "_ref") or self._ref not in self._entities:
            return

        del self._entities[self._ref]
        self._delete(self._ref)

    def get_subscriber(self) -> Optional["cyclonedds.sub.Subscriber"]:
        """Retrieve the subscriber associated with this entity.

        Returns
        -------
        Optional[Subscriber]
            Not all entities are associated with a subscriber, so this method may return None.

        Raises
        ------
        DDSException
        """
        ref = self._get_subscriber(self._ref)
        if ref >= 0:
            return self.get_entity(ref)
        raise DDSException(
            ref, f"Occurred when getting the subscriber for {repr(self)}"
        )

    subscriber: Optional["cyclonedds.sub.Subscriber"] = property(get_subscriber)

    def get_publisher(self) -> Optional["cyclonedds.pub.Publisher"]:
        """Retrieve the publisher associated with this entity.

        Returns
        -------
        Optional[Publisher]
            Not all entities are associated with a publisher, so this method may return None.

        Raises
        ------
        DDSException
        """
        ref = self._get_publisher(self._ref)
        if ref >= 0:
            return self.get_entity(ref)
        raise DDSException(ref, f"Occurred when getting the publisher for {repr(self)}")

    publisher: Optional["cyclonedds.pub.Publisher"] = property(get_publisher)

    def get_datareader(self) -> Optional["cyclonedds.sub.DataReader"]:
        """Retrieve the datareader associated with this entity.

        Returns
        -------
        Optional[DataReader]
            Not all entities are associated with a datareader, so this method may return None.

        Raises
        ------
        DDSException
        """
        ref = self._get_datareader(self._ref)
        if ref >= 0:
            return self.get_entity(ref)
        raise DDSException(
            ref, f"Occurred when getting the datareader for {repr(self)}"
        )

    datareader: Optional["cyclonedds.sub.DataReader"] = property(get_datareader)

    def get_instance_handle(self) -> int:
        """Retrieve the instance associated with this entity.

        Returns
        -------
        int
            The integer handle is just a number you can use in writer/reader calls.

        Raises
        ------
        DDSException
        """
        handle = dds_c_t.instance_handle()
        ret = self._get_instance_handle(self._ref, ct.byref(handle))
        if ret == 0:
            return int(handle)
        raise DDSException(
            ret, f"Occurred when getting the instance handle for {repr(self)}"
        )

    instance_handle: int = property(get_instance_handle)

    def get_guid(self) -> uuid.UUID:
        """Get a globally unique identifier for this entity.

        Returns
        -------
        uuid.UUID
            View the python documentation for this class for detailed usage.

        Raises
        ------
        DDSException
        """
        guid = dds_c_t.guid()
        ret = self._get_guid(self._ref, ct.byref(guid))
        if ret == 0:
            return guid.as_python_guid()
        raise DDSException(ret, f"Occurred when getting the GUID for {repr(self)}")

    guid: uuid.UUID = property(get_guid)

    def read_status(self, mask: int = None) -> int:
        """Read the status bits set on this Entity. You can build a mask by using :class:`DDSStatus`.

        Parameters
        ----------
        mask
            The :class:`DDSStatus` mask. If not supplied the mask is used that was set on this Entity using set_status_mask.

        Returns
        -------
        int
            The :class:`DDSStatus` bits that were set.

        Raises
        ------
        DDSException
        """
        status = ct.c_uint32()
        ret = self._read_status(
            self._ref,
            ct.byref(status),
            ct.c_uint32(mask) if mask else self.get_status_mask(),
        )
        if ret == 0:
            return status.value
        raise DDSException(ret, f"Occurred when reading the status for {repr(self)}")

    def take_status(self, mask: int = None) -> int:
        """Take the status bits set on this Entity, after which they will be set to 0 again.
        You can build a mask by using :class:`DDSStatus`.

        Parameters
        ----------
        mask
            The :class:`DDSStatus` mask. If not supplied the mask is used that was set on this Entity using set_status_mask.

        Returns
        -------
        int
            The :class:`DDSStatus` bits that were set.

        Raises
        ------
        DDSException
        """
        status = ct.c_uint32()
        ret = self._take_status(
            self._ref,
            ct.byref(status),
            ct.c_uint32(mask) if mask else self.get_status_mask(),
        )
        if ret == 0:
            return status.value
        raise DDSException(ret, f"Occurred when taking the status for {repr(self)}")

    def get_status_changes(self) -> int:
        """Get all status changes since the last read_status() or take_status().

        Returns
        -------
        int
            The :class:`DDSStatus` bits that were set.

        Raises
        ------
        DDSException
        """
        status = ct.c_uint32()
        ret = self._get_status_changes(self._ref, ct.byref(status))
        if ret == 0:
            return status.value
        raise DDSException(
            ret, f"Occurred when getting the status changes for {repr(self)}"
        )

    def get_status_mask(self) -> int:
        """Get the status mask for this Entity.

        Returns
        -------
        int
            The :class:`DDSStatus` bits that are enabled.

        Raises
        ------
        DDSException
        """
        mask = ct.c_uint32()
        ret = self._get_status_mask(self._ref, ct.byref(mask))
        if ret == 0:
            return mask.value
        raise DDSException(
            ret, f"Occurred when getting the status mask for {repr(self)}"
        )

    def set_status_mask(self, mask: int) -> None:
        """Set the status mask for this Entity. By default the mask is 0. Only the status changes
            for the bits in this mask are tracked on this entity.

        Parameters
        ----------
        mask : int
            The :class:`DDSStatus` bits to track.

        Raises
        ------
        DDSException
        """
        ret = self._set_status_mask(self._ref, ct.c_uint32(mask))
        if ret == 0:
            return
        raise DDSException(
            ret, f"Occurred when setting the status mask for {repr(self)}"
        )

    status_mask: int = property(get_status_mask, set_status_mask)

    def get_qos(self) -> Qos:
        """Get the :class:`Qos` associated with this entity. Note that the object returned is not
        the same python object that you used to set the :class:`Qos` on this object. Modifications to the :class:`Qos` object
        that is returned does **not** modify the Qos of the Entity.

        Returns
        -------
        Qos
            The :class:`Qos` object associated with this entity.

        Raises
        ------
        DDSException
        """
        cqos = _CQos.cqos_create()
        ret = self._get_qos(self._ref, cqos)
        if ret == 0:
            qos = _CQos.cqos_to_qos(cqos)
            _CQos.cqos_destroy(cqos)
            return qos
        _CQos.cqos_destroy(cqos)
        raise DDSException(
            ret, f"Occurred when getting the Qos Policies for {repr(self)}"
        )

    def set_qos(self, qos: Qos) -> None:
        """Set :class:`Qos` policies on this entity. Note, only a limited number of :class:`Qos` policies can be set after
        the object is created (:class:`Policy.LatencyBudget` and :class:`Policy.OwnershipStrength`). Any policies not set
        explicitly in the supplied :class:`Qos` remain unchanged.

        Parameters
        ----------
        qos : Qos
            The :class:`Qos` to apply to this entity.

        Raises
        ------
        DDSException
            If you pass an immutable policy or cause the total collection of qos policies to become inconsistent
            an exception will be raised.
        """
        cqos = _CQos.qos_to_cqos(qos)
        ret = self._set_qos(self._ref, cqos)
        _CQos.cqos_destroy(cqos)
        if ret == 0:
            return
        raise DDSException(
            ret, f"Occurred when setting the Qos Policies for {repr(self)}"
        )

    def get_listener(self) -> "Listener":
        """Return a listener with the right methods set. Modifying the returned listener object does not modify
        this entity, you will have to call set_listener() with the changed object.

        Returns
        -------
        Listener
            A listener with which you can add additional callbacks.
        """
        return self._listener.copy() if self._listener else Listener()

    def set_listener(self, listener: Optional["Listener"]) -> None:
        """Update the listener for this object. If a listener already exist for this object only the fields you explicitly
        have set on your new listener are overwritten. Passing None will remove this entity's Listener.

        Future changes to the passed Listener object will not affect the Listener associated with this Entity.

        Parameters
        ----------
        listener :
            The listener object to use, or None to remove the current listener from this Entity.

        Raises
        ------
        DDSException
        """
        if listener is not None:
            if self._listener is not None:
                if self._listener != listener:
                    listener.copy_to(self._listener)
            else:
                self._listener = listener.copy()
            ref = self._listener._ref
        else:
            ref = None
            self._listener = None

        ret = self._set_listener(self._ref, ref)
        if ret == 0:
            return
        raise DDSException(ret, f"Occurred when setting the Listener for {repr(self)}")

    def get_parent(self) -> Optional["Entity"]:
        """Get the parent entity associated with this entity. A ``Domain`` object is the only object without parent,
        but if the domain is not created through the Python API this call won't find it
        and return None from the DomainParticipant.

        Returns
        -------
        Optional[Entity]
            The parent of this entity. This would be the Subscriber for a DataReader, DomainParticipant for a Topic etc.

        Raises
        ------
        DDSException
        """
        ret = self._get_parent(self._ref)

        if ret > 0:
            return self.get_entity(ret)

        if ret is None or ret == 0:
            return None

        raise DDSException(ret, f"Occurred when getting the parent of {repr(self)}")

    parent: Optional["Entity"] = property(get_parent)

    def get_participant(self) -> Optional["cyclonedds.domain.DomainParticipant"]:
        """Get the domain participant for this entity. This should work on all valid Entity objects except a Domain.

        Returns
        -------
        Optional[cyclonedds.domain.DomainParticipant]
            Only fails for a Domain object.

        Raises
        ------
        DDSException
        """
        ret = self._get_participant(self._ref)

        if ret > 0:
            return self.get_entity(ret)

        if ret is None or ret == 0:
            return None

        raise DDSException(
            ret, f"Occurred when getting the participant of {repr(self)}"
        )

    participant: Optional["cyclonedds.domain.DomainParticipant"] = property(get_participant)

    def get_children(self) -> List["Entity"]:
        """Get the list of children of this entity. For example, the list of datareaders belonging to a subscriber.
        Opposite of parent.

        Returns
        -------
        List[Entity]
            All the entities considered children of this entity.

        Raises
        ------
        DDSException
        """
        num_children = self._get_children(self._ref, None, 0)
        if num_children < 0:
            raise DDSException(
                num_children,
                f"Occurred when getting the number of children of {repr(self)}",
            )
        if num_children == 0:
            return []

        children_list = (dds_c_t.entity * int(num_children))()
        children_list_pt = ct.cast(children_list, ct.POINTER(dds_c_t.entity))

        ret = self._get_children(self._ref, children_list_pt, num_children)
        if ret >= 0:
            return [self.get_entity(children_list[i]) for i in range(ret)]

        raise DDSException(ret, f"Occurred when getting the children of {repr(self)}")

    children: List["Entity"] = property(get_children)

    def get_domain_id(self) -> int:
        """Get the id of the domain this entity resides in.

        Returns
        -------
        int
            The domain id.

        Raises
        ------
        DDSException
        """
        domainid = dds_c_t.domainid()
        ret = self._get_domainid(self._ref, ct.byref(domainid))
        if ret == 0:
            return domainid.value

        raise DDSException(ret, f"Occurred when getting the domainid of {repr(self)}")

    domain_id: int = property(get_domain_id)

    def begin_coherent(self) -> None:
        """Begin coherent publishing or begin accessing a coherent set in a Subscriber.

        This can only be invoked on Publishers, Subscribers, DataWriters and DataReaders.
        Invoking on a DataWriter or DataReader behaves as if it was invoked on its parent
        Publisher or Subscriber respectively.
        """
        ret = self._begin_coherent(self._ref)
        if ret < 0:
            raise DDSException(ret, f"Occurred when beginning coherent on {repr(self)}")

    def end_coherent(self) -> None:
        """End coherent publishing or end accessing a coherent set in a Subscriber.

        This can only be invoked on Publishers, Subscribers, DataWriters and DataReaders.
        Invoking on a DataWriter or DataReader behaves as if it was invoked on its parent
        Publisher or Subscriber respectively.
        """
        ret = self._end_coherent(self._ref)
        if ret < 0:
            raise DDSException(ret, f"Occurred when ending coherent on {repr(self)}")

    @classmethod
    def get_entity(cls, entity_id) -> Optional["Entity"]:
        """Turn a CycloneDDS C Entity id into a Python object. You shouldn't need this."""
        return cls._entities.get(entity_id)

    @classmethod
    def _init_from_retcode(cls, code):
        entity = cls.__new__(cls)
        Entity.__init__(entity, code)
        return entity

    @c_call("dds_delete")
    def _delete(self, entity: dds_c_t.entity) -> None:
        pass

    @c_call("dds_get_subscriber")
    def _get_subscriber(self, entity: dds_c_t.entity) -> dds_c_t.entity:
        pass

    @c_call("dds_get_datareader")
    def _get_datareader(self, entity: dds_c_t.entity) -> dds_c_t.entity:
        pass

    @c_call("dds_get_publisher")
    def _get_publisher(self, entity: dds_c_t.entity) -> dds_c_t.entity:
        pass

    @c_call("dds_get_instance_handle")
    def _get_instance_handle(
        self, entity: dds_c_t.entity, handle: ct.POINTER(dds_c_t.instance_handle)
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_guid")
    def _get_guid(
        self, entity: dds_c_t.entity, guid: ct.POINTER(dds_c_t.guid)
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_read_status")
    def _read_status(
        self, entity: dds_c_t.entity, status: ct.POINTER(ct.c_uint32), mask: ct.c_uint32
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_take_status")
    def _take_status(
        self, entity: dds_c_t.entity, status: ct.POINTER(ct.c_uint32), mask: ct.c_uint32
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_status_changes")
    def _get_status_changes(
        self, entity: dds_c_t.entity, status: ct.POINTER(ct.c_uint32)
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_status_mask")
    def _get_status_mask(
        self, entity: dds_c_t.entity, mask: ct.POINTER(ct.c_uint32)
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_set_status_mask")
    def _set_status_mask(
        self, entity: dds_c_t.entity, mask: ct.c_uint32
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_qos")
    def _get_qos(self, entity: dds_c_t.entity, qos: dds_c_t.qos_p) -> dds_c_t.returnv:
        pass

    @c_call("dds_set_qos")
    def _set_qos(self, entity: dds_c_t.entity, qos: dds_c_t.qos_p) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_listener")
    def _get_listener(
        self, entity: dds_c_t.entity, listener: dds_c_t.listener_p
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_set_listener")
    def _set_listener(
        self, entity: dds_c_t.entity, listener: dds_c_t.listener_p
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_parent")
    def _get_parent(self, entity: dds_c_t.entity) -> dds_c_t.entity:
        pass

    @c_call("dds_get_participant")
    def _get_participant(self, entity: dds_c_t.entity) -> dds_c_t.entity:
        pass

    @c_call("dds_get_children")
    def _get_children(
        self,
        entity: dds_c_t.entity,
        children_list: ct.POINTER(dds_c_t.returnv),
        size: ct.c_size_t,
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_domainid")
    def _get_domainid(
        self, entity: dds_c_t.entity, domainid: ct.POINTER(dds_c_t.domainid)
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_begin_coherent")
    def _begin_coherent(self, entity: dds_c_t.entity) -> dds_c_t.returnv:
        pass

    @c_call("dds_end_coherent")
    def _end_coherent(self, entity: dds_c_t.entity) -> dds_c_t.returnv:
        pass

    def __repr__(self) -> str:
        ref = None
        try:
            ref = self._ref
        except Exception:
            pass
        return f"<Entity, type={self.__class__.__module__}.{self.__class__.__name__}, addr={hex(id(self))}, id={ref}>"


_inconsistent_topic_fn = c_callable(
    None, [dds_c_t.entity, dds_c_t.inconsistent_topic_status, ct.c_void_p]
)
_data_available_fn = c_callable(None, [dds_c_t.entity, ct.c_void_p])
_liveliness_lost_fn = c_callable(
    None, [dds_c_t.entity, dds_c_t.liveliness_lost_status, ct.c_void_p]
)
_liveliness_changed_fn = c_callable(
    None, [dds_c_t.entity, dds_c_t.liveliness_changed_status, ct.c_void_p]
)
_offered_deadline_missed_fn = c_callable(
    None, [dds_c_t.entity, dds_c_t.offered_deadline_missed_status, ct.c_void_p]
)
_offered_incompatible_qos_fn = c_callable(
    None, [dds_c_t.entity, dds_c_t.offered_incompatible_qos_status, ct.c_void_p]
)
_data_on_readers_fn = c_callable(None, [dds_c_t.entity, ct.c_void_p])
_on_sample_lost_fn = c_callable(
    None, [dds_c_t.entity, dds_c_t.sample_lost_status, ct.c_void_p]
)
_on_sample_rejected_fn = c_callable(
    None, [dds_c_t.entity, dds_c_t.sample_rejected_status, ct.c_void_p]
)
_on_requested_deadline_missed_fn = c_callable(
    None, [dds_c_t.entity, dds_c_t.requested_deadline_missed_status, ct.c_void_p]
)
_on_requested_incompatible_qos_fn = c_callable(
    None, [dds_c_t.entity, dds_c_t.requested_incompatible_qos_status, ct.c_void_p]
)
_on_publication_matched_fn = c_callable(
    None, [dds_c_t.entity, dds_c_t.publication_matched_status, ct.c_void_p]
)
_on_subscription_matched_fn = c_callable(
    None, [dds_c_t.entity, dds_c_t.subscription_matched_status, ct.c_void_p]
)


def _is_override(func):
    obj = func.__self__
    if type(obj) == Listener:
        return False

    parent_method = getattr(super(type(obj), obj), func.__name__)
    return func.__func__ != parent_method.__func__


class Listener(DDS):
    """Listeners are callback containers for entities."""

    def __init__(self, **kwargs):
        """Create a Listener object. The initializer takes override function lambdas.

        Please note that all listener callbacks are dispatched synchronously from DDS receive thread(s). You can get away with doing
        tiny amounts of processing in these callback methods, but aquiring the Python GIL from the DDS receive thread will severely
        hurt your DDS performance. Furthermore, deleting entities or writing data inside listener callbacks can get you into deadlocks.

        Parameters
        ----------
        on_data_available : Callable
            Set on_data_available callback.
        on_inconsistent_topic : Callable
            Set on_inconsistent_topic callback.
        on_liveliness_lost : Callable
            Set on_liveliness_lost callback.
        on_liveliness_changed : Callable
            Set on_liveliness_changed callback.
        on_offered_deadline_missed : Callable
            Set on_offered_deadline_missed callback.
        on_offered_incompatible_qos : Callable
            Set on_offered_incompatible_qos callback.
        on_data_on_readers : Callable
            Set on_data_on_readers callback.
        on_sample_lost : Callable
            Set on_sample_lost callback.
        on_sample_rejected : Callable
            Set on_sample_rejected callback.
        on_requested_deadline_missed : Callable
            Set on_requested_deadline_missed callback.
        on_requested_incompatible_qos : Callable
            Set on_requested_incompatible_qos callback.
        on_publication_matched : Callable
            Set on_publication_matched callback.
        on_subscription_matched : Callable
            Set on_subscription_matched callback.
        """
        super().__init__(self._create_listener(None))
        self._set_functors = {}

        if _is_override(self.on_data_available):
            self.set_on_data_available(self.on_data_available)
            self._set_functors["on_data_available"] = self.on_data_available

        if _is_override(self.on_inconsistent_topic):
            self.set_on_inconsistent_topic(self.on_inconsistent_topic)
            self._set_functors["on_inconsistent_topic"] = self.on_inconsistent_topic

        if _is_override(self.on_liveliness_lost):
            self.set_on_liveliness_lost(self.on_liveliness_lost)
            self._set_functors["on_liveliness_lost"] = self.on_liveliness_lost

        if _is_override(self.on_liveliness_changed):
            self.set_on_liveliness_changed(self.on_liveliness_changed)
            self._set_functors["on_liveliness_changed"] = self.on_liveliness_changed

        if _is_override(self.on_offered_deadline_missed):
            self.set_on_offered_deadline_missed(self.on_offered_deadline_missed)
            self._set_functors[
                "on_offered_deadline_missed"
            ] = self.on_offered_deadline_missed

        if _is_override(self.on_offered_incompatible_qos):
            self.set_on_offered_incompatible_qos(self.on_offered_incompatible_qos)
            self._set_functors[
                "on_offered_incompatible_qos"
            ] = self.on_offered_incompatible_qos

        if _is_override(self.on_data_on_readers):
            self.set_on_data_on_readers(self.on_data_on_readers)
            self._set_functors["on_data_on_readers"] = self.on_data_on_readers

        if _is_override(self.on_sample_lost):
            self.set_on_sample_lost(self.on_sample_lost)
            self._set_functors["on_sample_lost"] = self.on_sample_lost

        if _is_override(self.on_sample_rejected):
            self.set_on_sample_rejected(self.on_sample_rejected)
            self._set_functors["on_sample_rejected"] = self.on_sample_rejected

        if _is_override(self.on_requested_deadline_missed):
            self.set_on_requested_deadline_missed(self.on_requested_deadline_missed)
            self._set_functors[
                "on_requested_deadline_missed"
            ] = self.on_requested_deadline_missed

        if _is_override(self.on_requested_incompatible_qos):
            self.set_on_requested_incompatible_qos(self.on_requested_incompatible_qos)
            self._set_functors[
                "on_requested_incompatible_qos"
            ] = self.on_requested_incompatible_qos

        if _is_override(self.on_publication_matched):
            self.set_on_publication_matched(self.on_publication_matched)
            self._set_functors["on_publication_matched"] = self.on_publication_matched

        if _is_override(self.on_subscription_matched):
            self.set_on_subscription_matched(self.on_subscription_matched)
            self._set_functors["on_subscription_matched"] = self.on_subscription_matched

        self.setters = {
            "on_data_available": self.set_on_data_available,
            "on_inconsistent_topic": self.set_on_inconsistent_topic,
            "on_liveliness_lost": self.set_on_liveliness_lost,
            "on_liveliness_changed": self.set_on_liveliness_changed,
            "on_offered_deadline_missed": self.set_on_offered_deadline_missed,
            "on_offered_incompatible_qos": self.set_on_offered_incompatible_qos,
            "on_data_on_readers": self.set_on_data_on_readers,
            "on_sample_lost": self.set_on_sample_lost,
            "on_sample_rejected": self.set_on_sample_rejected,
            "on_requested_deadline_missed": self.set_on_requested_deadline_missed,
            "on_requested_incompatible_qos": self.set_on_requested_incompatible_qos,
            "on_publication_matched": self.set_on_publication_matched,
            "on_subscription_matched": self.set_on_subscription_matched,
        }

        for name, value in kwargs.items():
            if name not in self.setters:
                raise ArgumentError(f"Invalid listener attribute '{name}'")
            self.setters[name](value)

    def __del__(self):
        self._delete_listener(self._ref)

    def reset(self) -> None:
        self._reset_listener(self._ref)

    def copy(self) -> "Listener":
        listener = Listener(**self._set_functors)
        return listener

    def copy_to(self, listener: "Listener") -> None:
        for name, functor in self._set_functors.items():
            listener.setters[name](functor)

    def merge(self, listener: "Listener") -> None:
        """
        Copies any configured (non-default) callbacks from the given `listener` to self, replacing existing callbacks
        already configured on this listener.
        """
        listener.copy_to(self)

    def on_inconsistent_topic(
        self,
        reader: "cyclonedds.sub.DataReader",
        status: dds_c_t.inconsistent_topic_status,
    ) -> None:
        pass

    def set_on_inconsistent_topic(
        self, callable: Callable[["cyclonedds.sub.DataReader"], None]
    ):
        self.on_inconsistent_topic = callable
        if callable is None:
            self._set_inconsistent_topic(self._ref, None)
            del self._set_functors["on_inconsistent_topic"]
        else:
            self._set_functors["on_inconsistent_topic"] = self.on_inconsistent_topic

            def call(topic, status, arg):
                self.on_inconsistent_topic(Entity.get_entity(topic), status)

            self._on_inconsistent_topic = _inconsistent_topic_fn(call)
            self._set_inconsistent_topic(self._ref, self._on_inconsistent_topic)

    def on_data_available(self, reader: "cyclonedds.sub.DataReader") -> None:
        pass

    def set_on_data_available(
        self, callable: Callable[["cyclonedds.sub.DataReader"], None]
    ):
        self.on_data_available = callable
        if callable is None:
            self._set_data_available(self._ref, None)
            del self._set_functors["on_data_available"]
        else:
            self._set_functors["on_data_available"] = self.on_data_available

            def call(reader, arg):
                self.on_data_available(Entity.get_entity(reader))

            self._on_data_available = _data_available_fn(call)
            self._set_data_available(self._ref, self._on_data_available)

    def on_liveliness_lost(
        self,
        writer: "cyclonedds.pub.DataWriter",
        status: dds_c_t.liveliness_lost_status,
    ) -> None:
        pass

    def set_on_liveliness_lost(
        self,
        callable: Callable[
            ["cyclonedds.pub.DataWriter", dds_c_t.liveliness_lost_status], None
        ],
    ):
        self.on_liveliness_lost = callable
        if callable is None:
            self._set_liveliness_lost(self._ref, None)
            del self._set_functors["on_liveliness_lost"]
        else:
            self._set_functors["on_liveliness_lost"] = self.on_liveliness_lost

            def call(writer, status, arg):
                self.on_liveliness_lost(Entity.get_entity(writer), status)

            self._on_liveliness_lost = _liveliness_lost_fn(call)
            self._set_liveliness_lost(self._ref, self._on_liveliness_lost)

    def on_liveliness_changed(
        self,
        reader: "cyclonedds.sub.DataReader",
        status: dds_c_t.liveliness_changed_status,
    ) -> None:
        pass

    def set_on_liveliness_changed(
        self,
        callable: Callable[
            ["cyclonedds.sub.DataReader", dds_c_t.liveliness_changed_status], None
        ],
    ):
        self.on_liveliness_changed = callable
        if callable is None:
            self._set_liveliness_changed(self._ref, None)
            del self._set_functors["on_liveliness_changed"]
        else:
            self._set_functors["on_liveliness_changed"] = self.on_liveliness_changed

            def call(reader, status, arg):
                self.on_liveliness_changed(Entity.get_entity(reader), status)

            self._on_liveliness_changed = _liveliness_changed_fn(call)
            self._set_liveliness_changed(self._ref, self._on_liveliness_changed)

    def on_offered_deadline_missed(
        self,
        writer: "cyclonedds.pub.DataWriter",
        status: dds_c_t.offered_deadline_missed_status,
    ) -> None:
        pass

    def set_on_offered_deadline_missed(
        self,
        callable: Callable[
            ["cyclonedds.pub.DataWriter", dds_c_t.offered_deadline_missed_status], None
        ],
    ):
        self.on_offered_deadline_missed = callable
        if callable is None:
            self._set_on_offered_deadline_missed(self._ref, None)
            del self._set_functors["on_offered_deadline_missed"]
        else:
            self._set_functors[
                "on_offered_deadline_missed"
            ] = self.on_offered_deadline_missed

            def call(writer, status, arg):
                self.on_offered_deadline_missed(Entity.get_entity(writer), status)

            self._on_offered_deadline_missed = _offered_deadline_missed_fn(call)
            self._set_on_offered_deadline_missed(
                self._ref, self._on_offered_deadline_missed
            )

    def on_offered_incompatible_qos(
        self,
        writer: "cyclonedds.pub.DataWriter",
        status: dds_c_t.offered_incompatible_qos_status,
    ) -> None:
        pass

    def set_on_offered_incompatible_qos(
        self,
        callable: Callable[
            ["cyclonedds.pub.DataWriter", dds_c_t.offered_incompatible_qos_status], None
        ],
    ):
        self.on_offered_incompatible_qos = callable
        if callable is None:
            self._set_on_offered_incompatible_qos(self._ref, None)
            del self._set_functors["on_offered_incompatible_qos"]
        else:
            self._set_functors[
                "on_offered_incompatible_qos"
            ] = self.on_offered_incompatible_qos

            def call(writer, status, arg):
                self.on_offered_incompatible_qos(Entity.get_entity(writer), status)

            self._on_offered_incompatible_qos = _offered_incompatible_qos_fn(call)
            self._set_on_offered_incompatible_qos(
                self._ref, self._on_offered_incompatible_qos
            )

    def on_data_on_readers(self, subscriber: "cyclonedds.sub.Subscriber") -> None:
        pass

    def set_on_data_on_readers(
        self, callable: Callable[["cyclonedds.sub.Subscriber"], None]
    ):
        self.on_data_on_readers = callable
        if callable is None:
            self._set_data_available(self._ref, None)
            del self._set_functors["on_data_on_readers"]
        else:
            self._set_functors["on_data_on_readers"] = self.on_data_on_readers

            def call(subscriber, arg):
                self.on_data_on_readers(Entity.get_entity(subscriber))

            self._on_data_on_readers = _data_on_readers_fn(call)
            self._set_on_data_on_readers(self._ref, self._on_data_on_readers)

    def on_sample_lost(
        self, writer: "cyclonedds.pub.DataWriter", status: dds_c_t.sample_lost_status
    ) -> None:
        pass

    def set_on_sample_lost(
        self,
        callable: Callable[
            ["cyclonedds.pub.DataWriter", dds_c_t.sample_lost_status], None
        ],
    ):
        self.on_sample_lost = callable
        if callable is None:
            self._set_on_sample_lost(self._ref, None)
            del self._set_functors["on_sample_lost"]
        else:
            self._set_functors["on_sample_lost"] = self.on_sample_lost

            def call(writer, status, arg):
                self.on_sample_lost(Entity.get_entity(writer), status)

            self._on_sample_lost = _on_sample_lost_fn(call)
            self._set_on_sample_lost(self._ref, self._on_sample_lost)

    def on_sample_rejected(
        self,
        reader: "cyclonedds.sub.DataReader",
        status: dds_c_t.sample_rejected_status,
    ) -> None:
        pass

    def set_on_sample_rejected(
        self,
        callable: Callable[
            ["cyclonedds.sub.DataReader", dds_c_t.sample_rejected_status], None
        ],
    ):
        self.on_sample_rejected = callable
        if callable is None:
            self._set_on_sample_rejected(self._ref, None)
            del self._set_functors["on_sample_rejected"]
        else:
            self._set_functors["on_sample_rejected"] = self.on_sample_rejected

            def call(writer, status, arg):
                self.on_sample_rejected(Entity.get_entity(writer), status)

            self._on_sample_rejected = _on_sample_rejected_fn(call)
            self._set_on_sample_rejected(self._ref, self._on_sample_rejected)

    def on_requested_deadline_missed(
        self,
        reader: "cyclonedds.sub.DataReader",
        status: dds_c_t.requested_deadline_missed_status,
    ) -> None:
        pass

    def set_on_requested_deadline_missed(
        self,
        callable: Callable[
            ["cyclonedds.sub.DataReader", dds_c_t.requested_deadline_missed_status],
            None,
        ],
    ):
        self.on_requested_deadline_missed = callable
        if callable is None:
            self._set_on_requested_deadline_missed(self._ref, None)
            del self._set_functors["on_requested_deadline_missed"]
        else:
            self._set_functors[
                "on_requested_deadline_missed"
            ] = self.on_requested_deadline_missed

            def call(reader, status, arg):
                self.on_requested_deadline_missed(Entity.get_entity(reader), status)

            self._on_requested_deadline_missed = _on_requested_deadline_missed_fn(call)
            self._set_on_requested_deadline_missed(
                self._ref, self._on_requested_deadline_missed
            )

    def on_requested_incompatible_qos(
        self,
        reader: "cyclonedds.sub.DataReader",
        status: dds_c_t.requested_incompatible_qos_status,
    ) -> None:
        pass

    def set_on_requested_incompatible_qos(
        self,
        callable: Callable[
            ["cyclonedds.sub.DataReader", dds_c_t.requested_incompatible_qos_status],
            None,
        ],
    ):
        self.on_requested_incompatible_qos = callable
        if callable is None:
            self._set_on_requested_incompatible_qos(self._ref, None)
            del self._set_functors["on_requested_incompatible_qos"]
        else:
            self._set_functors[
                "on_requested_incompatible_qos"
            ] = self.on_requested_incompatible_qos

            def call(reader, status, arg):
                self.on_requested_incompatible_qos(Entity.get_entity(reader), status)

            self._on_requested_incompatible_qos = _on_requested_incompatible_qos_fn(
                call
            )
            self._set_on_requested_incompatible_qos(
                self._ref, self._on_requested_incompatible_qos
            )

    def on_publication_matched(
        self,
        writer: "cyclonedds.pub.DataWriter",
        status: dds_c_t.publication_matched_status,
    ) -> None:
        pass

    def set_on_publication_matched(
        self,
        callable: Callable[
            ["cyclonedds.pub.DataWriter", dds_c_t.publication_matched_status], None
        ],
    ):
        self.on_publication_matched = callable
        if callable is None:
            self._set_on_publication_matched(self._ref, None)
            del self._set_functors["on_publication_matched"]
        else:
            self._set_functors["on_publication_matched"] = self.on_publication_matched

            def call(writer, status, arg):
                self.on_publication_matched(Entity.get_entity(writer), status)

            self._on_publication_matched = _on_publication_matched_fn(call)
            self._set_on_publication_matched(self._ref, self._on_publication_matched)

    def on_subscription_matched(
        self,
        reader: "cyclonedds.sub.DataReader",
        status: dds_c_t.subscription_matched_status,
    ) -> None:
        pass

    def set_on_subscription_matched(
        self,
        callable: Callable[
            ["cyclonedds.sub.DataReader", dds_c_t.subscription_matched_status], None
        ],
    ):
        self.on_subscription_matched = callable
        if callable is None:
            self._set_on_subscription_matched(self._ref, None)
            del self._set_functors["on_subscription_matched"]
        else:
            self._set_functors["on_subscription_matched"] = self.on_subscription_matched

            def call(reader, status, arg):
                self.on_subscription_matched(Entity.get_entity(reader), status)

            self._on_subscription_matched = _on_subscription_matched_fn(call)
            self._set_on_subscription_matched(self._ref, self._on_subscription_matched)

    @c_call("dds_create_listener")
    def _create_listener(self, arg: ct.c_void_p) -> dds_c_t.listener_p:
        pass

    @c_call("dds_reset_listener")
    def _reset_listener(self, listener: dds_c_t.listener_p) -> None:
        pass

    @c_call("dds_copy_listener")
    def _copy_listener(self, dst: dds_c_t.listener_p, src: dds_c_t.listener_p) -> None:
        pass

    @c_call("dds_merge_listener")
    def _merge_listener(self, dst: dds_c_t.listener_p, src: dds_c_t.listener_p) -> None:
        pass

    @c_call("dds_lset_inconsistent_topic")
    def _set_inconsistent_topic(
        self, listener: dds_c_t.listener_p, callback: _inconsistent_topic_fn
    ) -> None:
        pass

    @c_call("dds_lset_data_available")
    def _set_data_available(
        self, listener: dds_c_t.listener_p, callback: _data_available_fn
    ) -> None:
        pass

    @c_call("dds_lset_liveliness_lost")
    def _set_liveliness_lost(
        self, listener: dds_c_t.listener_p, callback: _liveliness_lost_fn
    ) -> None:
        pass

    @c_call("dds_lset_liveliness_changed")
    def _set_liveliness_changed(
        self, listener: dds_c_t.listener_p, callback: _liveliness_changed_fn
    ) -> None:
        pass

    @c_call("dds_lset_offered_deadline_missed")
    def _set_on_offered_deadline_missed(
        self, listener: dds_c_t.listener_p, callback: _offered_deadline_missed_fn
    ) -> None:
        pass

    @c_call("dds_lset_offered_incompatible_qos")
    def _set_on_offered_incompatible_qos(
        self, listener: dds_c_t.listener_p, callback: _offered_incompatible_qos_fn
    ) -> None:
        pass

    @c_call("dds_lset_data_on_readers")
    def _set_on_data_on_readers(
        self, listener: dds_c_t.listener_p, callback: _data_on_readers_fn
    ) -> None:
        pass

    @c_call("dds_lset_sample_lost")
    def _set_on_sample_lost(
        self, listener: dds_c_t.listener_p, callback: _on_sample_lost_fn
    ) -> None:
        pass

    @c_call("dds_lset_sample_rejected")
    def _set_on_sample_rejected(
        self, listener: dds_c_t.listener_p, callback: _on_sample_rejected_fn
    ) -> None:
        pass

    @c_call("dds_lset_requested_deadline_missed")
    def _set_on_requested_deadline_missed(
        self, listener: dds_c_t.listener_p, callback: _on_requested_deadline_missed_fn
    ) -> None:
        pass

    @c_call("dds_lset_requested_incompatible_qos")
    def _set_on_requested_incompatible_qos(
        self, listener: dds_c_t.listener_p, callback: _on_requested_incompatible_qos_fn
    ) -> None:
        pass

    @c_call("dds_lset_publication_matched")
    def _set_on_publication_matched(
        self, listener: dds_c_t.listener_p, callback: _on_publication_matched_fn
    ) -> None:
        pass

    @c_call("dds_lset_subscription_matched")
    def _set_on_subscription_matched(
        self, listener: dds_c_t.listener_p, callback: _on_subscription_matched_fn
    ) -> None:
        pass

    @c_call("dds_delete_listener")
    def _delete_listener(self, listener: dds_c_t.listener_p) -> None:
        pass


class SampleState:
    """SampleState constants for building condition masks. This class is static and
    there should never be a need to instantiate it. It operates on the state of
    a single sample.

    Attributes
    ----------
    Read: int
        Only consider samples that have already been read.
    NotRead: int
        Only consider unread samples.
    Any: int
        Ignore the read/unread state of samples.
    """

    Read: int = 1
    NotRead: int = 2
    Any: int = 3


class ViewState:
    """ViewState constants for building condition masks. This class is static and
    there should never be a need to instantiate it. It operates on the state of
    an instance.

    Attributes
    ----------
    New: int
        Only consider samples belonging to newly created instances.
    Old: int
        Only consider samples belonging to previously created instances.
    Any: int
        Ignore the fact whether instances are new or not.
    """

    New: int = 4
    Old: int = 8
    Any: int = 12


class InstanceState:
    """InstanceState constants for building condition masks. This class is static and
    there should never be a need to instantiate it. It operates on the state of
    an instance.

    Attributes
    ----------
    Alive: int
        Only consider samples belonging to an alive instance (it has alive writer(s))
    NotAliveDisposed: int
        Only consider samples belonging to an instance that is not alive because it was actively disposed.
    NotAliveNoWriters: int
        Only consider samples belonging to an instance that is not alive because it has no writers.
    Any: int
        Ignore the liveliness status of the instance.
    """

    Alive: int = 16
    NotAliveDisposed: int = 32
    NotAliveNoWriters: int = 64
    Any: int = 112


class DDSStatus:
    """DDSStatus contains constants to build status masks. It is static and should never
    need to be instantiated.

    Attributes
    ----------
    InconsistentTopic: int
    OfferedDeadlineMissed: int
    RequestedDeadlineMissed: int
    OfferedIncompatibleQos: int
    RequestedIncompatibleQos: int
    SampleLost: int
    SampleRejected: int
    DataOnReaders: int
    DataAvailable: int
    LivelinessLost: int
    LivelinessChanged: int
    PublicationMatched: int
    SubscriptionMatched: int
    All = (1 << 14) - 1
    """

    InconsistentTopic = 1 << 0
    OfferedDeadlineMissed = 1 << 1
    RequestedDeadlineMissed = 1 << 2
    OfferedIncompatibleQos = 1 << 3
    RequestedIncompatibleQos = 1 << 4
    SampleLost = 1 << 5
    SampleRejected = 1 << 6
    DataOnReaders = 1 << 7
    DataAvailable = 1 << 8
    LivelinessLost = 1 << 9
    LivelinessChanged = 1 << 10
    PublicationMatched = 1 << 11
    SubscriptionMatched = 1 << 12
    All: int = (1 << 13) - 1


class _Condition(Entity):
    """Utility class to implement common methods between Read and Queryconditions"""

    def get_mask(self) -> int:
        mask: ct.c_uint32 = ct.c_uint32()
        ret = self._get_mask(self._ref, ct.byref(mask))
        if ret == 0:
            return mask.value
        raise DDSException(ret, f"Occurred when obtaining the mask of {repr(self)}")

    def is_triggered(self) -> bool:
        ret = self._triggered(self._ref)
        if ret < 0:
            raise DDSException(
                ret, f"Occurred when checking if {repr(self)} was triggered"
            )
        return ret == 1

    triggered: bool = property(is_triggered)

    @c_call("dds_get_mask")
    def _get_mask(
        self, condition: dds_c_t.entity, mask: ct.POINTER(ct.c_uint32)
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_triggered")
    def _triggered(self, condition: dds_c_t.entity) -> dds_c_t.returnv:
        pass


class ReadCondition(_Condition):
    """Condition that triggers when new data is available to read according to the mask.
    Construct a mask using InstanceState, ViewState and SampleState.
    """

    def __init__(self, reader: "cyclonedds.sub.DataReader", mask: int) -> None:
        """Construct a ReadCondition."""
        self.reader = reader
        self.mask = mask
        super().__init__(self._create_readcondition(reader._ref, mask))

    @c_call("dds_create_readcondition")
    def _create_readcondition(
        self, reader: dds_c_t.entity, mask: ct.c_uint32
    ) -> dds_c_t.entity:
        pass


_querycondition_filter_fn = c_callable(ct.c_bool, [ct.c_void_p])


class QueryCondition(_Condition):
    """Condition that triggers when new data is available to read according to the mask.
    Construct a mask using InstanceState, ViewState and SampleState. Add a filter function
    that receives the sample and returns a boolean whether to accept or reject the sample.
    """

    def __init__(
        self,
        reader: "cyclonedds.sub.DataReader",
        mask: int,
        filter: Callable[[Any], bool],
    ) -> None:
        """Construct a QueryCondition."""
        self.reader = reader
        self.mask = mask
        self.filter = filter

        def call(sample_pt):
            try:
                sample_info = ct.cast(sample_pt, ct.POINTER(dds_c_t.sample_buffer))[0]
                array_type = ct.c_ubyte * sample_info.len
                array = ct.cast(sample_info.buf, ct.POINTER(array_type))
                contents = array.contents[:]
                data = self.reader._topic.data_type.deserialize(bytes(contents))
                return self.filter(data)
            except Exception:  # Block any python exception from going into C
                return False

        self._filter = _querycondition_filter_fn(call)
        super().__init__(self._create_querycondition(reader._ref, mask, self._filter))

    @c_call("dds_create_querycondition")
    def _create_querycondition(
        self,
        reader: dds_c_t.entity,
        mask: ct.c_uint32,
        filter: _querycondition_filter_fn,
    ) -> dds_c_t.entity:
        pass


class GuardCondition(Entity):
    """A GuardCondition is a manually triggered condition that can be added to a :class:`WaitSet<cyclonedds.core.WaitSet>`."""

    def __init__(self, domain_participant: "cyclonedds.domain.DomainParticipant"):
        """Initialize a GuardCondition

        Parameters
        ----------
        domain_participant: DomainParticipant
            The domain in which the GuardCondition should be active.
        """
        super().__init__(self._create_guardcondition(domain_participant._ref))

    def set(self, triggered: bool) -> None:
        """Set the status of the GuardCondition to triggered or untriggered.

        Parameters
        ----------
        triggered: bool
            Wether to trigger this condition.

        Returns
        -------
        None

        Raises
        ------
        DDSException
        """
        ret = self._set_guardcondition(self._ref, triggered)
        if ret < 0:
            raise DDSException(ret, f"Occurred when calling set on {repr(self)}")

    def read(self) -> bool:
        """Read the status of the GuardCondition.

        Returns
        ----------
        bool
            Wether this condition is triggered.

        Raises
        ------
        DDSException
        """
        triggered = ct.c_bool()
        ret = self._read_guardcondition(self._ref, ct.byref(triggered))
        if ret < 0:
            raise DDSException(ret, f"Occurred when calling read on {repr(self)}")
        return bool(triggered)

    def take(self) -> bool:
        """Take the status of the GuardCondition. If it is True it will be False on the next call.

        Returns
        ----------
        bool
            Whether this condition is triggered.

        Raises
        ------
        DDSException
        """
        triggered = ct.c_bool()
        ret = self._take_guardcondition(self._ref, ct.byref(triggered))
        if ret < 0:
            raise DDSException(ret, f"Occurred when calling read on {repr(self)}")
        return bool(triggered)

    @c_call("dds_create_guardcondition")
    def _create_guardcondition(self, participant: dds_c_t.entity) -> dds_c_t.entity:
        pass

    @c_call("dds_set_guardcondition")
    def _set_guardcondition(
        self, guardcond: dds_c_t.entity, triggered: ct.c_bool
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_read_guardcondition")
    def _read_guardcondition(
        self, guardcond: dds_c_t.entity, triggered: ct.POINTER(ct.c_bool)
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_take_guardcondition")
    def _take_guardcondition(
        self, guardcond: dds_c_t.entity, triggered: ct.POINTER(ct.c_bool)
    ) -> dds_c_t.returnv:
        pass


class WaitSet(Entity):
    """A WaitSet is a way to provide synchronous access to events happening in the DDS system. You can attach almost any kind
    of entity to a WaitSet and then perform a blocking wait on the waitset. When one or more of the entities in the waitset
    trigger the wait is unblocked. What a 'trigger' is depends on the type of entity, you can find out more in
    ``todo(DDS) triggers``.
    """

    def __init__(
        self, domain_participant: "cyclonedds.domain.DomainParticipant"
    ) -> None:
        """Make a new WaitSet. It starts of empty. An empty waitset will never trigger.

        Parameters
        ----------
        domain_participant: DomainParticipant
            The domain in which you want to make a WaitSet
        """
        super().__init__(self._create_waitset(domain_participant._ref))
        self.attached = []

    def __del__(self) -> None:
        for v in self.attached:
            self._waitset_detach(self._ref, v[0]._ref)
        super().__del__()

    def attach(self, entity: Entity) -> None:
        """Attach an entity to this WaitSet. This is a no-op if the entity was already attached.

        Parameters
        ----------
        entity: Entity
            The entity you wish to attach.

        Raises
        ------
        DDSException: When you try to attach a non-triggerable entity.
        """
        if self.is_attached(entity):
            return

        value_pt = ct.c_int()

        ret = self._waitset_attach(self._ref, entity._ref, ct.byref(value_pt))
        if ret < 0:
            raise DDSException(
                ret, f"Occurred when trying to attach {repr(entity)} to {repr(self)}"
            )
        self.attached.append((entity, value_pt))

    def detach(self, entity: Entity) -> None:
        """Detach an entity from this WaitSet. If it was not attach this is a no-op.
        Note that this operation is not atomic, a trigger for the detached entity could still occurr right
        after detaching it.

        Parameters
        ----------
        entity: Entity
            The entity you wish to attach

        """
        for i, v in enumerate(self.attached):
            if v[0] == entity:
                ret = self._waitset_detach(self._ref, entity._ref)
                if ret < 0:
                    raise DDSException(
                        ret,
                        f"Occurred when trying to attach {repr(entity)} to {repr(self)}",
                    )
                del self.attached[i]
                break

    def is_attached(self, entity: Entity) -> bool:
        """Check whether an entity is attached.

        Parameters
        ----------
        entity: Entity
            Check the attachment of this entity.
        """
        for v in self.attached:
            if v[0] == entity:
                return True
        return False

    def get_entities(self) -> List[Entity]:
        """Get all entities attached"""
        # Note: should spend some time on synchronisation. What if the waitset is used across threads?
        # That is probably a bad idea in python, but who is going to stop the user from doing it anyway...
        return [v[0] for v in self.attached]

    def wait(self, timeout: int) -> int:
        """Block execution and wait for one of the entities in this waitset to trigger.

        Parameters
        ----------
        timeout: int
            The maximum number of nanoseconds to block. Use the function :func:`duration<cyclonedds.util.duration>`
            to write that in a human readable format.

        Returns
        -------
        int
            The number of triggered entities. This will be 0 when a timeout occurred.
        """
        ret = self._waitset_wait(self._ref, None, 0, timeout)

        if ret >= 0:
            return ret

        raise DDSException(ret, f"Occurred while waiting in {repr(self)}")

    def wait_until(self, abstime: int) -> int:
        """Block execution and wait for one of the entities in this waitset to trigger.

        Parameters
        ----------
        abstime: int
            The absolute time in nanoseconds since the start of the program (TODO CONFIRM THIS)
            to block. Use the function :func:`duration<cyclonedds.util.duration>` to write that in
            a human readable format.

        Returns
        -------
        int
            The number of triggered entities. This will be 0 when a timeout occurred.
        """
        cs = (ct.c_void_p * len(self.attached))()
        pcs = ct.cast(cs, ct.c_void_p)
        ret = self._waitset_wait_until(
            self._ref, ct.byref(pcs), len(self.attached), abstime
        )

        if ret >= 0:
            return ret

        raise DDSException(ret, f"Occurred while waiting in {repr(self)}")

    def set_trigger(self, value: bool) -> None:
        """Manually trigger a WaitSet. It is unlikely you would need this.

        Parameters
        ----------
        value: bool
            The trigger value.
        """
        ret = self._waitset_set_trigger(self._ref, value)
        if ret < 0:
            raise DDSException(ret, f"Occurred when setting trigger in {repr(self)}")

    async def wait_async(self, timeout: Optional[int] = None) -> int:
        """Asynchronously wait for a WaitSet to trigger. Use in event-loop based applications.

        Parameters
        ----------
        timeout: int, Optional = None
            Maximum number of nanoseconds to wait before returning. By default this is infinity.
        """
        timeout = timeout or dds_infinity

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return await loop.run_in_executor(pool, self.wait, timeout)

    @c_call("dds_create_waitset")
    def _create_waitset(self, domain_participant: dds_c_t.entity) -> dds_c_t.entity:
        pass

    @c_call("dds_waitset_attach")
    def _waitset_attach(
        self, waitset: dds_c_t.entity, entity: dds_c_t.entity, x: dds_c_t.attach
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_waitset_detach")
    def _waitset_detach(
        self, waitset: dds_c_t.entity, entity: dds_c_t.entity
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_waitset_wait")
    def _waitset_wait(
        self,
        waitset: dds_c_t.entity,
        xs: ct.POINTER(dds_c_t.attach),
        nxs: ct.c_size_t,
        reltimeout: dds_c_t.duration,
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_waitset_wait_until")
    def _waitset_wait_until(
        self,
        waitset: dds_c_t.entity,
        xs: ct.POINTER(dds_c_t.attach),
        nxs: ct.c_size_t,
        abstimeout: dds_c_t.duration,
    ) -> dds_c_t.returnv:
        pass

    @c_call("dds_waitset_set_trigger")
    def _waitset_set_trigger(
        self, waitset: dds_c_t.entity, value: ct.c_bool
    ) -> dds_c_t.returnv:
        pass


__all__ = [
    "DDSException",
    "Entity",
    "Qos",
    "Policy",
    "Listener",
    "DDSStatus",
    "ViewState",
    "InstanceState",
    "SampleState",
    "ReadCondition",
    "QueryCondition",
    "GuardCondition",
    "WaitSet",
]
