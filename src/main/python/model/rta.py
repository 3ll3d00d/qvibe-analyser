import logging
import math

import numpy as np
import pyqtgraph as pg
import qtawesome as qta
from qtpy import QtWidgets, QtCore
from qtpy.QtWidgets import QMessageBox
from qtpy.QtCore import Qt

from common import format_pg_plotitem, block_signals, FlowLayout
from model.charts import VisibleChart, ChartEvent
from model.frd import ExportDialog
from model.preferences import RTA_TARGET
from model.signal import smooth_savgol, Analysis, TriAxisSignal, REF_ACCELERATION_IN_G

TARGET_PLOT_NAME = 'Target'

logger = logging.getLogger('qvibe.rta')


class RTAEvent(ChartEvent):

    def __init__(self, chart, measurement_name, input, idx, preferences, budget_millis, view, visible):
        super().__init__(chart, measurement_name, input, idx, preferences, budget_millis)
        self.__view = view
        self.__visible = visible

    def process(self):
        self.output = [self.__make_sig(i) for i in self.input]
        self.should_emit = True

    def __make_sig(self, chunk):
        tas = TriAxisSignal(self.preferences,
                             self.measurement_name,
                             chunk,
                             self.chart.fs,
                             self.chart.resolution_shift,
                             idx=self.idx,
                             mode='vibration',
                             view_mode='spectrogram',
                             pre_calc=self.__visible)
        tas.set_view(self.__view, recalc=False)
        if self.__visible:
            tas.recalc()
        return tas


