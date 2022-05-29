from inspect import isclass
from textwrap import indent
from typing import Any, Type, List

from cyclonedds.idl import IdlStruct, IdlUnion, IdlBitmask, IdlEnum, types as pt
from cyclonedds.idl._type_normalize import (
    get_idl_annotations,
    get_idl_field_annotations,
    get_extended_type_hints,
    WrapOpt,
)
from cyclonedds.idl._type_helper import get_origin, get_args
from cyclonedds.idl.types import (
    array,
    bounded_str,
    sequence,
    _type_code_align_size_default_mapping,
    NoneType,
    char,
    typedef,
    case,
    default,
)


class _State:
    def __init__(self) -> None:
        self.types = set()
        self.output = ""
        self.module_scope = []

    def set_mod_scope(self, scope: List[str]):
        while len(scope) < len(self.module_scope):
            self._exit_scope()

        if not self.module_scope:
            for i in range(len(scope)):
                self._enter_scope(scope[i])
            return

        for i in range(len(self.module_scope)):
            if scope[i] != self.module_scope[i]:
                for j in range(i, len(self.module_scope)):
                    self._exit_scope()
                for j in range(i, len(scope)):
                    self._enter_scope(scope[j])
                break

    def _exit_scope(self):
        indent = "    " * (len(self.module_scope) - 1)
        self.output += f"{indent}}};\n"
        self.module_scope.pop()

    def _enter_scope(self, scope):
        indent = "    " * len(self.module_scope)
        self.output += f"{indent}module {scope} {{\n"
        self.module_scope.append(scope)

    def add_output(self, data):
        self.output += indent(data, "    " * len(self.module_scope))


