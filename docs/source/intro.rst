.. _intro:

Introduction
============

This is the documentation for Eclipse Cyclone DDS Python, wrapping the `Eclipse Cyclone DDS <repo>`_ C-API for easy creation of DDS applications.

.. _installing:

Prerequisites
-------------

Cyclone DDS Python requires Python version 3.6 or higher. It can be installed :ref:`with included Cyclone DDS binaries <installing-included>` or leveraging an existing Cyclone DDS installation by :ref:`installing from source <installing-from-source>`.

.. _installing-included:

Installing with included Cyclone DDS binaries
---------------------------------------------

This is the most straightforward method to install Cyclone DDS Python, but there are a couple of caveats. The pre-built package:

 * does not include the Cyclone DDS IDL compiler,
 * has no support for DDS Security,
 * has no support for shared memory via Iceoryx,
 * comes with generic Cyclone DDS binaries that are not optimized per-platform.

If these are of concern, please proceed with an :ref:`installation from source <installing-from-source>`. If not, running this installation is as simple as:

    $ pip install cyclonedds


If you get permission errors you are using your system python. This is not recommended, we recommend using `a virtual environment <venv>`_, `poetry <poetry>`_, `pipenv <pipenv>`_ or `pyenv <pyenv>`_. If you *just* want to get going, you can add ``--user`` to your pip command to install for the current user. See the `Installing Python Modules <py_installing>`_ Python documentation.

.. _installing-from-source:

Installing from source
----------------------

When installing from source you can make use of the full list of features offered by `Cyclone DDS <repo>`_. First install `Cyclone DDS <repo>`_ as normal. Then continue by setting the ``CYCLONEDDS_HOME`` environment variable to the installation location of `Cyclone DDS <repo>`_, which is the same as what was used for ``CMAKE_INSTALL_PREFIX``. You will have to have this variable active any time you run Python code that depends on ``cyclonedds`` so adding it to ``.bashrc`` on Linux, ``~/bash_profile`` on MacOS or the System Variables in Windows can be helpful. This also allows you to switch, move or update `Cyclone DDS <repo>`_ without recompiling the Python package.

You can either install the source from the latest release from pypi:

.. code-block:: shell
    :linenos:

    $ export CYCLONEDDS_HOME="/path/to/cyclone"
    $ pip install cyclonedds --no-binary :all:

or you can download the code from this repository to get the bleeding edge and directly install from your local filesystem:

.. code-block:: shell
    :linenos:

    $ git clone https://github.com/eclipse-cyclonedds/cyclonedds-python
    $ cd cyclonedds-python
    $ export CYCLONEDDS_HOME="/path/to/cyclone"
    $ pip install ./src/pycdr
    $ pip install ./src/cyclonedds

If you get permission errors you are using your system python. This is not recommended, we recommend using `a virtual environment <venv>`_, `poetry <poetry>`_, `pipenv <pipenv>`_ or `pyenv <pyenv>`_. If you *just* want to get going, you can add ``--user`` to your pip command to install for the current user. See the `Installing Python Modules <py_installing>`_ Python documentation.

Installing the Python backend for the Eclipse Cyclone DDS IDL compiler
----------------------------------------------------------------------

The code for the Python backend for the IDL compiler is contained in ``src/idlpy`` and builds like any other cmake project:

.. code-block:: shell
    :linenos:

    $ git clone https://github.com/eclipse-cyclonedds/cyclonedds-python
    $ cd cyclonedds-python/src/idlpy
    $ mkdir build
    $ cmake -DCMAKE_INSTALL_PREFIX=<install-location> \
            -DCMAKE_PREFIX_PATH="<cyclonedds-install-location>" \
            ..
    $ cmake --build .
    $ cmake --build . --target install

For more details on this process take a look at the `Eclipse Cyclone DDS C++ backend <cxx_repo>`_ which explains the cmake process in depth.

.. _repo: https://github.com/eclipse-cyclonedds/cyclonedds/
.. _venv: https://docs.python.org/3/tutorial/venv.html
.. _poetry: https://python-poetry.org/
.. _pipenv: https://pipenv.pypa.io/en/latest/
.. _pyenv: https://github.com/pyenv/pyenv
.. _py_installing: https://docs.python.org/3/installing/index.html
.. _cxx_repo: https://github.com/eclipse-cyclonedds/cyclonedds-cxx/

.. _first_app:

Your first Python DDS application
-----------------------------------

Let's make our entry into the world of DDS by making our presence known. We will not worry about configuration or what DDS does under the hood but just write a single message. To publish anything to DDS we need to define the type of message first. If you are worried about talking to other applications that are not necessarily running Python you would use the Cyclone DDS IDL compiler, but for now we will just manually define our message type directly in Python using the `pycdr` package:

.. code-block:: python3
    :linenos:

    from pycdr import cdr

    @cdr
    class Message:
        text: str

    name = input("What is your name? ")
    message = Message(text=f"{name} has started his first DDS Python application!")

With `pycdr` we write typed classes just like the standard library module `dataclasses <python:dataclasses>` (which in fact is what it uses under the hood). For this simple application we just put in a piece of text, but this system has the same expressive power as the OMG IDL specification, allowing you to use almost any complex datastructure you can think of.

Now to send our message over DDS we need to perform a few steps:
* Join the DDS network using a DomainParticipant
* Define which datatype and under what name we will publish our message as a Topic
* Make the DataWriter that publishes that Topic
* And finally publish the message.

.. code-block:: python3
    :linenos:

    from cyclonedds.domain import DomainParticipant
    from cyclonedds.topic import Topic
    from cyclonedds.pub import DataWriter

    participant = DomainParticipant()
    topic = Topic(participant, Message, "Announcements")
    writer = DataWriter(participant, topic)

    writer.write(message)

Hurray, we have published are first message! However, it is hard to tell if that actually did anything, since we don't have anything set up that is listening. Let's make a second script that takes messages from DDS and prints them to the terminal:

.. code-block:: python3
    :linenos:

    from cyclonedds.domain import DomainParticipant
    from cyclonedds.topic import Topic
    from cyclonedds.sub import DataReader
    from cyclonedds.util import duration
    from pycdr import cdr

    @cdr
    class Message:
        text: str

    participant = DomainParticipant()
    topic = Topic(participant, Message, "Announcements")
    reader = DataReader(participant, topic)

    # If we don't receive a single announcement for five minutes we want the script to exit.
    for msg in reader.take_iter(timeout=duration(minutes=5)):
        print(msg.text)

Now with this script running in a secondary terminal you should see the message pop up when you run the first script again.
