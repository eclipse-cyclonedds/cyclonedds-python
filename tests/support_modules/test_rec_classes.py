from cyclonedds.idl import IdlStruct, IdlUnion
from cyclonedds.idl.types import case, default
from dataclasses import dataclass
from typing import Optional


class OptNode(IdlUnion, discriminator=bool):
    node: case[True, 'Node']
    nothing: default[None]


@dataclass
class Node(IdlStruct):
    left: OptNode
    right: OptNode
    value: int



@dataclass
class CNode(IdlStruct):
    value: int
    left: Optional['CNode'] = None
    right: Optional['CNode'] = None

    def add(self, value):
        if value > self.value:
            if self.right:
                self.right.add(value)
            else:
                self.right = CNode(value=value)
        elif value < self.value:
            if self.left:
                self.left.add(value)
            else:
                self.left = CNode(value=value)

        return self


alltypes = [
    CNode,
    OptNode,
    Node
]
