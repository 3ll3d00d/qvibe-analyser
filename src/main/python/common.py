import logging
import time
from collections import Sequence
from contextlib import contextmanager

import numpy as np
import pyqtgraph as pg
from matplotlib.font_manager import FontProperties
from qtpy import QtCore
from qtpy.QtCore import QRunnable
from qtpy.QtGui import QCursor, QFont
from qtpy.QtWidgets import QApplication

logger = logging.getLogger('qta.common')


class ReactorRunner(QRunnable):
    def __init__(self, reactor):
        super().__init__()
        self.__reactor = reactor

    def run(self):
        self.__reactor.run(installSignalHandlers=False)

    def stop(self):
        self.__reactor.callFromThread(self.__reactor.stop)
        time.sleep(0.5)


@contextmanager
def wait_cursor(msg=None):
    '''
    Allows long running functions to show a busy cursor.
    :param msg: a message to put in the status bar.
    '''
    try:
        QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
        yield
    finally:
        QApplication.restoreOverrideCursor()


@contextmanager
def block_signals(widget):
    '''
    blocks signals on a given widget
    :param widget: the widget.
    '''
    try:
        widget.blockSignals(True)
        yield
    finally:
        widget.blockSignals(False)


class RingBuffer(Sequence):
    def __init__(self, capacity, dtype=np.float64):
        """
        Create a new ring buffer with the given capacity and element type

        Parameters
        ----------
        capacity: int
            The maximum capacity of the ring buffer
        dtype: data-type, optional
            Desired type of buffer elements. Use a type like (float, 2) to
            produce a buffer with shape (N, 2)
        """
        self.__buffer = np.empty(capacity, dtype)
        self.__left_idx = 0
        self.__right_idx = 0
        self.__capacity = capacity
        self.__event_count = 0

    def unwrap(self):
        """ Copy the data from this buffer into unwrapped form """
        return np.concatenate((
            self.__buffer[self.__left_idx:min(self.__right_idx, self.__capacity)],
            self.__buffer[:max(self.__right_idx - self.__capacity, 0)]
        ))

    def take_event_count(self, if_multiple=None):
        '''
        :param if_multiple: if set, only take the event count if it is a multiple of the supplied value.
        :return: the count of items added since the last take if the count is taken.
        '''
        count = self.__event_count
        if if_multiple is None or count % if_multiple == 0:
            self.__event_count = 0
            return count
        else:
            return None

    def _fix_indices(self):
        """
        Enforce our invariant that 0 <= self._left_index < self._capacity
        """
        if self.__left_idx >= self.__capacity:
            self.__left_idx -= self.__capacity
            self.__right_idx -= self.__capacity
        elif self.__left_idx < 0:
            self.__left_idx += self.__capacity
            self.__right_idx += self.__capacity

    @property
    def idx(self):
        return self.__left_idx, self.__right_idx

    @property
    def is_full(self):
        """ True if there is no more space in the buffer """
        return len(self) == self.__capacity

    # numpy compatibility
    def __array__(self):
        return self.unwrap()

    @property
    def dtype(self):
        return self.__buffer.dtype

    @property
    def shape(self):
        return (len(self),) + self.__buffer.shape[1:]

    @property
    def maxlen(self):
        return self.__capacity

    def append(self, value):
        if self.is_full:
            if not len(self):
                return
            else:
                self.__left_idx += 1

        self.__buffer[self.__right_idx % self.__capacity] = value
        self.__right_idx += 1
        self.__event_count += 1
        self._fix_indices()

    def peek(self):
        if len(self) == 0:
            return None
        idx = (self.__right_idx % self.__capacity) - 1
        logger.debug(f"Peeking at idx {idx}")
        res = self.__buffer[idx]
        return res

    def append_left(self, value):
        if self.is_full:
            if not len(self):
                return
            else:
                self.__right_idx -= 1

        self.__left_idx -= 1
        self._fix_indices()
        self.__buffer[self.__left_idx] = value
        self.__event_count += 1

    def extend(self, values):
        lv = len(values)
        if len(self) + lv > self.__capacity:
            if not len(self):
                return
        if lv >= self.__capacity:
            # wipe the entire array! - this may not be threadsafe
            self.__buffer[...] = values[-self.__capacity:]
            self.__right_idx = self.__capacity
            self.__left_idx = 0
            return

        ri = self.__right_idx % self.__capacity
        sl1 = np.s_[ri:min(ri + lv, self.__capacity)]
        sl2 = np.s_[:max(ri + lv - self.__capacity, 0)]
        self.__buffer[sl1] = values[:sl1.stop - sl1.start]
        self.__buffer[sl2] = values[sl1.stop - sl1.start:]
        self.__right_idx += lv

        self.__left_idx = max(self.__left_idx, self.__right_idx - self.__capacity)
        self.__event_count += len(values)

    def extend_left(self, values):
        lv = len(values)
        if len(self) + lv > self.__capacity:
            if not len(self):
                return
        if lv >= self.__capacity:
            # wipe the entire array! - this may not be threadsafe
            self.__buffer[...] = values[:self.__capacity]
            self.__right_idx = self.__capacity
            self.__left_idx = 0
            return

        self.__left_idx -= lv
        self._fix_indices()
        li = self.__left_idx
        sl1 = np.s_[li:min(li + lv, self.__capacity)]
        sl2 = np.s_[:max(li + lv - self.__capacity, 0)]
        self.__buffer[sl1] = values[:sl1.stop - sl1.start]
        self.__buffer[sl2] = values[sl1.stop - sl1.start:]

        self.__right_idx = min(self.__right_idx, self.__left_idx + self.__capacity)
        self.__event_count += len(values)

    def __len__(self):
        return self.__right_idx - self.__left_idx

    def __getitem__(self, item):
        # handle simple (b[1]) and basic (b[np.array([1, 2, 3])]) fancy indexing specially
        if not isinstance(item, tuple):
            item_arr = np.asarray(item)
            if issubclass(item_arr.dtype.type, np.integer):
                item_arr = (item_arr + self.__left_idx) % self.__capacity
                return self.__buffer[item_arr]

        # for everything else, get it right at the expense of efficiency
        return self.unwrap()[item]

    def __iter__(self):
        # alarmingly, this is comparable in speed to using itertools.chain
        return iter(self.unwrap())

    # Everything else
    def __repr__(self):
        return '<RingBuffer of {!r}>'.format(np.asarray(self))


