from typing import Optional
import warnings

from .entity_qos import EntityQosMapper

from cyclonedds.core import Qos


def warning_msg(message, category, filename, lineno, file=None, line=None):
    return "%s: %s\n" % (category.__name__, message)


warnings.formatwarning = warning_msg


class InapplicableQosWarning(UserWarning):
    pass


class QosPerEntity:
    def __init__(self, entity):
        self.topic_qos: Optional[Qos] = None
        self.subscriber_qos: Optional[Qos] = None
        self.publisher_qos: Optional[Qos] = None
        self.datareader_qos: Optional[Qos] = None
        self.datawriter_qos: Optional[Qos] = None
        self.entity = entity  # Keep track of the original entity for qos-all

    def entity_qos(self, qos, entity):
        if entity == "topic":
            self.topic_qos = self.check_entity_qos("topic", EntityQosMapper.topic, qos)
        elif entity == "publisher":
            self.publisher_qos = self.check_entity_qos("publisher", EntityQosMapper.pubsub, qos)
        elif entity == "subscriber":
            self.subscriber_qos = self.check_entity_qos("subscriber", EntityQosMapper.pubsub, qos)
        elif entity == "datawriter":
            self.datawriter_qos = self.check_entity_qos("datawriter", EntityQosMapper.writer, qos)
        elif entity == "datareader":
            self.datareader_qos = self.check_entity_qos("datareader", EntityQosMapper.reader, qos)
        else:  # qos-all
            for e in ["topic", "publisher", "subscriber", "datawriter", "datareader"]:
                self.entity_qos(qos, e)

    def check_entity_qos(self, entity, eqos_mapper, qos):
        eq = []
        for q in qos:
            policy_scope = f"Policy.{q.__scope__}"

            if policy_scope in eqos_mapper:
                eq.append(q)
            elif self.entity != "all" and self.entity is not None:
                warnings.warn(f"The {q} is not applicable for {entity}, will be ignored.", InapplicableQosWarning)
        return Qos(*eq)
