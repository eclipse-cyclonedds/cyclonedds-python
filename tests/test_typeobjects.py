from hashlib import md5

from cyclonedds.idl import annotations as annotate
from cyclonedds.idl import IdlUnion, types

import support_modules.test_classes as tc
import support_modules.test_rec_classes as trc


class UnionWithRenamedMember(IdlUnion, discriminator=bool):
    _value: types.case[[True], str]
    annotate.member_name("_value", "value")


def test_type_objects_and_mappings():
    for _type in tc.alltypes + trc.alltypes:
        instance = _type.__idl__.get_type_info()

        if instance is None:
            continue

        instance = instance.__class__.deserialize(instance.serialize())
        assert instance == instance.__class__.deserialize(instance.serialize())
        instance = _type.__idl__.get_type_mapping()
        instance = instance.__class__.deserialize(instance.serialize())
        assert instance == instance.__class__.deserialize(instance.serialize())


def test_deduplication_of_minimal_typeids_in_typeinfo():
    container_info = tc.ContainSameTypes.__idl__.get_type_info()
    assert container_info.minimal.dependent_typeid_count + 1 == \
           container_info.complete.dependent_typeid_count


def test_minimal_union_member_uses_idl_name():
    type_mapping = UnionWithRenamedMember.__idl__.get_type_mapping()
    type_object = type_mapping.identifier_object_pair_minimal[0].type_object
    member = type_object.value.value.member_seq[0]

    assert member.detail.name_hash == md5(b"value").digest()[:4]
