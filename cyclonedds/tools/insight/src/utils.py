from PySide6 import QtCore
import logging
import os
from enum import Enum

@QtCore.QEnum
class EntityType(Enum):
    UNDEFINED = 1
    TOPIC = 2
    READER = 3
    WRITER = 4

def qt_message_handler(mode, context, message):
    file = os.path.basename(context.file)
    log_msg = f"[{file}:{context.line}] {message}"
    if mode == QtCore.QtMsgType.QtInfoMsg:
        logging.info(log_msg)
    elif mode == QtCore.QtMsgType.QtWarningMsg:
        logging.warning(log_msg)
    elif mode == QtCore.QtMsgType.QtCriticalMsg:
        logging.critical(log_msg)
    elif mode == QtCore.QtMsgType.QtFatalMsg:
        logging.fatal(log_msg)
    else:
        logging.debug(log_msg)

def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance
