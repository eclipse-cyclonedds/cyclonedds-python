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
from enum import Enum, auto
from weakref import WeakValueDictionary
from typing import Any, Callable, Dict, Optional, List, Sequence, Tuple, TYPE_CHECKING

from .internal import c_call, c_callable, dds_c_t, DDS


# The TYPE_CHECKING variable will always evaluate to False, incurring no runtime costs
# But the import here allows your static type checker to resolve fully qualified cyclonedds names
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
    DDS_RETCODE_OUT_OF_RESOURCES = -5  # When an operation fails because of a lack of resources
    DDS_RETCODE_NOT_ENABLED = -6  # When a configurable feature is not enabled
    DDS_RETCODE_IMMUTABLE_POLICY = -7  # When an attempt is made to modify an immutable policy
    DDS_RETCODE_INCONSISTENT_POLICY = -8  # When a policy is used with inconsistent values
    DDS_RETCODE_ALREADY_DELETED = -9  # When an attempt is made to delete something more than once
    DDS_RETCODE_TIMEOUT = -10  # When a timeout has occurred
    DDS_RETCODE_NO_DATA = -11  # When expected data is not provided
    DDS_RETCODE_ILLEGAL_OPERATION = -12  # When a function is called when it should not be
    DDS_RETCODE_NOT_ALLOWED_BY_SECURITY = -13  # When credentials are not enough to use the function

    error_message_mapping = {
        DDS_RETCODE_OK: ("DDS_RETCODE_OK", "Success"),
        DDS_RETCODE_ERROR: ("DDS_RETCODE_ERROR", "Non specific error"),
        DDS_RETCODE_UNSUPPORTED: ("DDS_RETCODE_UNSUPPORTED", "Feature unsupported"),
        DDS_RETCODE_BAD_PARAMETER: ("DDS_RETCODE_BAD_PARAMETER", "Bad parameter value"),
        DDS_RETCODE_PRECONDITION_NOT_MET: ("DDS_RETCODE_PRECONDITION_NOT_MET", "Precondition for operation not met"),
        DDS_RETCODE_OUT_OF_RESOURCES: ("DDS_RETCODE_OUT_OF_RESOURCES", "Operation failed because of a lack of resources"),
        DDS_RETCODE_NOT_ENABLED: ("DDS_RETCODE_NOT_ENABLED", "A configurable feature is not enabled"),
        DDS_RETCODE_IMMUTABLE_POLICY: ("DDS_RETCODE_IMMUTABLE_POLICY", "An attempt was made to modify an immutable policy"),
        DDS_RETCODE_INCONSISTENT_POLICY: ("DDS_RETCODE_INCONSISTENT_POLICY", "A policy with inconsistent values was used"),
        DDS_RETCODE_ALREADY_DELETED: ("DDS_RETCODE_ALREADY_DELETED", "An attempt was made to delete something more than once"),
        DDS_RETCODE_TIMEOUT: ("DDS_RETCODE_TIMEOUT", "A timeout has occurred"),
        DDS_RETCODE_NO_DATA: ("DDS_RETCODE_NO_DATA", "Expected data is not provided"),
        DDS_RETCODE_ILLEGAL_OPERATION: ("DDS_RETCODE_ILLEGAL_OPERATION", "A function was called when it should not be"),
        DDS_RETCODE_NOT_ALLOWED_BY_SECURITY:
            ("DDS_RETCODE_NOT_ALLOWED_BY_SECURITY", "Insufficient credentials supplied to use the function")
    }

    def __init__(self, code, *args, msg=None, **kwargs):
        self.code = code
        self.msg = msg or ""
        super().__init__(*args, **kwargs)

    def __str__(self) -> str:
        if self.code in self.error_message_mapping:
            msg = self.error_message_mapping[self.code]
            return f"[{msg[0]}] {msg[1]}. {self.msg}"
        return f"[DDSException] Got an unexpected error code '{self.code}'. {self.msg}"

    def __repr__(self) -> str:
        return str(self)


class DDSAPIException(Exception):
    """This exception is thrown when misuse of the Python API is detected that are not explicitly bound to
    any C API functions.

    Attributes
    ----------
    msg: str
        A human readable description of what went wrong.
    """

    def __init__(self, msg):
        self.msg = msg
        super().__init__()

    def __str__(self) -> str:
        return f"[DDSAPIException] {self.msg}"


class _QosReliability(Enum):
    BestEffort = 0
    Reliable = 1


class _QosDurability(Enum):
    Volatile = 0
    TransientLocal = 1
    Transient = 2
    Persistent = 3


class _QosHistory(Enum):
    KeepLast = 0
    KeepAll = 1


class _QosAccessScope(Enum):
    Instance = 0
    Topic = 1
    Group = 2


class _QosOwnership(Enum):
    Shared = 0
    Exclusive = 1


class _QosLiveliness(Enum):
    Automatic = 0
    ManualByParticipant = 1
    ManualByTopic = 2


class _QosDestinationOrder(Enum):
    ByReceptionTimestamp = 0
    BySourceTimestamp = 1


class _QosIgnoreLocal(Enum):
    Nothing = 0
    Participant = 1
    Process = 2


class _PolicyType(Enum):
    Reliability = auto()
    Durability = auto()
    History = auto()
    ResourceLimits = auto()
    PresentationAccessScope = auto()
    Lifespan = auto()
    Deadline = auto()
    LatencyBudget = auto()
    Ownership = auto()
    OwnershipStrength = auto()
    Liveliness = auto()
    TimeBasedFilter = auto()
    Partitions = auto()
    TransportPriority = auto()
    DestinationOrder = auto()
    WriterDataLifecycle = auto()
    ReaderDataLifecycle = auto()
    DurabilityService = auto()
    IgnoreLocal = auto()


