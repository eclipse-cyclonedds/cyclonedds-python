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

from dataclasses import dataclass, make_dataclass, asdict, field
from inspect import isclass
from base64 import b64encode, b64decode
from typing import Sequence, Union, Set, Optional, ClassVar
import ctypes as ct

from .internal import static_c_call, dds_c_t, DDS


class BasePolicy:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.__name__ in ['Property', 'BinaryProperty']:
            return
        if cls.__scope__ != cls.__name__:
            cls.__name__ = f"{cls.__scope__}.{cls.__name__}"


def _no_init(*args, **kwargs):
    raise NotImplementedError("This Qos object cannot be initialized like this.")


def _policy_singleton(scope, name):
    return make_dataclass(
        name, [],
        bases=(BasePolicy,),
        namespace={'__scope__': scope, '__repr__': lambda s: f"Policy.{scope}.{name}"},
        frozen=True)()


class Policy:
    """The Policy class is fully static and should never need to be instantiated.

    See Also
    --------
    qoshowto: How to work with Qos and Policy, TODO.
    """
    __init__ = _no_init

    class Reliability:
        """The Reliability Qos Policy

        Examples
        --------
        >>> Policy.Reliability.BestEffort
        >>> Policy.Reliability.Reliable(max_blocking_time=duration(seconds=1))
        """
        __scope__ = "Reliability"
        __init__ = _no_init

        BestEffort: 'Policy.Reliability.BestEffort' = _policy_singleton("Reliability", "BestEffort")

        @dataclass(frozen=True)
        class Reliable(BasePolicy):
            """Use Reliable reliability

            Parameters
            ----------
            max_blocking_time : int
                The number of nanoseconds the writer will bock when its history is full.
                Use the :func:`duration<cyclonedds.util.duration>` function to avoid time calculation headaches.

            """
            __scope__: ClassVar[str] = "Reliability"
            max_blocking_time: int

    class Durability:
        """ The Durability Qos Policy

        Examples
        --------
        >>> Policy.Durability.Volatile
        >>> Policy.Durability.TransientLocal
        >>> Policy.Durability.Transient
        >>> Policy.Durability.Persistent
        """
        __init__ = _no_init
        __scope__ = "Durability"

        Volatile: 'Policy.Durability.Volatile' = _policy_singleton("Durability", "Volatile")
        TransientLocal: 'Policy.Durability.TransientLocal' = _policy_singleton("Durability", "TransientLocal")
        Transient: 'Policy.Durability.Transient' = _policy_singleton("Durability", "Transient")
        Persistent: 'Policy.Durability.Persistent' = _policy_singleton("Durability", "Persistent")

    class History:
        """ The History Qos Policy

        Examples
        --------
        >>> Policy.History.KeepAll
        >>> Policy.History.KeepLast(depth=10)

        Attributes
        ----------
        KeepAll: Tuple[PolicyType, Any]
                 The type of this entity is not publicly specified.
        """
        __init__ = _no_init
        __scope__ = "History"

        KeepAll: 'Policy.History.KeepAll' = _policy_singleton("History", "KeepAll")

        @dataclass(frozen=True)
        class KeepLast(BasePolicy):
            """
            Parameters
            ----------
            depth : int
                The depth of samples to keep in the history.
            """
            __scope__: ClassVar[str] = "History"
            depth: int

    @dataclass(frozen=True)
    class ResourceLimits(BasePolicy):
        """The ResourceLimits Qos Policy

        Examples
        --------
        >>> Policy.ResourceLimits(
        >>>     max_samples=10,
        >>>     max_instances=10,
        >>>     max_samples_per_instance=2
        >>> )

        Attributes
        ----------
        max_samples : int
            Max number of samples total.
        max_instances : int
            Max number of instances total.
        max_samples_per_instance : int
            Max number of samples per instance.
        """
        __scope__: ClassVar[str] = "ResourceLimits"
        max_samples: int = -1
        max_instances: int = -1
        max_samples_per_instance: int = -1

    class PresentationAccessScope:
        """The Presentation Access Scope Qos Policy

        Examples
        --------
        >>> Policy.PresentationAccessScope.Instance(coherent_access=True, ordered_access=False)
        >>> Policy.PresentationAccessScope.Topic(coherent_access=True, ordered_access=False)
        >>> Policy.PresentationAccessScope.Group(coherent_access=True, ordered_access=False)
        """
        __init__ = _no_init
        __scope__ = "PresentationAccessScope"

        @dataclass(frozen=True)
        class Instance(BasePolicy):
            """Use Instance Presentation Access Scope

            Attributes
            ----------
            coherent_access : bool
                Enable coherent access
            ordered_access : bool
                Enable ordered access
            """
            __scope__: ClassVar[str] = "PresentationAccessScope"
            coherent_access: bool
            ordered_access: bool

        @dataclass(frozen=True)
        class Topic(BasePolicy):
            """Use Topic Presentation Access Scope

            Attributes
            ----------
            coherent_access : bool
                Enable coherent access
            ordered_access : bool
                Enable ordered access
            """
            __scope__: ClassVar[str] = "PresentationAccessScope"
            coherent_access: bool
            ordered_access: bool

        @dataclass(frozen=True)
        class Group(BasePolicy):
            """Use Group Presentation Access Scope

            Attributes
            ----------
            coherent_access : bool
                Enable coherent access
            ordered_access : bool
                Enable ordered access
            """
            __scope__: ClassVar[str] = "PresentationAccessScope"
            coherent_access: bool
            ordered_access: bool

    @dataclass(frozen=True)
    class Lifespan(BasePolicy):
        """The Lifespan Qos Policy

        Examples
        --------
        >>> Policy.Lifespan(duration(seconds=2))

        Attributes
        ----------
        lifespan : int
            Expiration time relative to the source timestamp of a sample in nanoseconds.
        """
        __scope__: ClassVar[str] = "Lifespan"
        lifespan: int

    @dataclass(frozen=True)
    class Deadline(BasePolicy):
        """The Deadline Qos Policy

        Examples
        --------
        >>> Policy.Deadline(deadline=duration(seconds=2))

        Attributes
        ----------
        deadline : int
            Deadline of a sample in nanoseconds.
        """
        __scope__: ClassVar[str] = "Deadline"
        deadline: int

    @dataclass(frozen=True)
    class LatencyBudget(BasePolicy):
        """The Latency Budget Qos Policy

        Examples
        --------
        >>> Policy.LatencyBudget(duration(seconds=2))

        Parameters
        ----------
        budget : int
            Latency budget in nanoseconds.
        """
        __scope__: ClassVar[str] = "LatencyBudget"
        budget: int

    class Ownership:
        """The Ownership Qos Policy

        Examples
        --------
        >>> Policy.Ownership.Shared
        >>> Policy.Ownership.Exclusive

        Attributes
        ----------
        Shared:    Policy.Ownership.Shared
        Exclusive: Policy.Ownership.Exclusive
        """
        __init__ = _no_init
        __scope__ = "Ownership"

        Shared: 'Policy.Ownership.Shared' = _policy_singleton("Ownership", "Shared")
        Exclusive: 'Policy.Ownership.Exclusive' = _policy_singleton("Ownership", "Exclusive")

    @dataclass(frozen=True)
    class OwnershipStrength(BasePolicy):
        """The Ownership Strength Qos Policy

        Examples
        --------
        >>> Policy.OwnershipStrength(strength=2)

        Parameters
        ----------
        strength : int
            Ownership strength as integer.
        """
        __scope__: ClassVar[str] = "OwnershipStrength"
        strength: int

    class Liveliness:
        """The Liveliness Qos Policy

        Examples
        --------
        >>> Policy.Liveliness.Automatic(lease_duration=duration(seconds=10))
        >>> Policy.Liveliness.ManualByParticipant(lease_duration=duration(seconds=10))
        >>> Policy.Liveliness.ManualByTopic(lease_duration=duration(seconds=10))
        """
        __init__ = _no_init
        __scope__ = "Liveliness"

        @dataclass(frozen=True)
        class Automatic(BasePolicy):
            """Use Automatic Liveliness

            Attributes
            ----------
            lease_duration: int
                The lease duration in nanoseconds. Use the helper function :func:`duration<cyclonedds.util.duration>` to write
                the duration in a human readable format.
            """
            __scope__: ClassVar[str] = "Liveliness"
            lease_duration: int

        @dataclass(frozen=True)
        class ManualByParticipant(BasePolicy):
            """Use ManualByParticipant Liveliness

            Attributes
            ----------
            lease_duration: int
                The lease duration in nanoseconds. Use the helper function :func:`duration<cyclonedds.util.duration>` to write
                the duration in a human readable format.
            """
            __scope__: ClassVar[str] = "Liveliness"
            lease_duration: int

        @dataclass(frozen=True)
        class ManualByTopic(BasePolicy):
            """Use ManualByTopic Liveliness

            Attributes
            ----------
            lease_duration: int
                The lease duration in nanoseconds. Use the helper function :func:`duration<cyclonedds.util.duration>` to write
                the duration in a human readable format.
            """
            __scope__: ClassVar[str] = "Liveliness"
            lease_duration: int

    @dataclass(frozen=True)
    class TimeBasedFilter(BasePolicy):
        """The TimeBasedFilter Qos Policy

        Examples
        --------
        >>> Policy.TimeBasedFilter(filter_fn=duration(seconds=2))

        Attributes
        ----------
        filter_time: int
            Minimum time between samples in nanoseconds.  Use the helper function :func:`duration<cyclonedds.util.duration>`
            to write the duration in a human readable format.
        """
        __scope__: ClassVar[str] = "TimeBasedFilter"
        filter_time: int

    @dataclass(frozen=True)
    class Partition(BasePolicy):
        """The Partition Qos Policy

        Examples
        --------
        >>> Policy.Partition(partitions=["partition_a", "partition_b", "partition_c"])
        >>> Policy.Partition(partitions=[f"partition_{i}" for i in range(100)])

        Attributes
        ----------
        partitions : Sequence[str]
        """
        __scope__: ClassVar[str] = "Partition"
        partitions: Sequence[str]

        def __post_init__(self):
            # Tuple-fy partitions to ensure immutability
            # The super trick here is because the class is already frozen so _officially_
            # we are not supposed to be able to edit this variable.
            partitions = [self.partitions] if type(self.partitions) == str else self.partitions
            super().__setattr__('partitions', tuple(partitions))

    @dataclass(frozen=True)
    class TransportPriority(BasePolicy):
        """The TransportPriority Qos Policy

        Examples
        --------
        >>> Policy.TransportPriority(priority=10)

        Attributes
        ----------
        priority: int
        """
        __scope__: ClassVar[str] = "TransportPriority"
        priority: int

    class DestinationOrder:
        """The DestinationOrder Qos Policy

        Examples
        --------
        >>> Policy.DestinationOrder.ByReceptionTimestamp
        >>> Policy.DestinationOrder.BySourceTimestamp
        """
        __scope__: ClassVar[str] = "DestinationOrder"
        ByReceptionTimestamp: 'Policy.DestinationOrder.ByReceptionTimestamp' = \
            _policy_singleton("DestinationOrder", "ByReceptionTimestamp")
        BySourceTimestamp: 'Policy.DestinationOrder.BySourceTimestamp' = \
            _policy_singleton("DestinationOrder", "BySourceTimestamp")

    @dataclass(frozen=True)
    class WriterDataLifecycle(BasePolicy):
        """The WriterDataLifecycle Qos Policy

        Examples
        --------
        >>> Policy.WriterDataLifecycle(autodispose=False)

        Attributes
        ----------
        autodispose: bool
        """
        __scope__: ClassVar[str] = "WriterDataLifecycle"
        autodispose: bool

    @dataclass(frozen=True)
    class ReaderDataLifecycle(BasePolicy):
        """The ReaderDataLifecycle Qos Policy

        Examples
        --------
        >>> Policy.ReaderDataLifecycle(
        >>>     autopurge_nowriter_samples_delay=duration(minutes=2),
        >>>     autopurge_disposed_samples_delay=duration(minutes=5)
        >>> )

        Attributes
        ----------
        autopurge_nowriter_samples_delay: bool
        autopurge_disposed_samples_delay: bool
        """
        __scope__: ClassVar[str] = "ReaderDataLifecycle"
        autopurge_nowriter_samples_delay: int
        autopurge_disposed_samples_delay: int

    @dataclass(frozen=True)
    class DurabilityService(BasePolicy):
        """The DurabilityService Qos Policy

        Examples
        --------
        >>> Policy.DurabilityService(
        >>>     cleanup_delay=duration(minutes=2.5),
        >>>     history=Policy.History.KeepLast(20),
        >>>     max_samples=2000,
        >>>     max_instances=200,
        >>>     max_samples_per_instance=25
        >>> )

        Attributes
        ----------
        cleanup_delay: int
        history: Policy.History.KeepAll, Policy.History.KeepLast
        max_samples: int
        max_instances: int
        max_samples_per_instance: int
        """
        __scope__: ClassVar[str] = "DurabilityService"
        cleanup_delay: int
        history: Union['Policy.History.KeepAll', 'Policy.History.KeepLast']
        max_samples: int
        max_instances: int
        max_samples_per_instance: int

    class IgnoreLocal:
        """The IgnoreLocal Qos Policy

        Examples
        --------
        >>> Policy.IgnoreLocal.Nothing
        >>> Policy.IgnoreLocal.Participant
        >>> Policy.IgnoreLocal.Process
        """
        __init__ = _no_init
        __scope__ = "IgnoreLocal"

        Nothing: 'Policy.IgnoreLocal.Nothing' = _policy_singleton("IgnoreLocal", "Nothing")
        Participant: 'Policy.IgnoreLocal.Participant' = _policy_singleton("IgnoreLocal", "Participant")
        Process: 'Policy.IgnoreLocal.Process' = _policy_singleton("IgnoreLocal", "Process")

    @dataclass(frozen=True)
    class Userdata(BasePolicy):
        """The Userdata Qos Policy

        Examples
        --------
        >>> Policy.Userdata(data=b"Hello, World!")
        """
        __scope__: ClassVar[str] = "Userdata"
        data: bytes

        def __post_init__(self):
            if type(self.data) != bytes:
                raise ValueError("Userdata needs to be bytes.")

    @dataclass(frozen=True)
    class Topicdata(BasePolicy):
        """The Topicdata Qos Policy

        Examples
        --------
        >>> Policy.Topicdata(data=b"Hello, World!")
        """
        __scope__: ClassVar[str] = "Topicdata"
        data: bytes

        def __post_init__(self):
            if type(self.data) != bytes:
                raise ValueError("Topicdata needs to be bytes.")

    @dataclass(frozen=True)
    class Groupdata(BasePolicy):
        """The Groupdata Qos Policy

        Examples
        --------
        >>> Policy.Groupdata(data=b"Hello, World!")
        """
        __scope__: ClassVar[str] = "Groupdata"
        data: bytes

        def __post_init__(self):
            if type(self.data) != bytes:
                raise ValueError("Groupdata needs to be bytes.")

    @dataclass(frozen=True)
    class Property(BasePolicy):
        """The Property Qos Policy

        Examples
        --------
        >>> Policy.Property(key="host", value="central")
        """
        key: str
        value: str
        __scope__: str = field(init=False, repr=False, compare=False)

        def __post_init__(self):
            if type(self.value) != str:
                raise ValueError("Property value should be string.")
            # The super trick here is because the class is already frozen so _officially_
            # we are not supposed to be able to edit this variable.
            super().__setattr__('__scope__', f"Property<{self.key}>")

        def __repr__(self):
            return f"Property(key=\"{self.key}\", value=\"{self.value}\")"

    @dataclass(frozen=True)
    class BinaryProperty(BasePolicy):
        """The BinaryProperty Qos Policy

        Examples
        --------
        >>> Policy.BinaryProperty(key="host", value=b"central")
        """
        key: str
        value: bytes
        __scope__: str = field(init=False, repr=False, compare=False)

        def __post_init__(self):
            if type(self.value) != bytes:
                raise ValueError("BinaryProperty value should be bytes.")
            # The super trick here is because the class is already frozen so _officially_
            # we are not supposed to be able to edit this variable.
            super().__setattr__('__scope__', f"BinaryProperty<{self.key}>")

        def __repr__(self):
            return f"BinaryProperty(key=\"{self.key}\", value=b\"{self.value}\")"

    class TypeConsistency:
        """The TypeConsistency Qos Policy

        Examples
        --------
        >>> Policy.TypeConsistency.DisallowTypeCoercion
        >>> Policy.TypeConsistency.AllowTypeCoercion
        """
        __init__ = _no_init
        __scope__ = "TypeConsistency"

        @dataclass(frozen=True)
        class DisallowTypeCoercion(BasePolicy):
            __scope__: ClassVar[str] = "TypeConsistency"

            force_type_validation: bool = False

        @dataclass(frozen=True)
        class AllowTypeCoercion(BasePolicy):
            __scope__: ClassVar[str] = "TypeConsistency"

            ignore_sequence_bounds: bool = True
            ignore_string_bounds: bool = True
            ignore_member_names: bool = True
            prevent_type_widening: bool = False
            force_type_validation: bool = False

    @dataclass(frozen=True)
    class DataRepresentation(BasePolicy):
        """The DataRepresentation Qos Policy"""
        __scope__: ClassVar[str] = "DataRepresentation"
        use_cdrv0_representation: bool = False
        use_xcdrv2_representation: bool = False

    @dataclass(frozen=True)
    class EntityName(BasePolicy):
        """The EntityName Qos Policy"""
        __scope__: ClassVar[str] = "EntityName"
        name: str


