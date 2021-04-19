.. _intro:

Introduction
============

This is the documentation for CycloneDDS Python, wrapping the Eclipse CycloneDDS C-API for easy creation of DDS applications.

.. _installing:

Prerequisites
-------------

CycloneDDS Python requires CycloneDDS to be installed. While installing and using the CycloneDDS Python library you need to set the environment variable ``CYCLONEDDS_HOME`` to allow the installer to locate the library. It is recommended to set ``CYCLONEDDS_HOME`` automatically, by adding it to the *System Variables* on Windows, your ``~/.bashrc`` on Linux or ``~/bash_profile`` on MacOS.
CycloneDDS Python requires Python version 3.6 or higher, with Python 3.10 support provisional while it is still unreleased.

Installation
------------

You can install CycloneDDS directly from PyPI:

.. code-block:: shell

    pip install cyclonedds


Right now you also need to install one dependency manually, this will be resolved once we have a proper release cycle for CycloneDDS Python.

.. code-block:: shell

    pip install pycdr


If you get permission warnings you are trying to install CycloneDDS Python as system Python library. This can be resolved several ways, such as using :py:mod:`virtual environments <venv>`, `pyenv <https://github.com/pyenv/pyenv>`_, `pipenv <https://github.com/pypa/pipenv>`_, `poetry <https://python-poetry.org>`_ or by performing a user install. The last one is the easiest, just add ``--user`` to your pip install, but a managed environment with one of the other solutions will ease your dependency management in the future.

.. _first_app:

Your first Python DDS application
-----------------------------------

Let's make our entry into the world of DDS by making our presence known. We will not worry about configuration or what DDS does under the hood but just write a single message. To publish anything to DDS we need to define the type of message first. If you are worried about talking to other applications that are not necessarily running Python you would use the CycloneDDS IDL compiler, but for now we will just manually define our message type directly in Python using the `pycdr` package:

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
