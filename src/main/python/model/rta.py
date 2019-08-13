import logging

import pyqtgraph as pg

from common import format_pg_chart
from model.charts import VisibleChart, ChartEvent

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
                 rta_view_widget):
        self.__average = None
        super().__init__(prefs, fs_widget, resolution_widget, fps_widget, actual_fps_widget, False, coelesce=True)
        self.__frame = 0
        self.__time = -1
        self.__update_rate = None
        self.__active_view = None
        self.__chart = chart
        self.__series = {}
        self.__average_samples = -1
        self.__on_average_change(rta_average_widget.currentText())
        rta_average_widget.currentTextChanged.connect(self.__on_average_change)
        self.__on_rta_view_change(rta_view_widget.currentText())
        rta_view_widget.currentTextChanged.connect(self.__on_rta_view_change)
        format_pg_chart(self.__chart, (0, self.fs / 2), (0, 150), (40, 120))

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
                        self.visible)

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
        else:
            logger.error(f"No {self.__active_view} data available")