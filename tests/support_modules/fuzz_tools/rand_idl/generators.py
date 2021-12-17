from random import Random
from .operations import get_value_assortment
from . import containers as cn
from math import log2, ceil
from copy import copy


_typedef_types = [cn.RTypeDiscriminator.Sequence, cn.RTypeDiscriminator.BoundedSequence]
def emit_type_inner(top_scope: cn.RScope, scope: cn.RScope, random: Random, no_enums: bool = False) -> cn.RType:
    d = random.choices([c for c in cn.RTypeDiscriminator], weights=cn.RTypeDiscriminator.weights(no_enums), k=1)[0]

    if d == cn.RTypeDiscriminator.Simple:
        return cn.RType(
            discriminator=d,
            name=random.choice([
                "octet", "char", "short", "unsigned short", "long",
                "unsigned long", "long long", "unsigned long long", "boolean",
                "float", "double"
            ])
        )
    elif d == cn.RTypeDiscriminator.String:
        return cn.RType(
            discriminator=d
        )
    elif d == cn.RTypeDiscriminator.BoundedString:
        return cn.RType(
            discriminator=d,
            bound=random.randint(5, 25)
        )

    elif d == cn.RTypeDiscriminator.Sequence:
        inner = emit_type(top_scope, scope, random, True)  # TODO allow sequence of enum
        rtype = cn.RType(
            discriminator=d,
            inner=inner
        )

        if inner.discriminator in _typedef_types:
            td = emit_typedef(top_scope, Random(random.random()), rtype)
            return cn.RType(
                discriminator=cn.RTypeDiscriminator.Nested,
                reference=td
            )
        return rtype

    elif d == cn.RTypeDiscriminator.BoundedSequence:
        inner = emit_type(top_scope, scope, random, True)  # TODO allow sequence of enum
        rtype = cn.RType(
            discriminator=d,
            inner=inner,
            bound=random.randint(5, 25)
        )

        if inner.discriminator in _typedef_types:
            td = emit_typedef(top_scope, Random(random.random()), rtype)
            return cn.RType(
                discriminator=cn.RTypeDiscriminator.Nested,
                reference=td
            )
        return rtype

    elif d == cn.RTypeDiscriminator.Enumerator:
        return cn.RType(
            discriminator=d,
            reference=emit_enum(top_scope, Random(random.random()))
        )
    elif d == cn.RTypeDiscriminator.Nested:
        choices = [emit_struct, emit_union] if no_enums else [emit_struct, emit_union, emit_bitmask]
        return cn.RType(
            discriminator=d,
            reference=random.choice(choices)(top_scope, Random(random.random()))
        )
    raise Exception("TypeDiscrimitator was faulty?")


def emit_type(top_scope: cn.RScope, scope: cn.RScope, random: Random, no_enums: bool = False) -> cn.RType:
    inner = emit_type_inner(top_scope, scope, random, no_enums)

    if random.random() > 0.95:
        td = emit_typedef(top_scope, random, inner)
        inner = cn.RType(discriminator=cn.RTypeDiscriminator.Nested, reference=td)

    return inner


def emit_discriminator(top_scope: cn.RScope, scope: cn.RScope, random: Random) -> cn.RType:
    # TODO: allow discriminator enum
    # d = random.choices([cn.RTypeDiscriminator.Simple, cn.RTypeDiscriminator.Enumerator], weights=[5, 1], k=1)[0]
    d = cn.RTypeDiscriminator.Simple

    if d == cn.RTypeDiscriminator.Simple:
        return cn.RType(
            discriminator=d,
            name=random.choice([ # TODO allow char again "char",
                "octet",  "short", "unsigned short", "long", "unsigned long"
            ])
        )
    elif d == cn.RTypeDiscriminator.Enumerator:
        return cn.RType(
            discriminator=d,
            reference=emit_enum(top_scope, Random(random.random()))
        )
    raise Exception("TypeDiscrimitator was faulty?")


