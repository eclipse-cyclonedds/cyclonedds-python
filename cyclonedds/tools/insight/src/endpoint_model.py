from PySide6.QtCore import Qt, QModelIndex, QAbstractItemModel, Qt, Slot
from cyclonedds.builtin import DcpsEndpoint, DcpsParticipant
from cyclonedds import core
import logging
import os

import dds_data
from utils import EntityType


HOSTNAME_GET = core.Policy.Property("__Hostname", "")
APPNAME_GET = core.Policy.Property("__ProcessName", "")
PID_GET = core.Policy.Property("__Pid", "")
ADDRESS_GET = core.Policy.Property("__NetworkAddresses", "")


class EndpointModel(QAbstractItemModel):
    KeyRole = Qt.UserRole + 1
    ParticipantKeyRole = Qt.UserRole + 2
    ParticipantInstanceHandleRole = Qt.UserRole + 3
    TopicNameRole = Qt.UserRole + 4
    TypeNameRole = Qt.UserRole + 5
    QosRole = Qt.UserRole + 6
    TypeIdRole = Qt.UserRole + 7
    HostnameRole = Qt.UserRole + 8
    ProcessIdRole = Qt.UserRole + 9
    ProcessNameRole = Qt.UserRole + 10

    participants = {}
    endpoints = {}
    domain_id = -1
    topic_name = ""
    entity_type = EntityType.UNDEFINED

    def __init__(self, parent=None):
        super(EndpointModel, self).__init__(parent)
        print("New instance EndpointModel:", self)
        self.dds_data = dds_data.DdsData()
        # From dds_data to self
        self.dds_data.new_endpoint_signal.connect(self.new_endpoint_slot, Qt.ConnectionType.QueuedConnection)
        self.dds_data.removed_endpoint_signal.connect(self.remove_endpoint_slot, Qt.ConnectionType.QueuedConnection)
        self.dds_data.new_participant_signal.connect(self.new_participant, Qt.ConnectionType.QueuedConnection)
        self.dds_data.removed_participant_signal.connect(self.removed_participant, Qt.ConnectionType.QueuedConnection)

    def index(self, row, column, parent=QModelIndex()):
        return self.createIndex(row, column)

    def rowCount(self, parent=QModelIndex()):
        return len(self.endpoints.keys())

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        endp_key = list(self.endpoints.keys())[row]
        endp: DcpsEndpoint = self.endpoints[endp_key]

        hostname = "Unknown"
        appname = "Unknown"
        pid = "Unknown"
        if str(endp.participant_key) in self.participants.keys():
            p = self.participants[str(endp.participant_key)]
            hostname = p.qos[HOSTNAME_GET].value if p.qos[HOSTNAME_GET] is not None else "Unknown"
            appname = p.qos[APPNAME_GET].value if p.qos[APPNAME_GET] is not None else "Unknown"
            pid = p.qos[PID_GET].value if p.qos[PID_GET] is not None else "Unknown"

        if role == self.KeyRole:
            return str(endp.key)
        elif role == self.ParticipantKeyRole:
            return str(endp.participant_key)
        elif role == self.ParticipantInstanceHandleRole:
            return str(endp.participant_instance_handle)
        elif role == self.TopicNameRole:
            return str(endp.topic_name)
        elif role == self.TypeNameRole:
            return str(endp.type_name)
        elif role == self.QosRole:
            split = ""
            for idx, q in enumerate(endp.qos):
                split += "  " + str(q)
                if idx < len(endp.qos) - 1:
                    split += "\n"
            return split
        elif role == self.TypeIdRole:
            return str(endp.type_id)
        elif role == self.HostnameRole:
            return hostname
        elif role == self.ProcessIdRole:
            return pid
        elif role == self.ProcessNameRole:
            return os.path.basename(appname)

        return None

    def roleNames(self):
        return {
            self.KeyRole: b'endpoint_key',
            self.ParticipantKeyRole: b'endpoint_participant_key',
            self.ParticipantInstanceHandleRole: b'endpoint_participant_instance_handle',
            self.TopicNameRole: b'endpoint_topic_name',
            self.TypeNameRole: b'endpoint_topic_type',
            self.QosRole: b'endpoint_qos',
            self.TypeIdRole: b'endpoint_type_id',
            self.HostnameRole: b'endpoint_hostname',
            self.ProcessIdRole: b'endpoint_process_id',
            self.ProcessNameRole: b'endpoint_process_name'
        }

    @Slot(int, str, int)
    def setDomainId(self, domain_id: int, topic_name: str, entity_type: int):
        self.beginResetModel()
        self.domain_id = domain_id
        self.entity_type = EntityType(entity_type)
        self.topic_name = topic_name
        self.endpoints = {}
        self.participants = {}

        for parti in self.dds_data.getParticipants(domain_id):
            self.participants[str(parti.key)] = parti

        for (entity_end, endpoint) in self.dds_data.getEndpoints(domain_id):
            if entity_end == self.entity_type and endpoint.topic_name == self.topic_name:
                self.endpoints[str(endpoint.key)] = endpoint

        self.endResetModel()

    @Slot(int, DcpsEndpoint, EntityType)
    def new_endpoint_slot(self, domain_id: int, endpoint: DcpsEndpoint, entity_type: EntityType):
        if domain_id != self.domain_id:
            return
        if entity_type != self.entity_type:
            return

        self.beginResetModel()
        self.endpoints[str(endpoint.key)] = endpoint
        self.endResetModel()

    @Slot(int, str)
    def remove_endpoint_slot(self, domain_id, endpoint_key):
        if domain_id != self.domain_id:
            return
        
        if endpoint_key in self.endpoints.keys():
            self.beginResetModel()
            del self.endpoints[endpoint_key]
            self.endResetModel()

    @Slot(int, DcpsParticipant)
    def new_participant(self, domain_id, participant: DcpsParticipant):
        if domain_id != self.domain_id:
            return

        if str(participant.key) not in self.participants.keys():
            self.beginResetModel()
            self.participants[str(participant.key)] = participant
            self.endResetModel()

    @Slot(int, str)
    def removed_participant(self, domain_id, key: str):
        if domain_id != self.domain_id:
            return

        if key in self.participants.keys():
            self.beginResetModel()
            del self.participants[key]
            self.endResetModel()