class Policy:
    """The Policy class is fully static and should never need to be instantiated.

    See Also
    --------
    qoshowto: How to work with Qos and Policy, TODO.
    """
    class Reliability:
        """The Reliability Qos Policy

        Examples
        --------
        >>> Policy.Reliability.BestEffort(max_blocking_time=duration(seconds=1))
        >>> Policy.Reliability.Reliable(max_blocking_time=duration(seconds=1))
        """

        @staticmethod
        def BestEffort(max_blocking_time: int) -> Tuple[_PolicyType, Tuple[_QosReliability, int]]:
            """Use BestEffort reliability

            Parameters
            ----------
            max_blocking_time : int
                The number of nanoseconds the writer will bock when its history is full.
                Use the :func:`duration<cdds.util.duration>` function to avoid time calculation headaches.

            Returns
            -------
            Tuple[PolicyType, Any]
                The return type of this entity is not publicly specified.
            """
            return _PolicyType.Reliability, (_QosReliability.BestEffort, max_blocking_time)

        @staticmethod
        def Reliable(max_blocking_time: int) -> Tuple[_PolicyType, Tuple[_QosReliability, int]]:
            """Use Reliable reliability

            Parameters
            ----------
            max_blocking_time : int
                The number of nanoseconds the writer will bock when its history is full.
                Use the :func:`duration<cdds.util.duration>` function to avoid time calculation headaches.

            Returns
            -------
            Tuple[PolicyType, Any]
                The return type of this entity is not publicly specified.
            """
            return _PolicyType.Reliability, (_QosReliability.Reliable, max_blocking_time)

    class Durability:
        """ The Durability Qos Policy

        Examples
        --------
        >>> Policy.Durability.Volatile
        >>> Policy.Durability.TransientLocal
        >>> Policy.Durability.Transient
        >>> Policy.Durability.Persistent

        Attributes
        ----------
        Volatile:       Tuple[PolicyType, Any]
                        The type of this entity is not publicly specified.
        TransientLocal: Tuple[PolicyType, Any]
                        The type of this entity is not publicly specified.
        Transient:      Tuple[PolicyType, Any]
                        The type of this entity is not publicly specified.
        Persistent:     Tuple[PolicyType, Any]
                        The type of this entity is not publicly specified.
        """

        Volatile: Tuple[_PolicyType, _QosDurability] = (_PolicyType.Durability, _QosDurability.Volatile)
        TransientLocal: Tuple[_PolicyType, _QosDurability] = (_PolicyType.Durability, _QosDurability.TransientLocal)
        Transient: Tuple[_PolicyType, _QosDurability] = (_PolicyType.Durability, _QosDurability.Transient)
        Persistent: Tuple[_PolicyType, _QosDurability] = (_PolicyType.Durability, _QosDurability.Persistent)

    class History:
        """ The History Qos Policy

        Examples
        --------
        >>> Policy.History.KeepAll
        >>> Policy.History.KeepLast(amount=10)

        Attributes
        ----------
        KeepAll: Tuple[PolicyType, Any]
                 The type of this entity is not publicly specified.
        """

        KeepAll: Tuple[_PolicyType, Tuple[_QosHistory, int]] = (_PolicyType.History, (_QosHistory.KeepAll, 0))

        @staticmethod
        def KeepLast(amount: int) -> Tuple[_PolicyType, Tuple[_QosHistory, int]]:
            """
            Parameters
            ----------
            amount : int
                The amount of samples to keep in the history.

            Returns
            -------
            Tuple[PolicyType, Any]
                The type of this entity is not publicly specified.
            """
            return _PolicyType.History, (_QosHistory.KeepLast, amount)

    @staticmethod
    def ResourceLimits(max_samples: int, max_instances: int, max_samples_per_instance: int) \
            -> Tuple[_PolicyType, Tuple[int, int, int]]:
        """The ResourceLimits Qos Policy

        Examples
        --------
        >>> Policy.ResourceLimits(
        >>>     max_samples=10,
        >>>     max_instances=10,
        >>>     max_samples_per_instance=2
        >>> )

        Parameters
        ----------
        max_samples : int
            Max number of samples total.
        max_instances : int
            Max number of instances total.
        max_samples_per_instance : int
            Max number of samples per instance.

        Returns
        -------
        Tuple[PolicyType, Any]
            The type of this entity is not publicly specified.
        """
        return _PolicyType.ResourceLimits, (max_samples, max_instances, max_samples_per_instance)

    class PresentationAccessScope:
        """The Presentation Access Scope Qos Policy

        Examples
        --------
        >>> Policy.PresentationAccessScope.Instance(coherent_access=True, ordered_access=False)
        >>> Policy.PresentationAccessScope.Topic(coherent_access=True, ordered_access=False)
        >>> Policy.PresentationAccessScope.Group(coherent_access=True, ordered_access=False)
        """

        @staticmethod
        def Instance(coherent_access: bool, ordered_access: bool) -> Tuple[_PolicyType, Tuple[_QosAccessScope, bool, bool]]:
            """Use Instance Presentation Access Scope

            Parameters
            ----------
            coherent_access : bool
                Enable coherent access
            ordered_access : bool
                Enable ordered access

            Returns
            -------
            Tuple[PolicyType, Any]
                The type of this entity is not publicly specified.
            """

            return _PolicyType.PresentationAccessScope, (_QosAccessScope.Instance, coherent_access, ordered_access)

        @staticmethod
        def Topic(coherent_access: bool, ordered_access: bool) -> Tuple[_PolicyType, Tuple[_QosAccessScope, bool, bool]]:
            """Use Topic Presentation Access Scope

            Parameters
            ----------
            coherent_access : bool
                Enable coherent access
            ordered_access : bool
                Enable ordered access

            Returns
            -------
            Tuple[PolicyType, Any]
                The type of this entity is not publicly specified.
            """

            return _PolicyType.PresentationAccessScope, (_QosAccessScope.Topic, coherent_access, ordered_access)

        @staticmethod
        def Group(coherent_access: bool, ordered_access: bool) -> Tuple[_PolicyType, Tuple[_QosAccessScope, bool, bool]]:
            """Use Group Presentation Access Scope

            Parameters
            ----------
            coherent_access : bool
                Enable coherent access
            ordered_access : bool
                Enable ordered access

            Returns
            -------
            Tuple[PolicyType, Any]
                The type of this entity is not publicly specified.
            """

            return _PolicyType.PresentationAccessScope, (_QosAccessScope.Group, coherent_access, ordered_access)

    @staticmethod
    def Lifespan(lifespan: int) -> Tuple[_PolicyType, int]:
        """The Lifespan Qos Policy

        Examples
        --------
        >>> Policy.Lifespan(duration(seconds=2))

        Parameters
        ----------
        lifespan : int
            Expiration time relative to the source timestamp of a sample in nanoseconds.

        Returns
        -------
        Tuple[PolicyType, Any]
            The type of this entity is not publicly specified.
        """

        return _PolicyType.Lifespan, lifespan

    @staticmethod
    def Deadline(deadline: int) -> Tuple[_PolicyType, int]:
        """The Deadline Qos Policy

        Examples
        --------
        >>> Policy.Deadline(duration(seconds=2))

        Parameters
        ----------
        deadline : int
            Deadline of a sample in nanoseconds.

        Returns
        -------
        Tuple[PolicyType, Any]
            The type of this entity is not publicly specified.
        """

        return _PolicyType.Deadline, deadline

    @staticmethod
    def LatencyBudget(budget: int) -> Tuple[_PolicyType, int]:
        """The Latency Budget Qos Policy

        Examples
        --------
        >>> Policy.LatencyBudget(duration(seconds=2))

        Parameters
        ----------
        budget : int
            Latency budget in nanoseconds.

        Returns
        -------
        Tuple[PolicyType, Any]
            The type of this entity is not publicly specified.
        """

        return _PolicyType.LatencyBudget, budget

    class Ownership:
        """The Ownership Qos Policy

        Examples
        --------
        >>> Policy.Ownership.Shared
        >>> Policy.Ownership.Exclusive

        Attributes
        ----------
        Shared:    Tuple[PolicyType, Any]
                   The type of this entity is not publicly specified.
        Exclusive: Tuple[PolicyType, Any]
                   The type of this entity is not publicly specified.
        """

        Shared: Tuple[_PolicyType, _QosOwnership] = (_PolicyType.Ownership, _QosOwnership.Shared)
        Exclusive: Tuple[_PolicyType, _QosOwnership] = (_PolicyType.Ownership, _QosOwnership.Exclusive)

    @staticmethod
    def OwnershipStrength(strength: int) -> Tuple[_PolicyType, int]:
        """The Ownership Strength Qos Policy

        Examples
        --------
        >>> Policy.OwnershipStrength(2)

        Parameters
        ----------
        strength : int
            Ownership strength as integer.

        Returns
        -------
        Tuple[PolicyType, Any]
            The type of this entity is not publicly specified.
        """

        return _PolicyType.OwnershipStrength, strength

    class Liveliness:
        """The Liveliness Qos Policy

        Examples
        --------
        >>> Policy.Liveliness.Automatic(lease_duration=duration(seconds=10))
        >>> Policy.Liveliness.ManualByParticipant(lease_duration=duration(seconds=10))
        >>> Policy.Liveliness.ManualByTopic(lease_duration=duration(seconds=10))
        """

        @staticmethod
        def Automatic(lease_duration: int) -> Tuple[_PolicyType, Tuple[_QosLiveliness, int]]:
            """Use Automatic Liveliness

            Parameters
            ----------
            lease_duration: int
                The lease duration in nanoseconds. Use the helper function :func:`duration<cdds.util.duration>` to write
                the duration in a human readable format.

            Returns
            -------
            Tuple[PolicyType, Any]
                The type of this entity is not publicly specified.
            """

            return _PolicyType.Liveliness, (_QosLiveliness.Automatic, lease_duration)

        @staticmethod
        def ManualByParticipant(lease_duration: int) -> Tuple[_PolicyType, Tuple[_QosLiveliness, int]]:
            """Use ManualByParticipant Liveliness

            Parameters
            ----------
            lease_duration: int
                The lease duration in nanoseconds. Use the helper function :func:`duration<cdds.util.duration>` to write
                the duration in a human readable format.

            Returns
            -------
            Tuple[PolicyType, Any]
                The type of this entity is not publicly specified.
            """

            return _PolicyType.Liveliness, (_QosLiveliness.ManualByParticipant, lease_duration)

        @staticmethod
        def ManualByTopic(lease_duration: int) -> Tuple[_PolicyType, Tuple[_QosLiveliness, int]]:
            """Use ManualByTopic Liveliness

            Parameters
            ----------
            lease_duration: int
                The lease duration in nanoseconds. Use the helper function :func:`duration<cdds.util.duration>` to write
                the duration in a human readable format.

            Returns
            -------
            Tuple[PolicyType, Any]
                The type of this entity is not publicly specified.
            """

            return _PolicyType.Liveliness, (_QosLiveliness.ManualByTopic, lease_duration)

    @staticmethod
    def TimeBasedFilter(filter_fn: int) -> Tuple[_PolicyType, int]:
        """The TimeBasedFilter Qos Policy

        Examples
        --------
        >>> Policy.TimeBasedFilter(filter=duration(seconds=2))

        Parameters
        ----------
        filter : int
            Minimum time between samples in nanoseconds.  Use the helper function :func:`duration<cdds.util.duration>`
            to write the duration in a human readable format.

        Returns
        -------
        Tuple[PolicyType, Any]
            The type of this entity is not publicly specified.
        """

        return _PolicyType.TimeBasedFilter, filter_fn

    @staticmethod
    def Partitions(*partitions: List[str]) -> Tuple[_PolicyType, List[str]]:
        """The Partitions Qos Policy

        Examples
        --------
        >>> Policy.Partitions("partition_a", "partition_b", "partition_c")
        >>> Policy.Partitions(*[f"partition_{i}" for i in range(100)])

        Parameters
        ----------
        *partitions : str
            Each argument is a partition this Qos will be active in.

        Returns
        -------
        Tuple[PolicyType, Any]
            The type of this entity is not publicly specified.
        """

        return _PolicyType.Partitions, partitions

    @staticmethod
    def TransportPriority(priority: int) -> Tuple[_PolicyType, int]:
        return _PolicyType.TransportPriority, priority

    class DestinationOrder:
        ByReceptionTimestamp: Tuple[_PolicyType, _QosDestinationOrder] = \
            (_PolicyType.DestinationOrder, _QosDestinationOrder.ByReceptionTimestamp)
        BySourceTimestamp: Tuple[_PolicyType, _QosDestinationOrder] = \
            (_PolicyType.DestinationOrder, _QosDestinationOrder.BySourceTimestamp)

    @staticmethod
    def WriterDataLifecycle(autodispose: bool) -> Tuple[_PolicyType, bool]:
        return _PolicyType.WriterDataLifecycle, autodispose

    @staticmethod
    def ReaderDataLifecycle(autopurge_nowriter_samples_delay: int, autopurge_disposed_samples_delay: int) \
            -> Tuple[_PolicyType, Tuple[int, int]]:
        return _PolicyType.ReaderDataLifecycle, (autopurge_nowriter_samples_delay, autopurge_disposed_samples_delay)

    @staticmethod
    def DurabilityService(cleanup_delay: int, history: Tuple[_PolicyType, Tuple[_QosHistory, int]],
                          max_samples: int, max_instances: int, max_samples_per_instance) \
            -> Tuple[_PolicyType, Tuple[int, _QosHistory, int, int, int, int]]:
        assert (history[0] == _PolicyType.History)
        return _PolicyType.DurabilityService, (cleanup_delay, history[1][0], history[1][1],
                                               max_samples, max_instances, max_samples_per_instance)

    class IgnoreLocal:
        Nothing: Tuple[_PolicyType, _QosDestinationOrder] = (_PolicyType.IgnoreLocal, _QosIgnoreLocal.Nothing)
        Participant: Tuple[_PolicyType, _QosDestinationOrder] = (_PolicyType.IgnoreLocal, _QosIgnoreLocal.Participant)
        Process: Tuple[_PolicyType, _QosIgnoreLocal] = (_PolicyType.IgnoreLocal, _QosIgnoreLocal.Process)


class QosException(Exception):
    """This exception is thrown when you try to set a Qos with something that is not a Policy or other invalid usage
    of the Qos object"""

    def __init__(self, msg, *args, **kwargs):
        self.msg = msg
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"[Qos] {self.msg}"

    __repr__ = __str__


