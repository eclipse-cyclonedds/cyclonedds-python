from dataclasses import dataclass, field, InitVar
from enum import Enum, unique
from typing import Callable, List, Optional, Union
from .naming import Namer


@dataclass
class RObject:
    def depending(self) -> List['REntity']:
        pass

    def key_depending(self) -> List['REntity']:
        pass

    def type_check(self, l: Callable[['RType'], bool]) -> bool:
        pass


@dataclass
class REntity(RObject):
    name: str
    in_key_path: bool = field(init=False, default=False)


class RTypeDiscriminator(Enum):
    Simple = 0
    String = 1
    BoundedString = 2
    Sequence = 4
    BoundedSequence = 5
    Enumerator = 6
    Nested = 7

    @classmethod
    def weights(cls, no_enums):
        return [
            20,
            8,
            8,
            8,
            0, #todo: allow bounded seqs
            0 if no_enums else 1,
            1
        ]


class RExtensibility(Enum):
    NotSpecified = 0
    Final = 1
    Appendable = 2
    Mutable = 3


@dataclass
class RType(RObject):
    discriminator: RTypeDiscriminator
    name: Optional[str] = None
    inner: Optional['RType'] = None
    bound: Optional[int] = None
    reference: Optional['REntity'] = None
    duplex: bool = False

    def depending(self) -> List['REntity']:
        if self.duplex:
            return []

        if self.discriminator in [
            RTypeDiscriminator.Simple, RTypeDiscriminator.String, RTypeDiscriminator.BoundedString
            ]:
            return []
        if self.discriminator in [RTypeDiscriminator.Sequence, RTypeDiscriminator.BoundedSequence]:
            return self.inner.depending()
        if self.discriminator in [RTypeDiscriminator.Enumerator, RTypeDiscriminator.Nested]:
            return [self.reference] + self.reference.depending()

    def key_depending(self) -> List['REntity']:
        if self.discriminator in [
            RTypeDiscriminator.Simple, RTypeDiscriminator.String, RTypeDiscriminator.BoundedString
            ]:
            return []
        if self.discriminator in [RTypeDiscriminator.Sequence, RTypeDiscriminator.BoundedSequence]:
            return self.inner.key_depending()
        if self.discriminator in [RTypeDiscriminator.Enumerator, RTypeDiscriminator.Nested]:
            return [self.reference] + self.reference.key_depending()

    def type_check(self, l: Callable[['RType'], bool]) -> bool:
        if self.discriminator in [
            RTypeDiscriminator.Simple, RTypeDiscriminator.String, RTypeDiscriminator.BoundedString
            ]:
            return l(self)
        if self.discriminator in [RTypeDiscriminator.Sequence, RTypeDiscriminator.BoundedSequence]:
            return l(self) and self.inner.type_check(l)
        if self.discriminator in [RTypeDiscriminator.Enumerator, RTypeDiscriminator.Nested]:
            return l(self) and self.reference.type_check(l)

@dataclass
class RField(RObject):
    name: str
    annotations: List[str]
    type: RType
    array_bound: Optional[List[int]]

    def depending(self) -> List['REntity']:
        return self.type.depending()

    def key_depending(self) -> List['REntity']:
        return self.type.key_depending() if "key" in self.annotations else []

    def type_check(self, l: Callable[['RType'], bool]) -> bool:
        return self.type.type_check(l)

@dataclass
class RCase(RObject):
    labels: List[Union[int, str]]
    field: RField

    def depending(self) -> List['REntity']:
        return self.field.depending()

    def key_depending(self) -> List['REntity']:
        return self.field.key_depending()

    def type_check(self, l: Callable[['RType'], bool]) -> bool:
        return self.field.type_check(l)


@dataclass
class REnumEntry(RObject):
    name: str
    value: Optional[int] = None

    def depending(self) -> List['REntity']:
        return []

    def key_depending(self) -> List['REntity']:
        return []

    def type_check(self, l: Callable[['RType'], bool]) -> bool:
        return True