class Qos:
    """This class represents a collections of policies. It allows for easy inspection of this set. When you retrieve a
    Qos object from an entity modifying that object would actually does not change the Qos of the entity. To reflect this
    Qos objects are immutable.

    .. container:: operations

        .. describe:: x == y

            Checks if two Qos objects contain the same policies. This is a full comparison, not a match.

        .. describe:: x != y

            Checks if two Qos objects do not contain the same policies.

        .. describe:: p in qos

            Check if a Policy p is contained in Qos object qos. You can use all levels of generalization, for example:
            ``Policy.History in qos``, ``Policy.History.KeepLast in qos`` and ``Policy.History.KeepLast(1) in qos``.

        .. describe:: qos[p]

            Obtain the Policy matched with p from the Qos object, for example:
            ``qos[Policy.History] -> Policy.History.KeepAll``

        .. describe:: iter(x)

            The Qos object supports iteration over it's contents.

        .. describe:: len(x)

            Return the number of Policies in the Qos object.

        .. describe:: str(x)

            Human-readable description of the contained Qos policies.


    Attributes
    ----------
    policies: Tuple[BasePolicy]
        A sorted tuple of the Policies contained in this Qos object
    """
    _policy_mapper = {
        "Policy.Reliability.BestEffort": Policy.Reliability.BestEffort,
        "Policy.Reliability.Reliable": Policy.Reliability.Reliable,
        "Policy.Durability.Volatile": Policy.Durability.Volatile,
        "Policy.Durability.TransientLocal": Policy.Durability.TransientLocal,
        "Policy.Durability.Transient": Policy.Durability.Transient,
        "Policy.Durability.Persistent": Policy.Durability.Persistent,
        "Policy.History.KeepAll": Policy.History.KeepAll,
        "Policy.History.KeepLast": Policy.History.KeepLast,
        "Policy.ResourceLimits": Policy.ResourceLimits,
        "Policy.PresentationAccessScope.Instance": Policy.PresentationAccessScope.Instance,
        "Policy.PresentationAccessScope.Topic": Policy.PresentationAccessScope.Topic,
        "Policy.PresentationAccessScope.Group": Policy.PresentationAccessScope.Group,
        "Policy.Lifespan": Policy.Lifespan,
        "Policy.Deadline": Policy.Deadline,
        "Policy.LatencyBudget": Policy.LatencyBudget,
        "Policy.Ownership.Shared": Policy.Ownership.Shared,
        "Policy.Ownership.Exclusive": Policy.Ownership.Exclusive,
        "Policy.OwnershipStrength": Policy.OwnershipStrength,
        "Policy.Liveliness.Automatic": Policy.Liveliness.Automatic,
        "Policy.Liveliness.ManualByParticipant": Policy.Liveliness.ManualByParticipant,
        "Policy.Liveliness.ManualByTopic": Policy.Liveliness.ManualByTopic,
        "Policy.TimeBasedFilter": Policy.TimeBasedFilter,
        "Policy.Partition": Policy.Partition,
        "Policy.TransportPriority": Policy.TransportPriority,
        "Policy.DestinationOrder.ByReceptionTimestamp": Policy.DestinationOrder.ByReceptionTimestamp,
        "Policy.DestinationOrder.BySourceTimestamp": Policy.DestinationOrder.BySourceTimestamp,
        "Policy.WriterDataLifecycle": Policy.WriterDataLifecycle,
        "Policy.ReaderDataLifecycle": Policy.ReaderDataLifecycle,
        "Policy.DurabilityService": Policy.DurabilityService,
        "Policy.IgnoreLocal.Nothing": Policy.IgnoreLocal.Nothing,
        "Policy.IgnoreLocal.Participant": Policy.IgnoreLocal.Participant,
        "Policy.IgnoreLocal.Process": Policy.IgnoreLocal.Process,
        "Policy.Userdata": Policy.Userdata,
        "Policy.Groupdata": Policy.Groupdata,
        "Policy.Topicdata": Policy.Topicdata,
        "Policy.Property": Policy.Property,
        "Policy.BinaryProperty": Policy.BinaryProperty,
        "Policy.TypeConsistency.DisallowTypeCoercion": Policy.TypeConsistency.DisallowTypeCoercion,
        "Policy.TypeConsistency.AllowTypeCoercion": Policy.TypeConsistency.AllowTypeCoercion,
        "Policy.DataRepresentation": Policy.DataRepresentation,
        "Policy.EntityName": Policy.EntityName
    }

    def __init__(self, *policies, base: Optional['Qos'] = None):
        """Initialize a Qos object

        Parameters
        ----------
        *policies: BasePolicy
            Pass in any number of constructed Policies.
        base : Qos, optional
            Optionally inherit policies from another Qos object. Inherited policies
            are overwritten by those newly set.

        Raises
        ------
        TypeError
            If you pass something that is not a Policy or use a base that is not a Qos object
            this will be treated as a TypeError.
        ValueError
            If you pass two overlapping Policies, for example ``Policy.History.KeepLast(10)`` and
            ``Policy.History.KeepAll`` this will be treated as a ValueError.
        """
        policies = list(policies)
        for p in policies:
            if not isinstance(p, BasePolicy):
                raise TypeError(f"{repr(p)} is not a Policy.")

        if base is not None:
            if not isinstance(base, Qos):
                raise TypeError("base takes a Qos as argument.")
            for policy in base.policies:
                for p in policies:
                    if p.__scope__ == policy.__scope__:
                        break
                else:
                    policies.append(policy)

        self.__policies = tuple(sorted(policies, key=lambda x: x.__scope__))
        self._assert_consistency()

    def _assert_consistency(self):
        for i in range(len(self.__policies)):
            if not isinstance(self.__policies[i], BasePolicy):
                raise TypeError(str(self.__policies[i]), " is not a Policy.")

        for i in range(1, len(self.__policies)):
            if self.__policies[i - 1].__scope__ == self.__policies[i].__scope__:
                raise ValueError("Multiple Qos policies of type {}.".format(self.__policies[i].__scope__))

    @property
    def policies(self):
        return self.__policies

    def __iter__(self):
        return iter(self.policies)

    def __getitem__(self, key):
        if not hasattr(key, "__scope__"):
            raise ValueError(f"{key} is not a valid policy to look up in the qos")
        scope = key.__scope__
        for p in self.__policies:
            if p.__scope__ > scope:
                break
            if p.__scope__ == scope:
                return p
        return None

    def __contains__(self, key):
        if not hasattr(key, "__scope__"):
            raise ValueError(f"{key} is not a valid policy to look up in the qos")
        if isclass(key):
            scope = key.__scope__
            for p in self.__policies:
                if p.__scope__ > scope:
                    break
                if p.__scope__ == scope:
                    return True
        else:
            scope = key.__scope__
            for p in self.__policies:
                if p.__scope__ > scope:
                    break
                if p == key:
                    return True
        return False

    def __len__(self):
        return len(self.__policies)

    def __eq__(self, other):
        if not isinstance(other, Qos):
            return False

        if len(self.policies) != len(other.policies):
            return False

        for p, q in zip(self.policies, other.policies):
            if p != q:
                return False
        return True

    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join(repr(p) for p in self.policies)})"

    __str__ = __repr__

    def asdict(self):
        """Convert a Qos object to a python dictionary.

        Returns
        -------
        dict
            Fully describe the Qos object using a python dictionary with only built-in types
            (dict, list, string, int, boolean). This format is not guaranteed to stay consistent between
            cyclonedds versions but can be useful for debugging or use within an application.
        """
        ret = {}
        for p in self.policies:
            path = p.__class__.__name__.split(".")
            data = asdict(p)

            if "__scope__" in data:
                # Property & BinaryProperty
                path[0] = data["__scope__"]
                del data["__scope__"]
                if 'kind' in data:
                    del data['kind']

            for k, v in data.items():
                if type(v) == bytes:
                    data[k] = b64encode(v).decode()

            if len(path) == 1:
                ret[path[0]] = data
            else:  # if len(path) == 2:
                ret[path[0]] = {"kind": path[1]}
                if data:
                    ret[path[0]].update(data)
        return ret

    @classmethod
    def fromdict(cls, data: dict):
        """Convert a python dictionary as generated by ``asdict()`` to a Qos object.

        Returns
        -------
        Qos
            Note that the format of the python dictionary is not guaranteed between cyclonedds versions
            thus storing these dictionaries to disk and loading them again is not recommended.
        """
        policies = []
        for k, v in data.items():
            # Special case for subqos
            if k == "DurabilityService":
                if not v["history"]:
                    v["history"] = Policy.History.KeepAll
                else:
                    v["history"] = Policy.History.KeepLast(v["history"]["depth"])

            # Special case for UserData/TopicData/GroupData
            elif k in ['Userdata', 'Topicdata', 'Groupdata']:
                v["data"] = b64decode(v["data"].encode())
            elif k.startswith("Property"):
                k = "Property"
            elif k.startswith("BinaryProperty"):
                k = "BinaryProperty"
                v["value"] = b64decode(v["value"].encode())

            name = f"Policy.{k}"
            if name in Qos._policy_mapper:
                if v:
                    policies.append(Qos._policy_mapper[name](**v))
                else:
                    policies.append(Qos._policy_mapper[name])
                continue
            if "kind" in v:
                name += f".{v['kind']}"
                del v["kind"]
                if name in Qos._policy_mapper:
                    if v:
                        policies.append(Qos._policy_mapper[name](**v))
                    else:
                        policies.append(cls._policy_mapper[name])
                    continue
            raise ValueError("Not a valid Qos dictionary.")

        return cls(*policies)

    def __add__(self, other) -> 'Qos':
        return Qos(*other.policies, base=self)

    def __sub__(self, other) -> 'Qos':
        for pol in other:
            if pol not in self:
                raise ValueError(f"Cannot remove {pol} because that is not contained within this Qos object")
        return Qos(*[pol for pol in self.policies if pol not in other])

    def domain_participant(self) -> 'DomainParticipantQos':
        return DomainParticipantQos(
            *[policy for policy in self if policy.__scope__.split("<")[0] in DomainParticipantQos.supported_scopes]
        )

    def topic(self) -> 'TopicQos':
        return TopicQos(
            *[policy for policy in self if policy.__scope__.split("<")[0] in TopicQos.supported_scopes]
        )

    def publisher(self) -> 'PublisherQos':
        return PublisherQos(
            *[policy for policy in self if policy.__scope__.split("<")[0] in PublisherQos.supported_scopes]
        )

    def subscriber(self) -> 'SubscriberQos':
        return SubscriberQos(
            *[policy for policy in self if policy.__scope__.split("<")[0] in SubscriberQos.supported_scopes]
        )

    def datareader(self) -> 'DataReaderQos':
        return DataReaderQos(
            *[policy for policy in self if policy.__scope__.split("<")[0] in DataReaderQos.supported_scopes]
        )

    def datawriter(self) -> 'DataWriterQos':
        return DataWriterQos(
            *[policy for policy in self if policy.__scope__.split("<")[0] in DataWriterQos.supported_scopes]
        )


