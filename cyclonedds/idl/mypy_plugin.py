from mypy.plugin import Plugin, AnalyzeTypeContext
from mypy.types import RawExpressionType, AnyType, TypeOfAny
from mypy.typeanal import make_optional_type


class IdlMyPyPlugin(Plugin):
    def get_type_analyze_hook(self, fullname: str):
        if fullname.startswith("cyclonedds.idl.types"):
            if fullname == "cyclonedds.idl.types.array":
                return strip_length_array_type
            elif fullname == "cyclonedds.idl.types.sequence":
                return strip_length_sequence_type
            elif fullname == "cyclonedds.idl.types.typedef":
                return resolve_type_def
            elif fullname == "cyclonedds.idl.types.bounded_str":
                return bounded_str_to_str
            elif fullname == "cyclonedds.idl.types.default":
                return union_default_type
            elif fullname == "cyclonedds.idl.types.case":
                return union_case_type
        return None

    def get_class_decorator_hook(self, fullname: str):
        from mypy.plugins import dataclasses

        if fullname in ["cyclonedds.idl.IdlStruct", "cyclonedds.idl.IdlUnion"]:
            return dataclasses.dataclass_class_maker_callback


def plugin(version: str):
    return IdlMyPyPlugin


def strip_length_array_type(ctx: AnalyzeTypeContext):
    if len(ctx.type.args) == 0:
        # ref of type itself
        return AnyType(TypeOfAny.special_form)

    if len(ctx.type.args) != 2 or not isinstance(ctx.type.args[1], RawExpressionType) or \
            ctx.type.args[1].base_type_name != "builtins.int":
        ctx.api.fail("cyclonedds.idl.types.array requires two arguments, a subtype and a fixed size.", ctx.context)
        return AnyType(TypeOfAny.from_error)
    return ctx.api.named_type('typing.Sequence', [ctx.api.analyze_type(ctx.type.args[0])])


def resolve_type_def(ctx: AnalyzeTypeContext):
    if len(ctx.type.args) == 0:
        # ref of type itself
        return AnyType(TypeOfAny.special_form)

    if len(ctx.type.args) != 2:
        ctx.api.fail("cyclonedds.idl.types.typedef requires a name and one type argument.", ctx.context)
        return AnyType(TypeOfAny.from_error)
    return ctx.api.analyze_type(ctx.type.args[1])


def strip_length_sequence_type(ctx: AnalyzeTypeContext):
    if len(ctx.type.args) == 0:
        # ref of type itself
        return AnyType(TypeOfAny.special_form)

    if len(ctx.type.args) not in [1, 2]:
        ctx.api.fail("cyclonedds.idl.types.sequence requires a subtype and an optional max size.", ctx.context)
        return AnyType(TypeOfAny.from_error)
    elif len(ctx.type.args) == 2 and not isinstance(ctx.type.args[1], RawExpressionType):
        ctx.api.fail("cyclonedds.idl.types.sequence max size should be an integer.", ctx.context)
        return AnyType(TypeOfAny.from_error)
    elif len(ctx.type.args) == 2 and ctx.type.args[1].base_type_name != "builtins.int":
        ctx.api.fail("cyclonedds.idl.types.sequence max size should be an integer.", ctx.context)
        return AnyType(TypeOfAny.from_error)

    return ctx.api.named_type('typing.Sequence', [ctx.api.analyze_type(ctx.type.args[0])])


def bounded_str_to_str(ctx: AnalyzeTypeContext):
    if len(ctx.type.args) == 0:
        # ref of type itself
        return AnyType(TypeOfAny.special_form)

    if len(ctx.type.args) != 1 or not isinstance(ctx.type.args[0], RawExpressionType) or \
            ctx.type.args[0].base_type_name != "builtins.int":
        ctx.api.fail("cyclonedds.idl.types.bound_str requires one argument, a fixed size.", ctx.context)
        return AnyType(TypeOfAny.from_error)
    return ctx.api.named_type('builtins.str', [])


def union_default_type(ctx: AnalyzeTypeContext):
    if len(ctx.type.args) == 0:
        # ref of type itself
        return AnyType(TypeOfAny.special_form)

    if len(ctx.type.args) != 1:
        ctx.api.fail("cyclonedds.idl.types.default requires one argument, a type.", ctx.context)
        return AnyType(TypeOfAny.from_error)
    return make_optional_type(ctx.api.analyze_type(ctx.type.args[0]))


def union_case_type(ctx: AnalyzeTypeContext):
    if len(ctx.type.args) == 0:
        # ref of type itself
        return AnyType(TypeOfAny.special_form)

    if len(ctx.type.args) != 2:
        ctx.api.fail("cyclonedds.idl.types.case requires two arguments, a discriminator label and a type.", ctx.context)
        return AnyType(TypeOfAny.from_error)
    return make_optional_type(ctx.api.analyze_type(ctx.type.args[1]))
