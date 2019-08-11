import logging

import numpy as np
import pyqtgraph as pg

from common import format_pg_chart
from model.charts import VisibleChart, ChartEvent

logger = logging.getLogger('qvibe.vibration')


class Vibration(VisibleChart):

    def __init__(self, chart, accel_sens_widget, buffer_size_widget):
        super().__init__(True)
        self.__x = None
        self.__y = None
        self.__z = None
        self.__chart = chart
        self.__sens = None
        self.__buffer_size = None
        buffer_size_widget.valueChanged['int'].connect(self.__on_buffer_size_change)
        accel_sens_widget.currentTextChanged.connect(self.__on_sens_change)
        self.__on_buffer_size_change(buffer_size_widget.value())
        self.__on_sens_change(accel_sens_widget.currentText())

    def __on_buffer_size_change(self, size):
        self.__buffer_size = size
        self.__reset_limits()

    def __on_sens_change(self, sens):
        self.__sens = int(sens)
        self.__reset_limits()

    def __reset_limits(self):
        if self.__buffer_size is not None and self.__sens is not None:
            format_pg_chart(self.__chart, (0, self.__buffer_size), (-self.__sens, self.__sens))

    def do_update(self, data):
        '''
        updates the chart with the latest signal.
        '''
        t = data[:, 0]
        t = t - np.min(t)
        t = t/500
        if self.__x is None:
            self.__x = self.__chart.plot(t, data[:, 2], pen=pg.mkPen('r', width=1))
            self.__y = self.__chart.plot(t, data[:, 3], pen=pg.mkPen('g', width=1))
            self.__z = self.__chart.plot(t, data[:, 4], pen=pg.mkPen('b', width=1))
        else:
            self.__x.setData(t, data[:, 2])
            self.__y.setData(t, data[:, 3])
            self.__z.setData(t, data[:, 4])

    def get_data_processor(self):
        return ChartEvent(self)
