import logging

import numpy as np
import pyqtgraph as pg
from PIL import Image

from common import format_pg_plotitem, colourmap
from model.charts import VisibleChart, ChartEvent
from model.preferences import CHART_SPECTRO_SCALE_FACTOR, CHART_SPECTRO_SCALE_ALGO
from model.signal import Signal, TriAxisSignal

logger = logging.getLogger('qvibe.vibration')


class SpectrogramEvent(ChartEvent):

    def __init__(self, chart, measurement_name, input, idx, preferences, budget_millis, visible):
        super().__init__(chart, measurement_name, input, idx, preferences, budget_millis)
        self.__visible = visible

    def process(self):
        self.output = [self.__make_sig(i) for i in self.input]
        self.should_emit = True

    def __make_sig(self, chunk):
        return TriAxisSignal(self.preferences,
                             self.measurement_name,
                             chunk,
                             self.chart.fs,
                             self.chart.resolution_shift,
                             idx=self.idx,
                             mode='vibration',
                             view_mode='spectrogram',
                             pre_calc=self.__visible)


class Spectrogram(VisibleChart):

    def __init__(self, chart, prefs, fs_widget, fps_widget, actual_fps_widget, resolution_widget, buffer_size_widget,
                 mag_min_widget, mag_max_widget, freq_min_widget, freq_max_widget, visible_axes_widget,
                 measurement_store):
        self.__sens = None
        self.__buffer_size = None
        super().__init__(prefs, fs_widget, resolution_widget, fps_widget, actual_fps_widget, True)
        self.__rows = 0
        self.__series = {}
        self.__staging = None
        self.__buffers = {}
        self.__last_idx = {}
        self.__scale_factor = None
        self.__scale_algo = None

        self.__qview = chart
        self.__mag_min = lambda: mag_min_widget.value()
        self.__mag_max = lambda: mag_max_widget.value()
        self.__measurement_store = measurement_store
        self.__all_axes = visible_axes_widget

        self.__visible_axes = lambda: [i.text() for i in visible_axes_widget.selectedItems()]
        mag_min_widget.valueChanged['int'].connect(self.__on_mag_limit_change)
        mag_max_widget.valueChanged['int'].connect(self.__on_mag_limit_change)
        self.__freq_min = lambda: freq_min_widget.value()
        self.__freq_max = lambda: freq_max_widget.value()
        freq_min_widget.valueChanged['int'].connect(self.__on_freq_limit_change)
        freq_max_widget.valueChanged['int'].connect(self.__on_freq_limit_change)
        buffer_size_widget.valueChanged['int'].connect(self.__on_buffer_size_change)
        self.update_scale()
        self.__on_buffer_size_change(buffer_size_widget.value())
        self.__reset_limits()
        self.__measurement_store.signals.measurement_added.connect(lambda m: self.__create_charts(m.key))
        self.__measurement_store.signals.measurement_deleted.connect(lambda m: self.__remove_charts(m.key))
        self.__measurement_store.signals.visibility_changed.connect(self.__change_row_viz)
        visible_axes_widget.itemSelectionChanged.connect(self.__change_column_viz)

    def update_scale(self):
        '''
        update the scaling algorithm.
        '''
        new_scale_factor = int(self.preferences.get(CHART_SPECTRO_SCALE_FACTOR)[0:-1])
        new_scale_algo = getattr(Image, self.preferences.get(CHART_SPECTRO_SCALE_ALGO).upper())
        if new_scale_factor != self.__scale_factor or new_scale_algo != self.__scale_algo:
            logger.info(f"Changing scaling from {self.__scale_factor} {self.__scale_algo} to {new_scale_factor} {new_scale_algo}")
            self.__scale_factor = new_scale_factor
            self.__scale_algo = new_scale_algo
            if self.visible is True:
                for c in self.__series.values():
                    self.__qview.removeItem(c[0])
                self.__series = {}

    def __change_row_viz(self, measurement):
        visible_axes = self.__visible_axes()
        for k, v in self.__series.items():
            if k.startswith(f"{measurement.key}:"):
                logger.info(f"Changing {k} visibility to {measurement.visible}")
                if measurement.visible is True and len([m for m in visible_axes if k.endswith(f":{m}")]) > 0:
                    v[0].setVisible(measurement.visible)
                else:
                    v[0].setVisible(False)
        self.__qview.resizeEvent(None)

    def __change_column_viz(self):
        visible_measurements = self.__measurement_store.get_visible_measurements()
        for i in range(0, self.__all_axes.count()):
            name = self.__all_axes.item(i).text()
            visible = name in self.__visible_axes()
            for k, v in self.__series.items():
                if k.endswith(f":{name}"):
                    if visible is True and len([m for m in visible_measurements if k.startswith(f"{m}:")]) > 0:
                        logger.info(f"Setting {k} visible to {visible} at column {i}")
                        v[0].setVisible(visible)
                    else:
                        v[0].setVisible(False)
        self.__qview.resizeEvent(None)

    def __create_charts(self, measurement_name):
        ''' Creates a new set of charts for the named measurement. '''
        logger.info(f"Creating charts for {measurement_name}")
        self.__series[f"{measurement_name}:x"] = self.__init_img(measurement_name, 'x', self.__rows, 0)
        self.__series[f"{measurement_name}:y"] = self.__init_img(measurement_name, 'y', self.__rows, 1)
        self.__series[f"{measurement_name}:z"] = self.__init_img(measurement_name, 'z', self.__rows, 2)
        self.__rows += 1
        self.__reset_limits()

    def __remove_charts(self, measurement_name):
        '''
        Hides the images at the specified row.
        :param measurement_name: the name.
        '''
        logger.info(f"Removing charts for {measurement_name}")
        for k, v in self.__series.items():
            if k.startswith(f"{measurement_name}:"):
                v[0].setVisible(False)
        self.__qview.resizeEvent(None)

    def __on_mag_limit_change(self, val):
        for ax in self.__series.values():
            ax[1].setLevels([self.__mag_min(), self.__mag_max()])

    def __on_freq_limit_change(self, val):
        for ax in self.__series.values():
            ax[0].setXRange(self.__freq_min(), self.__freq_max(), padding=0)

    def __init_img(self, measurement, axis, row, column):
        # initialise a buffer
        meta = self.__get_meta()
        self.__buffers[f"{measurement}:{axis}"] = np.zeros(meta.sxx.T.shape)
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
        image.scale(x_scale / self.__scale_factor, y_scale / self.__scale_factor)
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

    def __get_meta(self):
        rnd = np.random.default_rng().random(size=self.fs * self.__buffer_size)
        s = Signal('test', 'test',  self.preferences, rnd, self.fs, self.resolution_shift, pre_calc=True,
                   view_mode='spectrogram')
        return s.get_analysis()

    def accept_data(self, data):
        self.__staging = data
        return data[0]

    def update_chart(self, measurement_name):
        '''
        updates the chart with the latest signal.
        '''
        if self.__staging is not None:
            if measurement_name in self.__measurement_store.get_visible_measurements():
                self.create_or_update(self.__staging, measurement_name, 'x')
                self.create_or_update(self.__staging, measurement_name, 'y')
                self.create_or_update(self.__staging, measurement_name, 'z')

    def create_or_update(self, chunks, measurement_name, axis):
        c_idx = len(chunks)
        buf = self.__buffers[f"{measurement_name}:{axis}"]
        buf = np.roll(buf, c_idx, 0)
        for idx, c in enumerate(chunks):
            dat = getattr(c, axis)
            if dat.has_data('spectrogram') is False:
                dat.recalc()
            sxx = dat.get_analysis().sxx
            buf[c_idx-idx-1] = sxx.T
        self.__buffers[f"{measurement_name}:{axis}"] = buf
        buf = np.array(Image.fromarray(buf).resize(size=[i*self.__scale_factor for i in buf.shape[::-1]],
                                                   resample=self.__scale_algo))
        self.__series[f"{measurement_name}:{axis}"][1].setImage(buf.T, autoLevels=False)

    def make_event(self, measurement_name, data, idx):
        '''
        reduces the data down to the fresh nperseg sized chunks.
        :param measurement_name: the measurement name.
        :param data: the data.
        :param idx: the snap idx.
        :return: the event if we have more than min_nperseg samples.
        '''
        last_processed_idx = max(self.__last_idx.get(measurement_name, 0), data[:, 0][0])
        latest_idx = data[:, 0][-1]
        fresh_sample_count = int(latest_idx - last_processed_idx)
        if fresh_sample_count >= self.min_nperseg:
            fresh_data = data[-fresh_sample_count:]
            remainder = fresh_data.shape[0] % self.min_nperseg
            if remainder > 0:
                fresh_data = fresh_data[:-remainder]
            assert fresh_data.shape[0] % self.min_nperseg == 0
            self.__last_idx[measurement_name] = fresh_data[:, 0][-1]
            if fresh_data.shape[0] > self.min_nperseg:
                chunks = np.vsplit(fresh_data, fresh_data.shape[0] / self.min_nperseg)
            else:
                chunks = [fresh_data]
            return SpectrogramEvent(self, measurement_name, chunks, idx, self.preferences, self.budget_millis,
                                    self.visible)
        return None

