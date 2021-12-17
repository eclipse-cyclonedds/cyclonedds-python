from typing import Tuple, List, Union
from random import Random
import string
from . import containers as cn


def get_value_assortment(ftype: cn.RType, max_amount: int, random: Random) -> List[int]:
    """Return up to max_amount integer that fit in ftype."""

    assert ftype.discriminator in [cn.RTypeDiscriminator.Simple, cn.RTypeDiscriminator.Enumerator]

    if ftype.discriminator == cn.RTypeDiscriminator.Enumerator:
        values = [f.name for f in ftype.reference.fields]
        if len(values) <= max_amount:
            return values
        return random.choices(values, k=max_amount)

    if ftype.name == "char":
        # special case for chars
        values = [f"'{c}'" for c in string.ascii_letters]
        if len(values) <= max_amount:
            return values
        return random.choices(values, k=max_amount)

    domain = {
        "octet": [0, 255],
        "short": [0, 32767],
        "unsigned short": [0, 65535],
        "long": [0, 2147483647],
        "unsigned long": [0, 2147483647] # TODO: case label range should be larger
    }[ftype.name]

    rvalues = set()
    while len(rvalues) < max_amount:
        rvalues.add(random.randint(*domain))

    return list(rvalues)


def resolved(type_a: cn.RType):
    if type_a.discriminator == cn.RTypeDiscriminator.Nested and isinstance(type_a.reference, cn.RTypedef):
        return resolved(type_a.reference.rtype)
    return type_a


def type_assignable(type_a: cn.RType, type_b: cn.RType):
    # This is not full assignability checking, only used to generate two types that are definitely incompatible
    type_a = resolved(type_a)
    type_b = resolved(type_b)

    if type_a == type_b:
        return True

    # Stringy types
    if type_a.discriminator in [cn.RTypeDiscriminator.String, cn.RTypeDiscriminator.BoundedString]:
        if type_b.discriminator in [cn.RTypeDiscriminator.String, cn.RTypeDiscriminator.BoundedString]:
            return True
        if type_b.discriminator in [cn.RTypeDiscriminator.Sequence, cn.RTypeDiscriminator.BoundedSequence]:
            type_b_inner = resolved(type_b.inner)
            if type_b_inner.discriminator == cn.RTypeDiscriminator.Simple and type_b_inner.name == "char":
                return True
    if type_b.discriminator in [cn.RTypeDiscriminator.String, cn.RTypeDiscriminator.BoundedString]:
        if type_a.discriminator in [cn.RTypeDiscriminator.Sequence, cn.RTypeDiscriminator.BoundedSequence]:
            type_a_inner = resolved(type_a.inner)
            if type_a_inner.discriminator == cn.RTypeDiscriminator.Simple and type_a_inner.name == "char":
                return True

    # Sequency types
    if type_a.discriminator in [cn.RTypeDiscriminator.Sequence, cn.RTypeDiscriminator.BoundedSequence]:
        if type_b.discriminator in [cn.RTypeDiscriminator.Sequence, cn.RTypeDiscriminator.BoundedSequence]:
            return type_assignable(type_a.inner, type_b.inner)

    # Enumeratory types
    if type_a.discriminator == cn.RTypeDiscriminator.Enumerator:
        if type_b.discriminator in [cn.RTypeDiscriminator.Enumerator, cn.RTypeDiscriminator.Simple]:
            return True
    if type_b.discriminator == cn.RTypeDiscriminator.Enumerator:
        if type_a.discriminator in [cn.RTypeDiscriminator.Enumerator, cn.RTypeDiscriminator.Simple]:
            return True

    # Simple types
    if type_a.discriminator == cn.RTypeDiscriminator.Simple and type_b.discriminator == cn.RTypeDiscriminator.Simple:
        if type_a.name == type_b.name:
            return True

        if type_a.name in ["octet", "char"] and type_b.name in ["octet", "char"]:
            return True

        return False

    # Nested
    if type_a.discriminator == cn.RTypeDiscriminator.Nested and type_b.discriminator == cn.RTypeDiscriminator.Nested:
        # Again, only to generate incompatible types, no need to be super careful here
        if isinstance(type_a.reference, cn.RStruct) and isinstance(type_b.reference, cn.RStruct):
            return True
        if isinstance(type_a.reference, cn.RUnion) and isinstance(type_b.reference, cn.RUnion):
            return True
        if isinstance(type_a.reference, cn.RBitmask) and isinstance(type_b.reference, cn.RBitmask):
            return True

    return False