class RTA(VisibleChart):
    def __init__(self, parent_layout, parent_tab, chart, prefs, fs_widget, resolution_widget, fps_widget,
                 actual_fps_widget, mag_min_widget, mag_max_widget, freq_min_widget, freq_max_widget,
                 ref_curve_selector, show_value_selector, measurement_store_signals, colour_provider):
        measurement_store_signals.measurement_added.connect(self.__add_measurement)
        measurement_store_signals.measurement_deleted.connect(self.__remove_measurement)
        self.__ui = ControlUi(parent_layout, parent_tab)
        self.__known_measurements = []
        self.__show_average = self.__ui.show_average.isChecked()
        self.__ref_curve_selector = ref_curve_selector
        self.__show_value_selector = show_value_selector
        self.__ref_curve = None
        self.__reset_selector(self.__ref_curve_selector)
        self.__reset_selector(self.__show_value_selector)
        self.__plots = {}
        self.__plot_data = {}
        self.__smooth = False
        self.__colour_provider = colour_provider
        self.__move_crosshairs = False
        self.__chunk_calc = None
        self.__ui.toggle_crosshairs.toggled[bool].connect(self.__toggle_crosshairs)
        super().__init__(prefs, fs_widget, resolution_widget, fps_widget, actual_fps_widget,
                         False, coalesce=True, cache_size=-1, cache_purger=self.__purge_cache)
        self.__peak_cache = {}
        self.__hold_secs = self.__ui.hold_secs.value()
        self.__show_peak = self.__ui.show_peak.isChecked()
        self.__show_live = self.__ui.show_live.isChecked()
        self.__target_data = None
        self.__target_adjustment_db = self.__ui.target_adjust_db.value()
        self.__show_target = self.__ui.show_target.isChecked()
        self.__show_target_toggle = self.__ui.show_target
        self.__ui.target_adjust_db.valueChanged.connect(self.__adjust_target_level)
        self.__sg_wl = self.__ui.sg_window_length.value()
        self.__sg_poly = None
        self.__on_sg_poly(self.__ui.sg_poly_order.value())
        self.__frame = 0
        self.__time = -1
        self.__update_rate = None
        self.__active_view = None
        self.__chart = chart
        # wire the analysis to the view controls
        self.__mag_min = lambda: mag_min_widget.value()
        self.__mag_max = lambda: mag_max_widget.value()
        self.__freq_min = lambda: freq_min_widget.value()
        self.__freq_max = lambda: freq_max_widget.value()
        self.__on_rta_view_change(self.__ui.rta_view.currentText())
        self.__ui.rta_view.currentTextChanged.connect(self.__on_rta_view_change)
        self.__on_rta_smooth_change(self.__ui.smooth_rta.isChecked())
        self.__ui.smooth_rta.toggled[bool].connect(self.__on_rta_smooth_change)
        self.__legend = None
        format_pg_plotitem(self.__chart.getPlotItem(),
                           (0, self.fs / 2),
                           (-150, 150),
                           x_range=(self.__freq_min(), self.__freq_max()),
                           y_range=(self.__mag_min(), self.__mag_max()))
        # link limit controls to the chart
        mag_min_widget.valueChanged['int'].connect(self.__on_mag_limit_change)
        mag_max_widget.valueChanged['int'].connect(self.__on_mag_limit_change)
        freq_min_widget.valueChanged['int'].connect(self.__on_freq_limit_change)
        freq_max_widget.valueChanged['int'].connect(self.__on_freq_limit_change)
        # curve display wiring
        self.__ui.show_peak.toggled[bool].connect(self.__on_show_peak_change)
        self.__ui.show_live.toggled[bool].connect(self.__on_show_live_change)
        self.__ui.show_average.toggled[bool].connect(self.__on_show_average_change)
        self.__ui.show_target.toggled[bool].connect(self.__on_show_target_change)
        self.__ui.hold_secs.valueChanged.connect(self.__set_max_cache_age)
        # S-G filter params
        self.__ui.sg_window_length.valueChanged['int'].connect(self.__on_sg_window_length)
        self.__ui.sg_poly_order.valueChanged['int'].connect(self.__on_sg_poly)
        self.reload_target()
        # export
        self.__ui.export_frd.clicked.connect(self.__export_frd)
        # ref curves
        self.__ref_curve_selector.currentTextChanged.connect(self.__set_reference_curve)
        # marker curves
        self.__show_value_selector.currentTextChanged.connect(self.__set_show_value_curve)
        # crosshairs
        self.__v_line_label = CurveAwareLabel()
        self.__v_line = pg.InfiniteLine(angle=90, movable=False, label=self.__v_line_label, labelOpts={'position': 0.95})
        self.__h_line = pg.InfiniteLine(angle=0, movable=False, label=AccelerationLabel(), labelOpts={'position': 0.95})
        self.__chart.getPlotItem().addItem(self.__v_line, ignoreBounds=True)
        self.__chart.getPlotItem().addItem(self.__h_line, ignoreBounds=True)

        def mouse_moved(evt):
            pos = evt[0]
            if self.__chart.getPlotItem().sceneBoundingRect().contains(pos) and self.__move_crosshairs is True:
                mouse_point = self.__chart.getPlotItem().vb.mapSceneToView(pos)
                self.__v_line.setPos(mouse_point.x())
                self.__h_line.setPos(mouse_point.y())

        self.__proxy = pg.SignalProxy(self.__chart.scene().sigMouseMoved, delay=0.125, rateLimit=20, slot=mouse_moved)

    def __toggle_crosshairs(self, move_crosshairs):
        self.__move_crosshairs = move_crosshairs

    def __add_measurement(self, measurement):
        '''
        Adds the measurement to the ref curve selector.
        :param measurement: the measurement.
        '''
        self.__known_measurements.append(measurement.key)

    def __remove_measurement(self, measurement):
        '''
        Remove the measurement from the ref curve.
        :param measurement: the measurement.
        '''
        if measurement.key in self.__known_measurements:
            self.__known_measurements.remove(measurement.key)
        self.__remove_from_selector(self.__ref_curve_selector, measurement.key)
        self.__remove_from_selector(self.__show_value_selector, measurement.key)

    def __set_reference_curve(self, curve):
        '''
        Updates the reference curve.
        :param curve: the new reference curve.
        '''
        new_curve = curve if curve != '' else None
        old_curve = self.__ref_curve
        if self.__ref_curve != new_curve:
            logger.info(f"Updating reference curve from {self.__ref_curve} to {new_curve}")
            self.__ref_curve = new_curve
            min_y, max_y = self.__chart.getPlotItem().getViewBox().state['viewRange'][1]
            adj = (max_y - min_y) / 2
            if old_curve is None:
                self.__chart.getPlotItem().setYRange(-adj, adj, padding=0.0)
            elif self.__ref_curve is None:
                centre = (self.__mag_max() - self.__mag_min()) / 2
                self.__chart.getPlotItem().setYRange(centre - adj + self.__mag_min(), centre + adj + self.__mag_min(),
                                                     padding=0.0)

            self.__render_target()
            self.update_all_plots()

    def __set_show_value_curve(self, curve):
        '''
        Updates the curve associated with the vline.
        :param curve: the curve.
        '''
        curve = curve if curve != '' else None
        if curve in self.__plots:
            curve = self.__plots[curve]
        else:
            curve = None
        self.__v_line_label.curve = curve
        self.__v_line.label.valueChanged()

    def __export_frd(self):
        '''
        Shows the export dialog.
        '''
        available_data = {n: d for n in self.cached_measurement_names() for d in self.cached_data(n) if d is not None}
        if len(available_data.keys()) > 0:
            ExportDialog(self.__chart, available_data).exec()
        else:
            msg_box = QMessageBox()
            msg_box.setText('No data has been recorded')
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle('Nothing to export')
            msg_box.exec()

    def __on_sg_window_length(self, wl):
        '''
        Updates the S-G window length.
        :param wl: the length.
        '''
        if wl % 2 == 0:
            self.__ui.sg_window_length.setValue(wl+1)
        else:
            self.__sg_wl = wl
        if self.__smooth is True:
            self.update_all_plots()

    def __on_sg_poly(self, poly):
        '''
        Updates the S-G poly order.
        :param poly: the poly order.
        '''
        self.__sg_poly = poly
        wl_min = poly + 1
        if wl_min % 2 == 0:
            wl_min += 1
        self.__ui.sg_window_length.setMinimum(wl_min)
        if self.__smooth is True:
            self.update_all_plots()

    def __set_max_cache_age(self, seconds):
        '''
        Sets the max age of the cache in seconds.
        :param seconds: the max age of a cache entry.
        '''
        self.__hold_secs = seconds
        self.for_each_cache(self.__purge_cache)

    def __on_show_peak_change(self, checked):
        '''
        shows or hides the peak curves.
        :param checked: if checked then show the curves otherwise hide.
        '''
        self.__show_peak = checked
        self.update_all_plots()

    def __on_show_live_change(self, checked):
        '''
        shows or hides the live curves.
        :param checked: if checked then show the curves otherwise hide.
        '''
        self.__show_live = checked
        self.update_all_plots()

    def __on_mag_limit_change(self, val):
        '''
        Updates the visible y axis range.
        :param val: ignored.
        '''
        self.__chart.getPlotItem().setYRange(self.__mag_min(), self.__mag_max(), padding=0)

    def __on_freq_limit_change(self, val):
        '''
        Updates the visible x axis range.
        :param val: ignored.
        '''
        self.__chart.getPlotItem().setXRange(self.__freq_min(), self.__freq_max(), padding=0)

    def __on_rta_smooth_change(self, state):
        '''
        Puts the visible curves into smoothed mode or not.
        :param state: if checked then smooth else unsmoothed.
        '''
        self.__smooth = state
        self.update_all_plots()

    def __on_rta_view_change(self, view):
        '''
        Changes the current view (avg, peak, psd).
        :param view: the view.
        '''
        old_view = self.__active_view
        logger.info(f"Updating active view from {old_view} to {view}")
        self.__active_view = view

        def propagate_view_change(cache):
            for c in cache:
                c.set_view(view)

        self.for_each_cache(propagate_view_change)
        self.update_all_plots()
        logger.info(f"Updated active view from {old_view} to {view}")

    def __on_show_average_change(self, checked):
        '''
        whether to average the cached data.
        :param checked: whether to apply averaging.
        '''
        self.__show_average = checked
        self.update_all_plots()

    def __on_show_target_change(self, checked):
        '''
        whether to show the target curve.
        :param checked: whether to show the target.
        '''
        self.__show_target = checked
        self.__render_target()
        if self.__ref_curve == TARGET_PLOT_NAME:
            self.update_all_plots()

    def __adjust_target_level(self, adjustment):
        ''' Adjusts the target level. '''
        self.__target_adjustment_db = adjustment
        self.__render_target()
        if self.__ref_curve == TARGET_PLOT_NAME:
            self.update_all_plots()

    def reload_target(self):
        '''
        Loads the target from preferences.
        '''
        if self.preferences.has(RTA_TARGET) is True:
            self.__show_target_toggle.setEnabled(True)
            self.__ui.target_adjust_db.setEnabled(True)
            self.__ui.target_adjust_db.setValue(0)
            import io
            arr = np.loadtxt(io.StringIO(self.preferences.get(RTA_TARGET)), dtype=np.float64, ndmin=2)
            f = arr[0]
            m = arr[1]
            if np.min(m) < 40.0:
                adj = 85.0 - (np.mean(m[0: np.argmax(f > 60)]) if np.max(f) > 60 else np.mean(m))
                adjusted_m = m + adj
            else:
                adjusted_m = m
            self.__target_data = Analysis((f, adjusted_m, adjusted_m))
        else:
            self.__show_target_toggle.setChecked(False)
            self.__show_target_toggle.setEnabled(False)
            self.__ui.target_adjust_db.setValue(0)
            self.__ui.target_adjust_db.setEnabled(False)
            self.__target_data = None
        self.__render_target()

    def make_event(self, measurement_name, data, idx):
        '''
        create a min_nperseg sixed window on the data and slide it forward in fresh_sample_count
        stride a window over the data in fresh_sample_count
        :param measurement_name: the measurement the data came from.
        :param data: the data to analyse.
        :param idx: the index of the data set.
        '''
        chunks = self.__chunk_calc.recalc(measurement_name, data)
        if chunks is not None:
            return RTAEvent(self, measurement_name, chunks, idx, self.preferences, self.budget_millis,
                            self.__active_view, self.visible)
        return None

    def reset_chart(self):
        '''
        Removes all curves.
        '''
        for c in self.__plots.values():
            self.__chart.removeItem(c)
        self.__reset_selector(self.__ref_curve_selector)
        self.__reset_selector(self.__show_value_selector)
        self.__ref_curve = None
        self.__v_line_label.curve = None
        self.__plots = {}
        self.__plot_data = {}
        self.__chunk_calc = ChunkCalculator(self.min_nperseg)

    def on_min_nperseg_change(self):
        '''
        Propagates min_nperseg to the chunk calculator.
        '''
        if self.__chunk_calc is None:
            self.__chunk_calc = ChunkCalculator(self.min_nperseg)
        else:
            self.__chunk_calc.min_nperseg = self.min_nperseg

    @staticmethod
    def __reset_selector(selector):
        '''
        Clears out the combo.
        '''
        with block_signals(selector):
            selector.clear()
            selector.addItem('')

    def update_chart(self, measurement_name):
        '''
        Updates all the curves for the named recorder with the latest data and config.
        :param measurement_name: the recorder.
        '''
        data = self.cached_data(measurement_name)
        if data is not None and len(data) > 0:
            if data[-1].shape[0] >= self.min_nperseg:
                self.__display_triaxis_signal(data)
                for axis in ['x', 'y', 'z', 'sum']:
                    self.render_peak(data, axis)

    def __display_triaxis_signal(self, signals, plot_name_prefix=''):
        '''
        ensures the correct analysis curves for the signal are displayed on screen.
        :param signal: the TriAxisSignals to average.
        :param plot_name_prefix: extension to signal name for creating a plot name.
        '''
        for signal in signals:
            if signal.view != self.__active_view:
                logger.info(f"Updating active view from {signal.view} to {self.__active_view} at {signal.idx}")
                signal.set_view(self.__active_view)
            if signal.has_data(self.__active_view) is False and signal.shape[0] >= self.min_nperseg:
                signal.recalc()
        self.render_signal(signals, 'x', plot_name_prefix=plot_name_prefix)
        self.render_signal(signals, 'y', plot_name_prefix=plot_name_prefix)
        self.render_signal(signals, 'z', plot_name_prefix=plot_name_prefix)
        self.render_signal(signals, 'sum', plot_name_prefix=plot_name_prefix)

    def __purge_cache(self, cache):
        '''
        Purges the cache of data older than peak_secs.
        :param cache: the cache (a deque)
        '''
        while len(cache) > 1:
            latest = cache[-1].time[-1]
            if (latest - cache[0].time[-1]) >= (self.__hold_secs * 1000.0):
                cache.popleft()
            else:
                break

    def __render_target(self):
        '''
        Renders the target data.
        '''
        if self.__target_data is None or self.__show_target is False:
            if TARGET_PLOT_NAME in self.__plots:
                self.__remove_named_plot(TARGET_PLOT_NAME)
        elif self.__target_data is not None and self.__show_target is True:
            pen_args = {'style': Qt.SolidLine}
            y_db = self.__target_data.y + self.__target_adjustment_db
            self.__render_or_update(pen_args, TARGET_PLOT_NAME, self.__target_data.x, y_db)

    def render_peak(self, data, axis):
        '''
        Converts a peak dataset into a renderable plot item.
        :param data: the cached data.
        :param axis: the axis to display.
        '''
        y_data = x_data = pen_args = None
        sig = getattr(data[-1], axis)
        if self.__show_peak is True:
            has_data = sig.get_analysis(self.__active_view)
            if has_data is not None:
                if all([d.shape[0] >= self.min_nperseg for d in data]):
                    data_ = [getattr(d, axis).get_analysis(self.__active_view).y for d in data]
                    y_data = np.maximum.reduce(data_)
                x_data = has_data.x
            pen_args = {'style': Qt.DashLine}
        self.__manage_plot_item(f"{sig.measurement_name}:{sig.axis}:peak", data[-1].idx, sig.measurement_name, sig.axis,
                                x_data, y_data, pen_args)

    def render_signal(self, data, axis, plot_name_prefix=''):
        '''
        Converts (one or more) signal into a renderable plot item.
        :param data: the cached data.
        :param axis: the axis to display.
        :param plot_name_prefix: optional plot name prefix.
        '''
        y_data = y_avg = x_data = None
        sig = getattr(data[-1], axis)
        has_data = sig.get_analysis(self.__active_view)
        if has_data is not None:
            if self.__show_average is True:
                if all([d.shape[0] >= self.min_nperseg for d in data]):
                    y_avg = np.average([getattr(d, axis).get_analysis(self.__active_view).y for d in data], axis=0)
            if self.__show_live is True:
                y_data = has_data.y
            x_data = has_data.x
        pen = {'style': Qt.SolidLine}
        plot_name = f"{plot_name_prefix}{sig.measurement_name}:{sig.axis}"
        self.__manage_plot_item(plot_name, data[-1].idx, sig.measurement_name, sig.axis, x_data, y_data, pen)
        avg_pen = {'style': Qt.DashDotDotLine}
        avg_plot_name = f"{plot_name_prefix}{sig.measurement_name}:{sig.axis}:avg"
        self.__manage_plot_item(avg_plot_name, data[-1].idx, sig.measurement_name, sig.axis, x_data, y_avg, avg_pen)

    def __manage_plot_item(self, name, idx, measurement_name, axis, x_data, y_data, pen_args):
        '''
        Creates or updates a plot item or removes it.
        :param name: plot name.
        :param idx: the underlying signal index.
        :param measurement_name: the originating measurement.
        :param axis: the axis for which this data is for.
        :param x_data: x data.
        :param y_data: y data.
        :param pen_args: the args to describe the pen
        '''
        if y_data is not None:
            logger.debug(f"Tick {axis} {idx} {np.min(y_data):.4f} - {np.max(y_data):.4f} - {len(y_data)} ")
            self.__show_or_remove_analysis(name, measurement_name, axis, x_data, y_data, pen_args if pen_args else {})
        elif name in self.__plots:
            self.__remove_named_plot(name)

    def __remove_named_plot(self, name):
        '''
        Eliminates the named plot.
        :param name: the name.
        '''
        self.__chart.removeItem(self.__plots[name])
        del self.__plots[name]
        del self.__plot_data[name]
        self.__legend.removeItem(name)
        self.__remove_from_selector(self.__ref_curve_selector, name)
        self.__remove_from_selector(self.__show_value_selector, name)

    @staticmethod
    def __remove_from_selector(selector, name):
        '''
        Removes the named item from the selector.
        :param selector: the selector.
        :param name: the name.
        '''
        idx = selector.findText(name)
        if idx > -1:
            if selector.currentIndex() == idx:
                selector.setCurrentIndex(0)
            selector.removeItem(idx)

    def __show_or_remove_analysis(self, plot_name, measurement_name, axis, x_data, y_data, pen_args):
        '''
        If the series should be visible, creates or updates a PlotItem with the x and y data.
        If the series should not be visible, removes the PlotItem if it is displayed atm.
        :param plot_name: plot name.
        :param measurement_name: the measurement name.
        :param axis: the axis.
        :param x_data: x data.
        :param y_data: y data.
        :param pen_args: the description of the pen.
        '''
        if self.is_visible(measurement=measurement_name, axis=axis) is True:
            y = smooth_savgol(x_data, y_data, wl=self.__sg_wl, poly=self.__sg_poly)[1] if self.__smooth is True else y_data
            self.__render_or_update(pen_args, plot_name, x_data, y, axis=axis)
        elif plot_name in self.__plots:
            self.__remove_named_plot(plot_name)

    def __render_or_update(self, pen_args, plot_name, x_data, y, axis=None):
        '''
        actually updates (or creates) the plot.
        :param pen_args: the pen args.
        :param plot_name: the plot name.
        :param x_data: x.
        :param y: y.
        :param axis: the axis.
        '''
        self.__plot_data[plot_name] = x_data, y
        if self.__ref_curve is not None:
            ref_plot_name = None
            if self.__ref_curve in self.__known_measurements:
                if axis is not None:
                    ref_plot_name = f"{self.__ref_curve}:{axis}"
            elif self.__ref_curve in self.__plot_data:
                ref_plot_name = self.__ref_curve
            if ref_plot_name in self.__plot_data:
                ref_plot_data = self.__plot_data[ref_plot_name]
                x_data, y = self.__normalise(ref_plot_data[0], ref_plot_data[1], x_data, y)
        if plot_name in self.__plots:
            self.__plots[plot_name].setData(x_data, y)
            self.__v_line.label.valueChanged()
        else:
            if self.__legend is None:
                self.__legend = self.__chart.addLegend(offset=(-15, -15))
            pen = pg.mkPen(color=self.__colour_provider.get_colour(plot_name), width=2, **pen_args)
            self.__plots[plot_name] = self.__chart.plot(x_data, y, pen=pen, name=plot_name)
            self.__ensure_curve_in_selector(self.__ref_curve_selector, plot_name)
            self.__ensure_curve_in_selector(self.__show_value_selector, plot_name, include_measurement=False)

    def __ensure_curve_in_selector(self, selector, plot_name, include_measurement=True):
        ''' Ensures the name is in the combo '''
        if selector.findText(plot_name) == -1:
            if include_measurement is True:
                m_name = next((m for m in self.__known_measurements if plot_name.startswith(f"{m}:")), None)
                if m_name is not None:
                    if selector.findText(m_name) == -1:
                        selector.addItem(m_name)
            selector.addItem(plot_name)

    @staticmethod
    def __normalise(ref_x, ref_y, data_x, data_y):
        '''
        Creates a new dataset which shows the delta between the data and the reference.
        :param ref_x: the ref x values.
        :param ref_y: the ref y values.
        :param data_x: the data x values.
        :param data_y: the data y values.
        :return: the resulting normalised x and y values.
        '''
        ref_step = ref_x[1] - ref_x[0]
        data_step = data_x[1] - data_x[0]
        if ref_step == data_step:
            count = min(ref_x.size, data_x.size) - 1
            new_x = data_x[0:count]
            new_y = data_y[0:count] - ref_y[0:count]
        else:
            if data_x[-1] == ref_x[-1]:
                # same max so upsample to the more precise one
                if data_step < ref_step:
                    new_x = data_x
                    new_y = data_y - np.interp(data_x, ref_x, ref_y)[1]
                else:
                    new_x = ref_x
                    new_y = data_y - np.interp(ref_x, data_x, data_y)[1]
            elif data_x[-1] > ref_x[-1]:
                # restrict the self data range to the limits of the target
                capped_x = data_x[data_x <= ref_x[-1]]
                capped_y = data_y[0:capped_x.size]
                if data_step < ref_step:
                    new_x = capped_x
                    new_y = capped_y - np.interp(capped_x, ref_x, ref_y)[1]
                else:
                    new_x = ref_x
                    new_y = np.interp(ref_x, capped_x, capped_y)[1] - ref_y
            else:
                # restrict the target data range to the limits of the self
                capped_x = ref_x[ref_x <= data_x[-1]]
                capped_y = ref_y[0:capped_x.size]
                if ref_step < data_step:
                    new_x = data_x
                    new_y = data_y - np.interp(data_x, capped_x, capped_y)[1]
                else:
                    new_x = capped_x
                    new_y = np.interp(ref_x, data_x, data_y)[1] - ref_y
        return new_x, new_y


