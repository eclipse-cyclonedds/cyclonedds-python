PyCDR
=====

The PyCDR package implements the OMG XCDR-V1 encoding in pure python. There should almost never be a need to delve into the details of this package when using DDS. In most cases the IDL compiler will write the code that uses this package. However, it is possible to write the objects manually. This is of course only useful if you do not plan to interact with other language clients, but makes perfect sense in a python-only project.

Usage
-----

If you are manually writing CDR objects your most important tool is :func:`@cdr<pycdr.cdr>`. This decorator is a combination of the :func:`@dataclass<python:dataclasses.dataclass>` with the extra added in machinery for CDR serialization and deserialization. The second most important tool is the :func:`@keylist<pycdr.keylist>` decorator, which allows you to define the key structure for you object.

The following basic example will be very familiar if you have used dataclasses before. We will go over it here again briefly, for more detail go to the standard library documentation of :mod:`dataclasses<python:dataclasses>`.

.. code-block:: python
   :linenos:

   from pycdr import cdr


   @cdr
   class Point2D:
      x: int
      y: int

   p1 = Point2D(20, -12)
   p2 = Point2D(x=12, y=-20)
   p1.x += 5


As you can see the :func:`@cdr<pycdr.cdr>` turns a class with just names and types into a dataclass. The `__init__` method is automatically generated for easy object construction. All normal dataclasses functionality is preserved, so you can still use :func:`field<python:dataclasses.field>` from the dataclasses module to define default factories or add a `__post_init__` method for more complicated construction scenarios.


Types
-----

Not all types that are possible to write in Python are encodable with XCDR. This means that you are slightly limited in what you can put in an :func:`@cdr<pycdr.cdr>` class. An exhaustive list follows:

Integers
^^^^^^^^

The default python :class:`int<python:int>` type maps to a XCDR 64 bit integer. For most applications that should suffice, but the :mod:`types<pycdr.types>` module has all the other integers types supported in python.

.. code-block:: python
   :linenos:

   from pycdr import cdr
   from pycdr.types import int8, uint8, int16, uint16, int32, uint32, int64, uint64

   @cdr
   class SmallPoint2D:
      x: int8
      y: int8

Note that these special types are just normal :class:`int<python:int>` s at runtime. They are only used to indicate the serialization functionality what type to use on the network. If you store a number that is not supported by that integer type you will get an error during encoding. The int128 and uint128 are not supported.

Floats
^^^^^^

The python :class:`float<python:float>` type maps to a 64 bit float, which would be a `double` in C-style languages. The :mod:`types<pycdr.types>` module has a float32 and float64 type, float128 is not supported.

Strings
^^^^^^^

The python :class:`str<python:str>` type maps directly to the XCDR string. Under the hood it is encoded with utf-8.

Lists
^^^^^

The python :func:`list<python:list>` is a versatile type. In normal python a list would be able to contain any other types, but to be able to encode it all of the contents must be the same type, and this type must be known beforehand. This can be achieved by using the :class:`sequence<pycdr.types.sequence>` type.


.. code-block:: python
   :linenos:

   from pycdr import cdr
   from pycdr.types import sequence

   @cdr
   class Names:
      names: sequence[str]

   n = Names(names=["foo", "bar", "baz"])

In XCDR this will result in an 'unbounded sequence', which should be fine in most cases. However, you can switch over to a 'bounded sequence' or 'array' using annotations. This can be useful to either limit the maximum allowed number of items (bounded sequence) or if the length of the list is always the same (array).

.. code-block:: python
   :linenos:

   from pycdr import cdr
   from pycdr.types import sequence, array

   @cdr
   class Numbers:
      ThreeNumbers: array[int, 3]
      MaxFourNumbers: sequence[int, 4]

Dictionaries
^^^^^^^^^^^^

