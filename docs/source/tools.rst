Tools
=====

When you install the ``cyclonedds`` Python package you also get a ``cyclonedds`` command line tool with several subcommands.

The ``cyclonedds`` command line tool
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

 The main help screen shows the commands available:

.. image:: static/images/cyclonedds-help.svg
    :alt: ``cyclonedds --help``

``cyclonedds ls``
-----------------

.. image:: static/images/cyclonedds-ls-help.svg
    :alt: ``cyclonedds ls --help``

The ``ls`` subcommand shows you the entities in your DDS system and their QoS settings. For example, here is the output when running the ``Vehicle`` example from this repo in the background:

.. image:: static/images/cyclonedds-ls-demo.svg
    :alt: ``cyclonedds ls --suppress-progress-bar --force-color-mode``


``cyclonedds ps``
-----------------

.. image:: static/images/cyclonedds-ps-help.svg
    :alt: ``cyclonedds ps --help``

The ``ps`` subcommand shows you the applications in your DDS system. Note that this depends on so called 'Participant Properties', tactfully named QoS properties in DDS participants. These were merged into CycloneDDS for version 0.10.0. Here is an example of the output when running the ``Vehicle`` example from this repo in the background on a single host:

.. image:: static/images/cyclonedds-ps-demo.svg
    :alt: ``cyclonedds ps --suppress-progress-bar --force-color-mode``


``cyclonedds typeof``
---------------------

.. image:: static/images/cyclonedds-typeof-help.svg
    :alt: ``cyclonedds typeof --help``

The ``typeof`` subcommand shows you the type(s) of a topic in your system. With XTypes it can happen that more than one type for each topic exists and that they are still compatible. The types are represented in IDL. Here is an example of the output when running the ``Vehicle`` example:

.. image:: static/images/cyclonedds-typeof-demo.svg
    :alt: ``cyclonedds typeof Vehicle --suppress-progress-bar --force-color-mode``


``cyclonedds subscribe``
------------------------

.. image:: static/images/cyclonedds-subscribe-help.svg
    :alt: ``cyclonedds subscribe --help``

The ``subscribe`` subcommand dynamically subscribes to a topic and shows you the data as it arrives. The type is discovered in a similar manner as ``typeof``. Here is an example of the output when running the ``Vehicle`` example:

.. image:: static/images/cyclonedds-subscribe-demo.svg
    :alt: ``timeout -s INT 10s cyclonedds subscribe Vehicle --suppress-progress-bar --force-color-mode``

``cyclonedds performance``
--------------------------

.. image:: static/images/cyclonedds-performance-help.svg
    :alt: ``cyclonedds performance --help``

The ``performance`` subcommand is a nicer frontend to ``ddsperf`` with four modes: ``publish``, ``subscribe``, ``ping`` and ``pong``. The below performance run example is the ``cyclonedds performance subscribe`` mode rendered with ``cyclonedds performance publish`` running in the background.

.. image:: static/images/cyclonedds-performance-subscribe-demo.svg
    :alt: ``cyclonedds performance --duration 21s --render-output-once-on-exit --force-color-mode subscribe --triggering-mode waitset``


Legacy tools
^^^^^^^^^^^^

There are two more tools in the Python repository which are scheduled for removal as soon as their full feature set is available using the main command line tool.

.. toctree::
    :maxdepth: 1
    :glob:

    tools.*
