from random import Random, randint
from string import ascii_letters, ascii_lowercase
from importlib import import_module
from inspect import isclass
from struct import pack, unpack

from cyclonedds.idl import IdlStruct, IdlUnion, IdlBitmask, IdlEnum
from cyclonedds.idl.types import int8, int16, int32, int64, uint8, uint16, uint32, uint64, char, byte, \
                                 float32, float64, sequence, array, bounded_str, typedef

from cyclonedds.idl._type_normalize import get_extended_type_hints, WrapOpt


def _random_for_primitive_type(random: Random, _type):
    if _type == bool:
        return random.choice([True, False])
    if _type == int8:
        return random.randint(-128, 127)
    if _type in [uint8, byte]:
        return random.randint(0, 255)
    if _type == int16:
        return random.randint(-32_768, 32_767)
    if _type == uint16:
        return random.randint(0, 65_535)
    if _type == int32:
        return random.randint(-2_147_483_648, 2_147_483_647)
    if _type == uint32:
        return random.randint(0, 4_294_967_295)
    if _type in [int, int64]:
        return random.randint(-9223372036854775808, 9223372036854775807)
    if _type == uint64:
        return random.randint(0, 18446744073709551615)
    if _type == float32:
        return unpack("@f", pack("@f", random.random()))[0]
    if _type in [float, float64]:
        return unpack("@d", pack("@d", random.random()))[0]
    if _type == str:
        return "".join(random.choices(ascii_lowercase, k=random.randint(0, 6)))
    if _type == char:
        return random.choice(ascii_letters)

    if isinstance(_type, bounded_str):
        return "".join(random.choices(ascii_lowercase, k=random.randint(0, _type.max_length - 1)))
    if isinstance(_type, array):
        return [_random_value_for(random, _type.subtype) for i in range(_type.length)]
    if isinstance(_type, sequence):
        return [_random_value_for(random, _type.subtype) for i in range(
            random.randint(0, _type.max_length) if _type.max_length else random.randint(0, 6)
        )]
    if isinstance(_type, typedef):
        return _random_value_for(random, _type.subtype)
    if isinstance(_type, WrapOpt):
        if random.random() > 0.5:
            return None
        return _random_value_for(random, _type.inner)

    raise Exception(f"Could not make value for {_type}")


def _random_value_for(random: Random, _type):
    if isclass(_type) and (issubclass(_type, IdlStruct) or issubclass(_type, IdlBitmask)):
        values = {}
        for member_name, member_type in get_extended_type_hints(_type).items():
            values[member_name] = _random_value_for(random, member_type)
        return _type(**values)

    if isclass(_type) and issubclass(_type, IdlUnion):
        active_name, active_type = random.choice(list(get_extended_type_hints(_type).items()))
        active_type = active_type.subtype  # strip off default[] or case[]

        return _type(**{active_name: _random_value_for(random, active_type)})

    if isclass(_type) and issubclass(_type, IdlEnum):
        return random.choice([e for e in _type])

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
