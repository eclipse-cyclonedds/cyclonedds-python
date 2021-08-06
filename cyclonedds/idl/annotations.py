from typing import cast, Any, Union, Callable, List, Type
from ._main import IdlField, IdlStruct, IdlUnion


class AnnotationException(Exception):
    pass


def default_literal(apply_to: Any, value: Any) -> None:
    field: IdlField = cast(IdlField, apply_to)
    field.annotations["default_literal"] = value


def key(value: Any) -> None:
    field: IdlField = cast(IdlField, value)
    field.annotations["key"] = True

def must_understand(value: Any) -> None:
    field: IdlField = cast(IdlField, value)
    field.annotations["must_understand"] = True


def autoid(autoid_type: str) -> Callable[[Type[IdlStruct]], Type[IdlStruct]]:
    if autoid_type not in ["hash", "sequential"]:
        raise AnnotationException(f"autoid is either 'hash' or 'sequential'.")

    def autoid_inner(cls: Type[IdlStruct]) -> Type[IdlStruct]:
        cls.__idl_annotations__["autoid"] = autoid_type
        return cls

    return autoid_inner


def final(cls: Type[IdlStruct]) -> Type[IdlStruct]:
    cls.__idl_annotations__["extensibility"] = "final"
    return cls


def mutable(cls: Type[IdlStruct]) -> Type[IdlStruct]:
    cls.__idl_annotations__["extensibility"] = "mutable"
    return cls


def appendable(cls: Type[IdlStruct]) -> Type[IdlStruct]:
    cls.__idl_annotations__["extensibility"] = "appendable"
    return cls


def keylist(list_of_keys: List[str]) -> Callable[[Type[IdlStruct]], Type[IdlStruct]]:
    def keylist_inner(cls: Type[IdlStruct]) -> Type[IdlStruct]:
        cls.__idl_annotations__["keylist"] = list_of_keys
        return cls

    return keylist_inner


def discriminator_key(cls: Type[IdlUnion]) -> Type[IdlUnion]:
    cls.__idl_annotations__["discriminator_is_key"] = True
    return cls