class Qos(DDS):
    _qosses = {}
    _attr_dispatch = {
        _PolicyType.Reliability: "set_reliability",
        _PolicyType.Durability: "set_durability",
        _PolicyType.History: "set_history",
        _PolicyType.ResourceLimits: "set_resource_limits",
        _PolicyType.PresentationAccessScope: "set_presentation_access_scope",
        _PolicyType.Lifespan: "set_lifespan",
        _PolicyType.Deadline: "set_deadline",
        _PolicyType.LatencyBudget: "set_latency_budget",
        _PolicyType.Ownership: "set_ownership",
        _PolicyType.OwnershipStrength: "set_ownership_strength",
        _PolicyType.Liveliness: "set_liveliness",
        _PolicyType.TimeBasedFilter: "set_time_based_filter",
        _PolicyType.Partitions: "set_partitions",
        _PolicyType.TransportPriority: "set_transport_priority",
        _PolicyType.DestinationOrder: "set_destination_order",
        _PolicyType.WriterDataLifecycle: "set_writer_data_lifecycle",
        _PolicyType.ReaderDataLifecycle: "set_reader_data_lifecycle",
        _PolicyType.DurabilityService: "set_durability_service",
        _PolicyType.IgnoreLocal: "set_ignore_local"
    }

    def __init__(self, *args, **kwargs):
        if "_reference" in kwargs:
            self._ref = kwargs["_reference"]
            del kwargs["_reference"]
            self.destructor = False
        else:
            super().__init__(self._create_qos())
            self._qosses[self._ref] = self
            self.destructor = True

        self._pre_alloc_data_pointers()

        for policy in args:
            if not policy or len(policy) < 2 or policy[0] not in self._attr_dispatch:
                raise QosException(f"Passed invalid argument to Qos: {policy}")
            getattr(self, self._attr_dispatch[policy[0]])(policy)

        for name, value in kwargs.items():
            setter = getattr(self, "set_" + name)
            setter(value)

    def __iadd__(self, policy: Sequence):
        if not policy or len(policy) < 2 or policy[0] not in self._attr_dispatch:
            raise QosException(f"Passed invalid argument to Qos: {policy}")
        getattr(self, self._attr_dispatch[policy[0]])(policy)
        return self

    @classmethod
    def get_qos(cls, qos_id: int):
        return cls._qosses.get(qos_id)

    def __del__(self):
        if self.destructor:
            self._delete_qos(self._ref)

    def __eq__(self, o: 'Qos') -> bool:
        return self._eq(self._ref, o._ref)

    def get_userdata(self) -> Tuple[ct.c_size_t, ct.c_void_p]:
        if not self._get_userdata(self._ref, ct.byref(self._gc_userdata_value), ct.byref(self._gc_userdata_size)):
            raise QosException("Userdata or Qos object invalid.")

        if self._gc_userdata_size == 0:
            return None, 0

        return self._gc_userdata_value, self._gc_userdata_value

    def get_userdata_as(self, _type: type) -> Any:
        if not self._get_userdata(self._ref, ct.byref(self._gc_userdata_value), ct.byref(self._gc_userdata_size)):
            raise QosException("Userdata or Qos object invalid.")

        if self._gc_userdata_size == 0:
            return None

        if ct.sizeof(_type) != self._gc_userdata_value:
            raise QosException("Could not decode userdata to struct.")

        struct = ct.cast(self._gc_userdata_value, ct.POINTER(_type))

        return struct[0]

    def get_topicdata(self) -> Tuple[ct.c_size_t, ct.c_void_p]:
        if not self._get_topicdata(self._ref, ct.byref(self._gc_topicdata_value), ct.byref(self._gc_topicdata_size)):
            raise QosException("topicdata or Qos object invalid.")

        if self._gc_topicdata_size == 0:
            return None, 0

        return self._gc_topicdata_value, self._gc_topicdata_value

    def get_topicdata_as(self, _type: type) -> Any:
        if not self._get_topicdata(self._ref, ct.byref(self._gc_topicdata_value), ct.byref(self._gc_topicdata_size)):
            raise QosException("topicdata or Qos object invalid.")

        if self._gc_topicdata_size == 0:
            return None

        if ct.sizeof(_type) != self._gc_topicdata_value:
            raise QosException("Could not decode topicdata to struct.")

        struct = ct.cast(self._gc_topicdata_value, ct.POINTER(_type))

        return struct[0]

    def get_groupdata(self) -> Tuple[ct.c_size_t, ct.c_void_p]:
        if not self._get_groupdata(self._ref, ct.byref(self._gc_groupdata_value), ct.byref(self._gc_groupdata_size)):
            raise QosException("groupdata or Qos object invalid.")

        if self._gc_groupdata_size == 0:
            return None, 0

        return self._gc_groupdata_value, self._gc_groupdata_value

    def get_groupdata_as(self, _type: type) -> Any:
        if not self._get_groupdata(self._ref, ct.byref(self._gc_groupdata_value), ct.byref(self._gc_groupdata_size)):
            raise QosException("groupdata or Qos object invalid.")

        if self._gc_groupdata_size == 0:
            return None

        if ct.sizeof(_type) != self._gc_groupdata_value:
            raise QosException("Could not decode groupdata to struct.")

        struct = ct.cast(self._gc_groupdata_value, ct.POINTER(_type))

        return struct[0]

    def get_durability(self) -> Tuple[_PolicyType, _QosDurability]:
        if not self._get_durability(self._ref, ct.byref(self._gc_durability)):
            raise QosException("Durability or Qos object invalid.")

        return _PolicyType.Durability, _QosDurability(self._gc_durability.value)

    def get_history(self) -> Tuple[_PolicyType, Tuple[_QosHistory, int]]:
        if not self._get_history(self._ref, ct.byref(self._gc_history), ct.byref(self._gc_history_depth)):
            raise QosException("History or Qos object invalid.")

        return _PolicyType.History, (_QosHistory(self._gc_history.value), self._gc_history_depth.value)

    def get_resource_limits(self) -> Tuple[_PolicyType, Tuple[int, int, int]]:
        if not self._get_resource_limits(self._ref, ct.byref(self._gc_max_samples),
                                         ct.byref(self._gc_max_instances),
                                         ct.byref(self._gc_max_samples_per_instance)):
            raise QosException("Resource limits or Qos object invalid.")

        return _PolicyType.ResourceLimits, (self._gc_max_samples.value, self._gc_max_instances.value,
                                            self._gc_max_samples_per_instance.value)

    def get_presentation_access_scope(self) -> Tuple[_PolicyType, Tuple[_QosAccessScope, bool, bool]]:
        if not self._get_presentation(self._ref, ct.byref(self._gc_access_scope),
                                      ct.byref(self._gc_coherent_access),
                                      ct.byref(self._gc_ordered_access)):
            raise QosException("Presentation or Qos object invalid.")

        return _PolicyType.PresentationAccessScope, (_QosAccessScope(self._gc_access_scope.value),
                                                     bool(self._gc_coherent_access),
                                                     bool(self._gc_ordered_access))

    def get_lifespan(self) -> Tuple[_PolicyType, int]:
        if not self._get_lifespan(self._ref, ct.byref(self._gc_lifespan)):
            raise QosException("Lifespan or Qos object invalid.")

        return _PolicyType.Lifespan, self._gc_lifespan.value

    def get_deadline(self) -> Tuple[_PolicyType, int]:
        if not self._get_deadline(self._ref, ct.byref(self._gc_deadline)):
            raise QosException("Deadline or Qos object invalid.")

        return _PolicyType.Deadline, self._gc_deadline.value

    def get_latency_budget(self) -> Tuple[_PolicyType, int]:
        if not self._get_latency_budget(self._ref, ct.byref(self._gc_latency_budget)):
            raise QosException("Deadline or Qos object invalid.")

        return _PolicyType.LatencyBudget, self._gc_latency_budget.value

    def get_ownership(self) -> Tuple[_PolicyType, _QosOwnership]:
        if not self._get_ownership(self._ref, ct.byref(self._gc_ownership)):
            raise QosException("Ownership or Qos object invalid.")

        return _PolicyType.Ownership, _QosOwnership(self._gc_ownership.value)

    def get_ownership_strength(self) -> Tuple[_PolicyType, int]:
        if not self._get_ownership_strength(self._ref, ct.byref(self._gc_ownership_strength)):
            raise QosException("Ownership strength or Qos object invalid.")

        return _PolicyType.OwnershipStrength, self._gc_ownership_strength.value

    def get_liveliness(self) -> Tuple[_PolicyType, Tuple[_QosLiveliness, int]]:
        if not self._get_liveliness(self._ref, ct.byref(self._gc_liveliness), ct.byref(self._gc_lease_duration)):
            raise QosException("Liveliness or Qos object invalid.")

        return _PolicyType.Liveliness, (_QosLiveliness(self._gc_liveliness.value), self._gc_lease_duration.value)

    def get_time_based_filter(self) -> Tuple[_PolicyType, int]:
        if not self._get_time_based_filter(self._ref, ct.byref(self._gc_time_based_filter)):
            raise QosException("Time Based Filter or Qos object invalid.")

        return _PolicyType.TimeBasedFilter, self._gc_time_based_filter.value

    def get_partitions(self) -> Tuple[_PolicyType, List[str]]:
        if not self._get_partitions(self._ref, ct.byref(self._gc_partition_num), ct.byref(self._gc_partition_names)):
            raise QosException("Partition or Qos object invalid.")

        names = [None] * self._gc_partition_num.value
        for i in range(self._gc_partition_num.value):
            names[i] = bytes(self._gc_partition_names[i]).decode()

        return _PolicyType.Partitions, tuple(names)

    def get_reliability(self) -> Tuple[_PolicyType, Tuple[_QosReliability, int]]:
        if not self._get_reliability(self._ref, ct.byref(self._gc_reliability), ct.byref(self._gc_max_blocking_time)):
            raise QosException("Reliability or Qos object invalid.")

        return _PolicyType.Reliability, (_QosReliability(self._gc_reliability.value), self._gc_max_blocking_time.value)

    def get_transport_priority(self) -> Tuple[_PolicyType, int]:
        if not self._get_transport_priority(self._ref, ct.byref(self._gc_transport_priority)):
            raise QosException("Transport Priority or Qos object invalid.")

        return _PolicyType.TransportPriority, self._gc_transport_priority.value

    def get_destination_order(self) -> Tuple[_PolicyType, _QosDestinationOrder]:
        if not self._get_destination_order(self._ref, ct.byref(self._gc_destination_order)):
            raise QosException("Destination Order or Qos object invalid.")

        return _PolicyType.DestinationOrder, _QosDestinationOrder(self._gc_destination_order.value)

    def get_writer_data_lifecycle(self) -> Tuple[_PolicyType, bool]:
        if not self._get_writer_data_lifecycle(self._ref, ct.byref(self._gc_writer_autodispose)):
            raise QosException("Writer Data Lifecycle or Qos object invalid.")

        return _PolicyType.WriterDataLifecycle, bool(self._gc_writer_autodispose)

    def get_reader_data_lifecycle(self) -> Tuple[_PolicyType, Tuple[int, int]]:
        if not self._get_reader_data_lifecycle(self._ref, ct.byref(self._gc_autopurge_nowriter_samples_delay),
                                               ct.byref(self._gc_autopurge_disposed_samples_delay)):
            raise QosException("Reader Data Lifecycle or Qos object invalid.")

        return _PolicyType.ReaderDataLifecycle, (self._gc_autopurge_nowriter_samples_delay.value,
                                                 self._gc_autopurge_disposed_samples_delay.value)

    def get_durability_service(self) -> Tuple[_PolicyType, Tuple[int, _QosHistory, int, int, int, int]]:
        if not self._get_durability_service(
                self._ref,
                ct.byref(self._gc_durservice_service_cleanup_delay),
                ct.byref(self._gc_durservice_history_kind),
                ct.byref(self._gc_durservice_history_depth),
                ct.byref(self._gc_durservice_max_samples),
                ct.byref(self._gc_durservice_max_instances),
                ct.byref(self._gc_durservice_max_samples_per_instance)):
            raise QosException("Durability Service or Qos object invalid.")

        return _PolicyType.DurabilityService, (
            self._gc_durservice_service_cleanup_delay.value,
            _QosHistory(self._gc_durservice_history_kind.value),
            self._gc_durservice_history_depth.value,
            self._gc_durservice_max_samples.value,
            self._gc_durservice_max_instances.value,
            self._gc_durservice_max_samples_per_instance.value
        )

    def get_ignore_local(self) -> Tuple[_PolicyType, _QosIgnoreLocal]:
        if not self._get_ignorelocal(self._ref, ct.byref(self._gc_ignorelocal)):
            raise QosException("Ignorelocal or Qos object invalid.")

        return _PolicyType.IgnoreLocal, _QosIgnoreLocal(self._gc_ignorelocal.value)

    def get_propnames(self) -> List[str]:
        if not self._get_propnames(self._ref, ct.byref(self._gc_propnames_num), ct.byref(self._gc_propnames_names)):
            raise QosException("Propnames or Qos object invalid.")

        names = [None] * self._gc_propnames_num
        for i in range(self._gc_propnames_num):
            names[i] = self._gc_propnames_names[0][i].encode()

        return names

    def get_prop(self, name: str) -> str:
        if not self._get_prop(self._ref, name.encode(), ct.byref(self._gc_prop_get_value)):
            raise QosException("Propname or Qos object invalid.")

        return bytes(self._gc_prop_get_value).decode()

    def get_bpropnames(self) -> List[str]:
        if not self._get_bpropnames(self._ref, ct.byref(self._gc_bpropnames_num), ct.byref(self._gc_bpropnames_names)):
            raise QosException("Propnames or Qos object invalid.")

        names = [None] * self._gc_bpropnames_num
        for i in range(self._gc_bpropnames_num):
            names[i] = self._gc_bpropnames_names[0][i].encode()

        return names

    def get_bprop(self, name: str) -> bytes:
        if not self._get_bprop(self._ref, name.encode(), ct.byref(self._gc_bprop_get_value)):
            raise QosException("Propname or Qos object invalid.")

        return bytes(self._gc_bprop_get_value)

    def set_userdata(self, value: ct.Structure) -> None:
        value_p = ct.cast(ct.byref(value), ct.c_void_p)
        self._set_userdata(self._ref, value_p, ct.sizeof(value))

    def set_topicdata(self, value: ct.Structure) -> None:
        value_p = ct.cast(ct.byref(value), ct.c_void_p)
        self._set_topicdata(self._ref, value_p, ct.sizeof(value))

    def set_groupdata(self, value: ct.Structure) -> None:
        value_p = ct.cast(ct.byref(value), ct.c_void_p)
        self._set_groupdata(self._ref, value_p, ct.sizeof(value))

    def set_durability(self, durability: Tuple[_PolicyType, _QosDurability]) -> None:
        assert(durability[0] == _PolicyType.Durability)
        self._set_durability(self._ref, durability[1].value)

    def set_history(self, history: Tuple[_PolicyType, Tuple[_QosHistory, int]]) -> None:
        assert(history[0] == _PolicyType.History)
        self._set_history(self._ref, history[1][0].value, history[1][1])

    def set_resource_limits(self, limits: Tuple[_PolicyType, Tuple[int, int, int]]) -> None:
        assert(limits[0] == _PolicyType.ResourceLimits)
        self._set_resource_limits(self._ref, *limits[1])

    def set_presentation_access_scope(self, presentation: Tuple[_PolicyType, Tuple[_QosAccessScope, bool, bool]]) -> None:
        assert(presentation[0] == _PolicyType.PresentationAccessScope)
        self._set_presentation_access_scope(self._ref, presentation[1][0].value, presentation[1][1], presentation[1][2])

    def set_lifespan(self, lifespan: Tuple[_PolicyType, int]) -> None:
        assert(lifespan[0] == _PolicyType.Lifespan)
        self._set_lifespan(self._ref, lifespan[1])

    def set_deadline(self, deadline: Tuple[_PolicyType, int]) -> None:
        assert(deadline[0] == _PolicyType.Deadline)
        self._set_deadline(self._ref, deadline[1])

    def set_latency_budget(self, latency_budget: Tuple[_PolicyType, int]) -> None:
        assert(latency_budget[0] == _PolicyType.LatencyBudget)
        self._set_latency_budget(self._ref, latency_budget[1])

    def set_ownership(self, ownership: Tuple[_PolicyType, _QosOwnership]) -> None:
        assert(ownership[0] == _PolicyType.Ownership)
        self._set_ownership(self._ref, ownership[1].value)

    def set_ownership_strength(self, strength: Tuple[_PolicyType, int]) -> None:
        assert(strength[0] == _PolicyType.OwnershipStrength)
        self._set_ownership_strength(self._ref, strength[1])

    def set_liveliness(self, liveliness: Tuple[_PolicyType, Tuple[_QosLiveliness, int]]) -> None:
        assert(liveliness[0] == _PolicyType.Liveliness)
        self._set_liveliness(self._ref, liveliness[1][0].value, liveliness[1][1])

    def set_time_based_filter(self, minimum_separation: Tuple[_PolicyType, int]) -> None:
        assert(minimum_separation[0] == _PolicyType.TimeBasedFilter)
        self._set_time_based_filter(self._ref, minimum_separation[1])

    def set_partitions(self, partitions: Tuple[_PolicyType, List[str]]) -> None:
        assert(partitions[0] == _PolicyType.Partitions)
        ps = [p.encode() for p in partitions[1]]
        p_pt = (ct.c_char_p * len(ps))()
        for i, p in enumerate(ps):
            p_pt[i] = p
        self._set_partitions(self._ref, len(ps), p_pt)

    def set_reliability(self, reliability: Tuple[_PolicyType, Tuple[_QosReliability, int]]) -> None:
        assert(reliability[0] == _PolicyType.Reliability)
        self._set_reliability(self._ref, reliability[1][0].value, reliability[1][1])

    def set_transport_priority(self, value: Tuple[_PolicyType, int]) -> None:
        assert(value[0] == _PolicyType.TransportPriority)
        self._set_transport_priority(self._ref, value[1])

    def set_destination_order(self, destination_order_kind: Tuple[_PolicyType, _QosDestinationOrder]) -> None:
        assert(destination_order_kind[0] == _PolicyType.DestinationOrder)
        self._set_destination_order(self._ref, destination_order_kind[1].value)

    def set_writer_data_lifecycle(self, autodispose: Tuple[_PolicyType, bool]) -> None:
        assert(autodispose[0] == _PolicyType.WriterDataLifecycle)
        self._set_writer_data_lifecycle(self._ref, autodispose[1])

    def set_reader_data_lifecycle(self, autopurge: Tuple[_PolicyType, Tuple[int, int]]) -> None:
        assert(autopurge[0] == _PolicyType.ReaderDataLifecycle)
        self._set_reader_data_lifecycle(self._ref, *autopurge[1])

    def set_durability_service(self, settings: Tuple[_PolicyType, Tuple[int, _QosHistory, int, int, int, int]]) -> None:
        assert(settings[0] == _PolicyType.DurabilityService)
        self._set_durability_service(
            self._ref, settings[1][0], settings[1][1].value, settings[1][2],
            settings[1][3], settings[1][4], settings[1][5]
        )

    def set_ignore_local(self, ignorelocal: Tuple[_PolicyType, _QosIgnoreLocal]) -> None:
        assert(ignorelocal[0] == _PolicyType.IgnoreLocal)
        self._set_ignore_local(self._ref, ignorelocal[1].value)

    def set_props(self, values: Dict[str, str]) -> None:
        for name, value in values.items():
            self.set_prop(name, value)

    def set_prop(self, name: str, value: str) -> None:
        self._set_prop(self._ref, name.encode(), value.encode())

    def unset_prop(self, name: str) -> None:
        self._unset_prop(self._ref, name.encode())

    def set_bprops(self, values: Dict[str, ct.Structure]) -> None:
        for name, value in values.items():
            self.set_bprop(name, value)

    def set_bprop(self, name: str, value: ct.Structure) -> None:
        self._set_bprop(self._ref, name.encode(), ct.cast(ct.byref(value), ct.c_void_p), ct.sizeof(value))

    def unset_bprop(self, name: str) -> None:
        self._unset_bprop(self._ref, name.encode())

    def _pre_alloc_data_pointers(self):
        self._gc_userdata_size = ct.c_size_t()
        self._gc_userdata_value = ct.c_void_p()
        self._gc_topicdata_size = ct.c_size_t()
        self._gc_topicdata_value = ct.c_void_p()
        self._gc_groupdata_size = ct.c_size_t()
        self._gc_groupdata_value = ct.c_void_p()
        self._gc_durability = dds_c_t.durability()
        self._gc_history = dds_c_t.history()
        self._gc_history_depth = ct.c_int32()
        self._gc_max_samples = ct.c_int32()
        self._gc_max_instances = ct.c_int32()
        self._gc_max_samples_per_instance = ct.c_int32()
        self._gc_access_scope = dds_c_t.presentation_access_scope()
        self._gc_coherent_access = ct.c_bool()
        self._gc_ordered_access = ct.c_bool()
        self._gc_lifespan = dds_c_t.duration()
        self._gc_deadline = dds_c_t.duration()
        self._gc_latency_budget = dds_c_t.duration()
        self._gc_ownership = dds_c_t.ownership()
        self._gc_ownership_strength = ct.c_int32()
        self._gc_liveliness = dds_c_t.liveliness()
        self._gc_lease_duration = dds_c_t.duration()
        self._gc_time_based_filter = dds_c_t.duration()
        self._gc_partition_num = ct.c_uint32()
        self._gc_partition_names = (ct.POINTER(ct.c_char_p))()
        self._gc_reliability = dds_c_t.reliability()
        self._gc_max_blocking_time = dds_c_t.duration()
        self._gc_transport_priority = ct.c_int32()
        self._gc_destination_order = dds_c_t.destination_order()
        self._gc_writer_autodispose = ct.c_bool()
        self._gc_autopurge_nowriter_samples_delay = dds_c_t.duration()
        self._gc_autopurge_disposed_samples_delay = dds_c_t.duration()
        self._gc_durservice_service_cleanup_delay = dds_c_t.duration()
        self._gc_durservice_history_kind = dds_c_t.history()
        self._gc_durservice_history_depth = ct.c_int32()
        self._gc_durservice_max_samples = ct.c_int32()
        self._gc_durservice_max_instances = ct.c_int32()
        self._gc_durservice_max_samples_per_instance = ct.c_int32()
        self._gc_ignorelocal = dds_c_t.ingnorelocal()
        self._gc_propnames_num = ct.c_uint32()
        self._gc_propnames_names = (ct.POINTER(ct.c_char_p))()
        self._gc_prop_get_value = ct.c_char_p()
        self._gc_bpropnames_num = ct.c_uint32()
        self._gc_bpropnames_names = (ct.POINTER(ct.c_char_p))()
        self._gc_bprop_get_value = ct.c_char_p()

    @c_call("dds_create_qos")
    def _create_qos(self) -> dds_c_t.qos_p:
        pass

    @c_call("dds_delete_qos")
    def _delete_qos(self, qos: dds_c_t.qos_p) -> None:
        pass

    @c_call("dds_qset_reliability")
    def _set_reliability(self, qos: dds_c_t.qos_p, reliability_kind: dds_c_t.reliability,
                         blocking_time: dds_c_t.duration) -> None:
        pass

    @c_call("dds_qset_durability")
    def _set_durability(self, qos: dds_c_t.qos_p, durability_kind: dds_c_t.durability) -> None:
        pass

    @c_call("dds_qset_userdata")
    def _set_userdata(self, qos: dds_c_t.qos_p, value: ct.c_void_p, size: ct.c_size_t) -> None:
        pass

    @c_call("dds_qset_topicdata")
    def _set_topicdata(self, qos: dds_c_t.qos_p, value: ct.c_void_p, size: ct.c_size_t) -> None:
        pass

    @c_call("dds_qset_groupdata")
    def _set_groupdata(self, qos: dds_c_t.qos_p, value: ct.c_void_p, size: ct.c_size_t) -> None:
        pass

    @c_call("dds_qset_history")
    def _set_history(self, qos: dds_c_t.qos_p, history_kind: dds_c_t.history, depth: ct.c_int32) -> None:
        pass

    @c_call("dds_qset_resource_limits")
    def _set_resource_limits(self, qos: dds_c_t.qos_p, max_samples: ct.c_int32, max_instances: ct.c_int32,
                             max_samples_per_instance: ct.c_int32) -> None:
        pass

    @c_call("dds_qset_presentation")
    def _set_presentation_access_scope(self, qos: dds_c_t.qos_p, access_scope: dds_c_t.presentation_access_scope,
                                       coherent_access: ct.c_bool, ordered_access: ct.c_bool) -> None:
        pass

    @c_call("dds_qset_lifespan")
    def _set_lifespan(self, qos: dds_c_t.qos_p, lifespan: dds_c_t.duration) -> None:
        pass

    @c_call("dds_qset_deadline")
    def _set_deadline(self, qos: dds_c_t.qos_p, deadline: dds_c_t.duration) -> None:
        pass

    @c_call("dds_qset_latency_budget")
    def _set_latency_budget(self, qos: dds_c_t.qos_p, latency_budget: dds_c_t.duration) -> None:
        pass

    @c_call("dds_qset_ownership")
    def _set_ownership(self, qos: dds_c_t.qos_p, ownership_kind: dds_c_t.ownership) -> None:
        pass

    @c_call("dds_qset_ownership_strength")
    def _set_ownership_strength(self, qos: dds_c_t.qos_p, ownership_strength: ct.c_int32) -> None:
        pass

    @c_call("dds_qset_liveliness")
    def _set_liveliness(self, qos: dds_c_t.qos_p, liveliness_kind: dds_c_t.liveliness,
                        lease_duration: dds_c_t.duration) -> None:
        pass

    @c_call("dds_qset_time_based_filter")
    def _set_time_based_filter(self, qos: dds_c_t.qos_p, minimum_separation: dds_c_t.duration) -> None:
        pass

    @c_call("dds_qset_partition1")
    def _set_partition(self, qos: dds_c_t.qos_p, name: ct.c_char_p) -> None:
        pass

    @c_call("dds_qset_partition")
    def _set_partitions(self, qos: dds_c_t.qos_p, n: ct.c_uint32, ps: ct.POINTER(ct.c_char_p)) -> None:
        pass

    @c_call("dds_qset_transport_priority")
    def _set_transport_priority(self, qos: dds_c_t.qos_p, value: ct.c_int32) -> None:
        pass

    @c_call("dds_qset_destination_order")
    def _set_destination_order(self, qos: dds_c_t.qos_p, destination_order_kind: dds_c_t.destination_order) -> None:
        pass

    @c_call("dds_qset_writer_data_lifecycle")
    def _set_writer_data_lifecycle(self, qos: dds_c_t.qos_p, autodispose: ct.c_bool) -> None:
        pass

    @c_call("dds_qset_reader_data_lifecycle")
    def _set_reader_data_lifecycle(self, qos: dds_c_t.qos_p, autopurge_nowriter_samples_delay: dds_c_t.duration,
                                   autopurge_disposed_samples_delay: dds_c_t.duration) -> None:
        pass

    @c_call("dds_qset_durability_service")
    def _set_durability_service(self, qos: dds_c_t.qos_p, service_cleanup_delay: dds_c_t.duration,
                                history_kind: dds_c_t.history, history_depth: ct.c_int32, max_samples: ct.c_int32,
                                max_instances: ct.c_int32, max_samples_per_instance: ct.c_int32) -> None:
        pass

    @c_call("dds_qset_ignorelocal")
    def _set_ignore_local(self, qos: dds_c_t.qos_p, ingorelocal_kind: dds_c_t.ingnorelocal) -> None:
        pass

    @c_call("dds_qset_prop")
    def _set_prop(self, qos: dds_c_t.qos_p, name: ct.c_char_p, value: ct.c_char_p) -> None:
        pass

    @c_call("dds_qunset_prop")
    def _unset_prop(self, qos: dds_c_t.qos_p, name: ct.c_char_p) -> None:
        pass

    @c_call("dds_qset_bprop")
    def _set_bprop(self, qos: dds_c_t.qos_p, name: ct.c_char_p, value: ct.c_void_p, size: ct.c_size_t) -> None:
        pass

    @c_call("dds_qunset_bprop")
    def _unset_bprop(self, qos: dds_c_t.qos_p, name: ct.c_char_p) -> None:
        pass

    @c_call("dds_qget_reliability")
    def _get_reliability(self, qos: dds_c_t.qos_p, reliability_kind: ct.POINTER(dds_c_t.reliability),
                         blocking_time: ct.POINTER(dds_c_t.duration)) -> bool:
        pass

    @c_call("dds_qget_durability")
    def _get_durability(self, qos: dds_c_t.qos_p, durability_kind: ct.POINTER(dds_c_t.durability)) -> bool:
        pass

    @c_call("dds_qget_userdata")
    def _get_userdata(self, qos: dds_c_t.qos_p, value: ct.POINTER(ct.c_void_p), size: ct.POINTER(ct.c_size_t)) -> bool:
        pass

    @c_call("dds_qget_topicdata")
    def _get_topicdata(self, qos: dds_c_t.qos_p, value: ct.POINTER(ct.c_void_p), size: ct.POINTER(ct.c_size_t)) -> bool:
        pass

    @c_call("dds_qget_groupdata")
    def _get_groupdata(self, qos: dds_c_t.qos_p, value: ct.POINTER(ct.c_void_p), size: ct.POINTER(ct.c_size_t)) -> bool:
        pass

    @c_call("dds_qget_history")
    def _get_history(self, qos: dds_c_t.qos_p, history_kind: ct.POINTER(dds_c_t.history),
                     depth: ct.POINTER(ct.c_int32)) -> bool:
        pass

    @c_call("dds_qget_resource_limits")
    def _get_resource_limits(self, qos: dds_c_t.qos_p, max_samples: ct.POINTER(ct.c_int32),
                             max_instances: ct.POINTER(ct.c_int32),
                             max_samples_per_instance: ct.POINTER(ct.c_int32)) -> bool:
        pass

    @c_call("dds_qget_presentation")
    def _get_presentation(self, qos: dds_c_t.qos_p, access_scope: ct.POINTER(dds_c_t.presentation_access_scope),
                          coherent_access: ct.POINTER(ct.c_bool), ordered_access: ct.POINTER(ct.c_bool)) -> bool:
        pass

    @c_call("dds_qget_lifespan")
    def _get_lifespan(self, qos: dds_c_t.qos_p, lifespan: ct.POINTER(dds_c_t.duration)) -> bool:
        pass

    @c_call("dds_qget_deadline")
    def _get_deadline(self, qos: dds_c_t.qos_p, deadline: ct.POINTER(dds_c_t.duration)) -> bool:
        pass

    @c_call("dds_qget_latency_budget")
    def _get_latency_budget(self, qos: dds_c_t.qos_p, latency_budget: ct.POINTER(dds_c_t.duration)) -> bool:
        pass

    @c_call("dds_qget_ownership")
    def _get_ownership(self, qos: dds_c_t.qos_p, ownership_kind: ct.POINTER(dds_c_t.ownership)) -> bool:
        pass

    @c_call("dds_qget_ownership_strength")
    def _get_ownership_strength(self, qos: dds_c_t.qos_p, strength: ct.POINTER(ct.c_int32)) -> bool:
        pass

    @c_call("dds_qget_liveliness")
    def _get_liveliness(self, qos: dds_c_t.qos_p, liveliness_kind: ct.POINTER(dds_c_t.liveliness),
                        lease_duration: ct.POINTER(dds_c_t.duration)) -> bool:
        pass

    @c_call("dds_qget_time_based_filter")
    def _get_time_based_filter(self, qos: dds_c_t.qos_p, minimum_separation: ct.POINTER(dds_c_t.duration)) -> bool:
        pass

    @c_call("dds_qget_partition")
    def _get_partitions(self, qos: dds_c_t.qos_p, n: ct.POINTER(ct.c_uint32), ps: ct.POINTER(ct.POINTER(ct.c_char_p))) -> bool:
        pass

    @c_call("dds_qget_transport_priority")
    def _get_transport_priority(self, qos: dds_c_t.qos_p, value: ct.POINTER(ct.c_int32)) -> bool:
        pass

    @c_call("dds_qget_destination_order")
    def _get_destination_order(self, qos: dds_c_t.qos_p,
                               destination_order_kind: ct.POINTER(dds_c_t.destination_order)) -> bool:
        pass

    @c_call("dds_qget_writer_data_lifecycle")
    def _get_writer_data_lifecycle(self, qos: dds_c_t.qos_p, autodispose: ct.POINTER(ct.c_bool)) -> bool:
        pass

    @c_call("dds_qget_reader_data_lifecycle")
    def _get_reader_data_lifecycle(self, qos: dds_c_t.qos_p,
                                   autopurge_nowriter_samples_delay: ct.POINTER(dds_c_t.duration),
                                   autopurge_disposed_samples_delay: ct.POINTER(dds_c_t.duration)) -> bool:
        pass

    @c_call("dds_qget_durability_service")
    def _get_durability_service(self, qos: dds_c_t.qos_p, service_cleanup_delay: ct.POINTER(dds_c_t.duration),
                                history_kind: ct.POINTER(dds_c_t.history), history_depth: ct.POINTER(ct.c_int32),
                                max_samples: ct.POINTER(ct.c_int32), max_instances: ct.POINTER(ct.c_int32),
                                max_samples_per_instance: ct.POINTER(ct.c_int32)) -> bool:
        pass

    @c_call("dds_qget_ignorelocal")
    def _get_ignorelocal(self, qos: dds_c_t.qos_p, ingorelocal_kind: ct.POINTER(dds_c_t.ingnorelocal)) -> bool:
        pass

    @c_call("dds_qget_prop")
    def _get_prop(self, qos: dds_c_t.qos_p, name: ct.POINTER(ct.c_char_p), value: ct.POINTER(ct.c_char_p)) -> bool:
        pass

    @c_call("dds_qget_bprop")
    def _get_bprop(self, qos: dds_c_t.qos_p, name: ct.POINTER(ct.c_char_p), value: ct.POINTER(ct.c_char_p)) -> bool:
        pass

    @c_call("dds_qget_propnames")
    def _get_propnames(self,  qos: dds_c_t.qos_p, size: ct.POINTER(ct.c_uint32),
                       names: ct.POINTER(ct.POINTER(ct.c_char_p))) -> bool:
        pass

    @c_call("dds_qget_bpropnames")
    def _get_bpropnames(self,  qos: dds_c_t.qos_p, size: ct.POINTER(ct.c_uint32),
                        names: ct.POINTER(ct.POINTER(ct.c_char_p))) -> bool:
        pass

    @c_call("dds_qos_equal")
    def _eq(self, qos_a: dds_c_t.qos_p, qos_b: dds_c_t.qos_p) -> bool:
        pass


