from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Set
from cyclonedds.qos import Qos
from cyclonedds.idl._typesupport.DDS.XTypes import TypeIdentifier


@dataclass
class DiscoveredType:
    type_id: TypeIdentifier
    dtype: Any
    code: str
    nested_dtypes: Dict[str, Any]
    participants: Set[str]


@dataclass
class TypeDiscoveryData:
    types: Dict[TypeIdentifier, DiscoveredType] = field(default_factory=dict)
    topic_qosses: List[Qos] = field(default_factory=list)
    writer_qosses: List[Qos] = field(default_factory=list)
    reader_qosses: List[Qos] = field(default_factory=list)

    def add_type_id(self, participant, _type: TypeIdentifier):
        if _type not in self.types:
            self.types[_type] = DiscoveredType(_type, None, "", {}, set((participant,)))
        else:
            self.types[_type].participants.add(participant)

    def split_qos(self, qosses: List[Qos]) -> Tuple[Qos, List[Qos]]:
        if not qosses:
            return Qos(), []

        if len(qosses) == 1:
            return qosses[0], []

        head, tail = qosses[0], qosses[1:]
        shared = []

        for policy in head:
            for other in tail:
                if policy not in other:
                    break
                if policy != other[policy]:
                    break
            else:
                shared.append(policy)

        shared = Qos(*shared)

        separate = []

        for policy in qosses:
            uniq = policy - shared
            if policy != shared and uniq not in separate:
                separate.append(uniq)

        if len(separate) == 1:
            separate = []

        return shared, separate
