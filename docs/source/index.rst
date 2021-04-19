CycloneDDS Python
=================

Cyclone DDS Python is a modern and easy to use binding for Cyclone DDS. It provides access to almost all features available in the CycloneDDS C API while abstracting all of C's quirks and hassles.

Features
--------

* Modern Python API for python 3.6+ (python 3.10 support experimental while it is in alpha)
* Object oriented design, taking care of any C memory management under the hood
* (Eventually) fully type-hinted and documented API that your IDE will love

Getting started
---------------

Getting your hands dirty for the first time? Here are some points to get started for any skill level.

* **First steps:** ``first_steps_with_python`` | :doc:`intro` | :ref:`first_app`
* **Usage:**

  a. IDL datatypes in Python
  b. Publishing and subscribing
  c. Working with Qos
  d. Conditions and Waitsets
  e. Listeners
  f. Using built-in topics

* **Examples:** are available in the *repository*.

..  a. :ref:`corepubsub`
..  b. :ref:`qos`
..  c. :ref:`conditionswaitsets`
..  d. :ref:`listeners`
..  e. :ref:`builtin`

Getting help
------------

Having trouble with something? These resources might provide some answers.

* Go to the Frequently Asked Questions.
* Look through the :ref:`index <genindex>` or run a :ref:`search <search>`.
* Report bugs on GitHub via the issue tracker.
* Ask your question on the GitHub discussions page.

API documentation
-----------------

In-depth information on all parts of the API.

.. toctree::
  :maxdepth: 2
  :hidden:

  intro
  datatypes

.. toctree::
   :maxdepth: 3

   usage
   api

Other
-----

* Our GitHub repository
* Entries on Pypi for *pycdr* and *cyclonedds*
* Changelog
* Learn more about :doc:`DDS <dds>`

.. toctree::
  :maxdepth: 2
  :hidden:

  pycdr
  dds