class LimitedScopeQos(Qos):
    for_entity: str
    supported_scopes: Set[str]

    def _assert_consistency(self):
        super()._assert_consistency()

        for policy in self.policies:
            if policy.__scope__.split("<")[0] not in self.supported_scopes:
                raise ValueError(f"{self.for_entity} Qos does not support {policy}.")


class DomainParticipantQos(LimitedScopeQos):
    for_entity: str = "DomainParticipant"
    supported_scopes: Set[str] = {"EntityName", "BinaryProperty", "Property", "Userdata", "IgnoreLocal"}


class TopicQos(LimitedScopeQos):
    for_entity: str = "Topic"
    supported_scopes: Set[str] = {
        "EntityName",
        "BinaryProperty",
        "Deadline",
        "DestinationOrder",
        "Durability",
        "DurabilityService",
        "History",
        "IgnoreLocal",
        "LatencyBudget",
        "Lifespan",
        "Liveliness",
        "Ownership",
        "Property",
        "Reliability",
        "ResourceLimits",
        "Topicdata",
        "TransportPriority",
        "TypeConsistency",
        "DataRepresentation"
    }


class PublisherQos(LimitedScopeQos):
    for_entity: str = "Publisher"
    supported_scopes: Set[str] = {
        "EntityName",
        "BinaryProperty",
        "Groupdata",
        "IgnoreLocal",
        "Partition",
        "PresentationAccessScope",
        "Property"
    }