class IdlType:
    easy_types = {
        pt.int8: "char",
        pt.int16: "short",
        pt.int32: "long",
        pt.int64: "long long",
        pt.uint8: "octet",
        pt.uint16: "short",
        pt.uint32: "unsigned long",
        pt.uint64: "unsigned long long",
        pt.float32: "float",
        pt.float64: "double",
        pt.wchar: "wchar",
        int: "long long",
        bool: "bool",
        float: "double",
        char: "char",
        str: "string",
    }

    @classmethod
    def _kind_type(cls, state, _type):
        if _type in cls.easy_types:
            return cls.easy_types[_type]
        elif _type in _type_code_align_size_default_mapping:
            return get_args(_type)[1]
        elif isinstance(_type, WrapOpt):
            return "@optional " + cls._kind_type(state, _type.inner)
        elif isclass(_type) and issubclass(
            _type, (IdlStruct, IdlUnion, IdlBitmask, IdlEnum)
        ):
            cls._proc_type(state, _type)
            return _type.__idl_typename__.replace(".", "::")
        elif get_origin(_type) == list:
            return "sequence<" + cls._kind_type(state, get_args(_type)[0]) + "> "
        elif get_origin(_type) == dict:
            return (
                "map<"
                + cls._kind_type(state, get_args(_type)[0])
                + ", "
                + cls._kind_type(state, get_args(_type)[0])
                + "> "
            )
        elif isinstance(_type, typedef):
            cls._proc_type(state, _type)
            return _type.name
        elif isinstance(_type, array):
            return cls._kind_type(state, _type.subtype)
        elif isinstance(_type, sequence):
            if _type.max_length:
                return (
                    "sequence<"
                    + cls._kind_type(state, _type.subtype)
                    + f", {_type.max_length}> "
                )
            else:
                return "sequence<" + cls._kind_type(state, _type.subtype) + "> "
        elif isinstance(_type, bounded_str):
            return f"bounded_str<{_type.max_length}> "

        return "unknown"

    @classmethod
    def _array_size(cls, _type):
        if isinstance(_type, array):
            inner = cls._array_size(_type.subtype)
            if inner is not None:
                return _type.length, *inner
            return (_type.length,)
        return tuple()

    @classmethod
    def _scoped_name(cls, name):
        m = name.replace(".", "::").split("::")
        return m[:-1], m[-1]

    @classmethod
    def _annot(cls, _type):
        out = ""
        for name, value in get_idl_annotations(_type).items():
            if name == "nested":
                out += "@nested\n"
            elif name == "autoid":
                out += f"@autoid({value.upper()})\n"
            elif name == "extensibility":
                out += f"@{value}\n"
            elif name == "bit_bound":
                out += f"@bit_bound({value})"
        return out

    @classmethod
    def _proc_type(cls, state, _type, top_level=False):
        if id(_type) in state.types:
            return

        state.types.add(id(_type))

        if isclass(_type) and issubclass(_type, IdlStruct):
            out = cls._annot(_type)

            scope, enname = cls._scoped_name(_type.__idl__.idl_transformed_typename)
            out += f"struct {enname} {{"
            field_annot = get_idl_field_annotations(_type)
            for name, _type in get_extended_type_hints(_type).items():
                out += "\n    "
                if "key" in field_annot.get(name, {}):
                    out += "@key "
                out += cls._kind_type(state, _type) + f" {name}"
                for arr in cls._array_size(_type):
                    out += f"[{arr}]"
                out += ";"
            out += "\n};\n"
            state.set_mod_scope(scope)
            state.add_output(out)
        elif isclass(_type) and issubclass(_type, IdlUnion):
            out = cls._annot(_type)

            scope, enname = cls._scoped_name(_type.__idl__.idl_transformed_typename)
            out += f"union {enname}"
            out += (
                " switch (" + cls._kind_type(state, _type.__idl_discriminator__) + ") {"
            )
            for name, __type in get_extended_type_hints(_type).items():
                if isinstance(__type, pt.case):
                    for l in __type.labels:
                        if isclass(_type.__idl_discriminator__) and issubclass(
                            _type.__idl_discriminator__, IdlEnum
                        ):
                            dscope, _ = cls._scoped_name(
                                _type.__idl_discriminator__.__idl_typename__
                            )
                            enum_scope = "::".join(dscope)
                            out += f"\n    case {enum_scope}::{_type.__idl_discriminator__(l).name}:"
                        else:
                            out += f"\n    case {l}:"
                else:
                    out += "\n    default:"

                out += "\n        " + cls._kind_type(state, __type.subtype) + f" {name}"
                for arr in cls._array_size(__type.subtype):
                    out += f"[{arr}]"
                out += ";"
            out += "\n};\n"
            state.set_mod_scope(scope)
            state.add_output(out)
        elif isclass(_type) and issubclass(_type, IdlBitmask):
            out = cls._annot(_type)

            scope, enname = cls._scoped_name(_type.__idl_typename__)
            out += f"bitmask {enname} {{"
            for name, _type in get_extended_type_hints(_type).items():
                out += f"\n    @position({_type.__idl_positions__[name]}) {name},"
            out = out[:-1]
            out += f"\n}};\n"
            state.set_mod_scope(scope)
            state.add_output(out)
        elif isclass(_type) and issubclass(_type, IdlEnum):
            out = cls._annot(_type)

            scope, enname = cls._scoped_name(_type.__idl_typename__)
            out += f"enum {enname} {{"
            v = -1
            for f in _type:
                if f.value != v + 1:
                    out += f"\n    @value({f.value}) {f.name},"
                else:
                    out += f"\n    {f.name},"
                v = f.value
            out = out[:-1]
            out += f"\n}};\n"
            state.set_mod_scope(scope)
            state.add_output(out)
        elif isinstance(_type, typedef):
            scope, enname = cls._scoped_name(_type.name)
            out = "typedef " + cls._kind_type(state, _type.subtype) + f" {_type.name}"
            for arr in cls._array_size(_type):
                out += f"[{arr}]"
            out += ";\n"
            state.set_mod_scope(scope)
            state.add_output(out)

    @classmethod
    def idl(cls, types: Type[Any]) -> str:
        state = _State()
        for _type in types:
            cls._proc_type(state, _type)
        state.set_mod_scope([])
        return state.output.strip()
