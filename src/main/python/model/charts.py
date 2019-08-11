import abc
import logging
import time

from qtpy.QtCore import QRunnable, QObject, Signal

logger = logging.getLogger('qvibe.charts')


class ChartDataProcessor(QRunnable):
    ''' Allows preprocessing of fresh data for a chart to occur away from the main thread. '''
    def __init__(self, chart):
        super().__init__()
        self.chart = chart
        self.input = None
        self.idx = None
        self.should_emit = False
        self.output = None

    def run(self):
        start = time.time()
        self.process()
        self.handle_data()
        end = time.time()
        logger.debug(f"Processing {self.chart.__class__.__name__} in {round((end - start) * 1000, 3)}ms")

    def process(self):
        ''' default implementation passes through the input '''
        self.should_emit = True
        self.output = self.input

    def handle_data(self):
        if self.should_emit is True:
            self.chart.signals.new_data.emit(self.output, False)


class ChartSignals(QObject):
    new_data = Signal(object, bool)


class VisibleChart:

    def __init__(self, visible):
        self.signals = ChartSignals()
        self.signals.new_data.connect(self.do_update)
        self.__visible = visible
        self.__received_data_with_invisible = False

    @property
    def visible(self):
        return self.__visible

    @visible.setter
    def visible(self, visible):
        if visible is True and self.__visible is False and self.__received_data_with_invisible is True:
            # if we have received data since we were last visible, update the charts
            self.do_update(None, True)
        self.__visible = visible

    @abc.abstractmethod
    def do_update(self, data, was_invisible):
        '''
        Update the chart.
        :param data: the data to update the chart with.
        :param was_invisible: True if this chart was previously invisible.
        '''
        pass

    @abc.abstractmethod
    def get_data_processor(self):
        ''' A function that can accept new data into the chart, typically implemented as a QRunnable. '''
        pass
