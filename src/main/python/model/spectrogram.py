import logging

import numpy as np
import pyqtgraph as pg

from common import format_pg_plotitem, colourmap
from model.charts import VisibleChart, ChartEvent
from model.signal import Signal, TriAxisSignal

logger = logging.getLogger('qvibe.vibration')


class SpectrogramEvent(ChartEvent):

    def __init__(self, chart, recorder_name, input, idx, preferences, budget_millis, visible):
        super().__init__(chart, recorder_name, input, idx, preferences, budget_millis)
        self.__visible = visible

    def process(self):
        self.output = [self.__make_sig(i) for i in self.input]
        self.should_emit = True

    def __make_sig(self, chunk):
        return TriAxisSignal(self.preferences,
                             self.recorder_name,
                             chunk,
                             self.chart.fs,
                             self.chart.resolution_shift,
                             False,
                             idx=self.idx,
                             mode='vibration',
                             view_mode='spectrogram',
                             pre_calc=self.__visible)


class Spectrogram(VisibleChart):

    def __init__(self, chart, prefs, fs_widget, fps_widget, actual_fps_widget, resolution_widget, buffer_size_widget):
        self.__sens = None
        self.__buffer_size = None
        super().__init__(prefs, fs_widget, resolution_widget, fps_widget, actual_fps_widget, True)
        self.__series = {}
        self.__staging = None
        self.__buffers = {}
        self.__last_idx = {}
        self.__qview = chart
        # self.__gradient = pg.GradientWidget(orientation='right')
        # self.__gradient.item.restoreState({
        #     'ticks': colourmap(),
        #     'mode': 'rgb'
        # })
        # self.__histo = pg.HistogramLUTItem()
        # self.__histo.gradient.restoreState({
        #     'ticks': colourmap(),
        #     'mode': 'rgb'
        # })
        # self.__qview.addItem(self.__histo)
        # self.__histo.setLevels(0, 150)
        buffer_size_widget.valueChanged['int'].connect(self.__on_buffer_size_change)
        self.__on_buffer_size_change(buffer_size_widget.value())
        self.__series['x'] = self.__init_img('x', 0)
        self.__series['y'] = self.__init_img('y', 1)
        self.__series['z'] = self.__init_img('z', 2)
        self.__reset_limits()

    def __init_img(self, axis, row):
        # initialise a buffer
        meta = self.__get_meta()
        self.__buffers[axis] = np.zeros(meta.sxx.T.shape)
        from qvibe import Inverse
        p = self.__qview.addPlot(row=0, column=row, axisItems={'left': Inverse(orientation='left')})
        # create the chart
        image = pg.ImageItem()
        p.addItem(image)
        pos, rgba_colors = zip(*colourmap())
        image.setLookupTable(pg.ColorMap(pos, rgba_colors).getLookupTable())
        image.setLevels([0, 150])
        # self.__histo.setImageItem(image)
        x_scale = 1.0 / (meta.sxx.shape[0]/meta.f[-1])
        y_scale = (1.0/self.fs) * (self.min_nperseg / 2)
        logger.debug(f"Scaling spectrogram from {meta.sxx.shape} to x: {x_scale} y:{y_scale}")
        image.scale(x_scale, y_scale)
        return p, image

    def __on_buffer_size_change(self, size):
        self.__buffer_size = size
        self.__reset_limits()

    def __reset_limits(self):
        if self.__buffer_size is not None:
            meta = self.__get_meta()
            for a in self.__series.values():
                format_pg_plotitem(a[0], (0, meta.f[-1]), (0, meta.t[-1]))

    def on_fs_change(self):
        self.__reset_limits()

    def reset_chart(self):
        # for c in self.__series.values():
        #     self.__chart.removeItem(c)
        # self.__series = {}
        self.__buffers = {}

    def __get_meta(self):
        rnd = np.random.default_rng().random(size=self.fs * self.__buffer_size)
        s = Signal('test', self.preferences, False, rnd, self.fs, self.resolution_shift, pre_calc=True,
                   view_mode='spectrogram')
        return s.get_analysis()

    def accept_data(self, data):
        self.__staging = data
        return data[0]

    def update_chart(self, recorder_name):
        '''
        updates the chart with the latest signal.
        '''
        if self.__staging is not None:
            self.create_or_update(self.__staging, 'x')
            self.create_or_update(self.__staging, 'y')
            self.create_or_update(self.__staging, 'z')

    def create_or_update(self, chunks, axis):
        c_idx = -len(chunks)
        buf = np.roll(self.__buffers[axis], c_idx, 0)
        for idx, c in enumerate(chunks):
            if c_idx == -1:
                buf[c_idx:] = getattr(c, axis).get_analysis().sxx.T
            else:
                buf[c_idx:c_idx+idx] = getattr(c, axis).get_analysis().sxx.T
        self.__buffers[axis] = buf
        self.__series[axis][1].setImage(buf.T, autoLevels=False)

    def make_event(self, recorder_name, data, idx):
        '''
        reduces the data down to the fresh nperseg sized chunks.
        :param recorder_name: the recorder.
        :param data: the data.
        :param idx: the snap idx.
        :return: the event if we have more than min_nperseg samples.
        '''
        last_processed_idx = max(self.__last_idx.get(recorder_name, 0), data[:, 0][0])
        latest_idx = data[:, 0][-1]
        fresh_sample_count = int(latest_idx - last_processed_idx)
        if fresh_sample_count >= self.min_nperseg:
            fresh_data = data[-fresh_sample_count:]
            remainder = fresh_data.shape[0] % self.min_nperseg
            if remainder > 0:
                fresh_data = fresh_data[:-remainder]
            assert fresh_data.shape[0] % self.min_nperseg == 0
            self.__last_idx[recorder_name] = fresh_data[:, 0][-1]
            if fresh_data.shape[0] > self.min_nperseg:
                chunks = np.vsplit(fresh_data, fresh_data.shape[0] / self.min_nperseg)
            else:
                chunks = [fresh_data]
            return SpectrogramEvent(self, recorder_name, chunks, idx, self.preferences, self.budget_millis,
                                    self.visible)
        return None