class Entity(DDS):
    """
    Base class for all entities in the DDS API. The lifetime of the underlying
    DDS API object is linked to the lifetime of the Python entity object.

    Attributes
    ----------
    subscriber:  Subscriber, optional
                 If this entity is associated with a DataReader retrieve it.
                 It is read-only. This is a proxy for get_subscriber().
    publisher:   Publisher, optional
                 If this entity is associated with a Publisher retrieve it.
                 It is read-only. This is a proxy for get_publisher().
    datareader:  DataReader, optional
                 If this entity is associated with a DataReader retrieve it.
                 It is read-only. This is a proxy for get_datareader().
    guid:        uuid.UUID
                 Return the globally unique identifier for this entity.
                 It is read-only. This is a proxy for get_guid().
    status_mask: int
                 The status mask for this entity. It is a set of bits formed
                 from ``DDSStatus``. This is a proxy for get/set_status_mask().
    qos:         Qos
                 The quality of service policies for this entity. This is a
                 proxy for get/set_qos().
    listener:    Listener
                 The listener associated with this entity. This is a
                 proxy for get/set_listener().
    parent:      Entity, optional
                 The entity that is this entities parent. For example: the subscriber for a
                 datareader, the participant for a topic.
                 It is read-only. This is a proxy for get_parent().
    participant: DomainParticipant, optional
                 Get the participant for any entity, will only fail for a ``Domain``.
                 It is read-only. This is a proxy for get_participant().
    children:    List[Entity]
                 Get a list of children belonging to this entity. It is the opposite as ``parent``.
                 It is read-only. This is a proxy for get_children().
    domainid:    int
                 Get the id of the domain this entity belongs to.
    """

    _entities: Dict[dds_c_t.entity, 'Entity'] = WeakValueDictionary()

    def __init__(self, ref: int) -> None:
        """Initialize an Entity. You should never need to initialize an Entity manually.

        Parameters
        ----------
        ref: int
            The reference id as returned by the DDS API.

        Raises
        ------
        DDSException
            If an invalid reference id is passed to this function this means instantiation of some other object failed.
        """
        if ref < 0:
            raise DDSException(ref, f"Occurred upon initialisation of a {self.__class__.__module__}.{self.__class__.__name__}")
        super().__init__(ref)
        self._entities[self._ref] = self

    def __del__(self):
        if not hasattr(self, "_ref") or self._ref not in self._entities:
            return

        del self._entities[self._ref]
        self._delete(self._ref)

    def get_subscriber(self) -> Optional['cyclonedds.sub.Subscriber']:
        """Retrieve the subscriber associated with this entity.

        Returns
        -------
        Subscriber, optional
            Not all entities are associated with a subscriber, so this method may return None.

        Raises
        ------
        DDSException
        """
        ref = self._get_subscriber(self._ref)
        if ref >= 0:
            return self.get_entity(ref)
        raise DDSException(ref, f"Occurred when getting the subscriber for {repr(self)}")

    subscriber: 'cyclonedds.sub.Subscriber' = property(get_subscriber, doc=None)

    def get_publisher(self) -> Optional['cyclonedds.pub.Publisher']:
        """Retrieve the publisher associated with this entity.

        Returns
        -------
        Publisher, optional
            Not all entities are associated with a publisher, so this method may return None.

        Raises
        ------
        DDSException
        """
        ref = self._get_publisher(self._ref)
        if ref >= 0:
            return self.get_entity(ref)
        raise DDSException(ref, f"Occurred when getting the publisher for {repr(self)}")

    publisher: 'cyclonedds.sub.Publisher' = property(get_publisher)

    def get_datareader(self) -> Optional['cyclonedds.sub.DataReader']:
        """Retrieve the datareader associated with this entity.

        Returns
        -------
        DataReader, optional
            Not all entities are associated with a datareader, so this method may return None.

        Raises
        ------
        DDSException
        """
        ref = self._get_datareader(self._ref)
        if ref >= 0:
            return self.get_entity(ref)
        raise DDSException(ref, f"Occurred when getting the datareader for {repr(self)}")

    datareader: Optional['cyclonedds.sub.DataReader'] = property(get_datareader)

    def get_instance_handle(self) -> int:
        """Retrieve the instance associated with this entity.

        Returns
        -------
        int
            TODO: replace this with some mechanism for an Instance class

        Raises
        ------
        DDSException
        """
        handle = dds_c_t.instance_handle()
        ret = self._get_instance_handle(self._ref, ct.byref(handle))
        if ret == 0:
            return int(handle)
        raise DDSException(ret, f"Occurred when getting the instance handle for {repr(self)}")

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
        """Read the status bits set on this Entity. You can build a mask by using ``cdds.core.DDSStatus``.

        Parameters
        ----------
        mask : int, optional
            The ``DDSStatus`` mask. If not supplied the mask is used that was set on this Entity using set_status_mask.

        Returns
        -------
        int
            The `DDSStatus`` bits that were set.

        Raises
        ------
        DDSException
        """
        status = ct.c_uint32()
        ret = self._read_status(self._ref, ct.byref(status), ct.c_uint32(mask) if mask else self.get_status_mask())
        if ret == 0:
            return status.value
        raise DDSException(ret, f"Occurred when reading the status for {repr(self)}")

    def take_status(self, mask=None) -> int:
        """Take the status bits set on this Entity, after which they will be set to 0 again.
        You can build a mask by using ``cdds.core.DDSStatus``.

        Parameters
        ----------
        mask : int, optional
            The ``DDSStatus`` mask. If not supplied the mask is used that was set on this Entity using set_status_mask.

        Returns
        -------
        int
            The `DDSStatus`` bits that were set.

        Raises
        ------
        DDSException
        """
        status = ct.c_uint32()
        ret = self._take_status(self._ref, ct.byref(status), ct.c_uint32(mask) if mask else self.get_status_mask())
        if ret == 0:
            return status.value
        raise DDSException(ret, f"Occurred when taking the status for {repr(self)}")

    def get_status_changes(self) -> int:
        """Get all status changes since the last read_status() or take_status().

        Returns
        -------
        int
            The `DDSStatus`` bits that were set.

        Raises
        ------
        DDSException
        """
        status = ct.c_uint32()
        ret = self._get_status_changes(self._ref, ct.byref(status))
        if ret == 0:
            return status.value
        raise DDSException(ret, f"Occurred when getting the status changes for {repr(self)}")

    def get_status_mask(self) -> int:
        """Get the status mask for this Entity.

        Returns
        -------
        int
            The `DDSStatus`` bits that are enabled.

        Raises
        ------
        DDSException
        """
        mask = ct.c_uint32()
        ret = self._get_status_mask(self._ref, ct.byref(mask))
        if ret == 0:
            return mask.value
        raise DDSException(ret, f"Occurred when getting the status mask for {repr(self)}")

    def set_status_mask(self, mask: int) -> None:
        """Set the status mask for this Entity. By default the mask is 0. Only the status changes
            for the bits in this mask are tracked on this entity.

        Parameters
        ----------
        mask : int
            The ``DDSStatus`` bits to track.

        Raises
        ------
        DDSException
        """
        ret = self._set_status_mask(self._ref, ct.c_uint32(mask))
        if ret == 0:
            return
        raise DDSException(ret, f"Occurred when setting the status mask for {repr(self)}")

    status_mask = property(get_status_mask, set_status_mask)

    def get_qos(self) -> Qos:
        """Get the set of ``Qos`` policies associated with this entity. Note that the object returned is not
        the same python object that you used to set the ``Qos`` on this object. Modifications to the ``Qos`` object
        that is returned does _not_ modify the Qos of the Entity.

        Returns
        -------
        Qos
            The Qos policies associated with this entity.

        Raises
        ------
        DDSException
        """
        qos = Qos()
        ret = self._get_qos(self._ref, qos._ref)
        if ret == 0:
            return qos
        raise DDSException(ret, f"Occurred when getting the Qos Policies for {repr(self)}")

    def set_qos(self, qos: Qos) -> None:
        """Set ``Qos`` policies on this entity. Note, only a limited number of ``Qos`` policies can be set after
        the object is created (``Policy.LatencyBudget`` and ``Policy.OwnershipStrength``). Any policies not set
        explicitly in the supplied ``Qos`` remain.

        Parameters
        ----------
        qos : Qos
            The ``Qos`` to apply to this entity.

        Raises
        ------
        DDSException
            If you pass an immutable policy or cause the total collection of qos policies to become inconsistent
            an exception will be raised.
        """
        ret = self._set_qos(self._ref, qos._ref)
        if ret == 0:
            return
        raise DDSException(ret, f"Occurred when setting the Qos Policies for {repr(self)}")

    qos = property(get_qos, set_qos)

    def get_listener(self) -> 'Listener':
        """Return a listener associated with this object. Modifying the returned listener object does not modify
        this entity, you will have to call set_listener() with the changed object.

        Returns
        -------
        Listener
            A listener with which you can add additional callbacks.

        Raises
        ------
        DDSException
        """
        listener = Listener()
        ret = self._get_listener(self._ref, listener._ref)
        if ret == 0:
            return listener
        raise DDSException(ret, f"Occurred when getting the Listener for {repr(self)}")

    def set_listener(self, listener: 'Listener') -> None:
        """Set the listener for this object. If a listener already exist for this object only the fields you explicitly
        have set on your new listener are overwritten.

        Parameters
        ----------
        listener : Listener
            The listener object to use.

        Raises
        ------
        DDSException
        """
        ret = self._set_listener(self._ref, listener._ref)
        if ret == 0:
            return
        raise DDSException(ret, f"Occurred when setting the Listener for {repr(self)}")

    listener = property(get_listener, set_listener)

    def get_parent(self) -> Optional['Entity']:
        """Get the parent entity associated with this entity. A ``Domain`` object is the only object without parent,
        but if the domain is not created through the Python API this call won't find it
        and return None from the DomainParticipant.

        Returns
        -------
        Entity, optional
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

    parent = property(get_parent)

    def get_participant(self) -> Optional['cyclonedds.domain.DomainParticipant']:
        """Get the domain participant for this entity. This should work on all valid Entity objects except a Domain.

        Returns
        -------
        DomainParticipant, optional
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

        raise DDSException(ret, f"Occurred when getting the participant of {repr(self)}")

    participant = property(get_participant)

    def get_children(self) -> List['Entity']:
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
            raise DDSException(num_children, f"Occurred when getting the number of children of {repr(self)}")
        if num_children == 0:
            return []

        children_list = (dds_c_t.entity * int(num_children))()
        children_list_pt = ct.cast(children_list, ct.POINTER(dds_c_t.entity))

        ret = self._get_children(self._ref, children_list_pt, num_children)
        if ret >= 0:
            return [self.get_entity(children_list[i]) for i in range(ret)]

        raise DDSException(ret, f"Occurred when getting the children of {repr(self)}")

    children = property(get_children)

    def get_domainid(self) -> int:
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

    domainid = property(get_domainid)

    @classmethod
    def get_entity(cls, entity_id) -> Optional['Entity']:
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
    def _get_instance_handle(self, entity: dds_c_t.entity, handle: ct.POINTER(dds_c_t.instance_handle)) \
            -> dds_c_t.returnv:
        pass

    @c_call("dds_get_guid")
    def _get_guid(self, entity: dds_c_t.entity, guid: ct.POINTER(dds_c_t.guid)) -> dds_c_t.returnv:
        pass

    @c_call("dds_read_status")
    def _read_status(self, entity: dds_c_t.entity, status: ct.POINTER(ct.c_uint32), mask: ct.c_uint32) \
            -> dds_c_t.returnv:
        pass

    @c_call("dds_take_status")
    def _take_status(self, entity: dds_c_t.entity, status: ct.POINTER(ct.c_uint32), mask: ct.c_uint32) \
            -> dds_c_t.returnv:
        pass

    @c_call("dds_get_status_changes")
    def _get_status_changes(self, entity: dds_c_t.entity, status: ct.POINTER(ct.c_uint32)) \
            -> dds_c_t.returnv:
        pass

    @c_call("dds_get_status_mask")
    def _get_status_mask(self, entity: dds_c_t.entity, mask: ct.POINTER(ct.c_uint32)) \
            -> dds_c_t.returnv:
        pass

    @c_call("dds_set_status_mask")
    def _set_status_mask(self, entity: dds_c_t.entity, mask: ct.c_uint32) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_qos")
    def _get_qos(self, entity: dds_c_t.entity, qos: dds_c_t.qos_p) -> dds_c_t.returnv:
        pass

    @c_call("dds_set_qos")
    def _set_qos(self, entity: dds_c_t.entity, qos: dds_c_t.qos_p) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_listener")
    def _get_listener(self, entity: dds_c_t.entity, listener: dds_c_t.listener_p) -> dds_c_t.returnv:
        pass

    @c_call("dds_set_listener")
    def _set_listener(self, entity: dds_c_t.entity, listener: dds_c_t.listener_p) -> dds_c_t.returnv:
        pass

    @c_call("dds_get_parent")
    def _get_parent(self, entity: dds_c_t.entity) -> dds_c_t.entity:
        pass

    @c_call("dds_get_participant")
    def _get_participant(self, entity: dds_c_t.entity) -> dds_c_t.entity:
        pass

    @c_call("dds_get_children")
    def _get_children(self, entity: dds_c_t.entity, children_list: ct.POINTER(dds_c_t.returnv), size: ct.c_size_t) \
            -> dds_c_t.returnv:
        pass

    @c_call("dds_get_domainid")
    def _get_domainid(self, entity: dds_c_t.entity, domainid: ct.POINTER(dds_c_t.domainid)) -> dds_c_t.returnv:
        pass

    def __repr__(self) -> str:
        ref = None
        try:
            ref = self._ref
        except Exception:
            pass
        return f"<Entity, type={self.__class__.__module__}.{self.__class__.__name__}, addr={hex(id(self))}, id={ref}>"


