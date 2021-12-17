from dataclasses import dataclass
from . import containers as cn
from . import generators as gn
from .operations import type_assignable
from random import Random
from copy import deepcopy


def mutate_struct(top_scope: cn.RScope, struct: cn.RStruct, random: Random) -> cn.RStruct:
    if not any('key' in field.annotations for field in struct.fields) and struct.in_key_path:
        # Keyless struct in key path -> full type is key, no mutations allowed
        return

    if struct.extensibility in [cn.RExtensibility.NotSpecified, cn.RExtensibility.Final]:
        return
    if struct.extensibility == cn.RExtensibility.Appendable:
        action = random.choices([1, 2], weights=[1, 1], k=1)[0]

        if action == 1:
            # add a field
            struct.fields.append(
                gn.emit_field(top_scope, struct.scope, Random(random.random()))
            )
        elif action == 2:
            # remove a field (check if not key)
            if 'key' not in struct.fields[-1].annotations:
                struct.fields.pop()
        elif action == 3:
            # do nothing
            pass
        return
    if struct.extensibility == cn.RExtensibility.Mutable:
        action = random.choices([1, 2], weights=[1, 1], k=1)[0]

        if action == 1:
            # add a field
            struct.fields.append(
                gn.emit_field(top_scope, struct.scope, Random(random.random()))
            )
        elif action == 2:
            # remove a field (check if not key)
            i = random.randint(0, len(struct.fields) - 1)
            if 'key' not in struct.fields[i].annotations:
                struct.fields.pop(i)
        elif action == 3:
            # do nothing
            pass

        random.shuffle(struct.fields)


def mutate(top_scope: cn.RScope, seed):
    # Determine first things that cannot be mutated because strong assignibility is required
    # collection -> final -> mutable/appendable
    avoid_mutating = set()
    def scan_avoid_mutating_field(field: cn.RField):
        nonlocal avoid_mutating
        if field.array_bound is not None or field.type.discriminator in [cn.RTypeDiscriminator.Sequence, cn.RTypeDiscriminator.BoundedSequence]:
            dependencies = field.depending()
            if dependencies and isinstance(dependencies[0], (cn.RStruct, cn.RUnion)) and \
                    dependencies[0].extensibility in [cn.RExtensibility.NotSpecified, cn.RExtensibility.Final]:
                for sub_entity in dependencies:
                    avoid_mutating.add(id(sub_entity))

    for entity in top_scope.entities:
        if isinstance(entity, cn.RStruct):
            for field in entity.fields:
                scan_avoid_mutating_field(field)
        if isinstance(entity, cn.RUnion):
            for case in entity.cases:
                scan_avoid_mutating_field(case.field)
            if entity.default:
                scan_avoid_mutating_field(entity.default)
        if isinstance(entity, cn.RTypedef):
            if entity.array_bound or entity.rtype.discriminator in [cn.RTypeDiscriminator.Sequence, cn.RTypeDiscriminator.BoundedSequence]:
                dependencies = entity.rtype.depending()
                if dependencies and isinstance(dependencies[0], (cn.RStruct, cn.RUnion)) and \
                        dependencies[0].extensibility in [cn.RExtensibility.NotSpecified, cn.RExtensibility.Final]:
                    for sub_entity in dependencies:
                        avoid_mutating.add(id(sub_entity))

    random = Random(seed)
    entities = top_scope.entities
    top_scope.entities = []
    for entity in entities:
        if isinstance(entity, cn.RStruct) and id(entity) not in avoid_mutating:
            mutate_struct(top_scope, entity, random)
        top_scope.entities.append(entity)


def non_valid_mutate_struct(top_scope: cn.RScope, struct: cn.RStruct, random: Random) -> cn.RStruct:
    if struct.extensibility in [cn.RExtensibility.NotSpecified, cn.RExtensibility.Final]:
        action = random.choices([1, 2], weights=[1, 1], k=1)[0]
        if action == 1:
            # add a field
            struct.fields.append(
                gn.emit_field(top_scope, struct.scope, Random(random.random()))
            )
        elif action == 2:
            # remove a field
            struct.fields.pop(random.randint(0, len(struct.fields) - 1))
        return

    if struct.extensibility == cn.RExtensibility.Appendable:
        action = random.choices([1, 2, 3], weights=[1, 1, 2], k=1)[0]

        if not any('key' in field.annotations for field in struct.fields):
            # keyless struct
            action = 1

        if action == 1:
            # add a field in the middle
            if len(struct.fields) == 0:
                # Problem! Can't make invalid
                return
            elif len(struct.fields) == 1:
                struct.fields.insert(
                    0,
                    gn.emit_field(top_scope, struct.scope, Random(random.random()))
                )
            else:
                struct.fields.insert(
                    random.randint(0, len(struct.fields) - 2),
                    gn.emit_field(top_scope, struct.scope, Random(random.random()))
                )
            return
        elif action == 2:
            # remove a key field
            for i, field in enumerate(struct.fields):
                if 'key' in field.annotations:
                    struct.fields.pop(i)
                    break
            return
        elif action == 3:
            # add a keyfield
            struct.fields.append(
                gn.emit_field(top_scope, struct.scope, Random(random.random()))
            )
            struct.fields[-1].annotations.append("key")
        return
    if struct.extensibility == cn.RExtensibility.Mutable:
        action = random.choices([1, 2], weights=[1, 1], k=1)[0]

        if action == 1 and struct.in_key_path:
            # remove a key field
            for i, field in enumerate(struct.fields):
                if 'key' in field.annotations:
                    struct.fields.pop(i)
                    return
            else:
                # Ah, keyless, have to ruin it another way
                pass

        fields_copy = deepcopy(struct.fields)

        # change some types
        for z in range(2):
            i = random.randint(0, len(struct.fields) - 1)
            ptype = fields_copy[i].type
            ntype = None
            seed = random.random()
            j = 0

            while True:
                j += 1
                ntype = gn.emit_type(top_scope, struct.scope, Random(f"{seed}.{j}"))
                if type_assignable(ptype, ntype):
                    for sub in ntype.depending():
                        top_scope.entities.remove(sub)
                else:
                    break

            struct.fields[i].type = ntype
            if struct.fields[i].array_bound:
                if len(struct.fields[i].array_bound) > 2:
                    struct.fields[i].array_bound.pop()
                else:
                    struct.fields[i].array_bound.append(2)
            elif random.random() < 0.2:
                struct.fields[i].array_bound = [2]
        return


def non_valid_mutation(top_scope: cn.RScope, seed):
    # Mutate in such a way that types are not valid anymore
    random = Random(seed)
    entities = top_scope.entities
    top_scope.entities = []
    for entity in entities:
        if isinstance(entity, cn.RStruct):
            non_valid_mutate_struct(top_scope, entity, random)
        top_scope.entities.append(entity)
