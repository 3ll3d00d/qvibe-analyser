import logging

import pyqtgraph as pg

from common import format_pg_chart
from model.charts import VisibleChart, ChartEvent

logger = logging.getLogger('qvibe.rta')


class RTAEvent(ChartEvent):

    def __init__(self, chart, input, idx, preferences, budget_millis, view):
        super().__init__(chart, input, idx, preferences, budget_millis)
        self.__view = view

    def process(self):
        super().process()
        self.output.set_view(self.__view, recalc=False)
        if self.input.shape[0] >= self.chart.min_nperseg:
            self.output.recalc()
            self.should_emit = True
        else:
            self.should_emit = False


class RTA(VisibleChart):

    def __init__(self, chart, prefs, fs_widget, resolution_widget, fps_widget, rta_average_widget, rta_view_widget):
        self.__average = None
        super().__init__(prefs, fs_widget, resolution_widget, fps_widget, False, coelesce=True)
        self.__x = None
        self.__y = None
        self.__z = None
        self.__sum = None
        self.__cache = None
        self.__update_rate = None
        self.__active_view = None
        self.__chart = chart
        self.__average_samples = -1
        self.__on_average_change(rta_average_widget.currentText())
        rta_average_widget.currentTextChanged.connect(self.__on_average_change)
        self.__on_rta_view_change(rta_view_widget.currentText())
        rta_view_widget.currentTextChanged.connect(self.__on_rta_view_change)
        format_pg_chart(self.__chart, (0, self.fs / 2), (0, 150), (40, 120))

    def __on_rta_view_change(self, view):
        self.__active_view = view
        if self.__cache is not None:
            self.__cache.set_view(view)
            self.do_update(None)

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

    def make_event(self, data, idx):
        if self.__average_samples == -1 or len(data) <= self.__average_samples:
            d = data
        else:
            d = data[-self.__average_samples:]
        return RTAEvent(self, d, idx, self.preferences, self.budget_millis, self.__active_view)

    def do_update(self, data):
        if data is not None:
            self.__cache = data
        elif self.__cache is not None:
            data = self.__cache
        if data is not None:
            if data.has_data() is False:
                data.recalc()
            if data.has_data():
                if self.__x is None:
                    self.__x = self.__plot_new(data, 'x', 'r')
                    self.__y = self.__plot_new(data, 'y', 'g')
                    self.__z = self.__plot_new(data, 'z', 'b')
                else:
                    self.__update_existing(self.__x, data, 'x')
                    self.__update_existing(self.__y, data, 'y')
                    self.__update_existing(self.__z, data, 'z')

    def __plot_new(self, data, axis, colour):
        view = self.__get_view(axis, data)
        return self.__chart.plot(view.x, view.y, pen=pg.mkPen(colour, width=1))

    def __get_view(self, axis, data):
        sig = getattr(data, axis)
        view = sig.get_analysis(self.__active_view)
        return view

    def __update_existing(self, chart, data, axis):
        view = self.__get_view(axis, data)
        if view is not None:
            chart.setData(view.x, view.y)
        else:
            logger.error(f"No {self.__active_view} data available")
