import support_modules.test_classes as tc
import support_modules.test_rec_classes as trc



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
