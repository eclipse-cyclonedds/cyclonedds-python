from PySide6 import QtCore
import logging

def qt_message_handler(mode, context, message):
    if mode == QtCore.QtMsgType.QtInfoMsg:
        logging.info(message)
    elif mode == QtCore.QtMsgType.QtWarningMsg:
        logging.warning(message)
    elif mode == QtCore.QtMsgType.QtCriticalMsg:
        logging.critical(message)
    elif mode == QtCore.QtMsgType.QtFatalMsg:
        logging.fatal(message)
    else:
        logging.debug(message)

def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance
