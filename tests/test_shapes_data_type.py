from dataclasses import dataclass
import cyclonedds.idl as idl
import cyclonedds.idl.annotations as annotate
import cyclonedds.idl.types as types
from enum import auto


@dataclass
@annotate.appendable
@annotate.autoid("sequential")
class ShapeType(idl.IdlStruct, typename="ShapeTypeBase"):
    color: str
    annotate.key("color")
    x: types.int32
    y: types.int32
    shapesize: types.int32


@annotate.appendable
class ShapeFillKind(idl.IdlEnum, typename="ShapeFillKind", default="SOLID_FILL"):
    SOLID_FILL = auto()
    TRANSPARENT_FILL = auto()
    HORIZONTAL_HATCH_FILL = auto()
    VERTICAL_HATCH_FILL = auto()


@dataclass
@annotate.appendable
@annotate.autoid("sequential")
class ShapeTypeExtended(ShapeType, typename="ShapeType"):
    fillKind: "ShapeFillKind"
    angle: types.float32


def test_shapes():
    shape = ShapeTypeExtended(
        color="red",
        x=101,
        y=202,
        shapesize=5,
        fillKind=ShapeFillKind.TRANSPARENT_FILL,
        angle=0.0,
    )
    assert shape == ShapeTypeExtended.deserialize(shape.serialize())
