Usage
=====

Here should be some extensive documentation on how to use the API.


Participant
^^^^^^^^^^^

All communication within a DDS network happens through *domains*. A domain is a combination of an integer identifier and a set of config parameters. The concept of a domain is what allows you to run multiple DDS systems on a single network without interference. As in any other DDS API, this connection to a domain is represented with a `DomainParticipant` . Your connection to the DDS network is started with the creation of the participant and ended with its destruction.

.. code-block:: python
    :linenos:

    from cyclonedds.domain import Participant

    dp = Participant(0)


