import abc
import logging
import math
import time
from queue import Queue, Empty

from collections import deque
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
    def __init__(self, chart, recorder_name, input, idx, preferences, budget_millis, analysis_mode='vibration'):
        super().__init__()
        self.chart = chart
        self.recorder_name = recorder_name
        self.input = input
        self.idx = idx
        self.preferences = preferences
        self.__analysis_mode = analysis_mode
        self.__budget_millis = budget_millis * 0.9
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
                                    idx=self.idx,
                                    mode=self.__analysis_mode,
                                    pre_calc=False)

    def handle_data(self):
        if self.should_emit is True:
            self.chart.signals.new_data.emit(self.recorder_name, self.idx, self.output)


class ChartSignals(QObject):
    new_data = Signal(str, int, object)


class VisibleChart:

    def __init__(self, prefs, fs_widget, resolution_widget, fps_widget, actual_fps_widget, visible, coelesce=False,
                 analysis_mode='vibration', cache_size=1, cache_purger=lambda c: None):
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
        self.__cache_size = cache_size
        self.__cache_purger = cache_purger
        self.__cached = {}
        self.__received_data_while_invisible = set()
        self.__visible_axes = []
        self.__visible_recorders = []
        self.__on_resolution_change(resolution_widget.currentText())
        self.__on_fs_change(fs_widget.value())
        # link to widgets
        fs_widget.valueChanged['int'].connect(self.__on_fs_change)
        resolution_widget.currentTextChanged.connect(self.__on_resolution_change)
        self.__on_fps_change(fps_widget.value())
        fps_widget.valueChanged['int'].connect(self.__on_fps_change)

    def set_visible_axes(self, axes):
        '''
        Updates the visible axes.
        :param axes: the axes.
        '''
        self.__visible_axes = axes
        self.update_all_plots()

    def update_all_plots(self):
        ''' Triggers an update of each plot. '''
        self.for_each_recorder(self.update_chart)

    def set_visible_recorders(self, recorders):
        '''
        Updates the visible axes.
        :param axes: the axes.
        '''
        self.__visible_recorders = recorders
        self.update_all_plots()

    def set_actual_fps(self):
        ''' pushes the tick count to the actual fps widget. '''
        recorders = self.cached_recorder_names()
        active = len(recorders)
        val = int(self.__ticks / len(recorders)) if active > 0 else 0
        self.__actual_fps_widget.setValue(val)
        self.__ticks = 0

    def is_visible(self, recorder=None, axis=None):
        '''
        :param recorder: the recorder name.
        :param axis: the axis.
        :return: true if both are visible.
        '''
        return (axis is None or axis in self.__visible_axes) and \
               (recorder is None or recorder in self.__visible_recorders)

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

    def for_each_recorder(self, func):
        ''' passes each recorder cache to the supplied function. '''
        for name in self.cached_recorder_names():
            func(name)

    def for_each_cache(self, func):
        ''' passes each cache to the supplied function. '''
        for name in self.cached_recorder_names():
            func(self.__cached[name])

    def cached_recorder_names(self):
        return list(self.__cached.keys())

    def cached_data(self, recorder_name):
        '''
        Gets the cached data for the given recorder name.
        :param recorder_name: the name.
        :return: the latest data (can be a single entry or a sequence) or None if this recorder has no data.
        '''
        if recorder_name in self.__cached:
            cached = self.__cached[recorder_name]
            return cached[-1] if self.__cache_size == 1 else cached
        else:
            return None

    def do_update(self, recorder_name, idx, data):
        '''
        Update the chart.
        :param recorder_name: the recorder that produced this data.
        :param data: the data to update the chart with.
        '''
        to_update = self.accept_data(data)
        if to_update is not None:
            if self.visible is True:
                start = time.time()
                self.update_chart(recorder_name)
                end = time.time()
                self.__ticks += 1
                logger.debug(f"Updated {self.__class__.__name__} {idx} in {to_millis(start, end)} ms")
            else:
                self.__received_data_while_invisible.add(recorder_name)

    def accept_data(self, data):
        '''
        Accepts the fresh data into the cache for the chart.
        :param data: the data.
        '''
        if data.recorder_name not in self.__cached:
            self.__cached[data.recorder_name] = deque(maxlen=self.__cache_size) if self.__cache_size > 0 else deque()
        cache = self.__cached[data.recorder_name]
        cache.append(data)
        self.__cache_purger(cache)
        return data

    @abc.abstractmethod
    def update_chart(self, recorder_name):
        '''
        Update the chart with the cached data if necessary.
        :param recorder_name: the named update.
        '''
        pass

    def reset(self):
        self.__cached = {}
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
        self.on_fs_change()

    def on_fs_change(self):
        ''' allows subclasses to react to fs change '''
        pass

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
        event = self.make_event(recorder_name, data, idx)
        if event is not None:
            self.processor.queue.put(event, block=False)

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
