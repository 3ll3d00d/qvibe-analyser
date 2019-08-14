import abc
import logging
import math
import time
from queue import Queue, Empty

from qtpy.QtCore import QObject, Signal, QThread, QTimer

from model.log import to_millis
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
                        events = self.coalesce(event)
                    else:
                        events = [event]
                    for e in events:
                        if isinstance(e, ChartEvent):
                            e.execute()
                        else:
                            logger.warning(f"{self.__class__.__name__} received unknown event {event.__class__.__name__}")
            except Empty:
                # ignore, don't care
                pass
            except:
                logger.exception('Unexpected exception during event processing')

    def coalesce(self, event):
        '''
        Yields the last event from the queue for each recorder.
        :param event: the 1st event.
        :return: the last event.
        '''
        events = {event.recorder_name: event}
        count = 0
        while not self.queue.empty():
            try:
                e = self.queue.get(block=False, timeout=None)
                if e is not None:
                    events[e.recorder_name] = e
                    self.queue.task_done()
                    count += 1
            except Empty:
                continue
        if count > 0:
            logger.warning(f"Coalesced {count} {event.__class__.__name__} events")
        return list(events.values())


class ChartEvent:
    ''' Allows preprocessing of fresh data for a chart to occur away from the main thread. '''
    def __init__(self, chart, recorder_name, input, idx, preferences, budget_millis, analysis_mode='vibration',
                 smooth=False):
        super().__init__()
        self.chart = chart
        self.recorder_name = recorder_name
        self.input = input
        self.idx = idx
        self.preferences = preferences
        self.__analysis_mode = analysis_mode
        self.__budget_millis = budget_millis * 0.9
        self.__smooth = smooth
        self.should_emit = False
        self.output = None

    def execute(self):
        start = time.time()
        self.process()
        mid = time.time()
        self.handle_data()
        end = time.time()
        elapsed_millis = to_millis(start, end)
        if elapsed_millis > self.__budget_millis:
            mid_millis = to_millis(start, mid)
            emit_millis = round(elapsed_millis - mid_millis, 3)
            logger.warning(f"{self.chart.__class__.__name__} : {self.idx} in {mid_millis}ms - {emit_millis}ms but budget is {self.__budget_millis}ms")
        else:
            logger.debug(f"{self.chart.__class__.__name__} : {self.idx} in {elapsed_millis}ms")

    def process(self):
        ''' default implementation passes through the input '''
        self.should_emit = True
        self.output = TriAxisSignal(self.preferences,
                                    self.recorder_name,
                                    self.input,
                                    self.chart.fs,
                                    self.chart.resolution_shift,
                                    self.__smooth,
                                    idx=self.idx,
                                    mode=self.__analysis_mode,
                                    pre_calc=False)

    def handle_data(self):
        if self.should_emit is True:
            self.chart.signals.new_data.emit(self.output)


class ChartSignals(QObject):
    new_data = Signal(object)


class VisibleChart:

    def __init__(self, prefs, fs_widget, resolution_widget, fps_widget, actual_fps_widget, visible, coelesce=False,
                 analysis_mode='vibration'):
        self.signals = ChartSignals()
        self.processor = ChartProcessor(coelesce=coelesce)
        self.signals.new_data.connect(self.do_update)
        self.__timer = QTimer()
        self.__timer.timeout.connect(self.set_actual_fps)
        self.preferences = prefs
        self.__visible = visible
        self.__analysis_mode = analysis_mode
        self.__resolution_shift = None
        self.__fs = None
        self.__fps = None
        self.__actual_fps_widget = actual_fps_widget
        self.__budget_millis = None
        self.__min_nperseg = 0
        self.__ticks = 0
        self.__cached = {}
        self.__received_data_while_invisible = set()
        self.__visible_series = []
        self.__on_resolution_change(resolution_widget.currentText())
        self.__on_fs_change(fs_widget.value())
        # link to widgets
        fs_widget.valueChanged['int'].connect(self.__on_fs_change)
        resolution_widget.currentTextChanged.connect(self.__on_resolution_change)
        self.__on_fps_change(fps_widget.value())
        fps_widget.valueChanged['int'].connect(self.__on_fps_change)

    def set_visible_series(self, series):
        ''' changes the visible series. '''
        self.__visible_series = series
        for k in self.cached.keys():
            self.update_chart(k)

    def set_actual_fps(self):
        ''' pushes the tick count to the actual fps widget. '''
        self.__actual_fps_widget.setValue(self.__ticks)
        self.__ticks = 0

    @property
    def visible_series(self):
        return self.__visible_series

    @property
    def fps(self):
        return self.__fps

    @property
    def budget_millis(self):
        return self.__budget_millis

    def __on_fps_change(self, fps):
        changed = fps != self.fps
        self.__fps = fps
        self.__budget_millis = 1000.0 / fps
        if changed is True:
            self.when_fps_changed()

    def when_fps_changed(self):
        pass

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
        if visible is True and self.__visible is False:
            # if we have received data since we were last visible, update the charts
            for r in self.__received_data_while_invisible:
                self.update_chart(r)
        self.__visible = visible
        if self.__visible is True:
            self.__timer.start(1000)
        else:
            self.__timer.stop()

    @property
    def cached(self):
        return self.__cached

    def do_update(self, data):
        '''
        Update the chart.
        :param data: the data to update the chart with.
        '''
        to_update = self.accept_data(data)
        if to_update is not None:
            if self.visible is True:
                start = time.time()
                self.update_chart(data.recorder_name)
                end = time.time()
                self.__ticks += 1
                logger.debug(f"Updated {self.__class__.__name__} {to_update.idx} in {to_millis(start, end)} ms")
            else:
                self.__received_data_while_invisible.add(data.recorder_name)

    def accept_data(self, data):
        '''
        Accepts the fresh data into the cache for the chart.
        :param data: the data.
        '''
        self.__cached[data.recorder_name] = data
        return data

    @abc.abstractmethod
    def update_chart(self, recorder_name):
        '''
        Update the chart with the cached data if necessary.
        :param recorder_name: the named update.
        '''
        pass

    def reset(self):
        self.__cached = None
        self.__ticks = 0
        self.reset_chart()

    @abc.abstractmethod
    def reset_chart(self):
        ''' Wipes data from the chart. '''
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

    def accept(self, recorder_name, data, idx):
        '''
        Pushes a data event into the queue.
        :param recorder_name: the name.
        :param data: the data.
        :param idx: the index.
        '''
        self.processor.queue.put(self.make_event(recorder_name, data, idx), block=False)

    def make_event(self, recorder_name, data, idx):
        '''
        makes the ChartEvent for this chart.
        :param recorder_name: the name.
        :param data: the data.
        :param idx: the index.
        :return: the event.
        '''
        return ChartEvent(self, recorder_name, data, idx, self.preferences, self.budget_millis,
                          analysis_mode=self.analysis_mode)
