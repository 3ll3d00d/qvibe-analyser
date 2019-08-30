import logging

import numpy as np
import pyqtgraph as pg
from PIL import Image

from common import format_pg_plotitem, colourmap
from model.charts import VisibleChart, ChartEvent
from model.signal import Signal, TriAxisSignal

logger = logging.getLogger('qvibe.vibration')

RESIZE_FACTOR = 8

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
                             idx=self.idx,
                             mode='vibration',
                             view_mode='spectrogram',
                             pre_calc=self.__visible)


class Spectrogram(VisibleChart):

    def __init__(self, chart, prefs, fs_widget, fps_widget, actual_fps_widget, resolution_widget, buffer_size_widget,
                 mag_min_widget, mag_max_widget, freq_min_widget, freq_max_widget, active_recorders_widget,
                 active_signals_widget):
        self.__sens = None
        self.__buffer_size = None
        super().__init__(prefs, fs_widget, resolution_widget, fps_widget, actual_fps_widget, True)
        self.__series = {}
        self.__staging = None
        self.__buffers = {}
        self.__last_idx = {}
        self.__recorders = []

        self.__qview = chart
        self.__mag_min = lambda: mag_min_widget.value()
        self.__mag_max = lambda: mag_max_widget.value()
        self.__all_recorders = active_recorders_widget
        self.__all_signals = active_signals_widget

        self.__visible_recorders = lambda: [i.text() for i in active_recorders_widget.selectedItems()]
        self.__visible_signals = lambda: [i.text() for i in active_signals_widget.selectedItems()]
        mag_min_widget.valueChanged['int'].connect(self.__on_mag_limit_change)
        mag_max_widget.valueChanged['int'].connect(self.__on_mag_limit_change)
        self.__freq_min = lambda: freq_min_widget.value()
        self.__freq_max = lambda: freq_max_widget.value()
        freq_min_widget.valueChanged['int'].connect(self.__on_freq_limit_change)
        freq_max_widget.valueChanged['int'].connect(self.__on_freq_limit_change)
        buffer_size_widget.valueChanged['int'].connect(self.__on_buffer_size_change)
        self.__on_buffer_size_change(buffer_size_widget.value())
        self.__reset_limits()
        active_recorders_widget.itemSelectionChanged.connect(self.__change_row_viz)
        active_signals_widget.itemSelectionChanged.connect(self.__change_column_viz)

    def __change_row_viz(self):
        for i in range(0, self.__all_recorders.count()):
            name = self.__all_recorders.item(i).text()
            visible = name in self.__visible_recorders()
            found = False
            for k, v in self.__series.items():
                if k.startswith(name):
                    logger.info(f"Setting {k} visible to {visible} at row {i}")
                    v[0].setVisible(visible)
                    found = True
            if found is not True:
                self.__create_charts(name)
        self.__qview.resizeEvent(None)

    def __change_column_viz(self):
        for i in range(0, self.__all_signals.count()):
            name = self.__all_signals.item(i).text()
            visible = name in self.__visible_signals()
            for k, v in self.__series.items():
                if k.endswith(f":{name}"):
                    logger.info(f"Setting {k} visible to {visible} at column {i}")
                    v[0].setVisible(visible)
        self.__qview.resizeEvent(None)

    def __create_charts(self, recorder):
        self.__series[f"{recorder}:x"] = self.__init_img(recorder, 'x', len(self.__recorders), 0)
        self.__series[f"{recorder}:y"] = self.__init_img(recorder, 'y', len(self.__recorders), 1)
        self.__series[f"{recorder}:z"] = self.__init_img(recorder, 'z', len(self.__recorders), 2)
        self.__reset_limits()
        self.__recorders.append(recorder)

    def __on_mag_limit_change(self, val):
        for ax in self.__series.values():
            ax[1].setLevels([self.__mag_min(), self.__mag_max()])

    def __on_freq_limit_change(self, val):
        for ax in self.__series.values():
            ax[0].setXRange(self.__freq_min(), self.__freq_max(), padding=0)

    def __init_img(self, recorder, axis, row, column):
        # initialise a buffer
        meta = self.__get_meta()
        self.__buffers[f"{recorder}:{axis}"] = np.zeros(meta.sxx.T.shape)
        from qvibe import Inverse
        kargs = {'row': row, 'col': column}
        if row == 0:
            kargs['title'] = axis
        # kargs['axisItems'] = {'left': Inverse(orientation='left')}
        p = self.__qview.addPlot(**kargs)
        p.getViewBox().invertY(True)
        # create the chart
        image = pg.ImageItem()
        p.addItem(image)
        if axis != 'x':
            p.showAxis('left', show=False)
        pos, rgba_colors = zip(*colourmap())
        image.setLookupTable(pg.ColorMap(pos, rgba_colors).getLookupTable())
        image.setLevels([self.__mag_min(), self.__mag_max()])
        x_scale = 1.0 / (meta.sxx.shape[0]/meta.f[-1])
        y_scale = (1.0/self.fs) * (self.min_nperseg / 2)
        logger.debug(f"Scaling spectrogram from {meta.sxx.shape} to x: {x_scale} y:{y_scale}")
        image.scale(x_scale / RESIZE_FACTOR, y_scale / RESIZE_FACTOR)
        return p, image

    def __on_buffer_size_change(self, size):
        self.__buffer_size = size
        self.__reset_limits()

    def __reset_limits(self):
        if self.__buffer_size is not None:
            meta = self.__get_meta()
            for a in self.__series.values():
                format_pg_plotitem(a[0], (0, meta.f[-1]), (0, meta.t[-1]),
                                   x_range=(self.__freq_min(), self.__freq_max()))

    def on_fs_change(self):
        self.__reset_limits()

    def reset_chart(self):
        for c in self.__series.values():
            self.__qview.removeItem(c[0])
        self.__series = {}
        self.__buffers = {}
        self.__recorders = []
        self.__change_row_viz()

    def __get_meta(self):
        rnd = np.random.default_rng().random(size=self.fs * self.__buffer_size)
        s = Signal('test', 'test',  self.preferences, rnd, self.fs, self.resolution_shift, pre_calc=True,
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
            if recorder_name in self.__visible_recorders():
                self.create_or_update(self.__staging, recorder_name, 'x')
                self.create_or_update(self.__staging, recorder_name, 'y')
                self.create_or_update(self.__staging, recorder_name, 'z')

    def create_or_update(self, chunks, recorder, axis):
        c_idx = len(chunks)
        buf = self.__buffers[f"{recorder}:{axis}"]
        buf = np.roll(buf, c_idx, 0)
        for idx, c in enumerate(chunks):
            dat = getattr(c, axis)
            if dat.has_data('spectrogram') is False:
                dat.recalc()
            sxx = dat.get_analysis().sxx
            buf[c_idx-idx-1] = sxx.T
        self.__buffers[f"{recorder}:{axis}"] = buf
        buf = np.array(Image.fromarray(buf).resize(size=[i*RESIZE_FACTOR for i in buf.shape[::-1]],
                                                   resample=Image.LANCZOS))
        self.__series[f"{recorder}:{axis}"][1].setImage(buf.T, autoLevels=False)

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

