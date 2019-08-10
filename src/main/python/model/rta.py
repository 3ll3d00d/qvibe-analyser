import logging
import math
import time

import numpy as np
import pyqtgraph as pg

from common import RingBuffer, format_pg_chart
from model.signal import TriAxisSignal, get_segment_length
from model.vibration import VisibleChart

logger = logging.getLogger('qvibe.rta')


class RTA(VisibleChart):

    def __init__(self, chart, prefs, fs_widget, resolution_widget, fps_widget):
        super().__init__(False)
        self.__x = None
        self.__y = None
        self.__z = None
        self.__sum = None
        self.__resolution_shift = None
        self.__buffer = None
        self.__fs = None
        self.__fps = None
        self.__min_nperseg = 0
        self.__update_rate = None
        self.__chart = chart
        self.__preferences = prefs
        self.__on_resolution_change(resolution_widget.currentText())
        self.__on_fs_change(fs_widget.value())
        self.__on_fps_change(fps_widget.value())
        # link to widgets
        fs_widget.valueChanged['int'].connect(self.__on_fs_change)
        fps_widget.valueChanged['int'].connect(self.__on_fps_change)
        resolution_widget.currentTextChanged.connect(self.__on_resolution_change)
        format_pg_chart(self.__chart, (0, self.__fs / 2), (40, 120))

    def __cache_nperseg(self):
        if self.__resolution_shift is not None and self.__fs is not None:
            self.__min_nperseg = get_segment_length(self.__fs, resolution_shift=self.__resolution_shift)

    def __on_fs_change(self, fs):
        self.__fs = fs
        self.__cache_nperseg()

    def __on_resolution_change(self, resolution):
        self.__resolution_shift = int(math.log(float(resolution[0:-3]), 2))
        self.__cache_nperseg()

    def __on_fps_change(self, fps):
        self.__fps = fps
        old_buf = self.__buffer
        self.__buffer = RingBuffer(fps, dtype=np.object)
        if old_buf is not None:
            self.__buffer.extend(old_buf)

    def on_signal(self, signal, idx):
        if signal.shape[0] >= self.__min_nperseg:
            start = time.time()
            tri = TriAxisSignal(self.__preferences, signal, self.__fs, self.__resolution_shift, pre_calc=self.visible)
            end = time.time()
            logger.debug(f"Created TriAxisSignal {idx} in {round((end-start)*1000.0, 3)}ms [precalc={self.visible}]")
            self.__buffer.append(tri)
            return True
        return False

    def do_update(self, was_invisible=False):
        tri = self.__buffer.peek()
        if tri is not None:
            if was_invisible is True:
                tri.recalc()
            if self.__x is None:
                self.__x = self.__chart.plot(tri.x.avg.x, tri.x.avg.y, pen=pg.mkPen('r', width=1))
                self.__y = self.__chart.plot(tri.y.avg.x, tri.y.avg.x, pen=pg.mkPen('g', width=1))
                self.__z = self.__chart.plot(tri.z.avg.x, tri.z.avg.x, pen=pg.mkPen('b', width=1))
            else:
                self.__x.setData(tri.x.avg.x, tri.x.avg.y)
                self.__y.setData(tri.y.avg.x, tri.y.avg.y)
                self.__z.setData(tri.z.avg.x, tri.z.avg.y)