class ChunkCalculator:
    def __init__(self, min_nperseg):
        self.last_idx = {}
        self.min_nperseg = min_nperseg

    def recalc(self, name, data):
        last_processed_idx = max(self.last_idx.get(name, 0), data[:, 0][0])
        latest_idx = data[:, 0][-1]
        fresh_sample_count = int(latest_idx - last_processed_idx)
        if fresh_sample_count > 0 and data.shape[0] >= self.min_nperseg:
            # work out how many samples to include
            # if we have less fresh data than min_nperseg then take the last nperseg samples
            # if we have more then take the lesser of all available data
            if fresh_sample_count <= self.min_nperseg:
                samples_to_analyse = self.min_nperseg
            else:
                target_chunks = math.ceil(fresh_sample_count / self.min_nperseg)
                samples_to_analyse = target_chunks * self.min_nperseg
                while samples_to_analyse > data.shape[0]:
                    target_chunks -= 1
                    samples_to_analyse = target_chunks * self.min_nperseg
            if last_processed_idx == 0:
                new_data = data[0:samples_to_analyse]
            else:
                new_data = data[-samples_to_analyse:]
            new_last_idx = new_data[:, 0][-1]
            logger.debug(f"Moving window by {new_last_idx - last_processed_idx} [{last_processed_idx} to {new_last_idx}]")
            self.last_idx[name] = new_last_idx
            if new_data.shape[0] > self.min_nperseg:
                return np.vsplit(new_data, new_data.shape[0] / self.min_nperseg)
            else:
                return [new_data]
        return None


