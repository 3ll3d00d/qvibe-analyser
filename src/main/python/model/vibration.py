import logging

import numpy as np
import pyqtgraph as pg

from common import format_pg_chart
from model.charts import VisibleChart

logger = logging.getLogger('qvibe.vibration')


class Vibration(VisibleChart):

    def __init__(self, chart, prefs, fs_widget, fps_widget, resolution_widget, accel_sens_widget, buffer_size_widget,
                 analysis_type_widget):
        super().__init__(prefs, fs_widget, resolution_widget, fps_widget,
                         True, analysis_mode=analysis_type_widget.currentText())
        self.__x = None
        self.__y = None
        self.__z = None
        self.__chart = chart
        self.__sens = None
        self.__buffer_size = None
        self.__cached = None
        buffer_size_widget.valueChanged['int'].connect(self.__on_buffer_size_change)
        analysis_type_widget.currentTextChanged.connect(self.__on_analysis_mode_change)
        accel_sens_widget.currentTextChanged.connect(self.__on_sens_change)
        self.__on_buffer_size_change(buffer_size_widget.value())
        self.__on_sens_change(accel_sens_widget.currentText())

    def __on_analysis_mode_change(self, analysis_mode):
        logger.info(f"Changing analysis mode from {self.analysis_mode} to {analysis_mode}")
        self.analysis_mode = analysis_mode
        if self.__cached is not None:
            self.__cached.set_mode(self.analysis_mode, recalc=False)
            self.do_update(None)

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
        if data is None and self.__cached is not None:
            d = self.__cached
        else:
            d = data
            self.__cached = d
        t = (d.time - np.min(d.time))/500
        if self.__x is None:
            self.__x = self.__chart.plot(t, d.x.data, pen=pg.mkPen('r', width=1))
            self.__y = self.__chart.plot(t, d.y.data, pen=pg.mkPen('g', width=1))
            self.__z = self.__chart.plot(t, d.z.data, pen=pg.mkPen('b', width=1))
        else:
            self.__x.setData(t, d.x.data)
            self.__y.setData(t, d.y.data)
            self.__z.setData(t, d.z.data)
