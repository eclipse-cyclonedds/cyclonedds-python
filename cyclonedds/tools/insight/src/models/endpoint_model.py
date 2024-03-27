from PySide6.QtCore import Qt, QModelIndex, QAbstractItemModel, Qt, Slot
from cyclonedds.builtin import DcpsEndpoint
import logging

import dds_data


class EndpointModel(QAbstractItemModel):
    KeyRole = Qt.UserRole + 1
    ParticipantKeyRole = Qt.UserRole + 2
    ParticipantInstanceHandleRole = Qt.UserRole + 3
    TopicNameRole = Qt.UserRole + 4
    TypeNameRole = Qt.UserRole + 5
    QosRole = Qt.UserRole + 6
    TypeIdRole = Qt.UserRole + 7

    endpoints = {}
    domain_id = -1
    topic_name = ""
    publisher = True

    def __init__(self, parent=None):
        super(EndpointModel, self).__init__(parent)
        print("New instance EndpointModel:", self)
        self.dds_data = dds_data.DdsData()

        # From dds_data to self
        self.dds_data.new_endpoint_signal.connect(self.new_endpoint_slot, Qt.ConnectionType.QueuedConnection)
        self.dds_data.removed_endpoint_signal.connect(self.remove_endpoint_slot, Qt.ConnectionType.QueuedConnection)

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

        return None

    def roleNames(self):
        return {
            self.KeyRole: b'endpoint_key',
            self.ParticipantKeyRole: b'endpoint_participant_key',
            self.ParticipantInstanceHandleRole: b'endpoint_participant_instance_handle',
            self.TopicNameRole: b'endpoint_topic_name',
            self.TypeNameRole: b'endpoint_topic_type',
            self.QosRole: b'endpoint_qos',
            self.TypeIdRole: b'endpoint_type_id'
        }

    @Slot(int, str, bool)
    def setDomainId(self, domain_id: int, topic_name: str, pub: bool):
        self.beginResetModel()
        self.domain_id = domain_id
        self.publisher = pub
        self.topic_name = topic_name
        self.endpoints = {}

        for (pub_end, endpoint) in self.dds_data.getEndpoints(domain_id):
            if pub_end == pub and endpoint.topic_name == self.topic_name:
                self.endpoints[str(endpoint.key)] = endpoint

        self.endResetModel()

    @Slot(int, DcpsEndpoint, bool)
    def new_endpoint_slot(self, domain_id: int, endpoint: DcpsEndpoint, pub: bool):
        if domain_id != self.domain_id:
            return
        if pub != self.publisher:
            return

        logging.debug("new_endpoint_slot " + str(domain_id) + ", " + str(endpoint))
        self.beginResetModel()
        self.endpoints[str(endpoint.key)] = endpoint
        self.endResetModel()

        print(self.publisher, len(self.endpoints))

    @Slot(int, str)
    def remove_endpoint_slot(self, domain_id, endpoint_key):
        if domain_id != self.domain_id:
            return
        
        if endpoint_key in self.endpoints.keys():
            logging.debug("remove_endpoint_slot: " + endpoint_key)
            print("self.endpoints.keys()", self.endpoints.keys())
            self.beginResetModel()
            del self.endpoints[endpoint_key]
            self.endResetModel()
            print("self.endpoints.keys()", self.endpoints.keys())
