from random import Random, randint
from string import ascii_letters, ascii_lowercase
from importlib import import_module
from inspect import isclass

from cyclonedds.idl import IdlStruct, IdlUnion
from cyclonedds.idl.types import int8, int16, int32, int64, uint8, uint16, uint32, uint64, char, \
                                 float32, float64, sequence, array, case, default, bounded_str

from cyclonedds.idl._type_helper import get_args, get_origin, get_type_hints


def _random_for_primitive_type(random: Random, _type):
    if _type == bool:
        return random.choice([True, False])
    if _type == int8:
        return random.randint(-128, 127)
    if _type == uint8:
        return random.randint(0, 255)
    if _type == int16:
        return random.randint(-32_768, 32_767)
    if _type == uint16:
        return random.randint(0, 65_535)
    if _type == int32:
        return random.randint(-2_147_483_648, 2_147_483_647)
    if _type == uint32:
        return random.randint(0, 4_294_967_295)
    if _type == int64:
        return random.randint(-9223372036854775808, 9223372036854775807)
    if _type == uint64:
        return random.randint(0, 18446744073709551615)
    if _type in [float32, float64]:
        return random.random()
    if _type == str:
        return "".join(random.choices(ascii_lowercase, k=random.randint(0, 20)))
    if _type == char:
        return random.choice(ascii_letters)

    try:
        ctype = get_args(_type)[1]
    except Exception as e:
        raise Exception(f"Could not make value for {_type}") from e


    if isinstance(ctype, bounded_str):
        return "".join(random.choices(ascii_lowercase, k=random.randint(0, ctype.max_length - 1)))
    if isinstance(ctype, array):
        return [_random_value_for(random, ctype.subtype) for i in range(ctype.length)]
    if isinstance(ctype, sequence):
        return [_random_value_for(random, ctype.subtype) for i in range(
            random.randint(0, ctype.max_length) if ctype.max_length else random.randint(0, 20)
        )]

    raise Exception(f"Could not make value for {_type}")


def _random_value_for(random: Random, _type):
    if isclass(_type) and issubclass(_type, IdlStruct):
        values = {}
        for member_name, member_type in get_type_hints(_type, include_extras=True).items():
            values[member_name] = _random_value_for(random, member_type)
        return _type(**values)

    if isclass(_type) and issubclass(_type, IdlUnion):
        if _type.__idl_default__ is not None and random.random() < 0.1:
            active_name, active_type = _type.__idl_default__
        else:
            active_name, active_type = random.choice(list(_type.__idl_cases__.values()))

        return _type(**{active_name: _random_value_for(random, active_type)})

    if type(_type) == str:
        try:
            rname, rmodule = _type[::-1].split(".", 1)
            name, module = rname[::-1], rmodule[::-1]
            pymodule = import_module(module)
            return _random_value_for(random, getattr(pymodule, name))
        except:
            pass

    return _random_for_primitive_type(random, _type)


def generate_random_instance(cls, seed=None):
    seed = seed if seed is not None else randint(0, 1_000_000_000)
    random = Random(seed)
    return _random_value_for(random, cls)
