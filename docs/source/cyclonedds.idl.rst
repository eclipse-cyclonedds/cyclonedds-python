idl
===

.. autoclass:: cyclonedds.idl.IdlStruct
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: cyclonedds.idl.IdlUnion
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: cyclonedds.idl.IdlBitmask
    :members:
    :undoc-members:
    :show-inheritance:

.. autoclass:: cyclonedds.idl.IdlEnum
    :members:
    :undoc-members:
    :show-inheritance:


idl.types
---------

The following classes are really types and should be used with a ``[]`` and not ``()``.

.. autoclass:: cyclonedds.idl.types.array
   :members:

.. autoclass:: cyclonedds.idl.types.sequence
   :members:

.. autoclass:: cyclonedds.idl.types.typedef
   :members:

.. autoclass:: cyclonedds.idl.types.bounded_str
   :members:

.. autoclass:: cyclonedds.idl.types.case
   :members:

.. autoclass:: cyclonedds.idl.types.default
   :members:

The following items map to Python ``int`` or ``float`` but indicate their full meaning to the C layer in encoding samples.

.. autodata:: cyclonedds.idl.types.char
   :annotation:

.. autodata:: cyclonedds.idl.types.uint8
   :annotation:

.. autodata:: cyclonedds.idl.types.uint16
   :annotation:

.. autodata:: cyclonedds.idl.types.uint32
   :annotation:

.. autodata:: cyclonedds.idl.types.uint64
   :annotation:

.. autodata:: cyclonedds.idl.types.int8
   :annotation:

.. autodata:: cyclonedds.idl.types.int16
   :annotation:

.. autodata:: cyclonedds.idl.types.int32
   :annotation:

.. autodata:: cyclonedds.idl.types.int64
   :annotation:

.. autodata:: cyclonedds.idl.types.float32
   :annotation:

.. autodata:: cyclonedds.idl.types.float64
   :annotation:

.. autodata:: cyclonedds.idl.types.NoneType
   :annotation:

idl.annotations
---------------

.. autofunction:: cyclonedds.idl.annotations.key

.. autofunction:: cyclonedds.idl.annotations.position

.. autofunction:: cyclonedds.idl.annotations.member_id

.. autofunction:: cyclonedds.idl.annotations.member_hash_id

.. autofunction:: cyclonedds.idl.annotations.xcdrv2

.. autofunction:: cyclonedds.idl.annotations.cdrv0

.. autofunction:: cyclonedds.idl.annotations.nested

.. autofunction:: cyclonedds.idl.annotations.must_understand

.. autofunction:: cyclonedds.idl.annotations.autoid

.. autofunction:: cyclonedds.idl.annotations.extensibility

.. autofunction:: cyclonedds.idl.annotations.final

.. autofunction:: cyclonedds.idl.annotations.appendable

.. autofunction:: cyclonedds.idl.annotations.mutable

.. autofunction:: cyclonedds.idl.annotations.keylist

.. autofunction:: cyclonedds.idl.annotations.bit_bound
