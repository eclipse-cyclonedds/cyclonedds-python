"""
 * Copyright(c) 2021 ADLINK Technology Limited and others
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
from typing import List, Optional, TYPE_CHECKING

from .internal import c_call, dds_c_t
from .core import Entity, DDSException
from .topic import Topic
from .qos import _CQos


if TYPE_CHECKING:
    import cyclonedds


class Domain(Entity):
    def __init__(self, domainid: int, config: Optional[str] = None):
        self._id = domainid
        if config is not None:
            super().__init__(self._create_domain(dds_c_t.domainid(domainid), config.encode("ascii")))
        else:
            super().__init__(self._create_domain(dds_c_t.domainid(domainid), None))

    def get_participants(self) -> List[Entity]:
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
    def __init__(self, domain_id: int = 0, qos: 'cyclonedds.core.Qos' = None, listener: 'cyclonedds.core.Listener' = None):
        cqos = _CQos.qos_to_cqos(qos) if qos else None
        super().__init__(self._create_participant(domain_id, cqos, listener._ref if listener else None),
                         listener=listener)
        if cqos:
            _CQos.cqos_destroy(cqos)

    def find_topic(self, name) -> Optional[Topic]:
        ret = self._find_topic(self._ref, name.encode("ASCII"))
        if ret > 0:
            # Note that this function returns a _new_ topic instance which we do not have in our entity list
            return Topic._init_from_retcode(ret)
        elif ret == DDSException.DDS_RETCODE_PRECONDITION_NOT_MET:
            # Not finding a topic is not really an error from python standpoint
            return None

        raise DDSException(ret, f"Occurred when getting the participant of {repr(self)}")

    @c_call("dds_create_participant")
    def _create_participant(self, domain_id: dds_c_t.domainid, qos: dds_c_t.qos_p, listener: dds_c_t.listener_p) \
            -> dds_c_t.entity:
        pass

    @c_call("dds_find_topic")
    def _find_topic(self, participant: dds_c_t.entity, name: ct.c_char_p) -> dds_c_t.entity:
        pass