Currently dictionaries are not supported by the Cyclone IDL compiler. However, if your project is pure python there is no problem in using them. Unlike a raw python :class:`dict<python:dict>` both the key and the value need to have a constant type. This is expressed using the :class:`Dict<python:typing.Dict>` from the :mod:`typing<python:typing>` module.

.. code-block:: python
   :linenos:

   from typing import Dict
   from pycdr import cdr

   @cdr
   class ColourMap:
      mapping: Dict[str, str]

   c = ColourMap({"red": "#ff0000", "blue": "#0000ff"})


Unions
^^^^^^

Unions in CDR are not like the Unions defined in the :mod:`typing<python:typing>` module. CDR unions are *discriminated*, meaning they have a value that indicates which of the possibilities is active. In future PyCDR will convert python Unions to discriminated unions automatically, with the caveat that the difference between the union types needs to be detectable at runtime. A concrete example would be that you cannot have a python union with a `int8` and a `uint8`, because for a value like `8` there is no way to determine which of those two is active.

You can also write discriminated unions using the :func:`@union<pycdr.types.union>` decorator and the :func:`case<pycdr.types.case>` and :func:`default<pycdr.types.default>` helper types. You again write a class in a dataclass style, except only one of the values can be active at a time. The :func:`@union<pycdr.types.union>` decorator takes one type as argument, which determines the type of what is differentiating the cases.

.. code-block:: python
   :linenos:

   from enum import Enum, auto
   from pycdr import cdr
   from pycdr.types import uint8, union, case, default, MaxLen


   class Direction(Enum):
      North = auto()
      East = auto()
      South = auto()
      West = auto()


   @union(Direction)
   class WalkInstruction:
      steps_n: case[Direction.North, int]
      steps_e: case[Direction.East, int]
      steps_s: case[Direction.South, int]
      steps_w: case[Direction.West, int]
      jumps: default[int]

   @cdr
   class TreasureMap:
      description: str
      steps: sequence[WalkInstruction, 20]

   map = TreasureMap(
      description="Find my Coins, Diamonds and other Riches!\nSigned\nCaptain Corsaro",
      steps=[
         WalkInstruction(steps_n=5),
         WalkInstruction(steps_e=3),
         WalkInstruction(jumps=1),
         WalkInstruction(steps_s=9)
      ]
   )

   print (map.steps[0].discriminator)  # You can always access the discriminator, which in this case would print 'Direction.North'


Objects
^^^^^^^

You can also reference other classes as member type. These other classes should be :func:`@dataclass<python:dataclasses.dataclass>` or :func:`@cdr<pycdr.cdr>` classes and again only contain serializable members. 

.. code-block:: python
   :linenos:

   from pycdr import cdr
   from pycdr.types import sequence

   @cdr
   class Point2D:
      x: int
      y: int

   @cdr
   class Cloud:
      points: sequence[Point]


Serialization
^^^^^^^^^^^^^

If you are using a DDS system you should not need this, serialization and deserialization happens automatically within the backend. However, for debug purposes or outside a DDS context it might be useful to look at the serialized data or create python objects from raw bytes. For this there are two functions: :func:`serialize<pycdr.serdata.serialize>` and :func:`deserialize<pycdr.serdata.serialize>`. These automatically get added to classes decorated with :func:`@cdr<pycdr.cdr>`. Serialize is a member function that will return :class:`bytes<python:bytes>` with the serialized object. Deserialize is a :func:`classmethod<python:classmethod>` that takes the :class:`bytes<python:bytes>` and returns the resultant object.

.. code-block:: python
   :linenos:

   from pycdr import cdr

   @cdr
   class Point2D:
      x: int
      y: int

   p = Point2D(10, 10)
   data = p.serialize()
   q = Point2D.deserialize(data)

   assert p == q


pycdr module
------------------

.. automodule:: pycdr
   :members:
   :undoc-members:
   :show-inheritance:

pycdr.types module
------------------

.. automodule:: pycdr.types
   :members:
   :undoc-members:
   :show-inheritance:
