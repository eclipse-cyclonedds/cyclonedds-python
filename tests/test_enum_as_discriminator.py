from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import DataWriter
from cyclonedds.idl import IdlEnum, IdlUnion
from cyclonedds.idl.types import case


class MyEnum(IdlEnum):
    A = 1
    B = 0


class MyUnion(IdlUnion, discriminator=MyEnum):
    a: case[MyEnum.A, int]
    b: case[MyEnum.B, str]


def test_enum_as_discriminator():
    dp = DomainParticipant(0)
    tp = Topic(dp, 'EnumDiscrTopic', MyUnion)
    dw = DataWriter(dp, tp)
    dw.write(MyUnion(a=9))
    dw.write(MyUnion(b="Hello"))
