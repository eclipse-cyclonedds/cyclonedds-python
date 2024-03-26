from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import Qt, QModelIndex, QAbstractItemModel, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QTreeView
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import QObject, Signal, Property, Slot

import dds_data
from enum import Enum

class NodeType(Enum):
	ROOT = 1
	DOMAIN = 2
	TOPIC = 3

class TreeNode:
    def __init__(self, data: str, is_domain=False, parent=None):
        self.parentItem = parent
        self.itemData = data
        self.childItems = []
        self.is_domain = is_domain

    def appendChild(self, item):
        self.childItems.append(item)

    def child(self, row):
        return self.childItems[row]

    def childCount(self):
        return len(self.childItems)

    def columnCount(self):
        return 1

    def data(self, column):
        return self.itemData

    def parent(self):
        return self.parentItem
    def row(self):
        if self.parentItem:
            return self.parentItem.childItems.index(self)
        return 0

    def removeChild(self, row):
        del self.childItems[row]

    def isDomain(self):
        return self.is_domain

class TreeModel(QAbstractItemModel):

    IsDomainRole = Qt.UserRole + 1
    DisplayRole = Qt.UserRole + 2


    def __init__(self, rootItem: TreeNode, parent=None):
        super(TreeModel, self).__init__(parent)
        self.rootItem = rootItem

        self.dds_data = dds_data.DdsData()
        self.dds_data.new_topic_signal.connect(self.new_topic_slot, Qt.ConnectionType.QueuedConnection)
        self.dds_data.remove_topic_signal.connect(self.remove_topic_slot, Qt.ConnectionType.QueuedConnection)
        self.dds_data.new_domain_signal.connect(self.addDomain, Qt.ConnectionType.QueuedConnection)


    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parentItem = parent.internalPointer() if parent.isValid() else self.rootItem
        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        childItem = index.internalPointer()
        parentItem = childItem.parent()
        if parentItem == self.rootItem:
            return QModelIndex()
        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()
        return parentItem.childCount()

    def columnCount(self, parent=QModelIndex()):
        return 1  # Only one column for a simple tree

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        item = index.internalPointer()
        if role == Qt.DisplayRole:
            return item.data()
        if role == self.DisplayRole:
            return item.data(index)
        if role == self.IsDomainRole:
            return item.isDomain()
        return None

    def roleNames(self):
        return {
            self.DisplayRole: b'display',
            self.IsDomainRole: b'is_domain',
        }

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return super(TreeModel, self).flags(index)

    @Slot(int, str)
    def new_topic_slot(self, domain_id, topic_name):
        for idx in range(self.rootItem.childCount()):
            child: TreeNode = self.rootItem.child(idx)
            if child.data(0) == str(domain_id):
                parent_index = self.createIndex(idx, 0, child)
                row_count = child.childCount()
                self.beginInsertRows(parent_index, row_count, row_count)
                topic_child = TreeNode(topic_name, False, child)
                child.appendChild(topic_child)
                self.endInsertRows()

    @Slot(int, str)
    def remove_topic_slot(self, domain_id, topic_name):
        for idx in range(self.rootItem.childCount()):
            child: TreeNode = self.rootItem.child(idx)
            if child.data(0) == str(domain_id):
                found_topic_idx = -1
                for idx_topic in range(child.childCount()):
                    child_topic: TreeNode = child.child(idx_topic)
                    if child_topic.data(0) == str(topic_name):
                        self.beginRemoveRows(self.createIndex(idx, 0, child), idx_topic, idx_topic)
                        child.removeChild(idx_topic)
                        self.endRemoveRows()
                        break


    @Slot(int)
    def addDomain(self, domain_id):

        for idx in range(self.rootItem.childCount()):
            child: TreeNode = self.rootItem.child(idx)
            if child.data(0) == str(domain_id):
                return
            
        self.beginResetModel()
        domainChild = TreeNode(str(domain_id), True, self.rootItem)
        self.rootItem.appendChild(domainChild)
        self.endResetModel()

    @Slot(int)
    def removeDomain(self, domain_id):
        dom_child_idx = -1
        for idx in range(self.rootItem.childCount()):
            child: TreeNode = self.rootItem.child(idx)
            if child.data(0) == str(domain_id):
                dom_child_idx = idx
                break

        if  dom_child_idx != -1:
            self.beginResetModel()
            self.rootItem.removeChild(dom_child_idx)
            self.endResetModel()
            
    @Slot(str)
    def removeDomainRequest(self, domain_id):
        print("removeDomainRequest", domain_id)
        #self.dds_data.remove_domain(int(domain_id))

    @Slot(int)
    def addDomainRequest(self, domain_id):
        self.dds_data.add_domain(domain_id)
