from copy import deepcopy
from typing import List, Tuple
from .generators import emit_struct
from .printers import print_entity, Stream
from .containers import RScope
from .mutator import mutate
from random import Random


def generate_random_types(module: str, xcdr_version: int, number=100, seed=0) -> Tuple[RScope]:
    scope = RScope(name=module, seed=seed)

    for i in range(number):
        random = Random(f"{seed}.{i}")
        struct = emit_struct(scope, xcdr_version, random)
        scope.topics.append(struct)

    return scope


def generate_random_mutations(scope: RScope, xcdr_version: int, seed=0) -> RScope:
    scope = deepcopy(scope)
    mutate(scope, xcdr_version, seed)
    return scope


def generate_random_idl(scope: RScope):
    stream = Stream()

    stream << "module " << scope.name << "{" << stream.endl << stream.indent

    for entity in scope.entities:
        print_entity(stream, entity)

    stream << stream.dedent << "};" << stream.endl

    return stream.string