def emit_field(top_scope: cn.RScope, scope: cn.RScope, random: Random) -> cn.RField:
    field_name = scope.namer.short()
    field_type = emit_type(top_scope, scope, random)

    array_bound = None
    # TODO: remove discriminator check if is_fully_descriptive bug is solved and
    if field_type.discriminator not in [cn.RTypeDiscriminator.BoundedSequence, cn.RTypeDiscriminator.Sequence, cn.RTypeDiscriminator.Enumerator] and random.random() < 0.2:
        dims = random.randint(1, 2)
        array_bound = [random.randint(1, 3) for i in range(dims)]

    return cn.RField(
        name=field_name,
        annotations=[],
        type=field_type,
        array_bound=array_bound
    )


def emit_struct(top_scope: cn.RScope, random: Random) -> cn.RStruct:
    scope = cn.RScope(name="anonymous", seed=random.random(), parent=top_scope)

    struct = cn.RStruct(
        name=top_scope.namer.long().capitalize(),
        scope=scope,
        extensibility=random.choice([cn.RExtensibility.NotSpecified, cn.RExtensibility.Appendable, cn.RExtensibility.Final, cn.RExtensibility.Mutable]),
        fields=[
            emit_field(top_scope, scope, Random(random.random())) for i in range(random.randint(1, 10))
        ]
    )

    if random.random() > 0.8:
        # add a field with different name but same type as another field
        i = random.randint(0, len(struct.fields) - 1)
        t = copy(struct.fields[i].type)
        t.duplex = True

        struct.fields.append(cn.RField(
            name=scope.namer.short(),
            annotations=[],
            type=t,
            array_bound=None
        ))

    fcopy = struct.fields.copy()
    random.shuffle(fcopy)

    for field in fcopy:
        # TODO: when @key on array of complex stuff is allowed
        if field.array_bound is not None:
            if field.type.discriminator in [
                cn.RTypeDiscriminator.BoundedSequence, cn.RTypeDiscriminator.Sequence,
                cn.RTypeDiscriminator.String, cn.RTypeDiscriminator.BoundedString, cn.RTypeDiscriminator.Nested]:
                    continue

        if field.type.discriminator in [cn.RTypeDiscriminator.Simple, cn.RTypeDiscriminator.Enumerator]:
            field.annotations.append('key')
            for e in field.depending():
                e.in_key_path = True
            if random.random() < 0.5:
                break

        # TODO: allow union/bitmask
        elif field.type.discriminator == cn.RTypeDiscriminator.Nested and isinstance(field.type.reference, cn.RStruct):
            if random.random() < 0.5:
                field.annotations.append('key')

                for d in field.key_depending():
                    if not d.type_check(lambda l: not isinstance(l.reference, cn.RUnion)):
                        # TODO: unions not (yet) allowed in keypath
                        field.annotations.remove('key')
                        break
                    if not d.type_check(lambda l: l.discriminator not in [cn.RTypeDiscriminator.Sequence, cn.RTypeDiscriminator.BoundedSequence]):
                        # TODO: sequences not allowed in keypath
                        field.annotations.remove('key')
                        break
                    if isinstance(d, cn.RStruct) and d.keyless():
                        allowed = True
                        for infield in d.fields:
                            # A keyless struct should not be too crazy
                            # TODO: when @key on array of complex stuff is allowed
                            if field.array_bound is not None:
                                if field.type.discriminator in [
                                    cn.RTypeDiscriminator.BoundedSequence, cn.RTypeDiscriminator.Sequence,
                                    cn.RTypeDiscriminator.String, cn.RTypeDiscriminator.BoundedString, cn.RTypeDiscriminator.Nested]:
                                        allowed = False
                                        break
                        if not allowed:
                            field.annotations.remove('key')
                            break
                else:
                    for e in field.depending():
                        e.in_key_path = True

                    if random.random() < 0.5:
                        break
            else:
                field.annotations.append('external')

    random.shuffle(fcopy)

    if struct.extensibility == cn.RExtensibility.Mutable:
        for field in struct.fields:
            field.annotations.append('hashid')


    if not all("key" not in field.annotations for field in fcopy):
        for field in fcopy:
            if not "key" in field.annotations:
                field.annotations.append("optional")
                break

    top_scope.entities.append(struct)
    return struct