class CurveAwareLabel:
    def __init__(self):
        self.curve = None
        self.__no_curve_format = '[{value:0.1f} Hz]'
        self.__curve_format = '[{value:0.1f} Hz / {mag:0.1f} dB{accel}]'
        self.__accel_format = '{sep}{accel:0.3f}{suffix}{unit}'

    def format(self, value):
        if self.curve is None:
            return self.__no_curve_format.format(value=value)
        else:
            mag = self.__get_y_pos(value)
            if mag == -1:
                accel = ''
            else:
                sep = ' / '
                unit = 'G'
                suffix = ''
                accel = 10.0 ** (mag/20) * REF_ACCELERATION_IN_G
                if accel <= 0.1:
                    accel *= 1000.0
                    suffix = 'm'
                accel = self.__accel_format.format(suffix=suffix, unit=unit, sep=sep, accel=accel)
            return self.__curve_format.format(value=value, mag=mag, accel=accel)

    def __get_y_pos(self, hz):
        try:
            x, y = self.curve.getData()
            return y[np.argmax(x >= hz)]
        except:
            return -1.0


class AccelerationLabel:
    def __init__(self):
        self.__format = '[{value:0.1f} dB / {accel:0.3f} {suffix}G]'

    def format(self, value):
        accel = 10.0 ** (value/20) * REF_ACCELERATION_IN_G
        if accel <= 0.1:
            accel *= 1000.0
            suffix = 'm'
        else:
            suffix = ''
        return self.__format.format(value=value, accel=accel, suffix=suffix)


