from itertools import product
from random import Random, randint
from string import ascii_uppercase,  ascii_lowercase


def _make_name(random: Random):
    consonants = "wrtpsdfgklzcvbnm"
    biconsonants = ["tr", "st", "sr", "pr", "pl", "sl", "kr", "kl", "kn", "dr", "wh"]
    vowels = "euioa"
    sgrams = ["".join(p) for p in product(biconsonants, vowels)] + [""] * (len(biconsonants) * len(vowels))
    bigrams = ["".join(p) for p in product(consonants, vowels)]
    trigrams = ["".join(p) for p in product(consonants, vowels, consonants)]
    return "".join([random.choice(sgrams)] + random.choices(bigrams, k=random.randint(1, 4)) + [random.choice(trigrams)]).capitalize()


def _make_field_type_nonest(random):
    return random.choice([
        "octet", "char", "short", "unsigned short", "long",
        "unsigned long", "long long", "unsigned long long", "boolean",
        "float", "double"
    ])


def _make_field_type(random, collector, max_depth=3, key=False):
    if max_depth <= 0:
        if not key and random.random() < 0.05:
            return "string"
        return _make_field_type_nonest(random)

    v = random.random()

    if key and max_depth == 2 and v < 0.04:
        return f"string<{random.randint(1, 5)}>"

    if not key and max_depth > 0 and v < 0.08:
        name = _make_name(random)
        collector.append(_make_struct(random, collector, name, max_depth-1))
        return name

    if not key and max_depth > 0 and v < 0.12:
        name = _make_name(random)
        collector.append(_make_union(random, collector, name, max_depth-1))
        return name

    if max_depth > 0 and v < 0.18:
        name = _make_name(random)
        collector.append(f"typedef {_make_field_type(random, collector, max_depth-1, key)} {name}[{random.randint(3, 20)}];\n")
        return name

    if not key and max_depth > 0 and v < 0.22:
        name = _make_name(random)
        collector.append(f"typedef sequence<{_make_field_type(random, collector, max_depth-1)}> {name};\n")
        return name

    """ Need bounded sequence support for this:
    if max_depth > 0 and v < 0.26:
        name = _make_name(random)
        collector.append(f"typedef sequence<{_make_field_type(random, collector, max_depth-1)}, {random.randint(3, 20)}> {name};\n")
        return name
    """

    if not key and max_depth > 0 and v < 0.28:
        name = _make_name(random)
        collector.append(f"typedef string<{random.randint(2, 20)}> {name};\n")
        return name

    if not key and random.random() < 0.05:
        return "string"

    return _make_field_type_nonest(random)


def _make_struct(random, collector, typename, max_depth=3):
    out = f"struct {typename} {{\n"
    number_of_fields = random.randint(2, 12)

    for i in range(number_of_fields):
        do_key = (random.random() < 0.2) or (i == number_of_fields - 1)
        at_key = "@key " if do_key else ""
        out += f"\t{at_key}{_make_field_type(random, collector, max_depth-1, key=do_key)} {ascii_lowercase[i]};\n"

    out += "\n};\n"
    return out


def _make_union(random, collector, typename, max_depth=3):
    discriminator = random.choice([
        "long", "unsigned long",
        "short", "unsigned short"
    ])

    key = "" if random.random() > 0.3 else "@key "

    out = f"union {typename} switch ({key}{discriminator}) {{\n"

    for i in range(random.randint(2, 12)):
        out += f"\tcase {i+1}:\n\t\t{_make_field_type(random, collector, 0)} {ascii_lowercase[i]};\n"

    if random.random() > 0.5:
        out += f"\tdefault:\n\t\t{_make_field_type(random, collector, 0)} z;\n"

    out += "\n};\n"
    return out


def random_idl_types(seed=None, module=None, number=None):
    seed = seed if seed is not None else randint(0, 1_000_000_000)
    random = Random(seed)
    module = module if module else "py_c_compat"
    number = number if number else 1

    names = []

    collector = []
    for i in range(number):
        name = _make_name(random)
        collector.append(_make_struct(random, collector, name))
        names.append(name)

    pre = f"""/*
 * Random datatype generation by fuzzy_idl_definition.py
 * Types: {', '.join(names)}
 * Seed: {seed}
 */

module {module} {{\n\n"""
    post = "\n};\n"

    return pre + "\n".join(collector) + post, names
