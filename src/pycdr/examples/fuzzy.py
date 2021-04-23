from dataclasses import make_dataclass, fields
from typing import get_args
from pycdr.types import int8, int16, int32, int64, uint8, uint16, uint32, uint64, float32, float64, \
    sequence, array, bound_str, make_union, case, default, ArrayHolder, SequenceHolder, BoundStringHolder
from string import ascii_letters, ascii_lowercase, ascii_uppercase
import random
from pycdr import cdr
import cyclonedds.core
from ddspy import ddspy_calc_key
import sys
import traceback

from pycdr.support import Buffer, Endianness


def keyformat(key):
    return ' '.join('{:02x}'.format(x) for x in key)


def value_for(type):
    if type == bool:
        return random.choice([True, False])
    if type == int8:
        return random.randint(-128, 127)
    if type == uint8:
        return random.randint(0, 255)
    if type == int16:
        return random.randint(-32_768, 32_767)
    if type == uint16:
        return random.randint(0, 65_535)
    if type == int32:
        return random.randint(-2_147_483_648, 2_147_483_647)
    if type == uint32:
        return random.randint(0, 4_294_967_295)
    if type == int64:
        return random.randint(-9223372036854775808, 9223372036854775807)
    if type == uint64:
        return random.randint(0, 18446744073709551615)
    if type == float64:
        return random.random()
    if type == str:
        return "".join(random.choices(ascii_lowercase, k=random.randint(0, 20)))

    if hasattr(type, 'randomizer'):
        return type.randomizer()

    try:
        ctype = get_args(type)[1]

        if isinstance(ctype, BoundStringHolder):
            return "".join(random.choices(ascii_lowercase, k=random.randint(0, ctype.max_length)))
        if isinstance(ctype, ArrayHolder):
            return [value_for(ctype.type) for i in range(ctype.length)]
        if isinstance(ctype, SequenceHolder):
            return [value_for(ctype.type) for i in range(random.randint(0, ctype.max_length) if ctype.max_length else random.randint(0, 20))]
    except Exception as e:
        print(e)
        traceback.print_exc()
    raise Exception(f"Could not make value for {type}")


def random_field_type_nonest():
    return random.choice([
        int8, int16, int32, int64,
        uint8, uint16, uint32, uint64, bool,
        float64, str, bound_str[random.randint(1, 20)]
    ])

def random_field_type(max_depth=3):
    if max_depth <= 0:
        return random_field_type_nonest()

    v = random.random()
    if max_depth > 0 and v < 0.02:
        return random_struct_type(max_depth-1)
    if max_depth > 0 and v < 0.04:
        return random_union(max_depth-1)
    return random.choice([
        int8, int16, int32, int64,
        uint8, uint16, uint32, uint64, bool,
        float64, str, bound_str[random.randint(1, 15)],
        sequence[random_field_type(max_depth-1)], sequence[random_field_type(max_depth-1), random.randint(10, 20)],
        array[random_field_type(max_depth-1), random.randint(3, 20)]
    ])

def random_struct_type(max_depth=3):
    field_num = random.randint(1, 5)
    names = random.sample(ascii_lowercase, k=field_num)
    types = [random_field_type(max_depth-1) for i in range(field_num)]
    keylist = random.choice([random.sample(names, k=random.randint(1, max(1, field_num-1))), None])
    cls = cdr(keylist=keylist)(make_dataclass("".join(random.choices(ascii_uppercase, k=20)), zip(names, types)))
    def randomizer():
        return cls(**{
            name: value_for(type) for (name, type) in zip(names, types)
        })
    cls.randomizer = staticmethod(randomizer)
    return cls

def random_union(max_depth=3):
    discriminator = random.choice([
        int8, int16, int32, int64,
        uint8, uint16, uint32, uint64,
    ])
    name = "".join(random.choices(ascii_letters, k=10))
    field_num = random.randint(1, 5)
    names = random.sample(ascii_lowercase, k=field_num)
    types = [random_field_type(max_depth-1) for i in range(field_num)]
    values = set()
    while len(values) < len(types):
        values.add(value_for(discriminator))
    cases = [case[value, field_type] for (value, field_type) in zip(values, types)]

    if random.random() > 0.5:
        names.append("def")
        types.append(random_field_type(max_depth-1))
        cases.append(default[types[-1]])

    cls = make_union(name, discriminator, {name: case for (name, case) in zip(names, cases)}, random.choice([True, False]))
    def randomizer():
        index = random.randint(0, len(names)-1)
        data = {names[index]: value_for(types[index])}
        return cls(**data)
    cls.randomizer = staticmethod(randomizer)
    return cls


i = 0

buffer = Buffer()

while i < 10:
    print(f"\r{i}", end='', flush=True)
    random.seed(i)
    i += 1
    cls = random_struct_type()

    for j in range(20):
        v = cls.randomizer()
        buffer.seek(0)
        buffer.set_endianness(Endianness.Big if random.random() > 0.5 else Endianness.Little)

        try:
            data = v.serialize(buffer=buffer)
        except:
            print("Serialization error")
            print(", ".join(f"{f.name}: {f.type.__name__ if '__name__' in dir(f.type) else repr(f.type)}" for f in fields(v)))
            print(v)
            print(buffer.asbytes())
            traceback.print_exc()
            sys.exit(1)

        try:
            v2 = cls.deserialize(data)
        except:
            print("Deserialization error")
            print(", ".join(f"{f.name}: {f.type}" for f in fields(v)))
            print(v)
            print(data)
            traceback.print_exc()
            sys.exit(1)

        try:
            assert v == v2
        except:
            print("Deserialization equality failure")
            print(", ".join(f"{f.name}: {f.type.__name__ if '__name__' in dir(f.type) else repr(f.type)}" for f in fields(v)))
            print(v)
            print(v2)
            print(data)
            sys.exit(1)

        try:
            k1 = cls.cdr.key(v)
            k2 = ddspy_calc_key(cls.cdr, data)
        except:
            print("Key calc error")
            print(", ".join(f"{f.name}: {f.type.__name__ if '__name__' in dir(f.type) else repr(f.type)}" for f in fields(v)))
            print(v)
            traceback.print_exc()
            sys.exit(1)

        try:
            assert k1 == k2
        except:
            print("Key deviation error")
            print(", ".join(f"{f.name}: {f.type.__name__ if '__name__' in dir(f.type) else repr(f.type)}" for f in fields(v)))
            print(v)

            with open('a.bin', 'wb') as f:
                f.write(k1)
            with open('b.bin', 'wb') as f:
                f.write(k2)

            print("optable")
            for op in cls.cdr.cdr_key_machine():
                print(f"\t{op}")
            print()
            sys.exit(1)