def emit_union(top_scope: cn.RScope, random: Random) -> cn.RUnion:
    scope = cn.RScope(name="anonymous", seed=random.random(), parent=top_scope)
    discriminator = emit_discriminator(top_scope, scope, Random(random.random()))

    labels = get_value_assortment(discriminator, 100, random)
    unused_labels = set(labels)

    cases = []
    for i in range(random.randint(1, 10)):
        caselabels = []
        while unused_labels:
            l = random.choice(list(unused_labels))
            unused_labels.remove(l)
            caselabels.append(l)
            if random.random() < 0.5:
                break
        cases.append(cn.RCase(caselabels, emit_field(top_scope, scope, Random(random.random()))))
        if not unused_labels:
            break

    default = None if not unused_labels or random.random() < 0.5 else emit_field(top_scope, scope, Random(random.random()))

    union = cn.RUnion(
        name=top_scope.namer.long().capitalize(),
        scope=scope,
        extensibility=random.choice([cn.RExtensibility.NotSpecified, cn.RExtensibility.Appendable, cn.RExtensibility.Final]),
        discriminator=discriminator,
        discriminator_is_key=False, # TODO union=key support random.choice([True, False]),
        cases=cases,
        default=default
    )

    if not union.discriminator_is_key:
        for e in union.depending():
            e.in_key_path = True

    top_scope.entities.append(union)
    return union


def emit_enum(top_scope: cn.RScope, random: Random) -> cn.REnumerator:
    scope = cn.RScope(name="anonymous", seed=random.random(), parent=top_scope)

    num_fields = random.randint(3, 20)
    fields = []
    v = 0

    for i in range(num_fields):
        if random.random() < 0.2:
            v += int(abs(random.normalvariate(0, 10)))
            fields.append(cn.REnumEntry(top_scope.namer.short().upper(), v))
        else:
            fields.append(cn.REnumEntry(top_scope.namer.short().upper()))

        v += 1

    # TODO: remove this next line when annotate is fixed for enum bounds
    # v += 1

    enum = cn.REnumerator(
        name=top_scope.namer.long().capitalize(),
        scope=scope,
        fields=fields,
        bit_bound=int(ceil(log2(v))) if random.random() < 0.5 else None
    )

    top_scope.entities.append(enum)
    return enum


def emit_bitmask(top_scope: cn.RScope, random: Random) -> cn.RBitmask:
    scope = cn.RScope(name="anonymous", seed=random.random(), parent=top_scope)

    num_fields = random.randint(3, 20)
    fields = []
    v = 0

    for i in range(num_fields):
        if random.random() < 0.2:
            v += int(abs(random.normalvariate(0, 2)))
            fields.append(cn.RBitmaskEntry(top_scope.namer.short(), v))
        else:
            fields.append(cn.RBitmaskEntry(top_scope.namer.short()))

        v += 1

    # It is possible for v to go over bit_bound 64 _technically_
    # The chance of this happening is very small, so we will just recurse
    # Don't worry about the stack
    # TODO: change back to 64
    if v > 32:
        return emit_bitmask(top_scope, random)

    enum = cn.RBitmask(
        name=top_scope.namer.long().capitalize(),
        scope=scope,
        fields=fields,
        bit_bound=v if random.random() < 0.5 or v > 32 else None
    )

    top_scope.entities.append(enum)
    return enum


def emit_typedef(top_scope: cn.RScope, random: Random, rtype: cn.RType) -> cn.RTypedef:
    scope = cn.RScope(name="anonymous", seed=random.random(), parent=top_scope)

    array_bound = None
    # TODO: remove discriminator check if is_fully_descriptive bug is solved and
    if rtype.discriminator not in [cn.RTypeDiscriminator.BoundedSequence, cn.RTypeDiscriminator.Sequence, cn.RTypeDiscriminator.Enumerator] and random.random() < 0.2:
        dims = random.randint(1, 2)
        array_bound = [random.randint(1, 3) for i in range(dims)]

    typedef = cn.RTypedef(
        name=top_scope.namer.long(),
        scope=scope,
        rtype=rtype,
        array_bound=array_bound
    )

    top_scope.entities.append(typedef)
    return typedef
