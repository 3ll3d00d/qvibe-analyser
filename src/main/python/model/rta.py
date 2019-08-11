import logging
import math

import numpy as np
import pyqtgraph as pg

from common import RingBuffer, format_pg_chart
from model.charts import VisibleChart, ChartDataProcessor
from model.signal import TriAxisSignal, get_segment_length

logger = logging.getLogger('qvibe.rta')


class RTADataProcessor(ChartDataProcessor):

    def __init__(self, chart, preferences):
        super().__init__(chart)
        self.preferences = preferences

    def process(self):
        if self.input.shape[0] >= self.chart.min_nperseg:
            self.output = TriAxisSignal(self.preferences,
                                        self.input,
                                        self.chart.fs,
                                        self.chart.resolution_shift,
                                        pre_calc=self.chart.visible)
            self.should_emit = True


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
        format_pg_chart(self.__chart, (0, self.fs / 2), (40, 120))

    @property
    def min_nperseg(self):
        return self.__min_nperseg

    @property
    def resolution_shift(self):
        return self.__resolution_shift

    @property
    def fs(self):
        return self.__fs

    def get_data_processor(self):
        return RTADataProcessor(self, self.__preferences)

    def __cache_nperseg(self):
        if self.resolution_shift is not None and self.fs is not None:
            self.__min_nperseg = get_segment_length(self.fs, resolution_shift=self.resolution_shift)

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

    def do_update(self, data, was_invisible):
        self.__buffer.append(data)
        if data is not None:
            if was_invisible is True:
                data.recalc()
            if self.__x is None:
                self.__x = self.__chart.plot(data.x.avg.x, data.x.avg.y, pen=pg.mkPen('r', width=1))
                self.__y = self.__chart.plot(data.y.avg.x, data.y.avg.x, pen=pg.mkPen('g', width=1))
                self.__z = self.__chart.plot(data.z.avg.x, data.z.avg.x, pen=pg.mkPen('b', width=1))
            else:
                self.__x.setData(data.x.avg.x, data.x.avg.y)
                self.__y.setData(data.y.avg.x, data.y.avg.y)
                self.__z.setData(data.z.avg.x, data.z.avg.y)