class ControlUi:
    def __init__(self, parent_layout, rtaTab):
        self.parent_layout = parent_layout
        self.rta_tab = rtaTab
        self.rta_controls_layout = FlowLayout()
        self.rta_controls_layout.setObjectName("rtaControlsLayout")
        self.rta_view_label = QtWidgets.QLabel(self.rta_tab)
        self.rta_view_label.setObjectName("rtaViewLabel")
        self.rta_controls_layout.addWidget(self.rta_view_label)
        self.rta_view = QtWidgets.QComboBox(self.rta_tab)
        self.rta_view.setObjectName("rtaView")
        self.rta_view.addItem("")
        self.rta_view.addItem("")
        self.rta_view.addItem("")
        self.rta_controls_layout.addWidget(self.rta_view)
        self.hold_time_label = QtWidgets.QLabel(self.rta_tab)
        self.hold_time_label.setObjectName("holdTimeLabel")
        self.rta_controls_layout.addWidget(self.hold_time_label)
        self.hold_secs = QtWidgets.QDoubleSpinBox(self.rta_tab)
        self.hold_secs.setDecimals(1)
        self.hold_secs.setMinimum(0.5)
        self.hold_secs.setMaximum(30.0)
        self.hold_secs.setSingleStep(0.1)
        self.hold_secs.setProperty("value", 2.0)
        self.hold_secs.setObjectName("holdSecs")
        self.rta_controls_layout.addWidget(self.hold_secs)
        self.show_live = QtWidgets.QPushButton(self.rta_tab)
        self.show_live.setCheckable(True)
        self.show_live.setChecked(True)
        self.show_live.setObjectName("showLive")
        self.rta_controls_layout.addWidget(self.show_live)
        self.show_peak = QtWidgets.QPushButton(self.rta_tab)
        self.show_peak.setCheckable(True)
        self.show_peak.setObjectName("showPeak")
        self.rta_controls_layout.addWidget(self.show_peak)
        self.show_average = QtWidgets.QPushButton(self.rta_tab)
        self.show_average.setCheckable(True)
        self.show_average.setObjectName("showAverage")
        self.rta_controls_layout.addWidget(self.show_average)
        self.show_target = QtWidgets.QPushButton(self.rta_tab)
        self.show_target.setCheckable(True)
        self.show_target.setObjectName("showTarget")
        self.rta_controls_layout.addWidget(self.show_target)
        self.target_adjust_db = QtWidgets.QDoubleSpinBox(self.rta_tab)
        self.target_adjust_db.setDecimals(1)
        self.target_adjust_db.setMinimum(-150.0)
        self.target_adjust_db.setMaximum(150.0)
        self.target_adjust_db.setSingleStep(0.1)
        self.target_adjust_db.setObjectName("targetAdjust")
        self.rta_controls_layout.addWidget(self.target_adjust_db)
        self.smooth_rta = QtWidgets.QPushButton(self.rta_tab)
        self.smooth_rta.setCheckable(True)
        self.smooth_rta.setObjectName("smoothRta")
        self.rta_controls_layout.addWidget(self.smooth_rta)
        self.sg_window_length = QtWidgets.QSpinBox(self.rta_tab)
        self.sg_window_length.setMinimum(1)
        self.sg_window_length.setMaximum(201)
        self.sg_window_length.setSingleStep(2)
        self.sg_window_length.setProperty("value", 101)
        self.sg_window_length.setObjectName("sgWindowLength")
        self.sg_window_length.lineEdit().setReadOnly(True)
        self.sg_window_length.setToolTip('Higher values = smoother curves')
        self.rta_controls_layout.addWidget(self.sg_window_length)
        self.sg_poly_order = QtWidgets.QSpinBox(self.rta_tab)
        self.sg_poly_order.setMinimum(1)
        self.sg_poly_order.setMaximum(11)
        self.sg_poly_order.setProperty("value", 7)
        self.sg_poly_order.setObjectName("sgPolyOrder")
        self.sg_poly_order.setToolTip('Lower values = smoother curves')
        self.rta_controls_layout.addWidget(self.sg_poly_order)
        spacerItem5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.rta_controls_layout.addItem(spacerItem5)
        self.toggle_crosshairs = QtWidgets.QPushButton(self.rta_tab)
        self.toggle_crosshairs.setCheckable(True)
        self.toggle_crosshairs.setObjectName("toggleCrosshairs")
        self.rta_controls_layout.addWidget(self.toggle_crosshairs)
        self.export_frd = QtWidgets.QToolButton(self.rta_tab)
        self.export_frd.setObjectName("exportFRD")
        self.rta_controls_layout.addWidget(self.export_frd)
        self.parent_layout.addLayout(self.rta_controls_layout, 0, 0, 1, 1)
        _translate = QtCore.QCoreApplication.translate
        self.rta_view_label.setText(_translate("MainWindow", "View"))
        self.rta_view.setItemText(0, _translate("MainWindow", "avg"))
        self.rta_view.setItemText(1, _translate("MainWindow", "peak"))
        self.rta_view.setItemText(2, _translate("MainWindow", "psd"))
        self.hold_time_label.setText(_translate("MainWindow", "Hold Time:"))
        self.hold_secs.setToolTip(_translate("MainWindow", "Seconds of data to include in peak calculation"))
        self.hold_secs.setSuffix(_translate("MainWindow", " s"))
        self.show_live.setText(_translate("MainWindow", "Live"))
        self.show_peak.setText(_translate("MainWindow", "Peak"))
        self.show_average.setText(_translate("MainWindow", "Average"))
        self.show_target.setText(_translate("MainWindow", "Target"))
        self.target_adjust_db.setSuffix(_translate("MainWindow", " dB"))
        self.target_adjust_db.setToolTip('Adjusts the level of the target curve')
        self.smooth_rta.setText(_translate("MainWindow", "Smooth"))
        self.toggle_crosshairs.setText(_translate("MainWindow", "Move Crosshairs"))
        self.toggle_crosshairs.setShortcut(_translate("MainWindow", "Ctrl+T"))
        self.toggle_crosshairs.setToolTip('Press CTRL+T to toggle')
        self.export_frd.setText(_translate("MainWindow", "..."))
        self.export_frd.setIcon(qta.icon('fa5s.file-export'))
