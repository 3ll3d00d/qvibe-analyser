import logging

import numpy as np
from qtpy.QtCore import QObject, Signal
from qtpy.QtWidgets import QMainWindow

from common import RingBuffer
from model.preferences import LOGGING_LEVEL
from ui.logs import Ui_logsForm


class LogViewer(QMainWindow, Ui_logsForm):
    change_level = Signal(str)
    set_size = Signal(int)
    set_exclude_filter = Signal(str)

    '''
    A window which displays logging.
    '''

    def __init__(self, max_size):
        super(LogViewer, self).__init__()
        self.setupUi(self)
        self.maxRows.setValue(max_size)
        self.logViewer.setMaximumBlockCount(max_size)

    def closeEvent(self, event):
        '''
        Propagates the window close event.
        '''
        self.hide()

    def set_log_size(self, size):
        '''
        Updates the log size.
        :param level: the new size.
        '''
        self.set_size.emit(size)
        self.logViewer.setMaximumBlockCount(size)

    def set_log_level(self, level):
        '''
        Updates the log level.
        :param level: the new level.
        '''
        self.change_level.emit(level)

    def set_excludes(self):
        self.set_exclude_filter.emit(self.excludes.text())

    def refresh(self, data):
        '''
        Refreshes the displayed data.
        :param data: the data.
        '''
        self.logViewer.clear()
        for d in data:
            if d is not None:
                self.logViewer.appendPlainText(d)

    def append_msg(self, msg):
        '''
        Shows the message.
        :param idx: the idx.
        :param msg: the msg.
        '''
        self.logViewer.appendPlainText(msg)
        self.logViewer.verticalScrollBar().setValue(self.logViewer.verticalScrollBar().maximum())


class MessageSignals(QObject):
    append_msg = Signal(str, name='append_msg')


class RollingLogger(logging.Handler):
    def __init__(self, preferences, size=1000, parent=None):
        super().__init__()
        self.__buffer = RingBuffer(size, dtype=np.object)
        self.__signals = MessageSignals()
        self.__visible = False
        self.__window = None
        self.__preferences = preferences
        self.__excludes = []
        self.parent = parent
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s	- %(name)s - %(funcName)s - %(message)s'))
        level = self.__preferences.get(LOGGING_LEVEL)
        if level is not None and level in logging._nameToLevel:
            level = logging._nameToLevel[level]
        else:
            level = logging.INFO
        self.__root = self.__init_root_logger(level)
        self.__levelName = logging.getLevelName(level)

    def __init_root_logger(self, level):
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.addHandler(self)
        return root_logger

    def emit(self, record):
        msg = self.format(record)
        if not any(e in msg for e in self.__excludes):
            self.__buffer.append(msg)
            self.__signals.append_msg.emit(msg)

    def show_logs(self):
        '''
        Creates a new log viewer window.
        '''
        if self.__window is None:
            self.__window = LogViewer(len(self.__buffer))
            self.__window.set_size.connect(self.set_size)
            self.__window.change_level.connect(self.change_level)
            self.__window.set_exclude_filter.connect(self.set_excludes)
            self.__signals.append_msg.connect(self.__window.append_msg)
            level_idx = self.__window.logLevel.findText(self.__levelName)
            self.__window.logLevel.setCurrentIndex(level_idx)
        self.__window.show()
        self.__window.refresh(self.__buffer)

    def set_excludes(self, excludes):
        self.__excludes = excludes.split(',')
        if len(self.__excludes) > 0:
            old_buf = self.__buffer
            self.__buffer = RingBuffer(old_buf.maxlen, dtype=np.object)
            for m in old_buf:
                if any(e in m for e in self.__excludes):
                    pass
                else:
                    self.__buffer.append(m)
            if self.__window is not None:
                self.__window.refresh(self.__buffer)

    def set_size(self, size):
        '''
        Changes the size of the log cache.
        '''
        old_buf = self.__buffer
        self.__buffer = RingBuffer(size, dtype=np.object)
        self.__buffer.extend(old_buf)
        if self.__window is not None:
            self.__window.refresh(self.__buffer)

    def change_level(self, level):
        '''
        Change the root logger level.
        :param level: the new level name.
        '''
        logging.info(f"Changing log level from {self.__levelName} to {level}")
        self.__root.setLevel(level)
        self.__levelName = level
        self.__preferences.set(LOGGING_LEVEL, self.__levelName)


def to_millis(start, end):
    '''
    Calculates the differences in time in millis.
    :param start: start time in seconds.
    :param end: end time in seconds.
    :return: delta in millis.
    '''
    return round((end - start) * 1000)
