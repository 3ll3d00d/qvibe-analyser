import logging

import pyqtgraph as pg

from qtpy.QtCore import Qt

from common import format_pg_plotitem
from model.charts import VisibleChart, ChartEvent

logger = logging.getLogger('qvibe.rta')


class RTAEvent(ChartEvent):

    def __init__(self, chart, recorder_name, input, idx, preferences, budget_millis, view, visible, smooth):
        super().__init__(chart, recorder_name, input, idx, preferences, budget_millis, smooth=smooth)
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
                 rta_view_widget, smooth_rta_widget, mag_min_widget, mag_max_widget, freq_min_widget, freq_max_widget):
        self.__average = None
        super().__init__(prefs, fs_widget, resolution_widget, fps_widget, actual_fps_widget, False, coelesce=True)
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

    def __on_mag_limit_change(self, val):
        self.__chart.getPlotItem().setYRange(self.__mag_min(), self.__mag_max(), padding=0)

    def __on_freq_limit_change(self, val):
        self.__chart.getPlotItem().setXRange(self.__freq_min(), self.__freq_max(), padding=0)

    def __on_rta_smooth_change(self, state):
        self.__smooth = state == Qt.Checked
        for n, d in self.cached.items():
            d.set_smooth(self.__smooth)

    def __on_rta_view_change(self, view):
        self.__active_view = view
        for name in self.cached.keys():
            self.cached[name].set_view(view)
            self.update_chart(name)

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
                        self.visible, self.__smooth)

    def reset_chart(self):
        for c in self.__series.values():
            self.__chart.removeItem(c)
        self.__series = {}

    def update_chart(self, recorder_name):
        data = self.cached.get(recorder_name, None)
        if data is not None:
            if data.has_data() is False:
                data.recalc()
            if data.has_data():
                self.create_or_update(data, 'x', 'r')
                self.create_or_update(data, 'y', 'g')
                self.create_or_update(data, 'z', 'b')
                self.create_or_update(data, 'sum', 'm')

    def create_or_update(self, data, axis, colour):
        sig = getattr(data, axis)
        view = sig.get_analysis(self.__active_view)
        if view is not None:
            import numpy as np
            logger.debug(f"Tick {data.idx} {np.min(view.y):.4f} - {np.max(view.y):.4f} - {len(view.y)} ")
            if sig.name in self.visible_series:
                if sig.name in self.__series:
                    self.__series[sig.name].setData(view.x, view.y)
                else:
                    self.__series[sig.name] = self.__chart.plot(view.x, view.y, pen=pg.mkPen(colour, width=1))
            elif sig.name in self.__series:
                self.__chart.removeItem(self.__series[sig.name])
                del self.__series[sig.name]
