import logging

import numpy as np
import pyqtgraph as pg
from qtpy.QtCore import Qt

from common import format_pg_plotitem
from model.charts import VisibleChart, ChartEvent
from model.preferences import SNAPSHOT_x
from model.signal import smooth_savgol, TriAxisSignal

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

    def __init__(self, chart, prefs, fs_widget, resolution_widget, fps_widget, actual_fps_widget, rta_average_widget,
                 rta_view_widget, smooth_rta_widget, mag_min_widget, mag_max_widget, freq_min_widget, freq_max_widget,
                 snapshot_buttons, snapshot_actions, take_snapshot_button, delete_snapshot_button,
                 snapshot_slot_selector, peak_hold_selector, peak_secs, colour_provider):
        self.__average = None
        self.__plots = {}
        self.__colour_provider = colour_provider
        super().__init__(prefs, fs_widget, resolution_widget, fps_widget, actual_fps_widget, False, coelesce=True,
                         cache_size=-1, cache_purger=self.__purge_cache)
        self.__peak_cache = {}
        self.__peak_secs = peak_secs.value()
        self.__show_peak = peak_hold_selector.isChecked()
        self.__loaded_snapshots = {
            0: None,
            1: None,
            2: None
        }
        self.__frame = 0
        self.__time = -1
        self.__update_rate = None
        self.__active_view = None
        self.__smooth = False
        self.__chart = chart
        self.__average_samples = -1
        # wire the analysis to the view controls
        self.__on_average_change(rta_average_widget.currentText())
        self.__mag_min = lambda: mag_min_widget.value()
        self.__mag_max = lambda: mag_max_widget.value()
        self.__freq_min = lambda: freq_min_widget.value()
        self.__freq_max = lambda: freq_max_widget.value()
        rta_average_widget.currentTextChanged.connect(self.__on_average_change)
        self.__on_rta_view_change(rta_view_widget.currentText())
        rta_view_widget.currentTextChanged.connect(self.__on_rta_view_change)
        self.__on_rta_smooth_change(Qt.Checked if smooth_rta_widget.isChecked() else Qt.Unchecked)
        smooth_rta_widget.stateChanged.connect(self.__on_rta_smooth_change)
        self.__legend = None
        format_pg_plotitem(self.__chart.getPlotItem(),
                           (0, self.fs / 2),
                           (0, 150),
                           x_range=(self.__freq_min(), self.__freq_max()),
                           y_range=(self.__mag_min(), self.__mag_max()))
        # link limit controls to the chart
        mag_min_widget.valueChanged['int'].connect(self.__on_mag_limit_change)
        mag_max_widget.valueChanged['int'].connect(self.__on_mag_limit_change)
        freq_min_widget.valueChanged['int'].connect(self.__on_freq_limit_change)
        freq_max_widget.valueChanged['int'].connect(self.__on_freq_limit_change)
        # allow snapshots to be toggled on and off & set the initial state
        for idx, btn in enumerate(snapshot_buttons):
            action = lambda s, i=idx: self.__toggle_snapshot(i, s)
            btn.toggled[bool].connect(action)
            snapshot_actions[idx].toggled[bool].connect(action)
            has = self.preferences.has(SNAPSHOT_x % idx)
            if has is True:
                self.__enable_snapshot_button(snapshot_buttons[idx], snapshot_actions[idx], self.__load_snapshot(idx))
            else:
                self.__disable_snapshot_button(snapshot_buttons[idx], snapshot_actions[idx])
        # peak hold wiring
        peak_hold_selector.stateChanged.connect(self.__on_peak_hold_change)
        peak_secs.valueChanged['int'].connect(self.__set_peak_cache_size)
        # create snapshot

        def save_snapshot():
            idx = int(snapshot_slot_selector.currentText()) - 1
            self.__save_snapshot(idx, snapshot_buttons[idx], snapshot_actions[idx], delete_snapshot_button)

        take_snapshot_button.clicked.connect(save_snapshot)

        # delete snapshot
        def enable_delete_snap(txt):
            delete_snapshot_button.setEnabled(self.preferences.has(SNAPSHOT_x % (int(txt) - 1)))

        snapshot_slot_selector.currentTextChanged['QString'].connect(enable_delete_snap)

        def delete_snapshot():
            idx = int(snapshot_slot_selector.currentText()) - 1
            self.preferences.clear(SNAPSHOT_x % idx)
            self.__disable_snapshot_button(snapshot_buttons[idx], snapshot_actions[idx])
            delete_snapshot_button.setEnabled(False)
            self.__show_snapshots()

        delete_snapshot_button.clicked.connect(delete_snapshot)

    def __toggle_snapshot(self, idx, state):
        '''
        Toggles the display state of the given snapshot.
        :param idx: the index.
        :param state: true if it should be shown.
        '''
        self.__loaded_snapshots[idx] = self.__load_snapshot(idx) if state is True else None
        self.__show_snapshots()

    def __load_snapshot(self, idx):
        stored = self.preferences.get(SNAPSHOT_x % idx)
        loaded = {
            k: TriAxisSignal.decode(self.preferences, self.resolution_shift, v, self.analysis_mode, self.__active_view)
            for k, v in stored.items()
        }
        return {k: v for k, v in loaded.items() if v is not None}

    def __save_snapshot(self, snapshot_id, snapshot_button, snapshot_action, delete_snapshot_button):
        '''
        Saves the current data as a snapshot.
        :param snapshot_id: the snapshot id.
        :param snapshot_button: the button.
        :param delete_snapshot_button: the delete button.
        '''
        data = {name: self.cached_data(name)[-1].encode() for name in self.cached_measurement_names()}
        self.preferences.set(SNAPSHOT_x % snapshot_id, data)
        delete_snapshot_button.setEnabled(True)
        self.__enable_snapshot_button(snapshot_button, snapshot_action, data)
        self.__show_snapshots()

    @staticmethod
    def __disable_snapshot_button(snapshot_button, snapshot_action):
        '''
        Disables the button and removes the tooltip.
        :param snapshot_button: the button.
        :param snapshot_action: the action.
        '''
        snapshot_button.setEnabled(False)
        snapshot_action.setEnabled(False)
        snapshot_button.setToolTip(None)

    @staticmethod
    def __enable_snapshot_button(snapshot_button, snapshot_action, data):
        '''
        Enables the button and adds a tooltip.
        :param snapshot_button: the button.
        :param data: the snapshot data.
        '''
        snapshot_button.setEnabled(True)
        snapshot_action.setEnabled(True)
        tip = '\n'.join(data.keys())
        snapshot_button.setToolTip(tip)

    def __set_peak_cache_size(self, seconds):
        '''
        Sets the max age of the cache in seconds.
        :param seconds: the max age of a cache entry.
        '''
        self.__peak_secs = seconds
        self.for_each_cache(self.__purge_cache)

    def __on_peak_hold_change(self, checked):
        '''
        shows or hides the peak curves.
        :param checked: if checked then show the curves otherwise hide.
        '''
        self.__show_peak = Qt.Checked == checked
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
        self.__smooth = state == Qt.Checked
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

    def __on_average_change(self, average):
        '''
        Changes the amount of data to feed into the analysis.
        :param average: the time in seconds to feed into the analysis.
        '''
        self.__average = average
        if self.__average == 'Forever':
            self.__average_samples = -1
        else:
            self.__average_samples = self.min_nperseg * int(self.__average[0:-1])
        logger.info(f"Average mode updated to {average}, requires {self.__average_samples} samples")

    def on_min_nperseg_change(self):
        if self.__average is not None:
            self.__on_average_change(self.__average)

    def make_event(self, measurement_name, data, idx):
        '''
        Creates an RTAEvent to pass to the analysis thread.
        :param measurement_name: the measurement the data came from.
        :param data: the data to analyse.
        :param idx: the index of the data set.
        '''
        if self.__average_samples == -1 or len(data) <= self.__average_samples:
            d = data
        else:
            d = data[-self.__average_samples:]
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
            self.__display_triaxis_signal(data[-1])
            self.render_peak(data, 'x')
            self.render_peak(data, 'y')
            self.render_peak(data, 'z')
            self.render_peak(data, 'sum')

    def __display_triaxis_signal(self, signal, plot_name_prefix=''):
        '''
        ensures the correct analysis curves for the signal are displayed on screen.
        :param signal: the TriAxisSignal.
        :param plot_name_prefix: extension to signal name for creating a plot name.
        '''
        if signal.view != self.__active_view:
            logger.info(f"Updating active view from {signal.view} to {self.__active_view} at {signal.idx}")
            signal.set_view(self.__active_view)
        if signal.has_data(self.__active_view) is False:
            signal.recalc()
        self.render_signal(signal, 'x', plot_name_prefix=plot_name_prefix)
        self.render_signal(signal, 'y', plot_name_prefix=plot_name_prefix)
        self.render_signal(signal, 'z', plot_name_prefix=plot_name_prefix)
        self.render_signal(signal, 'sum', plot_name_prefix=plot_name_prefix)

    def __show_snapshots(self):
        '''
        Ensures the selected snapshots are displayed on the chart.
        '''
        for id, snapshot in self.__loaded_snapshots.items():
            if snapshot is not None:
                for signal in snapshot.values():
                    self.__display_triaxis_signal(signal, plot_name_prefix=f"snapshot_{id}:")
            else:
                to_remove = {name: plot for name, plot in self.__plots.items() if name.startswith(f"snapshot_{id}:")}
                for name, plot in to_remove.items():
                    self.__remove_named_plot(name)

    def __purge_cache(self, cache):
        '''
        Purges the cache of data older than peak_secs.
        :param cache: the cache (a deque)
        '''
        while len(cache) > 1:
            latest = cache[-1].time[-1]
            if (latest - cache[0].time[-1]) >= (self.__peak_secs * 1000.0):
                cache.popleft()
            else:
                break

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
                data_ = [getattr(d, axis).get_analysis(self.__active_view).y for d in data]
                y_data = np.maximum.reduce(data_)
                x_data = has_data.x
            pen_args = {'style': Qt.DashLine}
        self.__manage_plot_item(f"{sig.measurement_name}:{sig.axis}:peak", data[-1].idx, sig.measurement_name, sig.axis,
                                x_data, y_data, pen_args)

    def render_signal(self, data, axis, plot_name_prefix=''):
        '''
        Converts a signal into a renderable plot item.
        :param data: the cached data.
        :param axis: the axis to display.
        :param plot_name_prefix: optional plot name prefix.
        '''
        y_data = None
        x_data = None
        sig = getattr(data, axis)
        view = sig.get_analysis(self.__active_view)
        if view is not None:
            y_data = view.y
            x_data = view.x
        pen_args = {'style': Qt.SolidLine}
        plot_name = f"{plot_name_prefix}{sig.measurement_name}:{sig.axis}"
        self.__manage_plot_item(plot_name, data.idx, sig.measurement_name, sig.axis, x_data, y_data, pen_args)

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
            logger.debug(f"Tick {idx} {np.min(y_data):.4f} - {np.max(y_data):.4f} - {len(y_data)} ")
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
            y = smooth_savgol(x_data, y_data)[1] if self.__smooth is True else y_data
            if plot_name in self.__plots:
                self.__plots[plot_name].setData(x_data, y)
            else:
                if self.__legend is None:
                    self.__legend = self.__chart.addLegend(offset=(-15, -15))
                pen = pg.mkPen(color=self.__colour_provider.get_colour(plot_name), width=2, **pen_args)
                self.__plots[plot_name] = self.__chart.plot(x_data, y, pen=pen, name=plot_name)
        elif plot_name in self.__plots:
            self.__remove_named_plot(plot_name)