class SubscriberQos(LimitedScopeQos):
    for_entity: str = "Subscriber"
    supported_scopes: Set[str] = {
        "EntityName",
        "BinaryProperty",
        "Groupdata",
        "IgnoreLocal",
        "Partition",
        "PresentationAccessScope",
        "Property"
    }


class DataWriterQos(LimitedScopeQos):
    for_entity: str = "DataWriter"
    supported_scopes: Set[str] = {
        "EntityName",
        "BinaryProperty",
        "Deadline",
        "DestinationOrder",
        "Durability",
        "DurabilityService",
        "History",
        "IgnoreLocal",
        "LatencyBudget",
        "Lifespan",
        "Liveliness",
        "Ownership",
        "OwnershipStrength",
        "Property",
        "Reliability",
        "ResourceLimits",
        "TransportPriority",
        "Userdata",
        "WriterDataLifecycle",
        "TypeConsistency",
        "DataRepresentation"
    }


class DataReaderQos(LimitedScopeQos):
    for_entity: str = "DataReader"
    supported_scopes: Set[str] = {
        "EntityName",
        "BinaryProperty",
        "Deadline",
        "DestinationOrder",
        "Durability",
        "History",
        "IgnoreLocal",
        "LatencyBudget",
        "Liveliness",
        "Ownership",
        "Property",
        "ReaderDataLifecycle",
        "Reliability",
        "ResourceLimits",
        "TimeBasedFilter",
        "Userdata",
        "TypeConsistency",
        "DataRepresentation"
    }


