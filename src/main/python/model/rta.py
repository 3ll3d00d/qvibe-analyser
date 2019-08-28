import logging

import numpy as np
import pyqtgraph as pg
from qtpy.QtCore import Qt

from common import format_pg_plotitem
from model.charts import VisibleChart, ChartEvent
from model.signal import smooth_savgol

logger = logging.getLogger('qvibe.rta')


class RTAEvent(ChartEvent):

    def __init__(self, chart, recorder_name, input, idx, preferences, budget_millis, view, visible):
        super().__init__(chart, recorder_name, input, idx, preferences, budget_millis)
        self.__view = view
        self.__visible = visible

    def process(self):
        super().process()
        self.output.set_view(self.__view, recalc=False)
        if self.input.shape[0] >= self.chart.min_nperseg and self.__visible:
            self.output.recalc()
            self.should_emit = True
        else:
            self.should_emit = False


class RTA(VisibleChart):

    def __init__(self, chart, prefs, fs_widget, resolution_widget, fps_widget, actual_fps_widget, rta_average_widget,
                 rta_view_widget, smooth_rta_widget, mag_min_widget, mag_max_widget, freq_min_widget, freq_max_widget,
                 snapshot_buttons, take_new_snaphot_button, snapshot_slot_selector, peak_hold_selector, peak_secs):
        self.__average = None
        super().__init__(prefs, fs_widget, resolution_widget, fps_widget, actual_fps_widget, False, coelesce=True,
                         cache_size=-1, cache_purger=self.__purge_cache)
        self.__peak_cache = {}
        self.__peak_secs = peak_secs.value()
        self.__show_peak = peak_hold_selector.isChecked()
        peak_hold_selector.stateChanged.connect(self.__on_peak_hold_change)
        peak_secs.valueChanged['int'].connect(self.__set_peak_cache_size)
        self.__frame = 0
        self.__time = -1
        self.__update_rate = None
        self.__active_view = None
        self.__smooth = False
        self.__chart = chart
        self.__series = {}
        self.__average_samples = -1
        self.__on_average_change(rta_average_widget.currentText())
        self.__mag_min = lambda: mag_min_widget.value()
        self.__mag_max = lambda: mag_max_widget.value()
        self.__freq_min = lambda: freq_min_widget.value()
        self.__freq_max = lambda: freq_max_widget.value()
        rta_average_widget.currentTextChanged.connect(self.__on_average_change)
        self.__on_rta_view_change(rta_view_widget.currentText())
        rta_view_widget.currentTextChanged.connect(self.__on_rta_view_change)
        self.__on_rta_smooth_change(Qt.Checked if smooth_rta_widget.isChecked() else Qt.Unchecked)
        smooth_rta_widget.stateChanged.connect(self.__on_rta_smooth_change)
        format_pg_plotitem(self.__chart.getPlotItem(),
                           (0, self.fs / 2),
                           (0, 150),
                           x_range=(self.__freq_min(), self.__freq_max()),
                           y_range=(self.__mag_min(), self.__mag_max()))
        mag_min_widget.valueChanged['int'].connect(self.__on_mag_limit_change)
        mag_max_widget.valueChanged['int'].connect(self.__on_mag_limit_change)
        freq_min_widget.valueChanged['int'].connect(self.__on_freq_limit_change)
        freq_max_widget.valueChanged['int'].connect(self.__on_freq_limit_change)

    def __set_peak_cache_size(self, seconds):
        self.__peak_secs = seconds
        self.for_each_cache(self.__purge_cache)

    def __on_peak_hold_change(self, checked):
        self.__show_peak = Qt.Checked == checked
        self.for_each_recorder(self.update_chart)

    def __on_mag_limit_change(self, val):
        self.__chart.getPlotItem().setYRange(self.__mag_min(), self.__mag_max(), padding=0)

    def __on_freq_limit_change(self, val):
        self.__chart.getPlotItem().setXRange(self.__freq_min(), self.__freq_max(), padding=0)

    def __on_rta_smooth_change(self, state):
        self.__smooth = state == Qt.Checked
        self.for_each_recorder(self.update_chart)

    def __on_rta_view_change(self, view):
        old_view = self.__active_view
        logger.info(f"Updating active view from {old_view} to {view}")
        self.__active_view = view

        def propagate_view_change(cache):
            for c in cache:
                c.set_view(view)

        self.for_each_cache(propagate_view_change)
        self.for_each_recorder(self.update_chart)
        logger.info(f"Updated active view from {old_view} to {view}")

    def __on_average_change(self, average):
        self.__average = average
        if self.__average == 'Forever':
            self.__average_samples = -1
        else:
            self.__average_samples = self.min_nperseg * int(self.__average[0:-1])
        logger.info(f"Average mode updated to {average}, requires {self.__average_samples} samples")

    def on_min_nperseg_change(self):
        if self.__average is not None:
            self.__on_average_change(self.__average)

    def make_event(self, recorder_name, data, idx):
        if self.__average_samples == -1 or len(data) <= self.__average_samples:
            d = data
        else:
            d = data[-self.__average_samples:]
        return RTAEvent(self, recorder_name, d, idx, self.preferences, self.budget_millis, self.__active_view,
                        self.visible)

    def reset_chart(self):
        for c in self.__series.values():
            self.__chart.removeItem(c)
        self.__series = {}

    def update_chart(self, recorder_name):
        data = self.cached_data(recorder_name)
        if data is not None and len(data) > 0:
            latest = data[-1]
            if latest.view != self.__active_view:
                logger.info(f"Updating active view from {latest.view} to {self.__active_view} at {latest.idx}")
                latest.set_view(self.__active_view)
            if latest.has_data(self.__active_view) is False:
                latest.recalc()
            self.create_or_update(latest, 'x', 'r')
            self.create_or_update(latest, 'y', 'g')
            self.create_or_update(latest, 'z', 'b')
            self.create_or_update(latest, 'sum', 'm')
            self.create_or_update(data, 'x', 'r', peak=True)
            self.create_or_update(data, 'y', 'g', peak=True)
            self.create_or_update(data, 'z', 'b', peak=True)
            self.create_or_update(data, 'sum', 'm', peak=True)

    def __purge_cache(self, cache):
        '''
        Purges the cache of data older than peak_secs.
        :param cache: the cache (a deque)
        '''
        while len(cache) > 1:
            latest = cache[-1].time[-1]
            if (latest - cache[0].time[-1]) >= (self.__peak_secs * 1000.0):
                cache.popleft()
            else:
                break

    def create_or_update(self, data, axis, colour, peak=False):
        '''
        Calculates the series name and the x-y data points based on whether this is a peak hold view or not. If no y
        data can be determined then it should mean an existing curve must be removed from the plot.
        :param data: the cached data.
        :param axis: the axis (x, y, z, sum) to process.
        :param colour: the colour of the data.
        :param peak: whether this is the peak hold data.
        '''
        y_data = None
        x_data = None
        if peak is True:
            sig = getattr(data[-1], axis)
            name = f"{sig.name}:peak"
            series_name = sig.name
            idx = data[-1].idx
            if self.__show_peak is True:
                has_data = sig.get_analysis(self.__active_view)
                if has_data is not None:
                    data_ = [getattr(d, axis).get_analysis(self.__active_view).y for d in data]
                    y_data = np.maximum.reduce(data_)
                    x_data = has_data.x
        else:
            sig = getattr(data, axis)
            view = sig.get_analysis(self.__active_view)
            if view is not None:
                y_data = view.y
                x_data = view.x
            name = sig.name
            series_name = sig.name
            idx = data.idx
        if y_data is not None:
            logger.debug(f"Tick {idx} {np.min(y_data):.4f} - {np.max(y_data):.4f} - {len(y_data)} ")
            if series_name in self.visible_series:
                y = smooth_savgol(x_data, y_data)[1] if self.__smooth is True else y_data
                if name in self.__series:
                    self.__series[name].setData(x_data, y)
                else:
                    line_style = Qt.DashDotLine if peak is True else Qt.SolidLine
                    self.__series[name] = self.__chart.plot(x_data, y, pen=pg.mkPen(colour, width=1, style=line_style))
            elif name in self.__series:
                self.__chart.removeItem(self.__series[name])
                del self.__series[name]
        elif name in self.__series:
            self.__chart.removeItem(self.__series[name])
            del self.__series[name]
