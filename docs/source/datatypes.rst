.. _datatypes:

IDL datatypes in Python
========================

At the time of writing there is no official mapping from OMG IDL to Python. The solutions we came up with here are therefore not standardized and are thus not compatible with other DDS implementations. However, they are based purely on the standard library type-hinting functionality as introduced in Python 3.5, meaning that any Python tooling available that works with type hints is also compatible with our implementation. Anyone familiar with the :py:mod:`dataclasses` standard library module will be immidiately familiar with this style of declaring types.

The type support is split into a separate package `pycdr`, allowing you to use it even in contexts where you do not need the full CycloneDDS Python ecosystem.

Working with the IDL compiler
-----------------------------

You use the IDL compiler if you already have an idl file to define your types or if you require interoperability with non-Python projects. Currently the ``idlpy`` component is not automatically installed with the cyclonedds python package since its installation process needs some cmake support. Clone the CycloneDDS-Python repo instead and install ``idlpy`` like other CycloneDDS cmake-based components:


.. code-block:: shell

    cd src/idlpy
    mkdir build
    cd build
    cmake -DCMAKE_INSTALL_PREFIX=<cyclonedds-install-location> \
          -DCMAKE_PREFIX_PATH="<cyclonedds-install-location>" \
          ..
    cmake --build .
    cmake --build . --target install

Note that you can install idlpy to a different directory than CycloneDDS, but make sure it is on your path if you wish to use the ``cyclonedds.idl`` package in Python.