class _CQos(DDS):
    """The _CQos object represents a qos pointer into DDS. Because they are somewhat annoying to deal with
    these are intended to be short-lived objects, used just to convert between the handy Qos object and the
    CycloneDDS C layer.
    """

    _all_scopes = (
        "Reliability", "Durability", "History", "ResourceLimits", "PresentationAccessScope",
        "Lifespan", "Deadline", "LatencyBudget", "Ownership", "OwnershipStrength",
        "Liveliness", "TimeBasedFilter", "Partition", "TransportPriority",
        "DestinationOrder", "WriterDataLifecycle", "ReaderDataLifecycle",
        "DurabilityService", "IgnoreLocal", "Userdata", "Groupdata", "Topicdata",
        "Property", "BinaryProperty", "TypeConsistency", "DataRepresentation",
        "EntityName"
    )

    @classmethod
    def cqos_create(cls):
        return cls._create_qos()

    @classmethod
    def qos_to_cqos(cls, qos: Qos):
        cqos = cls._create_qos()

        for policy in qos:
            getattr(cls, "_set_p_" + policy.__scope__.split("<")[0].lower())(cqos, policy)

        return cqos

    @classmethod
    def cqos_to_qos(cls, cqos):
        policies = []
        for scope in cls._all_scopes:
            p = getattr(cls, "_get_p_" + scope.lower())(cqos)
            if p is not None:
                if type(p) == list:
                    policies.extend(p)
                else:
                    policies.append(p)

        return Qos(*policies)

    @classmethod
    def cqos_destroy(cls, cqos):
        cls.delete_cqos(cqos)

    @static_c_call("dds_create_qos")
    def _create_qos(self) -> dds_c_t.qos_p:
        pass

    @static_c_call("dds_delete_qos")
    def delete_cqos(self, qos: dds_c_t.qos_p) -> None:
        pass

    @static_c_call("dds_free")
    def free(self, ptr: ct.c_void_p) -> None:
        pass

    # Reliability

    @classmethod
    def _set_p_reliability(cls, qos, policy):
        if policy == Policy.Reliability.BestEffort:
            return cls._set_reliability(qos, 0, 0)
        return cls._set_reliability(qos, 1, policy.max_blocking_time)

    @static_c_call("dds_qset_reliability")
    def _set_reliability(self, qos: dds_c_t.qos_p, reliability_kind: dds_c_t.reliability,
                         blocking_time: dds_c_t.duration) -> None:
        pass

    # Durability

    @classmethod
    def _set_p_durability(cls, qos, policy):
        if policy == Policy.Durability.Volatile:
            return cls._set_durability(qos, 0)
        elif policy == Policy.Durability.TransientLocal:
            return cls._set_durability(qos, 1)
        elif policy == Policy.Durability.Transient:
            return cls._set_durability(qos, 2)
        return cls._set_durability(qos, 3)

    @static_c_call("dds_qset_durability")
    def _set_durability(self, qos: dds_c_t.qos_p, durability_kind: dds_c_t.durability) -> None:
        pass

    # History

    @classmethod
    def _set_p_history(cls, qos, policy):
        if policy == Policy.History.KeepAll:
            return cls._set_history(qos, 1, 0)
        return cls._set_history(qos, 0, policy.depth)

    @static_c_call("dds_qset_history")
    def _set_history(self, qos: dds_c_t.qos_p, history_kind: dds_c_t.history, depth: ct.c_int32) -> None:
        pass

    # Resource Limits

    @classmethod
    def _set_p_resourcelimits(cls, qos, policy):
        return cls._set_resource_limits(qos, policy.max_samples, policy.max_instances, policy.max_samples_per_instance)

    @static_c_call("dds_qset_resource_limits")
    def _set_resource_limits(self, qos: dds_c_t.qos_p, max_samples: ct.c_int32, max_instances: ct.c_int32,
                             max_samples_per_instance: ct.c_int32) -> None:
        pass

    # Presentation access scpoe

    @classmethod
    def _set_p_presentationaccessscope(cls, qos, policy):
        if type(policy) is Policy.PresentationAccessScope.Instance:
            return cls._set_presentation_access_scope(qos, 0, policy.coherent_access, policy.ordered_access)
        elif type(policy) is Policy.PresentationAccessScope.Topic:
            return cls._set_presentation_access_scope(qos, 1, policy.coherent_access, policy.ordered_access)
        return cls._set_presentation_access_scope(qos, 2, policy.coherent_access, policy.ordered_access)

    @static_c_call("dds_qset_presentation")
    def _set_presentation_access_scope(self, qos: dds_c_t.qos_p, access_scope: dds_c_t.presentation_access_scope,
                                       coherent_access: ct.c_bool, ordered_access: ct.c_bool) -> None:
        pass

    # Lifespan

    @classmethod
    def _set_p_lifespan(cls, qos, policy):
        return cls._set_lifespan(qos, policy.lifespan)

    @static_c_call("dds_qset_lifespan")
    def _set_lifespan(self, qos: dds_c_t.qos_p, lifespan: dds_c_t.duration) -> None:
        pass

    # Deadline

    @classmethod
    def _set_p_deadline(cls, qos, policy):
        return cls._set_deadline(qos, policy.deadline)

    @static_c_call("dds_qset_deadline")
    def _set_deadline(self, qos: dds_c_t.qos_p, deadline: dds_c_t.duration) -> None:
        pass

    # Latency budget

    @classmethod
    def _set_p_latencybudget(cls, qos, policy):
        return cls._set_latency_budget(qos, policy.budget)

    @static_c_call("dds_qset_latency_budget")
    def _set_latency_budget(self, qos: dds_c_t.qos_p, latency_budget: dds_c_t.duration) -> None:
        pass

    # Ownership

    @classmethod
    def _set_p_ownership(cls, qos, policy):
        if policy == Policy.Ownership.Shared:
            return cls._set_ownership(qos, 0)
        return cls._set_ownership(qos, 1)

    @static_c_call("dds_qset_ownership")
    def _set_ownership(self, qos: dds_c_t.qos_p, ownership_kind: dds_c_t.ownership) -> None:
        pass

    # Ownership Strength

    @classmethod
    def _set_p_ownershipstrength(cls, qos, policy):
        return cls._set_ownership_strength(qos, policy.strength)

    @static_c_call("dds_qset_ownership_strength")
    def _set_ownership_strength(self, qos: dds_c_t.qos_p, ownership_strength: ct.c_int32) -> None:
        pass

    # Liveliness

    @classmethod
    def _set_p_liveliness(cls, qos, policy):
        if type(policy) is Policy.Liveliness.Automatic:
            return cls._set_liveliness(qos, 0, policy.lease_duration)
        elif type(policy) is Policy.Liveliness.ManualByParticipant:
            return cls._set_liveliness(qos, 1, policy.lease_duration)
        return cls._set_liveliness(qos, 2, policy.lease_duration)

    @static_c_call("dds_qset_liveliness")
    def _set_liveliness(self, qos: dds_c_t.qos_p, liveliness_kind: dds_c_t.liveliness,
                        lease_duration: dds_c_t.duration) -> None:
        pass

    # Time based filter

    @classmethod
    def _set_p_timebasedfilter(cls, qos, policy):
        return cls._set_time_based_filter(qos, policy.filter_time)

    @static_c_call("dds_qset_time_based_filter")
    def _set_time_based_filter(self, qos: dds_c_t.qos_p, minimum_separation: dds_c_t.duration) -> None:
        pass

    # Partition

    @classmethod
    def _set_p_partition(cls, qos, policy):
        ps = [p.encode() for p in policy.partitions]
        p_pt = (ct.c_char_p * len(ps))()
        for i, p in enumerate(ps):
            p_pt[i] = p
        cls._set_partition(qos, len(ps), p_pt)

    @static_c_call("dds_qset_partition")
    def _set_partition(self, qos: dds_c_t.qos_p, n: ct.c_uint32, ps: ct.POINTER(ct.c_char_p)) -> None:
        pass

    # Transport priority

    @classmethod
    def _set_p_transportpriority(cls, qos, policy):
        return cls._set_transport_priority(qos, policy.priority)

    @static_c_call("dds_qset_transport_priority")
    def _set_transport_priority(self, qos: dds_c_t.qos_p, value: ct.c_int32) -> None:
        pass

    # Destination order

    @classmethod
    def _set_p_destinationorder(cls, qos, policy):
        if policy == Policy.DestinationOrder.ByReceptionTimestamp:
            return cls._set_destination_order(qos, 0)
        return cls._set_destination_order(qos, 1)

    @static_c_call("dds_qset_destination_order")
    def _set_destination_order(self, qos: dds_c_t.qos_p, destination_order_kind: dds_c_t.destination_order) -> None:
        pass

    # Writer Data Lifecycle

    @classmethod
    def _set_p_writerdatalifecycle(cls, qos, policy):
        return cls._set_writer_data_lifecycle(qos, policy.autodispose)

    @static_c_call("dds_qset_writer_data_lifecycle")
    def _set_writer_data_lifecycle(self, qos: dds_c_t.qos_p, autodispose: ct.c_bool) -> None:
        pass

    # Reader Data Lifecycle

    @classmethod
    def _set_p_readerdatalifecycle(cls, qos, policy):
        return cls._set_reader_data_lifecycle(
            qos,
            policy.autopurge_nowriter_samples_delay,
            policy.autopurge_disposed_samples_delay
        )

    @static_c_call("dds_qset_reader_data_lifecycle")
    def _set_reader_data_lifecycle(self, qos: dds_c_t.qos_p, autopurge_nowriter_samples_delay: dds_c_t.duration,
                                   autopurge_disposed_samples_delay: dds_c_t.duration) -> None:
        pass

    # Durability Service

    @classmethod
    def _set_p_durabilityservice(cls, qos, policy):
        if policy.history == Policy.History.KeepAll:
            history_kind = 1
            history_depth = 0
        else:
            history_kind = 0
            history_depth = policy.history.depth

        return cls._set_durability_service(
            qos,
            policy.cleanup_delay,
            history_kind,
            history_depth,
            policy.max_samples,
            policy.max_instances,
            policy.max_samples_per_instance
        )

    @static_c_call("dds_qset_durability_service")
    def _set_durability_service(self, qos: dds_c_t.qos_p, service_cleanup_delay: dds_c_t.duration,
                                history_kind: dds_c_t.history, history_depth: ct.c_int32, max_samples: ct.c_int32,
                                max_instances: ct.c_int32, max_samples_per_instance: ct.c_int32) -> None:
        pass

    # Ignore local

    @classmethod
    def _set_p_ignorelocal(cls, qos, policy):
        if policy == Policy.IgnoreLocal.Nothing:
            return cls._set_ignore_local(qos, 0)
        elif policy == Policy.IgnoreLocal.Participant:
            return cls._set_ignore_local(qos, 1)
        return cls._set_ignore_local(qos, 2)

    @static_c_call("dds_qset_ignorelocal")
    def _set_ignore_local(self, qos: dds_c_t.qos_p, ingorelocal_kind: dds_c_t.ingnorelocal) -> None:
        pass

    # Userdata

    @classmethod
    def _set_p_userdata(cls, qos, policy):
        cls._set_userdata(qos, policy.data, len(policy.data))

    @static_c_call("dds_qset_userdata")
    def _set_userdata(self, qos: dds_c_t.qos_p, value: ct.c_void_p, size: ct.c_size_t) -> None:
        pass

    # Topic

    @classmethod
    def _set_p_topicdata(cls, qos, policy):
        cls._set_topicdata(qos, policy.data, len(policy.data))

    @static_c_call("dds_qset_topicdata")
    def _set_topicdata(self, qos: dds_c_t.qos_p, value: ct.c_void_p, size: ct.c_size_t) -> None:
        pass

    # Group

    @classmethod
    def _set_p_groupdata(cls, qos, policy):
        cls._set_groupdata(qos, policy.data, len(policy.data))

    @static_c_call("dds_qset_groupdata")
    def _set_groupdata(self, qos: dds_c_t.qos_p, value: ct.c_void_p, size: ct.c_size_t) -> None:
        pass

    # Property

    @classmethod
    def _set_p_property(cls, qos, policy):
        cls._set_property(qos, policy.key.encode('utf8'), policy.value.encode('utf8'))

    @static_c_call("dds_qset_prop")
    def _set_property(self, qos: dds_c_t.qos_p, key: ct.c_char_p, value: ct.c_char_p) -> None:
        pass

    # Binary property

    @classmethod
    def _set_p_binaryproperty(cls, qos, policy):
        cls._set_binaryproperty(qos, policy.key.encode('utf8'), policy.value, len(policy.value))

    @static_c_call("dds_qset_bprop")
    def _set_binaryproperty(self, qos: dds_c_t.qos_p, key: ct.c_char_p, value: ct.c_void_p, size: ct.c_size_t) -> None:
        pass

    # Type Consistency

    @classmethod
    def _set_p_typeconsistency(cls, qos, policy):
        if isinstance(policy, Policy.TypeConsistency.DisallowTypeCoercion):
            return cls._set_type_consistency(qos, 0, False, False, False, False, policy.force_type_validation)
        return cls._set_type_consistency(
            qos, 1, policy.ignore_sequence_bounds, policy.ignore_string_bounds, policy.ignore_member_names,
            policy.prevent_type_widening, policy.force_type_validation
        )

    @static_c_call("dds_qset_type_consistency")
    def _set_type_consistency(self, qos: dds_c_t.qos_p, type_consistency_kind: dds_c_t.type_consistency,
                              ignore_sequence_bounds: ct.c_bool, ignore_string_bounds: ct.c_bool,
                              ignore_member_names: ct.c_bool, prevent_type_widening: ct.c_bool,
                              force_type_validation: ct.c_bool) -> None:
        pass

    # Data Representation
    @classmethod
    def _set_p_datarepresentation(cls, qos, policy: Policy.DataRepresentation):
        if policy.use_cdrv0_representation and policy.use_xcdrv2_representation:
            representations = (dds_c_t.data_representation_id * 2)()
            representations[0] = 0
            representations[1] = 2
            return cls._set_data_representation(qos, 2, representations)
        if policy.use_cdrv0_representation:
            representations = dds_c_t.data_representation_id(0)
            return cls._set_data_representation(qos, 1, ct.byref(representations))
        if policy.use_xcdrv2_representation:
            representations = dds_c_t.data_representation_id(2)
            return cls._set_data_representation(qos, 1, ct.byref(representations))

    @static_c_call("dds_qset_data_representation")
    def _set_data_representation(self, qos: dds_c_t.qos_p, n: ct.c_uint32,
                                 values: ct.POINTER(dds_c_t.data_representation_id)) -> None:
        pass

    # Entity Name

    @classmethod
    def _set_p_entityname(cls, qos, policy: Policy.EntityName):
        return cls._set_entity_name(qos, policy.name.encode('utf8'))

    @static_c_call("dds_qset_entity_name")
    def _set_entity_name(self, qos: dds_c_t.qos_p, name: ct.c_char_p) -> None:
        pass

    # END OF SETTERS, START OF GETTERS #
    _gc_data_size = ct.c_size_t()
    _gc_data_value = ct.c_void_p()
    _gc_durability = dds_c_t.durability()
    _gc_history = dds_c_t.history()
    _gc_history_depth = ct.c_int32()
    _gc_max_samples = ct.c_int32()
    _gc_max_instances = ct.c_int32()
    _gc_max_samples_per_instance = ct.c_int32()
    _gc_access_scope = dds_c_t.presentation_access_scope()
    _gc_coherent_access = ct.c_bool()
    _gc_ordered_access = ct.c_bool()
    _gc_lifespan = dds_c_t.duration()
    _gc_deadline = dds_c_t.duration()
    _gc_latency_budget = dds_c_t.duration()
    _gc_ownership = dds_c_t.ownership()
    _gc_ownership_strength = ct.c_int32()
    _gc_liveliness = dds_c_t.liveliness()
    _gc_lease_duration = dds_c_t.duration()
    _gc_time_based_filter = dds_c_t.duration()
    _gc_partition_num = ct.c_uint32()
    _gc_partition_names = (ct.POINTER(ct.c_char_p))()
    _gc_reliability = dds_c_t.reliability()
    _gc_max_blocking_time = dds_c_t.duration()
    _gc_transport_priority = ct.c_int32()
    _gc_destination_order = dds_c_t.destination_order()
    _gc_writer_autodispose = ct.c_bool()
    _gc_autopurge_nowriter_samples_delay = dds_c_t.duration()
    _gc_autopurge_disposed_samples_delay = dds_c_t.duration()
    _gc_durservice_service_cleanup_delay = dds_c_t.duration()
    _gc_durservice_history_kind = dds_c_t.history()
    _gc_durservice_history_depth = ct.c_int32()
    _gc_durservice_max_samples = ct.c_int32()
    _gc_durservice_max_instances = ct.c_int32()
    _gc_durservice_max_samples_per_instance = ct.c_int32()
    _gc_ignorelocal = dds_c_t.ingnorelocal()
    _gc_propnames_num = ct.c_uint32()
    _gc_propnames_names = (ct.POINTER(ct.c_char_p))()
    _gc_prop_get_value = ct.c_char_p()
    _gc_bpropnames_num = ct.c_uint32()
    _gc_bpropnames_names = (ct.POINTER(ct.c_char_p))()
    _gc_bprop_get_value = ct.c_char_p()
    _gc_typecons_kind = dds_c_t.type_consistency()
    _gc_typecons_iseqbounds = ct.c_bool()
    _gc_typecons_istrbounds = ct.c_bool()
    _gc_typecons_imemnames = ct.c_bool()
    _gc_typecons_itypewide = ct.c_bool()
    _gc_typecons_forceval = ct.c_bool()

    # Reliability

    @classmethod
    def _get_p_reliability(cls, qos):
        if not cls._get_reliability(qos, ct.byref(cls._gc_reliability), ct.byref(cls._gc_max_blocking_time)):
            return None

        if cls._gc_reliability.value == 0:
            return Policy.Reliability.BestEffort
        return Policy.Reliability.Reliable(max_blocking_time=cls._gc_max_blocking_time.value)

    @static_c_call("dds_qget_reliability")
    def _get_reliability(self, qos: dds_c_t.qos_p, reliability_kind: ct.POINTER(dds_c_t.reliability),
                         blocking_time: ct.POINTER(dds_c_t.duration)) -> bool:
        pass

    # Durability

    @classmethod
    def _get_p_durability(cls, qos):
        if not cls._get_durability(qos, ct.byref(cls._gc_durability)):
            return None

        if cls._gc_durability.value == 0:
            return Policy.Durability.Volatile
        elif cls._gc_durability.value == 1:
            return Policy.Durability.TransientLocal
        elif cls._gc_durability.value == 2:
            return Policy.Durability.Transient
        return Policy.Durability.Persistent

    @static_c_call("dds_qget_durability")
    def _get_durability(self, qos: dds_c_t.qos_p, durability_kind: ct.POINTER(dds_c_t.durability)) -> bool:
        pass

    # History

    @classmethod
    def _get_p_history(cls, qos):
        if not cls._get_history(qos, ct.byref(cls._gc_history), ct.byref(cls._gc_history_depth)):
            return None

        if cls._gc_history.value == 1:
            return Policy.History.KeepAll
        return Policy.History.KeepLast(depth=cls._gc_history_depth.value)

    @static_c_call("dds_qget_history")
    def _get_history(self, qos: dds_c_t.qos_p, history_kind: ct.POINTER(dds_c_t.history),
                     depth: ct.POINTER(ct.c_int32)) -> bool:
        pass

    # Resource limits

    @classmethod
    def _get_p_resourcelimits(cls, qos):
        if not cls._get_resource_limits(
                qos, ct.byref(cls._gc_max_samples),
                ct.byref(cls._gc_max_instances),
                ct.byref(cls._gc_max_samples_per_instance)):
            return None

        return Policy.ResourceLimits(
            max_samples=cls._gc_max_samples.value,
            max_instances=cls._gc_max_instances.value,
            max_samples_per_instance=cls._gc_max_samples_per_instance.value
        )

    @static_c_call("dds_qget_resource_limits")
    def _get_resource_limits(self, qos: dds_c_t.qos_p, max_samples: ct.POINTER(ct.c_int32),
                             max_instances: ct.POINTER(ct.c_int32),
                             max_samples_per_instance: ct.POINTER(ct.c_int32)) -> bool:
        pass

    # Presentation access scope

    @classmethod
    def _get_p_presentationaccessscope(cls, qos):
        if not cls._get_presentation(
                qos, ct.byref(cls._gc_access_scope),
                ct.byref(cls._gc_coherent_access),
                ct.byref(cls._gc_ordered_access)):
            return None

        if cls._gc_access_scope.value == 0:
            return Policy.PresentationAccessScope.Instance(
                coherent_access=cls._gc_coherent_access.value,
                ordered_access=cls._gc_ordered_access.value
            )
        elif cls._gc_access_scope.value == 1:
            return Policy.PresentationAccessScope.Topic(
                coherent_access=cls._gc_coherent_access.value,
                ordered_access=cls._gc_ordered_access.value
            )
        return Policy.PresentationAccessScope.Group(
            coherent_access=cls._gc_coherent_access.value,
            ordered_access=cls._gc_ordered_access.value
        )

    @static_c_call("dds_qget_presentation")
    def _get_presentation(self, qos: dds_c_t.qos_p, access_scope: ct.POINTER(dds_c_t.presentation_access_scope),
                          coherent_access: ct.POINTER(ct.c_bool), ordered_access: ct.POINTER(ct.c_bool)) -> bool:
        pass

    # Lifespan

    @classmethod
    def _get_p_lifespan(cls, qos):
        if not cls._get_lifespan(qos, ct.byref(cls._gc_lifespan)):
            return None

        return Policy.Lifespan(lifespan=cls._gc_lifespan.value)

    @static_c_call("dds_qget_lifespan")
    def _get_lifespan(self, qos: dds_c_t.qos_p, lifespan: ct.POINTER(dds_c_t.duration)) -> bool:
        pass

    # Deadline

    @classmethod
    def _get_p_deadline(cls, qos):
        if not cls._get_deadline(qos, ct.byref(cls._gc_deadline)):
            return None

        return Policy.Deadline(deadline=cls._gc_deadline.value)

    @static_c_call("dds_qget_deadline")
    def _get_deadline(self, qos: dds_c_t.qos_p, deadline: ct.POINTER(dds_c_t.duration)) -> bool:
        pass

    # Latency Budget

    @classmethod
    def _get_p_latencybudget(cls, qos):
        if not cls._get_latency_budget(qos, ct.byref(cls._gc_latency_budget)):
            return None

        return Policy.LatencyBudget(budget=cls._gc_latency_budget.value)

    @static_c_call("dds_qget_latency_budget")
    def _get_latency_budget(self, qos: dds_c_t.qos_p, latency_budget: ct.POINTER(dds_c_t.duration)) -> bool:
        pass

    # Ownership

    @classmethod
    def _get_p_ownership(cls, qos):
        if not cls._get_ownership(qos, ct.byref(cls._gc_ownership)):
            return None

        if cls._gc_ownership.value == 0:
            return Policy.Ownership.Shared
        return Policy.Ownership.Exclusive

    @static_c_call("dds_qget_ownership")
    def _get_ownership(self, qos: dds_c_t.qos_p, ownership_kind: ct.POINTER(dds_c_t.ownership)) -> bool:
        pass

    # Ownership strength

    @classmethod
    def _get_p_ownershipstrength(cls, qos):
        if not cls._get_ownership_strength(qos, ct.byref(cls._gc_ownership_strength)):
            return None

        return Policy.OwnershipStrength(strength=cls._gc_ownership_strength.value)

    @static_c_call("dds_qget_ownership_strength")
    def _get_ownership_strength(self, qos: dds_c_t.qos_p, strength: ct.POINTER(ct.c_int32)) -> bool:
        pass

    # Liveliness

    @classmethod
    def _get_p_liveliness(cls, qos):
        if not cls._get_liveliness(qos, ct.byref(cls._gc_liveliness), ct.byref(cls._gc_lease_duration)):
            return None

        if cls._gc_liveliness.value == 0:
            return Policy.Liveliness.Automatic(lease_duration=cls._gc_lease_duration.value)
        if cls._gc_liveliness.value == 1:
            return Policy.Liveliness.ManualByParticipant(lease_duration=cls._gc_lease_duration.value)
        return Policy.Liveliness.ManualByTopic(lease_duration=cls._gc_lease_duration.value)

    @static_c_call("dds_qget_liveliness")
    def _get_liveliness(self, qos: dds_c_t.qos_p, liveliness_kind: ct.POINTER(dds_c_t.liveliness),
                        lease_duration: ct.POINTER(dds_c_t.duration)) -> bool:
        pass

    # Time based filter
    @classmethod
    def _get_p_timebasedfilter(cls, qos):
        if not cls._get_time_based_filter(qos, ct.byref(cls._gc_time_based_filter)):
            return None

        return Policy.TimeBasedFilter(filter_time=cls._gc_time_based_filter.value)

    @static_c_call("dds_qget_time_based_filter")
    def _get_time_based_filter(self, qos: dds_c_t.qos_p, minimum_separation: ct.POINTER(dds_c_t.duration)) -> bool:
        pass

    # Partition

    @classmethod
    def _get_p_partition(cls, qos):
        if not cls._get_partition(qos, ct.byref(cls._gc_partition_num), ct.byref(cls._gc_partition_names)):
            return None

        if cls._gc_partition_num.value == 0:
            return None

        names = [None] * cls._gc_partition_num.value
        for i in range(cls._gc_partition_num.value):
            names[i] = bytes(cls._gc_partition_names[i]).decode()

        return Policy.Partition(partitions=names)

    @static_c_call("dds_qget_partition")
    def _get_partition(self, qos: dds_c_t.qos_p, n: ct.POINTER(ct.c_uint32), ps: ct.POINTER(ct.POINTER(ct.c_char_p))) -> bool:
        pass

    # Transport priority

    @classmethod
    def _get_p_transportpriority(cls, qos):
        if not cls._get_transport_priority(qos, ct.byref(cls._gc_transport_priority)):
            return None

        return Policy.TransportPriority(priority=cls._gc_transport_priority.value)

    @static_c_call("dds_qget_transport_priority")
    def _get_transport_priority(self, qos: dds_c_t.qos_p, value: ct.POINTER(ct.c_int32)) -> bool:
        pass

    # Destination order

    @classmethod
    def _get_p_destinationorder(cls, qos):
        if not cls._get_destination_order(qos, ct.byref(cls._gc_destination_order)):
            return None

        if cls._gc_destination_order.value == 0:
            return Policy.DestinationOrder.ByReceptionTimestamp
        return Policy.DestinationOrder.BySourceTimestamp

    @static_c_call("dds_qget_destination_order")
    def _get_destination_order(self, qos: dds_c_t.qos_p,
                               destination_order_kind: ct.POINTER(dds_c_t.destination_order)) -> bool:
        pass

    # Writer data lifecycle

    @classmethod
    def _get_p_writerdatalifecycle(cls, qos):
        if not cls._get_writer_data_lifecycle(qos, ct.byref(cls._gc_writer_autodispose)):
            return None

        return Policy.WriterDataLifecycle(autodispose=cls._gc_writer_autodispose.value)

    @static_c_call("dds_qget_writer_data_lifecycle")
    def _get_writer_data_lifecycle(self, qos: dds_c_t.qos_p, autodispose: ct.POINTER(ct.c_bool)) -> bool:
        pass

    # Reader data lifecycle

    @classmethod
    def _get_p_readerdatalifecycle(cls, qos):
        if not cls._get_reader_data_lifecycle(qos, ct.byref(cls._gc_autopurge_nowriter_samples_delay),
                                              ct.byref(cls._gc_autopurge_disposed_samples_delay)):
            return None

        return Policy.ReaderDataLifecycle(
            autopurge_nowriter_samples_delay=cls._gc_autopurge_nowriter_samples_delay.value,
            autopurge_disposed_samples_delay=cls._gc_autopurge_disposed_samples_delay.value
        )

    @static_c_call("dds_qget_reader_data_lifecycle")
    def _get_reader_data_lifecycle(self, qos: dds_c_t.qos_p,
                                   autopurge_nowriter_samples_delay: ct.POINTER(dds_c_t.duration),
                                   autopurge_disposed_samples_delay: ct.POINTER(dds_c_t.duration)) -> bool:
        pass

    # Durability service

    @classmethod
    def _get_p_durabilityservice(cls, qos):
        if not cls._get_durability_service(
                qos,
                ct.byref(cls._gc_durservice_service_cleanup_delay),
                ct.byref(cls._gc_durservice_history_kind),
                ct.byref(cls._gc_durservice_history_depth),
                ct.byref(cls._gc_durservice_max_samples),
                ct.byref(cls._gc_durservice_max_instances),
                ct.byref(cls._gc_durservice_max_samples_per_instance)):
            return None

        if cls._gc_durservice_history_kind.value == 0:
            history = Policy.History.KeepLast(depth=cls._gc_durservice_history_depth.value)
        else:
            history = Policy.History.KeepAll

        return Policy.DurabilityService(
            cleanup_delay=cls._gc_durservice_service_cleanup_delay.value,
            history=history,
            max_samples=cls._gc_durservice_max_samples.value,
            max_instances=cls._gc_durservice_max_instances.value,
            max_samples_per_instance=cls._gc_durservice_max_samples_per_instance.value
        )

    @static_c_call("dds_qget_durability_service")
    def _get_durability_service(self, qos: dds_c_t.qos_p, service_cleanup_delay: ct.POINTER(dds_c_t.duration),
                                history_kind: ct.POINTER(dds_c_t.history), history_depth: ct.POINTER(ct.c_int32),
                                max_samples: ct.POINTER(ct.c_int32), max_instances: ct.POINTER(ct.c_int32),
                                max_samples_per_instance: ct.POINTER(ct.c_int32)) -> bool:
        pass

    # Ignore local

    @classmethod
    def _get_p_ignorelocal(cls, qos):
        if not cls._get_ignorelocal(qos, ct.byref(cls._gc_ignorelocal)):
            return None

        if cls._gc_ignorelocal.value == 0:
            return Policy.IgnoreLocal.Nothing
        if cls._gc_ignorelocal.value == 1:
            return Policy.IgnoreLocal.Participant
        return Policy.IgnoreLocal.Process

    @static_c_call("dds_qget_ignorelocal")
    def _get_ignorelocal(self, qos: dds_c_t.qos_p, ingorelocal_kind: ct.POINTER(dds_c_t.ingnorelocal)) -> bool:
        pass

    # Userdata

    @classmethod
    def _get_p_userdata(cls, qos):
        if not cls._get_userdata(qos, ct.byref(cls._gc_data_value), ct.byref(cls._gc_data_size)):
            return None

        if cls._gc_data_size.value == 0 or not bool(cls._gc_data_value):
            return None

        return Policy.Userdata(data=ct.string_at(cls._gc_data_value, cls._gc_data_size.value))

    @static_c_call("dds_qget_userdata")
    def _get_userdata(self, qos: dds_c_t.qos_p, value: ct.POINTER(ct.c_void_p), size: ct.POINTER(ct.c_size_t)) -> bool:
        pass

    # Topicdata

    @classmethod
    def _get_p_topicdata(cls, qos):
        if not cls._get_topicdata(qos, ct.byref(cls._gc_data_value), ct.byref(cls._gc_data_size)):
            return None

        if cls._gc_data_size.value == 0 or not bool(cls._gc_data_value):
            return None

        byte_type = ct.c_byte * cls._gc_data_size.value
        mybytes = bytes(ct.cast(cls._gc_data_value, ct.POINTER(byte_type))[0])

        return Policy.Topicdata(data=mybytes)

    @static_c_call("dds_qget_topicdata")
    def _get_topicdata(self, qos: dds_c_t.qos_p, value: ct.POINTER(ct.c_void_p), size: ct.POINTER(ct.c_size_t)) -> bool:
        pass

    # Groupdata

    @classmethod
    def _get_p_groupdata(cls, qos):
        if not cls._get_groupdata(qos, ct.byref(cls._gc_data_value), ct.byref(cls._gc_data_size)):
            return None

        if cls._gc_data_size == 0 or not bool(cls._gc_data_value):
            return None

        byte_type = ct.c_byte * cls._gc_data_size.value
        mybytes = bytes(ct.cast(cls._gc_data_value, ct.POINTER(byte_type))[0])

        return Policy.Groupdata(data=mybytes)

    @static_c_call("dds_qget_groupdata")
    def _get_groupdata(self, qos: dds_c_t.qos_p, value: ct.POINTER(ct.c_void_p), size: ct.POINTER(ct.c_size_t)) -> bool:
        pass

    # Properties

    @classmethod
    def _get_p_property(cls, qos):
        num = ct.c_size_t()
        names = ct.POINTER(ct.POINTER(ct.c_char))()
        if not cls._get_property_names(qos, ct.byref(num), ct.byref(names)):
            return None
        ret = []
        try:
            for i in range(num.value):
                name = ct.cast(names[i], ct.c_char_p)
                value = ct.c_char_p()
                if not cls._get_property_value(qos, name, ct.byref(value)):
                    raise Exception("Internal QOS property structure is corrupt!")
                ret.append(Policy.Property(name.value.decode("utf8"), value.value.decode("utf8")))
                cls.free(value)
        finally:
            for i in range(num.value):
                cls.free(names[i])
            cls.free(names)
        return ret

    @static_c_call("dds_qget_propnames")
    def _get_property_names(self, qos: dds_c_t.qos_p, num: ct.POINTER(ct.c_size_t),
                            names: ct.POINTER(ct.POINTER(ct.POINTER(ct.c_char)))) -> bool:
        pass

    @static_c_call("dds_qget_prop")
    def _get_property_value(self, qos: dds_c_t.qos_p, name: ct.c_char_p, value: ct.POINTER(ct.c_char_p)) -> bool:
        pass

    # Binary properties

    @classmethod
    def _get_p_binaryproperty(cls, qos):
        num = ct.c_size_t()
        names = ct.POINTER(ct.POINTER(ct.c_char))()
        if not cls._get_binaryproperty_names(qos, ct.byref(num), ct.byref(names)):
            return None
        ret = []
        try:
            for i in range(num.value):
                name = ct.cast(names[i], ct.c_char_p)
                value = ct.c_void_p()
                size = ct.c_size_t()
                if not cls._get_binaryproperty_value(qos, name, ct.byref(value), ct.byref(size)):
                    raise Exception("Internal QOS property structure is corrupt!")
                ret.append(Policy.BinaryProperty(name.value.decode("utf8"), ct.string_at(value, size.value)))
                cls.free(value)
        finally:
            for i in range(num.value):
                cls.free(names[i])
            cls.free(names)
        return ret

    @static_c_call("dds_qget_bpropnames")
    def _get_binaryproperty_names(self, qos: dds_c_t.qos_p, num: ct.POINTER(ct.c_size_t),
                                  names: ct.POINTER(ct.POINTER(ct.POINTER(ct.c_char)))) -> bool:
        pass

    @static_c_call("dds_qget_bprop")
    def _get_binaryproperty_value(self, qos: dds_c_t.qos_p, name: ct.c_char_p, value: ct.POINTER(ct.c_void_p),
                                  size: ct.POINTER(ct.c_size_t)) -> bool:
        pass

    # Type Consistency

    @classmethod
    def _get_p_typeconsistency(cls, qos):
        if not cls._get_type_consistency(qos, ct.byref(cls._gc_typecons_kind), ct.byref(cls._gc_typecons_iseqbounds),
                                         ct.byref(cls._gc_typecons_istrbounds), ct.byref(cls._gc_typecons_imemnames),
                                         ct.byref(cls._gc_typecons_itypewide), ct.byref(cls._gc_typecons_forceval)):
            return None

        if cls._gc_typecons_kind.value == 0:
            return Policy.TypeConsistency.DisallowTypeCoercion(
                force_type_validation=cls._gc_typecons_forceval.value
            )

        return Policy.TypeConsistency.AllowTypeCoercion(
            ignore_sequence_bounds=cls._gc_typecons_iseqbounds.value,
            ignore_string_bounds=cls._gc_typecons_istrbounds.value,
            ignore_member_names=cls._gc_typecons_imemnames.value,
            prevent_type_widening=cls._gc_typecons_itypewide.value,
            force_type_validation=cls._gc_typecons_forceval.value
        )

    @static_c_call("dds_qget_type_consistency")
    def _get_type_consistency(self, qos: dds_c_t.qos_p, type_consistency_kind: ct.POINTER(dds_c_t.type_consistency),
                              ignore_sequence_bounds: ct.POINTER(ct.c_bool), ignore_string_bounds: ct.POINTER(ct.c_bool),
                              ignore_member_names: ct.POINTER(ct.c_bool), prevent_type_widening: ct.POINTER(ct.c_bool),
                              force_type_validation: ct.POINTER(ct.c_bool)) -> bool:
        pass

    # Data Representation

    @classmethod
    def _get_p_datarepresentation(cls, qos):
        n = ct.c_uint32(0)
        values = ct.POINTER(dds_c_t.data_representation_id)()

        if not cls._get_data_representation(qos, ct.byref(n), ct.byref(values)):
            return None

        use_cdrv0 = False
        use_xcdrv2 = False
        for i in range(n.value):
            if values[i] == 0:
                use_cdrv0 = True
            elif values[i] == 2:
                use_xcdrv2 = True

        # Function docs of dds_qget_data_representation say the caller is responsible
        # for free'ing the buffer.
        cls.free(values)

        return Policy.DataRepresentation(use_cdrv0_representation=use_cdrv0, use_xcdrv2_representation=use_xcdrv2)

    @static_c_call("dds_qget_data_representation")
    def _get_data_representation(self, qos: dds_c_t.qos_p, n: ct.POINTER(ct.c_uint32),
                                 values: ct.POINTER(ct.POINTER(dds_c_t.data_representation_id))) -> bool:
        pass

    # Entity Name

    @classmethod
    def _get_p_entityname(cls, qos):
        if not cls._get_entity_name(qos, ct.byref(cls._gc_prop_get_value)):
            return None

        if cls._gc_prop_get_value is None or cls._gc_prop_get_value.value is None:
            return None

        if type(cls._gc_prop_get_value.value) != bytes:
            return None

        name = cls._gc_prop_get_value.value.decode('utf8')
        cls.free(cls._gc_prop_get_value)

        return Policy.EntityName(name=name)

    @static_c_call("dds_qget_entity_name")
    def _get_entity_name(self, qos: dds_c_t.qos_p, name: ct.POINTER(ct.c_char_p)) -> bool:
        pass
