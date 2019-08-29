import logging

import numpy as np
import pyqtgraph as pg

from common import format_pg_plotitem
from model.charts import VisibleChart

logger = logging.getLogger('qvibe.vibration')


class Vibration(VisibleChart):

    def __init__(self, chart, prefs, fs_widget, fps_widget, actual_fps_widget, resolution_widget, accel_sens_widget,
                 buffer_size_widget, analysis_type_widget):
        super().__init__(prefs, fs_widget, resolution_widget, fps_widget, actual_fps_widget,
                         True, analysis_mode=analysis_type_widget.currentText())
        self.__plots = {}
        self.__chart = chart
        self.__sens = None
        self.__buffer_size = None
        buffer_size_widget.valueChanged['int'].connect(self.__on_buffer_size_change)
        analysis_type_widget.currentTextChanged.connect(self.__on_analysis_mode_change)
        accel_sens_widget.currentTextChanged.connect(self.__on_sens_change)
        self.__on_buffer_size_change(buffer_size_widget.value())
        self.__on_sens_change(accel_sens_widget.currentText())

    def __on_analysis_mode_change(self, analysis_mode):
        logger.info(f"Changing analysis mode from {self.analysis_mode} to {analysis_mode}")
        self.analysis_mode = analysis_mode
        for name in self.cached_recorder_names():
            self.cached_data(name).set_mode(self.analysis_mode, recalc=False)
            self.update_chart(name)

    def __on_buffer_size_change(self, size):
        self.__buffer_size = size
        self.__reset_limits()

    def __on_sens_change(self, sens):
        self.__sens = int(sens)
        self.__reset_limits()

    def __reset_limits(self):
        if self.__buffer_size is not None and self.__sens is not None:
            format_pg_plotitem(self.__chart.getPlotItem(), (0, self.__buffer_size), (-self.__sens, self.__sens))

    def reset_chart(self):
        for c in self.__plots.values():
            self.__chart.removeItem(c)
        self.__plots = {}

    def update_chart(self, recorder_name):
        '''
        updates the chart with the latest signal.
        '''
        d = self.cached_data(recorder_name)
        if d is not None:
            t = (d.time - np.min(d.time))/500
            self.create_or_update(d.x, t, 'r')
            self.create_or_update(d.y, t, 'g')
            self.create_or_update(d.z, t, 'b')

    def create_or_update(self, series, t, colour):
        name = self.__get_plot_name(series)
        if self.is_visible(recorder=series.recorder_name, axis=series.axis) is True:
            if name in self.__plots:
                self.__plots[name].setData(t, series.data)
            else:
                self.__plots[name] = self.__chart.plot(t, series.data, pen=pg.mkPen(colour, width=1), name=name)
        elif name in self.__plots:
            self.__chart.removeItem(self.__plots[name])
            del self.__plots[name]

    @staticmethod
    def __get_plot_name(sig):
        return f"{sig.recorder_name}:{sig.axis}"