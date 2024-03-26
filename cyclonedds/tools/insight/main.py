# This Python file uses the following encoding: utf-8

import resources
import DdsData

from models.domain_model import DomainModel
from models.topic_model import TopicModel
from utils import qt_message_handler

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtGui import QIcon

import logging
import sys
from pathlib import Path
import threading

from models.tree_model import TreeModel, TreeNode

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)s] %(message)s')

    running = [True]

    qInstallMessageHandler(qt_message_handler)

    logging.info("Starting App...")

    rootItem = TreeNode("Root")

    app = QGuiApplication(sys.argv)
    app.setWindowIcon(QIcon("./res/cyclonedds.png"))
    app.setApplicationName("CycloneDDS Insight")
    app.setApplicationDisplayName("CycloneDDS Insight")
    app.setOrganizationName("cyclonedds")
    app.setOrganizationDomain("org.eclipse.cyclonedds")

    dds_data = DdsData.DdsData()
    dds_data.set_running(running)

    domainModel = DomainModel()

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("domainModel", domainModel)

    treeModel = TreeModel(rootItem)
    engine.rootContext().setContextProperty("treeModel", treeModel)

    qmlRegisterType(TopicModel, "org.eclipse.cyclonedds.insight", 1, 0, "TopicModel")

    qml_file = f"{Path(__file__).resolve().parent}/views/main.qml"
    engine.load(qml_file)
    if not engine.rootObjects():
        logging.critical("Failed to load qml")
        sys.exit(-1)

    #discover_thread = threading.Thread(target=discover, args=(0, dds_data,running))
    #discover_thread.start()
    dds_data.add_domain(0)
    dds_data.add_domain(1)

    logging.info("qt ...")
    ret_code = app.exec()
    logging.info("qt ... DONE")

    running[0] = False
    dds_data.join_observer()

    sys.exit(ret_code)
