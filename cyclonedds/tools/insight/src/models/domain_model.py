from PySide6.QtCore import Qt, QModelIndex, QAbstractItemModel, Qt, Slot

import dds_data


class DomainModel(QAbstractItemModel):
    DomainIdRole = Qt.UserRole + 1

    domains = []

    def __init__(self, parent=None):
        super(DomainModel, self).__init__(parent)
        self.dds_data = dds_data.DdsData()
        self.dds_data.new_domain_signal.connect(self.addDomain, Qt.ConnectionType.QueuedConnection)

    def index(self, row, column, parent=QModelIndex()):
        return self.createIndex(row, column, self.domains[row])

    def rowCount(self, parent=QModelIndex()):
        return len(self.domains)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()

        if role == self.DomainIdRole:
            return self.domains[row]
        return None

    def roleNames(self):
        return {
            self.DomainIdRole: b'domain_id'
        }

    @Slot(int)
    def addDomain(self, domain_id):
        if domain_id not in self.domains:
            self.beginResetModel()
            self.domains.append(domain_id)
            self.endResetModel()

    @Slot(int)
    def removeDomain(self, domain_id):
        if domain_id in self.domains:
            self.beginResetModel()
            self.domains.remove(domain_id)
            self.endResetModel()
