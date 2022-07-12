"""
 * Copyright(c) 2021 to 2022 ZettaScale Technology and others
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
"""

import ctypes as ct
from typing import List, Optional

from .internal import c_call, dds_c_t
from .core import Entity, DDSException, Listener
from .topic import Topic
from .qos import _CQos, LimitedScopeQos, DomainParticipantQos, Qos


class Domain(Entity):
    """A Domain represents a DDS domain with a set configuration. On the network a Domain
    is nothing more than an integer id. DDS domains are guaranteed to never mix, allowing
    logical separation of parts of your application.
    """

    def __init__(self, domain_id: int, config: Optional[str] = None):
        """Initialize a domain with domain id and configuration. The configuration is either
        a xml string or an url to a xml file.
        """
        self._id = domain_id
        if config is not None:
            super().__init__(self._create_domain(dds_c_t.domainid(domain_id), config.encode("ascii")))
        else:
            super().__init__(self._create_domain(dds_c_t.domainid(domain_id), None))

    def get_participants(self) -> List[Entity]:
        """Get all local participants of a domain."""
        num_participants = self._lookup_participant(self._id, None, 0)
        if num_participants < 0:
            raise DDSException(num_participants, f"Occurred when getting the number of participants of domain {self._id}")
        elif num_participants == 0:
            return []

        participants_list = (dds_c_t.entity * num_participants)()

        ret = self._lookup_participant(
            self._id,
            ct.cast(ct.byref(participants_list), ct.POINTER(dds_c_t.entity)),
            num_participants
        )

        if ret >= 0:
            return [Entity.get_entity(participants_list[i]) for i in range(ret)]

        raise DDSException(ret, f"Occurred when getting the participants of domain {self._id}")

    @c_call("dds_create_domain")
    def _create_domain(self, id: dds_c_t.domainid, config: ct.c_char_p) -> dds_c_t.entity:
        pass

    @c_call("dds_lookup_participant")
    def _lookup_participant(self, id: dds_c_t.domainid, participants: ct.POINTER(dds_c_t.entity), size: ct.c_size_t) \
            -> dds_c_t.entity:
        pass


class DomainParticipant(Entity):
    """The DomainParticipant is the central entrypoint for any DDS Application.
    It serves as root entity for all other entities.
    """

    def __init__(self, domain_id: int = 0, qos: Optional[Qos] = None,
                 listener: Optional[Listener] = None):
        """Initialize a DomainParticipant.

        Parameters
        ----------
        domain_id: int, optional, default 0
            The DDS Domain to use
        qos: cyclonedds.qos.Qos, optional, default None
            Apply DomainParticipant Qos.
        listener: cyclonedds.core.Listener, optional, default None
            Attach a Listener to the participant
        """
        if qos is not None:
            if isinstance(qos, LimitedScopeQos) and not isinstance(qos, DomainParticipantQos):
                raise TypeError(f"{qos} is not appropriate for a DomainParticipant")
            elif not isinstance(qos, Qos):
                raise TypeError(f"{qos} is not a valid qos object")

        if listener is not None:
            if not isinstance(listener, Listener):
                raise TypeError(f"{listener} is not a valid listener object.")

        cqos = _CQos.qos_to_cqos(qos) if qos else None
        try:
            super().__init__(self._create_participant(domain_id, cqos, listener._ref if listener else None),
                             listener=listener)
        finally:
            if cqos:
                _CQos.cqos_destroy(cqos)

    @c_call("dds_create_participant")
    def _create_participant(self, domain_id: dds_c_t.domainid, qos: dds_c_t.qos_p, listener: dds_c_t.listener_p) \
            -> dds_c_t.entity:
        pass
