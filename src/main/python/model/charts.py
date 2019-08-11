import abc
import logging
import math
import time
from queue import Queue, Empty

from qtpy.QtCore import QObject, Signal, QThread

from model.signal import TriAxisSignal, get_segment_length

logger = logging.getLogger('qvibe.charts')


class ChartProcessor(QThread):

    def __init__(self, coelesce=False):
        super().__init__()
        self.queue = Queue()
        self.running = True
        self.__coelesce = coelesce

    def stop(self):
        self.running = False

    def run(self):
        while self.running is True:
            try:
                event = self.queue.get(timeout=1)
                if event is not None:
                    self.queue.task_done()
                    if self.__coelesce is True:
                        event = self.coalesce(event)
                    if isinstance(event, ChartEvent):
                        event.execute()
                    else:
                        logger.warning(f"{self.__class__.__name__} received unknown event {event.__class__.__name__}")
            except Empty:
                # ignore, don't care
                pass
            except:
                logger.exception('Unexpected exception during event processing')

    def coalesce(self, event):
        '''
        Yields the last event from the queue.
        :param event: the 1st event.
        :return: the last event.
        '''
        e = None
        count = 0
        while not self.queue.empty():
            try:
                e = self.queue.get(block=False, timeout=None)
                if e is not None:
                    self.queue.task_done()
                    count += 1
            except Empty:
                continue
        if e is not None:
            logger.warning(f"Coalesced {count} {e.__class__.__name__} events")
            event = e
        return event


class ChartEvent:
    ''' Allows preprocessing of fresh data for a chart to occur away from the main thread. '''
    def __init__(self, chart, input, idx, preferences, analysis_mode='vibration'):
        super().__init__()
        self.chart = chart
        self.input = input
        self.idx = idx
        self.preferences = preferences
        self.__analysis_mode = analysis_mode
        self.should_emit = False
        self.output = None

    def execute(self):
        start = time.time()
        self.process()
        self.handle_data()
        end = time.time()
        logger.debug(f"{self.chart.__class__.__name__} : {self.idx} in {round((end - start) * 1000, 3)}ms")

    def process(self):
        ''' default implementation passes through the input '''
        self.should_emit = True
        self.output = TriAxisSignal(self.preferences,
                                    self.input,
                                    self.chart.fs,
                                    self.chart.resolution_shift,
                                    mode=self.__analysis_mode,
                                    pre_calc=False)

    def handle_data(self):
        if self.should_emit is True:
            self.chart.signals.new_data.emit(self.output)


class ChartSignals(QObject):
    new_data = Signal(object)


class VisibleChart:

    def __init__(self, prefs, fs_widget, resolution_widget, visible, coelesce=False, analysis_mode='vibration'):
        self.signals = ChartSignals()
        self.processor = ChartProcessor(coelesce=coelesce)
        self.signals.new_data.connect(self.do_update)
        self.preferences = prefs
        self.__visible = visible
        self.__analysis_mode = analysis_mode
        self.__resolution_shift = None
        self.__fs = None
        self.__min_nperseg = 0
        self.__received_data_with_invisible = False
        self.__on_resolution_change(resolution_widget.currentText())
        self.__on_fs_change(fs_widget.value())
        # link to widgets
        fs_widget.valueChanged['int'].connect(self.__on_fs_change)
        resolution_widget.currentTextChanged.connect(self.__on_resolution_change)

    @property
    def analysis_mode(self):
        return self.__analysis_mode

    @analysis_mode.setter
    def analysis_mode(self, analysis_mode):
        self.__analysis_mode = analysis_mode

    @property
    def min_nperseg(self):
        return self.__min_nperseg

    @property
    def resolution_shift(self):
        return self.__resolution_shift

    @property
    def fs(self):
        return self.__fs

    @property
    def visible(self):
        return self.__visible

    @visible.setter
    def visible(self, visible):
        if visible is True and self.__visible is False and self.__received_data_with_invisible is True:
            # if we have received data since we were last visible, update the charts
            self.do_update(None)
        self.__visible = visible

    @abc.abstractmethod
    def do_update(self, data):
        '''
        Update the chart.
        :param data: the data to update the chart with.
        '''
        pass

    def __cache_nperseg(self):
        if self.resolution_shift is not None and self.fs is not None:
            self.__min_nperseg = get_segment_length(self.fs, resolution_shift=self.resolution_shift)
            self.on_min_nperseg_change()

    def on_min_nperseg_change(self):
        pass

    def __on_fs_change(self, fs):
        self.__fs = fs
        self.__cache_nperseg()

    def __on_resolution_change(self, resolution):
        self.__resolution_shift = int(math.log(float(resolution[0:-3]), 2))
        self.__cache_nperseg()

    def accept(self, data, idx):
        '''
        Pushes a data event into the queue.
        :param data: the data.
        :param idx: the index.
        '''
        self.processor.queue.put(self.make_event(data, idx), block=False)

    def make_event(self, data, idx):
        '''
        makes the ChartEvent for this chart.
        :param data: the data.
        :param idx: the index.
        :return: the event.
        '''
        return ChartEvent(self, data, idx, self.preferences, analysis_mode=self.analysis_mode)