class PlotWidgetWithDateAxis(pg.PlotWidget):
    def __init__(self, parent=None, background='default', **kargs):
        super().__init__(parent=parent,
                         background=background,
                         axisItems={'bottom': TimeAxisItem(orientation='bottom')},
                         **kargs)


class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        import datetime
        return [str(datetime.timedelta(seconds=value)).split('.')[0] for value in values]


def format_pg_chart(chart, x_lim, y_lim):
    '''
    Applies a standard format to a pyqtgraph chart.
    :param chart: the chart.
    :param x_lim: the x axis limits.
    :param y_lim: the y axis limits.
    '''
    label_font = QFont()
    fp = FontProperties()
    label_font.setPointSize(fp.get_size_in_points() * 0.7)
    label_font.setFamily(fp.get_name())
    for name in ['left', 'right', 'bottom', 'top']:
        chart.getPlotItem().getAxis(name).setTickFont(label_font)
    chart.getPlotItem().showGrid(x=True, y=True, alpha=0.5)
    chart.getPlotItem().disableAutoRange()
    chart.getPlotItem().setLimits(xMin=x_lim[0], xMax=x_lim[1], yMin=0, yMax=150)
    chart.getPlotItem().setXRange(*x_lim, padding=0.0)
    chart.getPlotItem().setYRange(*y_lim, padding=0.0)
    chart.getPlotItem().setDownsampling(ds=True, auto=True, mode='peak')
    chart.getPlotItem().layout.setContentsMargins(10, 20, 30, 20)
