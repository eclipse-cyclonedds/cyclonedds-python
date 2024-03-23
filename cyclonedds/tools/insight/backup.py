# This Python file uses the following encoding: utf-8

import DdsData
from DdsData import Participant

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import Qt, QModelIndex, QAbstractItemModel, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QTreeView
from PySide6.QtQuick import QQuickView
from PySide6.QtCore import QObject, Signal, Property, Slot

from cyclonedds import core, domain, builtin, dynamic, util, internal

import sys
from pathlib import Path
from dataclasses import dataclass
import threading
import sys
import time
import re
from typing import List, Optional
from datetime import datetime, timedelta


class DomainModel(QAbstractItemModel):
    DomainIdRole = Qt.UserRole + 1

    domains = [0, 1, 2]

    def __init__(self, parent=None):
        super(DomainModel, self).__init__(parent)

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

class TopicModel(QAbstractItemModel):
    TopicNameRole = Qt.UserRole + 1
    ExpandedRole = Qt.UserRole + 2

    topics = ["a", "b", "x"]
    m_expanded = False

    def __init__(self, parent=None):
        super(TopicModel, self).__init__(parent)

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
        if role == self.ExpandedRole:
            return self.m_expanded
        return None

    def roleNames(self):
        return {
            self.TopicNameRole: b'topic_name',
            self.ExpandedRole: b'expanded'
        }

    @Slot()
    def expand(self):
        self.beginResetModel()
        self.m_expanded = True
        self.endResetModel()

    @Slot()
    def defalte(self):
        self.beginResetModel()
        self.m_expanded = False
        self.endResetModel()

    @Slot(result=bool)
    def isExpanded(self):
        return self.m_expanded


class TreeModel(QAbstractItemModel):

    UserRole = Qt.UserRole + 1
    DisplayRole = Qt.UserRole + 2
    UserRole = Qt.UserRole + 3
    UserRole = Qt.UserRole + 4

    def __init__(self, rootItem, parent=None):
        super(TreeModel, self).__init__(parent)
        self.rootItem = rootItem

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
        return None

    def roleNames(self):
        return {
            self.DisplayRole: b'display'
        }

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return super(TreeModel, self).flags(index)

class TreeNode:
    def __init__(self, data, parent=None):
        self.parentItem = parent
        self.itemData = data
        self.childItems = []

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

g_running = True


class Listener(core.Listener):

    def on_inconsistent_topic(self, reader, status) -> None:
        print("on_inconsistent_topic")

    def on_data_available(self, reader) -> None:
        print("on_data_available", reader)
        if reader:
            cond = core.ReadCondition(
                reader, core.SampleState.Any | core.ViewState.Any | core.InstanceState.Any
            )
            for sample in reader.take(N=20, condition=cond):
                print()
                print(sample)
                print(sample.sample_info)
                
                

    def on_liveliness_lost(self, writer, status) -> None:
        print("on_liveliness_lost")

    def on_liveliness_changed(self, reader, status) -> None:
        print("on_liveliness_changed, alive_count:", status.alive_count)

    def on_offered_deadline_missed(self, writer, status) -> None:
        print("on_offered_deadline_missed")

    def on_offered_incompatible_qos(self, writer, status) -> None:
        print("on_offered_incompatible_qos")

    def on_data_on_readers(self, subscriber) -> None:
        print("on_data_on_readers")

    def on_sample_lost(self, writer, status) -> None:
        print("on_sample_lost")

    def on_sample_rejected(self, reader, status) -> None:
        print("on_sample_rejected")

    def on_requested_deadline_missed(self, reader, status) -> None:
        print("on_requested_deadline_missed")

    def on_requested_incompatible_qos(self, reader, status) -> None:
        print("on_requested_incompatible_qos")

    def on_publication_matched(self, writer, status) -> None:
        print("on_publication_matched")

    def on_subscription_matched(self, reader, status) -> None:
        print("on_subscription_matched")