@dataclass
class RBitmaskEntry(RObject):
    name: str
    position: Optional[int] = None

    def depending(self) -> List['REntity']:
        return []

    def key_depending(self) -> List['REntity']:
        return []

    def type_check(self, l: Callable[['RType'], bool]) -> bool:
        return True


@dataclass
class RStruct(REntity):
    scope: 'RScope'
    extensibility: RExtensibility
    fields: List[RField]
    annotations: List[str] = field(default_factory=list)

    def depending(self) -> List['REntity']:
        rt = []
        for k in sum((f.depending() for f in self.fields), []):
            if k not in rt:
                rt.append(k)
        return rt

    def key_depending(self) -> List['REntity']:
        rt = []
        for k in sum((f.key_depending() for f in self.fields), []):
            if k not in rt:
                rt.append(k)
        return rt

    def type_check(self, l: Callable[['RType'], bool]) -> bool:
        return all(f.type_check(l) for f in self.fields)

    def keyless(self):
        return all('key' not in field.annotations for field in self.fields)


@dataclass
class RUnion(REntity):
    scope: 'RScope'
    extensibility: RExtensibility
    discriminator: RType
    discriminator_is_key: bool
    cases: List[RCase]
    default: Optional[RField]

    def depending(self) -> List['REntity']:
        return self.discriminator.depending() + \
         sum((f.depending() for f in self.cases), []) + \
         ([] if self.default is None else self.default.depending())

    def key_depending(self) -> List['REntity']:
        if self.discriminator_is_key:
            return self.discriminator.key_depending()

        return self.discriminator.key_depending() + \
         sum((f.key_depending() for f in self.cases), []) + \
         ([] if self.default is None else self.default.key_depending())

    def type_check(self, l: Callable[['RType'], bool]) -> bool:
        return all(f.type_check(l) for f in self.cases) and (self.default is None or self.default.type_check(l))


@dataclass
class REnumerator(REntity):
    scope: 'RScope'
    fields: List[REnumEntry]
    bit_bound: Optional[int] = None

    def depending(self) -> List['REntity']:
        return sum((f.depending() for f in self.fields), [])

    def key_depending(self) -> List['REntity']:
        return sum((f.key_depending() for f in self.fields), [])

    def type_check(self, l: Callable[['RType'], bool]) -> bool:
        return True


@dataclass
class RBitmask(REntity):
    scope: 'RScope'
    fields: List[RBitmaskEntry]
    bit_bound: Optional[int] = None

    def depending(self) -> List['REntity']:
        return sum((f.depending() for f in self.fields), [])

    def key_depending(self) -> List['REntity']:
        return sum((f.key_depending() for f in self.fields), [])

    def type_check(self, l: Callable[['RType'], bool]) -> bool:
        return True


@dataclass
class RTypedef(REntity):
    scope: 'RScope'
    rtype: RType
    array_bound: Optional[List[int]]

    def depending(self) -> List['REntity']:
        return self.rtype.depending()

    def key_depending(self) -> List['REntity']:
        return self.rtype.key_depending()

    def type_check(self, l: Callable[['RType'], bool]) -> bool:
        return self.rtype.type_check(l)


@dataclass
class RScope(REntity):
    seed: InitVar[int]
    parent: InitVar[Optional['RScope']] = None
    namer: Namer = field(init=False)
    entities: List[REntity] = field(default_factory=list)
    topics: List[REntity] = field(default_factory=list)

    def __post_init__(self, seed, parent=None):
        self.namer = Namer(seed=seed, prefix="", parent=None if parent is None else parent.namer)

    def depending(self) -> List['REntity']:
        return sum(([topic] + topic.depending() for topic in self.topics), [])

    def key_depending(self) -> List['REntity']:
        return sum(([topic] + topic.key_depending() for topic in self.topics), [])

    def type_check(self, l: Callable[['RType'], bool]) -> bool:
        return all(topic.type_check() for topic in self.topics)
