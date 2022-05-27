from dataclasses import dataclass
import pytest

import cyclonedds.internal
from cyclonedds.dynamic import get_types_for_typeid
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import DataWriter
from cyclonedds.sub import DataReader
from cyclonedds.util import duration
from cyclonedds.idl import IdlStruct, types as pt

from support_modules.test_fullxcdr2_classes import XBitmask, XEnum, XStruct, XUnion


if not cyclonedds.internal.feature_type_discovery:
    pytest.skip("Skipping tests that have to do with dynamic typing since type discovery is disabled.", allow_module_level=True)


def test_dynamic_subscribe(common_setup):
    type_id = common_setup.tp.data_type.__idl__.get_type_id()

    dp = DomainParticipant(common_setup.dp.domain_id)
    datatype, _ = get_types_for_typeid(dp, type_id, duration(seconds=1))
    assert datatype

    tp = Topic(dp, common_setup.tp.name, datatype)
    dr = DataReader(dp, tp)

    common_setup.dw.write(common_setup.msg)

    assert dr.read()[0].message == common_setup.msg.message


def test_dynamic_subscribe_complex():
    dp = DomainParticipant()
    tp = Topic(dp, 'DynTest', XStruct)
    wr = DataWriter(dp, tp)

    type_id = XStruct.__idl__.get_type_id()
    datatype, tmap = get_types_for_typeid(dp, type_id, duration(seconds=1))
    assert datatype
    assert datatype.__idl__.get_type_id() == XStruct.__idl__.get_type_id()

    tp = Topic(dp, 'DynTest', datatype)
    dr = DataReader(dp, tp)

    wr.write(XStruct(A=XUnion(A=XEnum.V1), k=1))

    assert dr.read()[0].k == 1



def test_dynamic_publish_complex():
    dp = DomainParticipant()
    tp = Topic(dp, 'DynTest', XStruct)
    rd = DataReader(dp, tp)

    type_id = XStruct.__idl__.get_type_id()
    datatype, tmap = get_types_for_typeid(dp, type_id, duration(seconds=1))
    assert datatype
    assert datatype.__idl__.get_type_id() == XStruct.__idl__.get_type_id()

    tp = Topic(dp, 'DynTest', datatype)
    wr = DataWriter(dp, tp)

    wr.write(datatype(A=tmap['XUnion'](A=tmap['XEnum'].V1), k=1))

    assert rd.read()[0].k == 1


def test_dynamic_repeated_typedef_array():
    arrtype = pt.typedef["arrtype", pt.array[int, 2]]

    @dataclass
    class Foo(IdlStruct):
        foo: arrtype
        bar: arrtype

    dp = DomainParticipant()
    tp = Topic(dp, "DynTest", Foo)
    rd = DataReader(dp, tp)

    d, w = get_types_for_typeid(dp, Foo.__idl__.get_type_id(), duration(seconds=1))
    tp2 = Topic(dp, "DynTest", d)
    wr = DataWriter(dp, tp2)

    wr.write(d([1,2], [1,2]))
    assert rd.read()[0].foo[0] == 1