def discover(dds_data):
    print("discovery ...")

    domain_id = 0

    dds_data.add_domain(domain_id)

    dp = domain.DomainParticipant(domain_id)

    listener_participant = Listener()
    listener_pub= Listener()
    listener_sub = Listener()

    rdp = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsParticipant)#, listener=listener_participant)
    rcp = core.ReadCondition(
        rdp, core.SampleState.Any | core.ViewState.Any | core.InstanceState.Any
    )
    rdw = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsPublication)#, listener=listener_pub)
    rcw = core.ReadCondition(
        rdw, core.SampleState.Any | core.ViewState.Any | core.InstanceState.Any
    )
    rdr = builtin.BuiltinDataReader(dp, builtin.BuiltinTopicDcpsSubscription)#, listener=listener_sub)
    rcr = core.ReadCondition(
        rdr, core.SampleState.Any | core.ViewState.Any | core.InstanceState.Any
    )

    hostname_get = core.Policy.Property("__Hostname", "")
    appname_get = core.Policy.Property("__ProcessName", "")
    pid_get = core.Policy.Property("__Pid", "")
    address_get = core.Policy.Property("__NetworkAddresses", "")

    print()

    while g_running:

        time.sleep(1)

        for p in rdp.take(N=20, condition=rcp):
            #print(p.sample_info)
            if p.sample_info.sample_state == core.SampleState.NotRead and p.sample_info.instance_state == core.InstanceState.Alive:
                hostname = (
                    p.qos[hostname_get].value
                    if p.qos[hostname_get] is not None
                    else "Unknown"
                )
                appname = (
                    p.qos[appname_get].value
                    if p.qos[appname_get] is not None
                    else "Unknown"
                )
                pid = p.qos[pid_get].value if p.qos[pid_get] is not None else "Unknown"
                address = (
                    p.qos[address_get].value
                    if p.qos[address_get] is not None
                    else "Unknown"
                )
                print("Found Participant: " + str(p.key))
                dds_data.add_domain_participant(domain_id, Participant(p.key, hostname,appname, pid, address))
            elif p.sample_info.instance_state == core.InstanceState.NotAliveDisposed:
                print("Removed Participant: " + str(p.key))

        for pub in rdw.take(N=20, condition=rcw):
            #print(pub.sample_info)
            if pub.sample_info.sample_state == core.SampleState.NotRead and pub.sample_info.instance_state == core.InstanceState.Alive:
                print("pub.pariticpantkey", pub.participant_key)

                childX = TreeNode(pub.topic_name, child1)
                child1.appendChild(childX)
            elif pub.sample_info.instance_state == core.InstanceState.NotAliveDisposed:
                print("pub removed: ", pub.participant_key)


        for sub in rdr.take(N=20, condition=rcr):

            #print(sub.sample_info)
            if sub.sample_info.sample_state == core.SampleState.NotRead and sub.sample_info.instance_state == core.InstanceState.Alive:
                print("Found subscriber participant:", sub.participant_key, "on topic: ", sub.topic_name)

            elif sub.sample_info.instance_state == core.InstanceState.NotAliveDisposed:
                print("Removed subscriber participant:", sub.participant_key)


    print("discovery ... DONE")


if __name__ == "__main__":
    print("Starting App...")
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    dds_data = DdsData.DdsData()

    # Create a simple tree structure
    rootItem = TreeNode("Root")
    child1 = TreeNode("Domain 0", rootItem)
    child2 = TreeNode("Domain 3", rootItem)
    child3 = TreeNode("TopicName1", child1)
    child4 = TreeNode("TopicName4", child1)
    child5 = TreeNode("TopicName5", child2)
    rootItem.appendChild(child1)
    rootItem.appendChild(child2)
    child1.appendChild(child3)
    child1.appendChild(child4)
    child2.appendChild(child5)

    discover_thread = threading.Thread(target=discover, args=(dds_data,))
    discover_thread.start()

    # Create QAbstractItemModel with the custom TreeModel
    treeModel = TreeModel(rootItem)

    engine.rootContext().setContextProperty("treeModel", treeModel)

    domainModel = DomainModel()
    engine.rootContext().setContextProperty("domainModel", domainModel)

    topicModel = TopicModel()
    engine.rootContext().setContextProperty("topicModel", topicModel)


    qml_file = Path(__file__).resolve().parent / "main.qml"
    engine.load(qml_file)
    if not engine.rootObjects():
        sys.exit(-1)

    ret_code = app.exec()
    g_running = False
    discover_thread.join()
    sys.exit(ret_code)
