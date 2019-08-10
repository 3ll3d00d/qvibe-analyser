import abc

import pyqtgraph as pg
import numpy as np

from common import format_pg_chart


class VisibleChart:

    def __init__(self, visible):
        self.__visible = visible
        self.__received_data_with_invisible = False

    @property
    def visible(self):
        return self.__visible

    @visible.setter
    def visible(self, visible):
        if visible is True and self.__visible is False and self.__received_data_with_invisible is True:
            # if we have received data since we were last visible, update the charts
            self.do_update(was_invisible=True)
        self.__visible = visible

    def update(self, signal, idx):
        should_update = self.on_signal(signal, idx)
        if self.visible is True:
            self.__received_data_with_invisible = False
            if should_update is True:
                self.do_update()
        else:
            self.__received_data_with_invisible = True

    @abc.abstractmethod
    def on_signal(self, signal, idx):
        '''
        :param signal: the fresh signal.
        :param idx: the signal idx.
        :return: True if the chart should be updated after receiving this sample.
        '''
        pass

    @abc.abstractmethod
    def do_update(self, was_invisible=False):
        '''
        Update the chart.
        '''
        pass


class Vibration(VisibleChart):

    def __init__(self, chart, accel_sens_widget, buffer_size_widget):
        super().__init__(True)
        self.__x = None
        self.__y = None
        self.__z = None
        self.__chart = chart
        self.__sample = None
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

    def on_signal(self, signal, idx):
        self.__sample = signal
        return True

    def do_update(self, was_invisible=False):
        '''
        updates the chart with the latest signal.
        '''
        t = self.__sample[:, 0]
        t = t - np.min(t)
        t = t/500
        if self.__x is None:
            self.__x = self.__chart.plot(t, self.__sample[:, 2], pen=pg.mkPen('r', width=1))
            self.__y = self.__chart.plot(t, self.__sample[:, 3], pen=pg.mkPen('g', width=1))
            self.__z = self.__chart.plot(t, self.__sample[:, 4], pen=pg.mkPen('b', width=1))
        else:
            self.__x.setData(t, self.__sample[:, 2])
            self.__y.setData(t, self.__sample[:, 3])
            self.__z.setData(t, self.__sample[:, 4])
