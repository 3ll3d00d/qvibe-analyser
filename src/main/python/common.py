from contextlib import contextmanager
import numpy as np
from collections import Sequence

from qtpy.QtGui import QCursor
from qtpy import QtCore
from qtpy.QtWidgets import QApplication


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

    def unwrap(self):
        """ Copy the data from this buffer into unwrapped form """
        return np.concatenate((
            self.__buffer[self.__left_idx:min(self.__right_idx, self.__capacity)],
            self.__buffer[:max(self.__right_idx - self.__capacity, 0)]
        ))

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
        self._fix_indices()

    def append_left(self, value):
        if self.is_full:
            if not len(self):
                return
            else:
                self.__right_idx -= 1

        self.__left_idx -= 1
        self._fix_indices()
        self.__buffer[self.__left_idx] = value

    def pop(self):
        if len(self) == 0:
            raise IndexError("pop from an empty RingBuffer")
        self.__right_idx -= 1
        self._fix_indices()
        res = self.__buffer[self.__right_idx % self.__capacity]
        return res

    def pop_left(self):
        if len(self) == 0:
            raise IndexError("pop from an empty RingBuffer")
        res = self.__buffer[self.__left_idx]
        self.__left_idx += 1
        self._fix_indices()
        return res

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
        self._fix_indices()

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
