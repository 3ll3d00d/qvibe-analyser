import logging

import numpy as np
import pyqtgraph as pg
from qtpy.QtWidgets import QMessageBox
from qtpy.QtCore import Qt

from common import format_pg_plotitem
from model.charts import VisibleChart, ChartEvent
from model.frd import ExportDialog
from model.preferences import RTA_TARGET
from model.signal import smooth_savgol, Analysis

logger = logging.getLogger('qvibe.rta')


class RTAEvent(ChartEvent):

    def __init__(self, chart, measurement_name, input, idx, preferences, budget_millis, view, visible):
        super().__init__(chart, measurement_name, input, idx, preferences, budget_millis)
        self.__view = view
        self.__visible = visible

    def process(self):
        super().process()
        self.output.set_view(self.__view, recalc=False)
        if self.input.shape[0] >= self.chart.min_nperseg and self.__visible:
            self.output.recalc()


class RTA(VisibleChart):

    def __init__(self, chart, prefs, fs_widget, resolution_widget, fps_widget, actual_fps_widget, show_average,
                 rta_view_widget, smooth_rta_widget, mag_min_widget, mag_max_widget, freq_min_widget, freq_max_widget,
                 show_live, show_peak, show_target, target_adjust_db, hold_secs, sg_window_length, sg_polyorder,
                 export_frd_button, colour_provider):
        self.__show_average = show_average.isChecked()
        self.__plots = {}
        self.__smooth = False
        self.__colour_provider = colour_provider
        super().__init__(prefs, fs_widget, resolution_widget, fps_widget, actual_fps_widget, False, coelesce=True,
                         cache_size=-1, cache_purger=self.__purge_cache)
        self.__peak_cache = {}
        self.__hold_secs = hold_secs.value()
        self.__show_peak = show_peak.isChecked()
        self.__show_live = show_live.isChecked()
        self.__target_data = None
        self.__target_adjustment_db = target_adjust_db.value()
        self.__show_target = show_target.isChecked()
        self.__show_target_toggle = show_target
        self.__target_adjust_db_widget = target_adjust_db
        target_adjust_db.setToolTip('Adjusts the level of the target curve')
        target_adjust_db.valueChanged.connect(self.__adjust_target_level)
        self.__sg_wl = sg_window_length.value()
        self.__sg_wl_widget = sg_window_length
        self.__sg_wl_widget.lineEdit().setReadOnly(True)
        self.__sg_poly = None
        self.__on_sg_poly(sg_polyorder.value())
        sg_window_length.setToolTip('Higher values = smoother curves')
        sg_polyorder.setToolTip('Lower values = smoother curves')
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
        self.__on_rta_view_change(rta_view_widget.currentText())
        rta_view_widget.currentTextChanged.connect(self.__on_rta_view_change)
        self.__on_rta_smooth_change(smooth_rta_widget.isChecked())
        smooth_rta_widget.toggled[bool].connect(self.__on_rta_smooth_change)
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
        show_peak.toggled[bool].connect(self.__on_show_peak_change)
        show_live.toggled[bool].connect(self.__on_show_live_change)
        show_average.toggled[bool].connect(self.__on_show_average_change)
        show_target.toggled[bool].connect(self.__on_show_target_change)
        hold_secs.valueChanged.connect(self.__set_max_cache_age)
        # S-G filter params
        sg_window_length.valueChanged['int'].connect(self.__on_sg_window_length)
        sg_polyorder.valueChanged['int'].connect(self.__on_sg_poly)
        self.reload_target()
        # export
        export_frd_button.clicked.connect(self.__export_frd)

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
            self.__sg_wl_widget.setValue(wl+1)
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
        self.__sg_wl_widget.setMinimum(wl_min)
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

    def __adjust_target_level(self, adjustment):
        ''' Adjusts the target level. '''
        self.__target_adjustment_db = adjustment
        self.__render_target()

    def reload_target(self):
        '''
        Loads the target from preferences.
        '''
        if self.preferences.has(RTA_TARGET) is True:
            self.__show_target_toggle.setEnabled(True)
            self.__target_adjust_db_widget.setEnabled(True)
            self.__target_adjust_db_widget.setValue(0)
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
            self.__target_adjust_db_widget.setValue(0)
            self.__target_adjust_db_widget.setEnabled(False)
            self.__target_data = None
        self.__render_target()

    def make_event(self, measurement_name, data, idx):
        '''
        Creates an RTAEvent to pass to the analysis thread.
        :param measurement_name: the measurement the data came from.
        :param data: the data to analyse.
        :param idx: the index of the data set.
        '''
        if len(data) <= self.min_nperseg:
            d = data
        else:
            d = data[-self.min_nperseg:]
        return RTAEvent(self, measurement_name, d, idx, self.preferences, self.budget_millis,
                        self.__active_view, self.visible)

    def reset_chart(self):
        '''
        Removes all curves.
        '''
        for c in self.__plots.values():
            self.__chart.removeItem(c)
        self.__plots = {}

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
            if 'Target' in self.__plots:
                self.__remove_named_plot('Target')
        elif self.__target_data is not None and self.__show_target is True:
            pen_args = {'style': Qt.SolidLine}
            y_db = self.__target_data.y + self.__target_adjustment_db
            self.__render_or_update(pen_args, 'Target', self.__target_data.x, y_db)

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
        self.__legend.removeItem(name)

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
            self.__render_or_update(pen_args, plot_name, x_data, y)
        elif plot_name in self.__plots:
            self.__remove_named_plot(plot_name)

    def __render_or_update(self, pen_args, plot_name, x_data, y):
        '''
        actually updates (or creates) the plot.
        :param pen_args: the pen args.
        :param plot_name: the plot name.
        :param x_data: x.
        :param y: y.
        '''
        if plot_name in self.__plots:
            self.__plots[plot_name].setData(x_data, y)
        else:
            if self.__legend is None:
                self.__legend = self.__chart.addLegend(offset=(-15, -15))
            pen = pg.mkPen(color=self.__colour_provider.get_colour(plot_name), width=2, **pen_args)
            self.__plots[plot_name] = self.__chart.plot(x_data, y, pen=pen, name=plot_name)
