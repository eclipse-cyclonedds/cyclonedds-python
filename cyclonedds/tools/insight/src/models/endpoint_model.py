from PySide6.QtCore import Qt, QModelIndex, QAbstractItemModel, Qt, Slot

import dds_data


class EndpointModel(QAbstractItemModel):
    TopicNameRole = Qt.UserRole + 1

    topics = []
    domain_id = -1

    def __init__(self, parent=None):
        super(EndpointModel, self).__init__(parent)
        self.dds_data = dds_data.DdsData()

    def index(self, row, column, parent=QModelIndex()):
        return self.createIndex(row, column, self.topics[row])

    def rowCount(self, parent=QModelIndex()):
        return len(self.topics)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()

        if role == self.TopicNameRole:
            return self.topics[row]
        return None

    def roleNames(self):
        return {
            self.TopicNameRole: b'topic_name'
        }

    @Slot(int)
    def setDomainId(self, domain_id):
        self.domain_id = domain_id

    @Slot(int, str)
    def new_topic_slot(self, domain_id, topic_name):
        if domain_id != self.domain_id:
            return

        if topic_name not in self.topics:
            self.beginResetModel()
            self.topics.append(topic_name)
            self.endResetModel()

        print("topics:", self.topics)

    @Slot(int, str)
    def remove_topic_slot(self, domain_id, topic_name):
        if domain_id != self.domain_id:
            return

        if topic_name in self.topics:
            self.beginResetModel()
            self.topics.remove(topic_name)
            self.endResetModel()