_inconsistent_topic_fn = c_callable(None, [dds_c_t.entity, dds_c_t.inconsistent_topic_status, ct.c_void_p])
_data_available_fn = c_callable(None, [dds_c_t.entity, ct.c_void_p])
_liveliness_lost_fn = c_callable(None, [dds_c_t.entity, dds_c_t.liveliness_lost_status, ct.c_void_p])
_liveliness_changed_fn = c_callable(None, [dds_c_t.entity, dds_c_t.liveliness_changed_status, ct.c_void_p])
_offered_deadline_missed_fn = c_callable(None, [dds_c_t.entity, dds_c_t.offered_deadline_missed_status, ct.c_void_p])


def _is_override(func):
    obj = func.__self__
    if type(obj) == Listener:
        return False
    prntM = getattr(super(type(obj), obj), func.__name__)

    return func.__func__ != prntM.__func__


class Listener(DDS):
    def __init__(self, **kwargs):
        super().__init__(self._create_listener(None))

        if _is_override(self.on_data_available):
            self.set_on_data_available(self.on_data_available)

        if _is_override(self.on_inconsistent_topic):
            self.set_on_inconsistent_topic(self.on_inconsistent_topic)

        if _is_override(self.on_liveliness_lost):
            self.set_on_liveliness_lost(self.on_liveliness_lost)

        if _is_override(self.on_liveliness_changed):
            self.set_on_liveliness_changed(self.on_liveliness_changed)

        if _is_override(self.on_offered_deadline_missed):
            self.set_on_offered_deadline_missed(self.on_offered_deadline_missed)

        self.setters = {
            "on_data_available": self.set_on_data_available,
            "on_inconsistent_topic": self.set_on_inconsistent_topic,
            "on_liveliness_lost": self.set_on_liveliness_lost,
            "on_liveliness_changed": self.set_on_liveliness_changed,
            "on_offered_deadline_missed": self.set_on_offered_deadline_missed
        }

        for name, value in kwargs.items():
            if name not in self.setters:
                raise DDSAPIException(f"Invalid listener attribute '{name}'")
            self.setters[name](value)

    def __del__(self):
        self._delete_listener(self._ref)

    def reset(self) -> None:
        self._reset_listener(self._ref)

    def copy(self) -> 'Listener':
        listener = Listener()
        self._copy_listener(listener._ref, self._ref)
        return listener

    def copy_to(self, listener: 'Listener') -> None:
        self._copy_listener(listener._ref, self._ref)

    def merge(self, listener: 'Listener') -> None:
        self._merge_listener(self._ref, listener._ref)

    def on_inconsistent_topic(self, reader: 'cyclonedds.sub.DataReader', status: dds_c_t.inconsistent_topic_status) -> None:
        pass

    def set_on_inconsistent_topic(self, callable_fn: Callable[['cyclonedds.sub.DataReader'], None]):
        self.on_inconsistent_topic = callable_fn
        if callable_fn is None:
            self._set_inconsistent_topic(self._ref, None)
        else:
            def call(topic, status, arg):
                self.on_inconsistent_topic(Entity.get_entity(topic), status)
            self._on_inconsistent_topic = _inconsistent_topic_fn(call)
            self._set_inconsistent_topic(self._ref, self._on_inconsistent_topic)

    def on_data_available(self, reader: 'cyclonedds.sub.DataReader') -> None:
        pass

    def set_on_data_available(self, callable_fn: Callable[['cyclonedds.sub.DataReader'], None]):
        self.on_data_available = callable_fn
        if callable_fn is None:
            self._set_data_available(self._ref, None)
        else:
            def call(reader, arg):
                self.on_data_available(Entity.get_entity(reader))
            self._on_data_available = _data_available_fn(call)
            self._set_data_available(self._ref, self._on_data_available)

    def on_liveliness_lost(self, writer: 'cyclonedds.pub.DataWriter', status: dds_c_t.liveliness_lost_status) -> None:
        pass

    def set_on_liveliness_lost(self, callable: Callable[['cyclonedds.pub.DataWriter', dds_c_t.liveliness_lost_status], None]):
        self.on_liveliness_lost = callable
        if callable is None:
            self._set_liveliness_lost(self._ref, None)
        else:
            def call(writer, status, arg):
                self.on_liveliness_lost(Entity.get_entity(writer), status)
            self._on_liveliness_lost = _liveliness_lost_fn(call)
            self._set_liveliness_lost(self._ref, self._on_liveliness_lost)

    def on_liveliness_changed(self, reader: 'cyclonedds.sub.DataReader', status: dds_c_t.liveliness_changed_status) -> None:
        pass

    def set_on_liveliness_changed(
            self,
            callable: Callable[['cyclonedds.sub.DataReader', dds_c_t.liveliness_changed_status], None]):
        self.on_liveliness_changed = callable
        if callable is None:
            self._set_liveliness_changed(self._ref, None)
        else:
            def call(reader, status, arg):
                self.on_liveliness_changed(Entity.get_entity(reader), status)
            self._on_liveliness_changed = _liveliness_changed_fn(call)
            self._set_liveliness_changed(self._ref, self._on_liveliness_changed)

    def on_offered_deadline_missed(self,
                                   writer: 'cyclonedds.sub.DataWriter',
                                   status: dds_c_t.offered_deadline_missed_status) -> None:
        pass

    def set_on_offered_deadline_missed(self, callable: Callable[['cyclonedds.sub.DataWriter',
                                                                 dds_c_t.offered_deadline_missed_status], None]):
        self.on_offered_deadline_missed = callable
        if callable is None:
            self._set_on_offered_deadline_missed(self._ref, None)
        else:
            def call(writer, status, arg):
                self.on_offered_deadline_missed(Entity.get_entity(writer), status)
            self._on_offered_deadline_missed = _offered_deadline_missed_fn(call)
            self._set_on_offered_deadline_missed(self._ref, self._on_offered_deadline_missed)

    # TODO: on_offered_incompatible_qos
    # TODO: on_data_on_readers
    # TODO: on_sample_lost
    # TODO: on_sample_rejected
    # TODO: on_requested_deadline_missed
    # TODO: on_requested_incompatible_qos
    # TODO: on_publication_matched
    # TODO: on_subscription_matched

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
    def _set_inconsistent_topic(self, listener: dds_c_t.listener_p, callback: _inconsistent_topic_fn) -> None:
        pass

    @c_call("dds_lset_data_available")
    def _set_data_available(self, listener: dds_c_t.listener_p, callback: _data_available_fn) -> None:
        pass

    @c_call("dds_lset_liveliness_lost")
    def _set_liveliness_lost(self, listener: dds_c_t.listener_p, callback: _liveliness_lost_fn) -> None:
        pass

    @c_call("dds_lset_liveliness_changed")
    def _set_liveliness_changed(self, listener: dds_c_t.listener_p, callback: _liveliness_changed_fn) -> None:
        pass

    @c_call("dds_lset_offered_deadline_missed")
    def _set_on_offered_deadline_missed(self, listener: dds_c_t.listener_p, callback: _offered_deadline_missed_fn) -> None:
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

    InconsistentTopic = 1 << 1
    OfferedDeadlineMissed = 1 << 2
    RequestedDeadlineMissed = 1 << 3
    OfferedIncompatibleQos = 1 << 4
    RequestedIncompatibleQos = 1 << 5
    SampleLost = 1 << 6
    SampleRejected = 1 << 7
    DataOnReaders = 1 << 8
    DataAvailable = 1 << 9
    LivelinessLost = 1 << 10
    LivelinessChanged = 1 << 11
    PublicationMatched = 1 << 12
    SubscriptionMatched = 1 << 13
    All = (1 << 14) - 1


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
            raise DDSException(ret, f"Occurred when checking if {repr(self)} was triggered")
        return ret == 1

    triggered: bool = property(is_triggered)

    @c_call("dds_get_mask")
    def _get_mask(self, condition: dds_c_t.entity, mask: ct.POINTER(ct.c_uint32)) -> dds_c_t.returnv:
        pass

    @c_call("dds_triggered")
    def _triggered(self, condition: dds_c_t.entity) -> dds_c_t.returnv:
        pass


