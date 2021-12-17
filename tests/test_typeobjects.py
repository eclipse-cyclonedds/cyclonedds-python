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
