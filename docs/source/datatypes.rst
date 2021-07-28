.. _datatypes:

IDL datatypes in Python
========================

At the time of writing there is no official mapping from OMG IDL to Python. The solutions we came up with here are therefore not standardized and are thus not compatible with other DDS implementations. However, they are based purely on the standard library type-hinting functionality as introduced in Python 3.5, meaning that any Python tooling available that works with type hints is also compatible with our implementation. Anyone familiar with the :py:mod:`dataclasses` standard library module will be immidiately familiar with this style of declaring types.