class ReadCondition(_Condition):
    def __init__(self, reader: 'cyclonedds.sub.DataReader', mask: int) -> None:
        self.reader = reader
        self.mask = mask
        super().__init__(self._create_readcondition(reader._ref, mask))

    @c_call("dds_create_readcondition")
    def _create_readcondition(self, reader: dds_c_t.entity, mask: ct.c_uint32) -> dds_c_t.entity:
        pass


_querycondition_filter_fn = c_callable(ct.c_bool, [ct.c_void_p])


class QueryCondition(_Condition):
    def __init__(self, reader: 'cyclonedds.sub.DataReader', mask: int, filter: Callable[[Any], bool]) -> None:
        self.reader = reader
        self.mask = mask
        self.filter = filter

        def call(sample_pt):
            try:
                return self.filter(ct.cast(sample_pt, ct.POINTER(reader.topic.data_type))[0])
            except Exception:  # Block any python exception from going into C
                return False

        self._filter = _querycondition_filter_fn(call)
        super().__init__(self._create_querycondition(reader._ref, mask, self._filter))

    @c_call("dds_create_querycondition")
    def _create_querycondition(self, reader: dds_c_t.entity, mask: ct.c_uint32, filter: _querycondition_filter_fn) \
            -> dds_c_t.entity:
        pass


