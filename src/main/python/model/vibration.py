import logging

import numpy as np
import pyqtgraph as pg
from scipy.signal import find_peaks

from common import format_pg_plotitem, block_signals
from model.charts import VisibleChart

logger = logging.getLogger('qvibe.vibration')


class Vibration(VisibleChart):

    def __init__(self, chart, prefs, fs_widget, fps_widget, actual_fps_widget, resolution_widget, accel_sens_widget,
                 buffer_size_widget, analysis_type_widget, left_marker_pos, right_marker_pos, time_range,
                 zoom_in_button, zoom_out_button, find_peaks_button, colour_provider):
        super().__init__(prefs, fs_widget, resolution_widget, fps_widget, actual_fps_widget,
                         True, analysis_mode=analysis_type_widget.currentText())
        self.__plots = {}
        self.__legend = None
        self.__colour_provider = colour_provider
        self.__chart = chart
        self.__sens = None
        self.__buffer_size = None
        self.__left_marker = None
        self.__right_marker = None
        self.__time_range = time_range
        self.__left_marker_pos = left_marker_pos
        self.__right_marker_pos = right_marker_pos
        buffer_size_widget.valueChanged['int'].connect(self.__on_buffer_size_change)
        analysis_type_widget.currentTextChanged.connect(self.__on_analysis_mode_change)
        accel_sens_widget.currentTextChanged.connect(self.__on_sens_change)
        self.__left_marker_pos.setEnabled(False)
        self.__right_marker_pos.setEnabled(False)
        self.__left_marker_pos.valueChanged.connect(self.__set_left_marker)
        self.__right_marker_pos.valueChanged.connect(self.__set_right_marker)
        self.__on_buffer_size_change(buffer_size_widget.value())
        self.__on_sens_change(accel_sens_widget.currentText())
        zoom_in_button.clicked.connect(self.__zoom_to_marker)
        zoom_out_button.clicked.connect(self.__reset_limits)
        self.__find_peaks_button = find_peaks_button
        self.__find_peaks_button.clicked.connect(self.__find_peaks)
        self.__find_peaks_button.setEnabled(False)

    def __find_peaks(self):
        '''
        Looks for peaks in the signal using a continuous wavelet transform.
        '''
        name, plot = next(iter(self.__plots.items()))
        x_min, x_max = self.__chart.getPlotItem().viewRange()[0]
        x_min_idx = np.argmax(plot.xData >= x_min-0.00001)
        x_max_idx = np.argmax(plot.xData >= x_max-0.00001) if x_max < plot.xData[-1] else -1
        y_data = np.require(plot.yData[x_min_idx:x_max_idx], requirements=['O', 'W'])
        peak_y = np.amax(y_data)
        peaks = find_peaks(y_data, height=peak_y * 0.99)
        if len(peaks[0]) > 0:
            peaks = peaks[0] + x_min_idx
            if len(peaks) > 1:
                left = plot.xData[peaks[0]]
                right = plot.xData[peaks[1]]
                logger.info(f"Found {len(peaks)} peaks in {name} - {left} -> {right}")
                self.__left_marker_pos.setValue(left)
            else:
                right = plot.xData[peaks[0]]
                logger.info(f"Found 1 peak in {name} - {right}")
            self.__right_marker_pos.setValue(right)
        else:
            logger.info(f"No values found within 1% of {peak_y}")

    def __propagate_marker(self, widget, value):
        with block_signals(widget):
            widget.setValue(value)
        self.__time_range.setValue(self.__right_marker.value() - self.__left_marker.value())

    def __set_left_marker(self, value):
        self.__left_marker.setValue(value)
        self.__time_range.setValue(self.__right_marker.value() - value)

    def __set_right_marker(self, value):
        self.__right_marker.setValue(value)
        self.__time_range.setValue(value - self.__left_marker.value())

    def __zoom_to_marker(self):
        self.__chart.getPlotItem().setXRange(self.__left_marker_pos.value(), self.__right_marker_pos.value())
        lims = self.__chart.getPlotItem().viewRange()
        x_min, x_max = lims[0]
        y_min, y_max = lims[1]
        y_maxes = []
        y_mins = []
        for name, plot in self.__plots.items():
            x_min_idx = np.argmax(plot.xData >= x_min)
            x_max_idx = np.argmax(plot.xData >= x_max) if x_max < plot.xData[-1] else -1
            y_data = plot.yData[x_min_idx:x_max_idx]
            y_mins.append(np.amin(y_data))
            y_maxes.append(np.amax(y_data))
        new_y_max = max(y_maxes)
        new_y_min = min(y_mins)
        self.__chart.getPlotItem().setYRange(max(new_y_min, y_min), min(new_y_max, y_max))

    def __on_analysis_mode_change(self, analysis_mode):
        logger.info(f"Changing analysis mode from {self.analysis_mode} to {analysis_mode}")
        self.analysis_mode = analysis_mode
        for name in self.cached_measurement_names():
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
        for n, c in self.__plots.items():
            self.__chart.removeItem(c)
            self.__legend.removeItem(n)
        self.__plots = {}

    def update_chart(self, measurement_name):
        '''
        updates the chart with the latest signal.
        '''
        d = self.cached_data(measurement_name)
        if d is not None:
            t = (d.time - np.min(d.time)) / self.fs
            self.create_or_update(d.x, t)
            self.create_or_update(d.y, t)
            self.create_or_update(d.z, t)

    def create_or_update(self, series, t):
        name = self.__get_plot_name(series)
        if self.is_visible(measurement=series.measurement_name, axis=series.axis) is True:
            if name in self.__plots:
                self.__plots[name].setData(t, series.data)
            else:
                colour = self.__colour_provider.get_colour(name)
                if self.__legend is None:
                    self.__legend = self.__chart.addLegend(offset=(-15, -15))
                    self.__init_markers()
                self.__plots[name] = self.__chart.plot(t, series.data, pen=pg.mkPen(colour, width=1), name=name)
        elif name in self.__plots:
            self.__chart.removeItem(self.__plots[name])
            del self.__plots[name]
            self.__legend.removeItem(name)
        self.__find_peaks_button.setEnabled(len(self.__plots.keys()) == 1)

    def __init_markers(self):
        self.__left_marker = pg.InfiniteLine(movable=True, bounds=[0.000, self.__buffer_size-0.001])
        self.__left_marker.sigPositionChangeFinished.connect(lambda: self.__propagate_marker(self.__left_marker_pos,
                                                                                             self.__left_marker.value()))
        self.__left_marker.sigPositionChanged.connect(self.__enforce_right_marker_bounds)
        self.__chart.addItem(self.__left_marker)
        self.__right_marker = pg.InfiniteLine(movable=True, bounds=[0.001, self.__buffer_size], pos=self.__buffer_size)
        self.__propagate_marker(self.__right_marker_pos, self.__buffer_size)
        self.__right_marker.sigPositionChangeFinished.connect(lambda: self.__propagate_marker(self.__right_marker_pos,
                                                                                              self.__right_marker.value()))
        self.__right_marker.sigPositionChanged.connect(self.__enforce_left_marker_bounds)
        self.__chart.addItem(self.__right_marker)
        self.__left_marker_pos.setEnabled(True)
        self.__right_marker_pos.setEnabled(True)

    def __enforce_left_marker_bounds(self):
        self.__left_marker.setBounds([0, self.__right_marker.value()-0.001])
        self.__left_marker_pos.setMaximum(self.__right_marker.value()-0.001)

    def __enforce_right_marker_bounds(self):
        self.__right_marker.setBounds([self.__left_marker.value() + 0.001, self.__buffer_size])
        self.__right_marker_pos.setMinimum(self.__left_marker.value() + 0.001)

    @staticmethod
    def __get_plot_name(sig):
        return f"{sig.measurement_name}:{sig.axis}"