class GuardCondition(Entity):
    """ A GuardCondition is a manually triggered condition that can be added to a :class:`WaitSet<cyclonedds.core.WaitSet>`."""

    def __init__(self, domain_participant: 'cyclonedds.domain.DomainParticipant'):
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
    def _set_guardcondition(self, guardcond: dds_c_t.entity, triggered: ct.c_bool) -> dds_c_t.returnv:
        pass

    @c_call("dds_read_guardcondition")
    def _read_guardcondition(self, guardcond: dds_c_t.entity, triggered: ct.POINTER(ct.c_bool)) -> dds_c_t.returnv:
        pass

    @c_call("dds_take_guardcondition")
    def _take_guardcondition(self, guardcond: dds_c_t.entity, triggered: ct.POINTER(ct.c_bool)) -> dds_c_t.returnv:
        pass


class WaitSet(Entity):
    """A WaitSet is a way to provide synchronous access to events happening in the DDS system. You can attach almost any kind
    of entity to a WaitSet and then perform a blocking wait on the waitset. When one or more of the entities in the waitset
    trigger the wait is unblocked. What a 'trigger' is depends on the type of entity, you can find out more in
    ``todo(DDS) triggers``.
    """
    def __init__(self, domain_participant: 'cyclonedds.domain.DomainParticipant'):
        """Make a new WaitSet. It starts of empty. An empty waitset will never trigger.

        Parameters
        ----------
        domain_participant: DomainParticipant
            The domain in which you want to make a WaitSet
        """

        super().__init__(self._create_waitset(domain_participant._ref))
        self.attached = []

    def __del__(self):
        for v in self.attached:
            self._waitset_detach(self._ref, v[0]._ref)
        super().__del__()

    def attach(self, entity: Entity) -> None:
        """Attach an entity to this WaitSet. This is a no-op if the entity was already attached.

        Parameters
        ----------
        entity: Entity
            The entity you wish to attach.

        Returns
        -------
        None

        Raises
        ------
        DDSException: When you try to attach a non-triggerable entity.
        """

        if self.is_attached(entity):
            return

        value_pt = ct.c_int()

        ret = self._waitset_attach(self._ref, entity._ref, ct.byref(value_pt))
        if ret < 0:
            raise DDSException(ret, f"Occurred when trying to attach {repr(entity)} to {repr(self)}")
        self.attached.append((entity, value_pt))

    def detach(self, entity: Entity) -> None:
        """Detach an entity from this WaitSet. If it was not attach this is a no-op.
        Note that this operation is not atomic, a trigger for the detached entity could still occurr right
        after detaching it.

        Parameters
        ----------
        entity: Entity
            The entity you wish to attach

        Returns
        -------
        None
        """

        for i, v in enumerate(self.attached):
            if v[0] == entity:
                ret = self._waitset_detach(self._ref, entity._ref)
                if ret < 0:
                    raise DDSException(ret, f"Occurred when trying to attach {repr(entity)} to {repr(self)}")
                del self.attached[i]
                break

    def is_attached(self, entity: Entity) -> bool:
        """Check whether an entity is attached.

        Parameters
        ----------
        entity: Entity
            Check the attachment of this entity.

        Returns
        -------
        bool
            Whether this entity is attached
        """

        for v in self.attached:
            if v[0] == entity:
                return True
        return False

    def get_entities(self):
        """Get all the attached entities

        Returns
        -------
        List[Entity]
            The attached entities
        """
        # Note: should spend some time on synchronisation. What if the waitset is used across threads?
        # That is probably a bad idea in python, but who is going to stop the user from doing it anyway...
        return [v[0] for v in self.attached]

    def wait(self, timeout: int) -> int:
        """Block execution and wait for one of the entities in this waitset to trigger.

        Parameters
        ----------
        timeout: int
            The maximum number of nanoseconds to block. Use the function :func:`duration<cdds.util.duration>`
            to write that in a human readable format.

        Returns
        -------
        int
            The number of triggered entities. This will be 0 when a timeout occurred.
        """

        cs = (ct.c_void_p * len(self.attached))()
        pcs = ct.cast(cs, ct.c_void_p)
        ret = self._waitset_wait(self._ref, ct.byref(pcs), len(self.attached), timeout)

        if ret >= 0:
            return ret

        raise DDSException(ret, f"Occurred while waiting in {repr(self)}")

    def wait_until(self, abstime: int):
        """Block execution and wait for one of the entities in this waitset to trigger.

        Parameters
        ----------
        abstime: int
            The absolute time in nanoseconds since the start of the program (TODO CONFIRM THIS)
            to block. Use the function :func:`duration<cdds.util.duration>` to write that in
            a human readable format.

        Returns
        -------
        int
            The number of triggered entities. This will be 0 when a timeout occurred.
        """

        cs = (ct.c_void_p * len(self.attached))()
        pcs = ct.cast(cs, ct.c_void_p)
        ret = self._waitset_wait_until(self._ref, ct.byref(pcs), len(self.attached), abstime)

        if ret >= 0:
            return ret

        raise DDSException(ret, f"Occurred while waiting in {repr(self)}")

    def set_trigger(self, value: bool) -> None:
        """Manually trigger a WaitSet. It is unlikely you would need this.

        Parameters
        ----------
        value: bool
            The trigger value.

        Returns
        -------
        None
        """
        ret = self._waitset_set_trigger(self._ref, value)
        if ret < 0:
            raise DDSException(ret, f"Occurred when setting trigger in {repr(self)}")

    @c_call("dds_create_waitset")
    def _create_waitset(self, domain_participant: dds_c_t.entity) -> dds_c_t.entity:
        pass

    @c_call("dds_waitset_attach")
    def _waitset_attach(self, waitset: dds_c_t.entity, entity: dds_c_t.entity, x: dds_c_t.attach) -> dds_c_t.returnv:
        pass

    @c_call("dds_waitset_detach")
    def _waitset_detach(self, waitset: dds_c_t.entity, entity: dds_c_t.entity) -> dds_c_t.returnv:
        pass

    @c_call("dds_waitset_wait")
    def _waitset_wait(self, waitset: dds_c_t.entity, xs: ct.POINTER(dds_c_t.attach),
                      nxs: ct.c_size_t, reltimeout: dds_c_t.duration) -> dds_c_t.returnv:
        pass

    @c_call("dds_waitset_wait_until")
    def _waitset_wait_until(self, waitset: dds_c_t.entity, xs: ct.POINTER(dds_c_t.attach),
                            nxs: ct.c_size_t, abstimeout: dds_c_t.duration) -> dds_c_t.returnv:
        pass

    @c_call("dds_waitset_set_trigger")
    def _waitset_set_trigger(self, waitset: dds_c_t.entity, value: ct.c_bool) -> dds_c_t.returnv:
        pass
