import gzip
import json
import logging
import os
import sys
import time

from model.charts import ColourProvider
from model.measurements import MeasurementStore
from model.rta import RTA
from model.save import SaveChartDialog, SaveWavDialog
from model.spectrogram import Spectrogram
from model.vibration import Vibration

os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt5'
os.environ['QT_API'] = 'pyqt5'
# if sys.platform == 'win32' and getattr(sys, '_MEIPASS', False):
    # Workaround for PyInstaller being unable to find Qt5Core.dll on PATH.
    # See https://github.com/pyinstaller/pyinstaller/issues/4293
    # os.environ['PATH'] = sys._MEIPASS + os.pathsep + os.environ['PATH']

import pyqtgraph as pg
import qtawesome as qta
import numpy as np

from qtpy import QtCore
from qtpy.QtCore import QTimer, QSettings, QThreadPool, QUrl, QTime, QRunnable, QThread
from qtpy.QtGui import QIcon, QFont, QDesktopServices
from qtpy.QtWidgets import QMainWindow, QApplication, QErrorMessage, QMessageBox, QFileDialog
from common import block_signals, ReactorRunner, np_to_str, parse_file, bump_tick_levels
from model.preferences import SYSTEM_CHECK_FOR_BETA_UPDATES, SYSTEM_CHECK_FOR_UPDATES, SCREEN_GEOMETRY, \
    SCREEN_WINDOW_STATE, PreferencesDialog, Preferences, BUFFER_SIZE, ANALYSIS_RESOLUTION, CHART_MAG_MIN, \
    CHART_MAG_MAX, keep_range, CHART_FREQ_MIN, CHART_FREQ_MAX, SNAPSHOT_GROUP
from model.checker import VersionChecker, ReleaseNotesDialog
from model.log import RollingLogger, to_millis
from model.preferences import RECORDER_TARGET_FS, RECORDER_TARGET_SAMPLES_PER_BATCH, RECORDER_TARGET_ACCEL_ENABLED, \
    RECORDER_TARGET_ACCEL_SENS, RECORDER_TARGET_GYRO_ENABLED, RECORDER_TARGET_GYRO_SENS, RECORDER_SAVED_IPS
from ui.app import Ui_MainWindow

from model.recorders import RecorderStore, RecorderConfig

logger = logging.getLogger('qvibe')


class QVibe(QMainWindow, Ui_MainWindow):
    snapshot_saved = QtCore.Signal(int, str, object)

    def __init__(self, app, prefs, parent=None):
        super(QVibe, self).__init__(parent)
        self.logger = logging.getLogger('qvibe')
        self.app = app
        self.preferences = prefs
        # basic setup and version checking
        if getattr(sys, 'frozen', False):
            self.__style_path_root = sys._MEIPASS
        else:
            self.__style_path_root = os.path.dirname(__file__)
        self.__version = '0.0.0-alpha.1'
        v_path = os.path.abspath(os.path.join(self.__style_path_root, 'VERSION'))
        try:
            with open(v_path) as version_file:
                self.__version = version_file.read().strip()
        except:
            logger.exception(f"Unable to read {v_path}")
        global_thread_pool = QThreadPool.globalInstance()
        global_thread_pool.setMaxThreadCount(QThread.idealThreadCount() + 4)
        if self.preferences.get(SYSTEM_CHECK_FOR_UPDATES):
            global_thread_pool.start(VersionChecker(self.preferences.get(SYSTEM_CHECK_FOR_BETA_UPDATES),
                                          self.__alert_on_old_version,
                                          self.__alert_on_version_check_fail,
                                          self.__version))
        # UI initialisation
        self.setupUi(self)
        # run a twisted reactor as its responsiveness is embarrassingly better than QTcpSocket
        from twisted.internet import reactor
        self.__reactor = reactor
        runner = ReactorRunner(self.__reactor)
        global_thread_pool.reserveThread()
        global_thread_pool.start(runner)
        self.app.aboutToQuit.connect(runner.stop)
        # core domain stores
        self.__timer = None
        self.__start_time = None
        self.__target_config = self.__load_config()
        self.__display_target_config()
        self.__measurement_store = MeasurementStore(self.measurementLayout, self.measurementBox, self.bufferSize,
                                                    self.preferences, self.__target_config)
        self.__measurement_store.signals.data_changed.connect(self.__display_measurement)
        self.__measurement_store.signals.measurement_added.connect(self.__display_measurement)
        self.__measurement_store.signals.visibility_changed.connect(self.__set_visible_measurements)
        self.__recorder_store = RecorderStore(self.__target_config,
                                              self.recordersLayout,
                                              self.centralwidget,
                                              self.__reactor,
                                              self.__measurement_store)
        self.__recorder_store.signals.on_status_change.connect(self.__handle_recorder_connect_event)
        target_resolution = f"{self.preferences.get(ANALYSIS_RESOLUTION)} Hz"
        self.resolutionHz.setCurrentText(target_resolution)
        # menus
        self.log_viewer = RollingLogger(self.preferences, parent=self)
        self.actionShow_Logs.triggered.connect(self.log_viewer.show_logs)
        self.action_Preferences.triggered.connect(self.show_preferences)
        self.actionSave_Chart.triggered.connect(self.export_chart)
        self.actionExport_Wav.triggered.connect(self.export_wav)
        # buffer
        self.bufferSize.setValue(self.preferences.get(BUFFER_SIZE))
        # magnitude range
        self.magMin.setValue(self.preferences.get(CHART_MAG_MIN))
        self.magMax.setValue(self.preferences.get(CHART_MAG_MAX))

        def keep_min_mag_range():
            keep_range(self.magMin, self.magMax, 20)

        self.magMin.valueChanged['int'].connect(lambda v: keep_min_mag_range())
        self.magMax.valueChanged['int'].connect(lambda v: keep_min_mag_range())
        # frequency range
        self.freqMin.setValue(self.preferences.get(CHART_FREQ_MIN))
        self.freqMax.setValue(self.preferences.get(CHART_FREQ_MAX))

        def keep_min_freq_range():
            keep_range(self.freqMin, self.freqMax, 20)

        self.freqMin.valueChanged['int'].connect(lambda v: keep_min_freq_range())
        self.freqMax.valueChanged['int'].connect(lambda v: keep_min_freq_range())

        # charts
        colour_provider = ColourProvider()
        self.__analysers = {
            0: Vibration(self.liveVibrationChart, self.preferences, self.targetSampleRate, self.fps, self.actualFPS,
                         self.resolutionHz, self.targetAccelSens, self.bufferSize, self.vibrationAnalysis,
                         self.leftMarker, self.rightMarker, self.timeRange, self.zoomInButton, self.zoomOutButton,
                         self.findPeaksButton, colour_provider),
            1: RTA(self.rtaLayout, self.rtaTab, self.rtaChart, self.preferences, self.targetSampleRate,
                   self.resolutionHz, self.fps, self.actualFPS, self.magMin, self.magMax, self.freqMin, self.freqMax,
                   self.refCurve, self.showValueFor, self.__measurement_store.signals, colour_provider),
            2: Spectrogram(self.spectrogramView, self.preferences, self.targetSampleRate, self.fps, self.actualFPS,
                           self.resolutionHz, self.bufferSize, self.magMin, self.magMax, self.freqMin, self.freqMax,
                           self.visibleCurves, self.__measurement_store),
        }
        self.__start_analysers()
        self.set_visible_chart(self.chartTabs.currentIndex())

        self.applyTargetButton.setIcon(qta.icon('fa5s.check', color='green'))
        self.resetTargetButton.setIcon(qta.icon('fa5s.undo'))
        self.visibleCurves.selectAll()
        # load saved recorders
        saved_recorders = self.preferences.get(RECORDER_SAVED_IPS)
        warn_on_no_recorders = False
        if saved_recorders is not None:
            self.__recorder_store.load(saved_recorders.split('|'))
        else:
            warn_on_no_recorders = True
        # show preferences if we have no IPs
        if warn_on_no_recorders is True:
            result = QMessageBox.question(self,
                                          'No Recorders',
                                          f"No qvibe-recorders have been added. \n\nUse the preferences screen to add then.\n\nWould you like to add one now?",
                                          QMessageBox.Yes | QMessageBox.No,
                                          QMessageBox.No)
            if result == QMessageBox.Yes:
                self.show_preferences()
        self.saveSnapshotButton.setIcon(qta.icon('fa5s.save'))
        self.saveSnapshotButton.clicked.connect(self.__save_snapshot)
        self.zoomInButton.setIcon(qta.icon('fa5s.compress-arrows-alt'))
        self.zoomOutButton.setIcon(qta.icon('fa5s.expand-arrows-alt'))
        self.loadMeasurementButton.setIcon(qta.icon('fa5s.folder-open'))
        self.actionSave_Signal.triggered.connect(self.__save_signal)
        self.actionLoad_Signal.triggered.connect(self.__load_signal)
        self.loadMeasurementButton.clicked.connect(self.__load_signal)
        self.connectAllButton.clicked.connect(self.__recorder_store.connect)
        self.disconnectAllButton.clicked.connect(self.__recorder_store.disconnect)
        self.snapshot_saved.connect(self.__add_snapshot)
        self.__measurement_store.load_snapshots()

    def __set_visible_measurements(self, measurement):
        '''
        Propagates the visible measurements to the charts.
        '''
        keys = self.__measurement_store.get_visible_measurements()
        for c in self.__analysers.values():
            c.set_visible_measurements(keys)

    def __display_measurement(self, measurement):
        '''
        Updates the charts with the data from the current measurement.
        :param measurement: the measurement.
        '''
        if measurement.visible is True:
            if measurement.latest_data is not None:
                for c in self.__analysers.values():
                    # TODO must unwrap
                    c.accept(measurement.key, measurement.data, measurement.idx)
        else:
            logger.info(f"Hiding {measurement}")

    def __save_snapshot(self):
        ''' Triggers the snapshot save job. '''
        runner = SnapshotSaver(int(self.snapSlotSelector.currentText()), self.preferences,
                               lambda: self.__capture_snap(convert=False), self.__measurement_store,
                               self.snapshot_saved)
        QThreadPool.globalInstance().start(runner)

    def __add_snapshot(self, id, ip, data):
        self.__measurement_store.add_snapshot(id, ip, data)

    def __save_signal(self):
        ''' Saves the current data to a file. '''
        dat = self.__capture_snap()
        if len(dat.keys()) > 0:
            file_name = QFileDialog(self).getSaveFileName(self, 'Save Signal', f"signal.qvibe", "QVibe Signals (*.qvibe)")
            file_name = str(file_name[0]).strip()
            if len(file_name) > 0:
                with gzip.open(file_name, 'wb+') as outfile:
                    outfile.write(json.dumps(dat).encode('utf-8'))
                self.statusbar.showMessage(f"Saved to {file_name}")
        else:
            msg_box = QMessageBox()
            msg_box.setText('No data has been recorded')
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle('Nothing to Save')
            msg_box.exec()

    def __capture_snap(self, convert=True):
        ''' Snaps the available data into for saving. '''
        return {k: np_to_str(v) if convert is True else v for k, v in self.__measurement_store.snap_rta().items()}

    def __load_signal(self):
        '''
        Loads a new signal (replacing any current data if required).
        '''
        parsers = {'qvibe': self.__parse_qvibe}
        name, data = parse_file('Signal (*.qvibe)', 'Load Signal', parsers)
        if name is not None:
            self.statusbar.showMessage(f"Loaded {name}")
            for d in data:
                self.__measurement_store.append(name, *d)

    @staticmethod
    def __parse_qvibe(file_name):
        '''
        Parses a qvibe file.
        :param file_name: the file name.
        :return: the measurements to load
        '''
        vals = []
        with gzip.open(file_name, 'r') as infile:
            dat = json.loads(infile.read().decode('utf-8'))
            if dat is not None and len(dat.keys()) > 0:
                for ip, data_txt in dat.items():
                    import io
                    vals.append([ip, np.loadtxt(io.StringIO(data_txt), dtype=np.float64, ndmin=2)])
                return os.path.basename(file_name)[0:-6], vals
        return None, None

    def reset_recording(self):
        '''
        Wipes all data from the recorders and the charts.
        '''
        self.__measurement_store.remove_rta()
        self.__recorder_store.reset()
        for c in self.__analysers.values():
            c.reset()

    def __start_analysers(self):
        for a in self.__analysers.values():
            logger.info(f"Starting processor for {a.__class__.__name__}")
            QThreadPool.globalInstance().reserveThread()
            a.processor.start()

            def stop_processor():
                logger.info(f"Stopping processor for {a.__class__.__name__}")
                a.processor.stop()
                QThreadPool.globalInstance().releaseThread()
                logger.info(f"Stopped processor for {a.__class__.__name__}")

            self.app.aboutToQuit.connect(stop_processor)
            logger.info(f"Started processor for {a.__class__.__name__}")

    def __handle_recorder_connect_event(self, ip, connected):
        ''' reacts to connection status changes.'''
        any_connected = self.__recorder_store.any_connected()
        self.fps.setEnabled(not any_connected)
        self.bufferSize.setEnabled(not any_connected)
        if any_connected is True:
            self.__on_start_recording()
        else:
            self.__on_stop_recording()

    def __on_start_recording(self):
        '''
        Starts the data collection timer.
        '''
        if self.__timer is None:
            self.__timer = QTimer()
            self.__timer.timeout.connect(self.__collect_signals)
        logger.info(f"Starting data collection timer at {self.fps.value()} fps")
        self.__start_time = time.time() * 1000
        self.__timer.start(1000.0 / self.fps.value())
        self.resetButton.setEnabled(False)

    def __on_stop_recording(self):
        if self.__timer is not None:
            logger.info('Stopping data collection timer')
            self.__timer.stop()
            self.resetButton.setEnabled(True)

    def __collect_signals(self):
        ''' collects the latest signal and pushes it into the analysers. '''
        elapsed = round((time.time() * 1000) - self.__start_time)
        new_time = QTime(0, 0, 0, 0).addMSecs(elapsed)
        self.elapsedTime.setTime(new_time)
        for recorder_name, signal, idx, errored in self.__recorder_store.snap():
            if len(signal) > 0:
                if errored is True:
                    msg_box = QMessageBox()
                    msg_box.setText(f"{recorder_name} has overflowed, data will be unreliable \n\n If this occurs repeatedly, try increasing batch size or reducing sample rate via the Sensor Config panel")
                    msg_box.setIcon(QMessageBox.Critical)
                    msg_box.setWindowTitle('Overflow')
                    msg_box.exec()
                self.__measurement_store.append('rta', recorder_name, signal, idx)

    def update_target(self):
        ''' updates the current target config from the UI values. '''
        self.__target_config.fs = self.targetSampleRate.value()
        self.__target_config.samples_per_batch = self.targetBatchSize.value()
        self.__target_config.accelerometer_enabled = self.targetAccelEnabled.isChecked()
        self.__target_config.accelerometer_sens = int(self.targetAccelSens.currentText())
        self.__target_config.gyro_enabled = self.targetGyroEnabled.isChecked()
        self.__target_config.gyro_sens = int(self.targetGyroSens.currentText())
        self.freqMax.setMaximum(int(self.__target_config.fs/2))

    def __load_config(self):
        ''' loads a config object from the preferences store '''
        config = RecorderConfig()
        config.fs = self.preferences.get(RECORDER_TARGET_FS)
        config.samples_per_batch = self.preferences.get(RECORDER_TARGET_SAMPLES_PER_BATCH)
        config.accelerometer_enabled = self.preferences.get(RECORDER_TARGET_ACCEL_ENABLED)
        config.accelerometer_sens = self.preferences.get(RECORDER_TARGET_ACCEL_SENS)
        config.gyro_enabled = self.preferences.get(RECORDER_TARGET_GYRO_ENABLED)
        config.gyro_sens = self.preferences.get(RECORDER_TARGET_GYRO_SENS)
        return config

    def __display_target_config(self):
        ''' updates the displayed target config '''
        with block_signals(self.targetSampleRate):
            self.targetSampleRate.setValue(self.__target_config.fs)
        with block_signals(self.targetBatchSize):
            self.targetBatchSize.setValue(self.__target_config.samples_per_batch)
        with block_signals(self.targetAccelEnabled):
            self.targetAccelEnabled.setChecked(self.__target_config.accelerometer_enabled)
        with block_signals(self.targetAccelSens):
            self.targetAccelSens.setCurrentText(str(self.__target_config.accelerometer_sens))
        with block_signals(self.targetGyroEnabled):
            self.targetGyroEnabled.setChecked(self.__target_config.gyro_enabled)
        with block_signals(self.targetGyroSens):
            self.targetGyroSens.setCurrentText(str(self.__target_config.gyro_sens))

    def reset_target(self):
        ''' resets the target config from preferences. '''
        self.__target_config = self.__load_config()
        self.__display_target_config()

    def apply_target(self):
        ''' saves the target config to the preferences. '''
        self.preferences.set(RECORDER_TARGET_FS, self.__target_config.fs)
        self.preferences.set(RECORDER_TARGET_SAMPLES_PER_BATCH, self.__target_config.samples_per_batch)
        self.preferences.set(RECORDER_TARGET_ACCEL_ENABLED, self.__target_config.accelerometer_enabled)
        self.preferences.set(RECORDER_TARGET_ACCEL_SENS, self.__target_config.accelerometer_sens)
        self.preferences.set(RECORDER_TARGET_GYRO_ENABLED, self.__target_config.gyro_enabled)
        self.preferences.set(RECORDER_TARGET_GYRO_SENS, self.__target_config.gyro_sens)
        self.__recorder_store.target_config = self.__target_config
        self.__measurement_store.target_config = self.__target_config

    def set_buffer_size(self, val):
        self.preferences.set(BUFFER_SIZE, val)

    def set_visible_chart(self, idx):
        for c_idx, c in self.__analysers.items():
            c.visible = (idx == c_idx)

    def set_visible_curves(self):
        '''
        Propagates the visible axes to the charts.
        '''
        visible = [c.text() for c in self.visibleCurves.selectedItems()]
        for c in self.__analysers.values():
            c.set_visible_axes(visible)

    def export_chart(self):
        '''
        Saves the currently selected chart to a file.
        '''
        idx = self.chartTabs.currentIndex()
        chart = None
        if idx == 0:
            chart = self.liveVibrationChart
        elif idx == 1:
            chart = self.rtaChart
        elif idx == 2:
            chart = self.spectrogramView
        if chart is not None:
            dialog = SaveChartDialog(self, self.__analysers[idx].__class__.__name__, chart, self.statusbar)
            dialog.exec()

    def export_wav(self):
        ''' Saves data from a recorder to a file. '''
        if len(self.__measurement_store) > 0:
            dialog = SaveWavDialog(self,
                                   self.preferences,
                                   self.__measurement_store,
                                   self.targetSampleRate.value(),
                                   int(self.targetAccelSens.currentText()),
                                   self.statusbar)
            dialog.exec()

    def show_release_notes(self):
        ''' Shows the release notes '''
        QThreadPool.globalInstance().start(VersionChecker(self.preferences.get(SYSTEM_CHECK_FOR_BETA_UPDATES),
                                                          self.__alert_on_old_version,
                                                          self.__alert_on_version_check_fail,
                                                          self.__version,
                                                          signal_anyway=True))

    @staticmethod
    def show_help():
        ''' Opens the user guide in a browser '''
        QDesktopServices.openUrl(QUrl('https://qvibe.readthedocs.io/en/latest'))

    @staticmethod
    def __alert_on_version_check_fail(message):
        '''
        Displays an alert if the version check fails.
        :param message: the message.
        '''
        msg_box = QMessageBox()
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle('Unable to Complete Version Check')
        msg_box.exec()

    def __alert_on_old_version(self, versions, issues):
        ''' Presents a dialog if there is a new version available. '''
        ReleaseNotesDialog(self, versions, issues).exec()

    def setupUi(self, main_window):
        super().setupUi(self)
        geometry = self.preferences.get(SCREEN_GEOMETRY)
        if geometry is not None:
            self.restoreGeometry(geometry)
        else:
            screen_geometry = self.app.desktop().availableGeometry()
            if screen_geometry.height() < 800:
                self.showMaximized()
        window_state = self.preferences.get(SCREEN_WINDOW_STATE)
        if window_state is not None:
            self.restoreState(window_state)

    def closeEvent(self, *args, **kwargs):
        '''
        Saves the window state on close.
        :param args:
        :param kwargs:
        '''
        self.preferences.set(SCREEN_GEOMETRY, self.saveGeometry())
        self.preferences.set(SCREEN_WINDOW_STATE, self.saveState())
        super().closeEvent(*args, **kwargs)
        self.app.closeAllWindows()

    def show_preferences(self):
        '''
        Shows the preferences dialog.
        '''
        PreferencesDialog(self.preferences, self.__style_path_root, self.__recorder_store, self.__analysers[2], parent=self).exec()
        self.__analysers[1].reload_target()

    def show_about(self):
        msg_box = QMessageBox()
        msg_box.setText(
            f"<a href='https://github.com/3ll3d00d/qvibe-analyser'>QVibe Analyser</a> v{self.__version} by 3ll3d00d")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle('About')
        msg_box.exec()


class SnapshotSaver(QRunnable):

    def __init__(self, id, preferences, capturer, store, signal):
        super().__init__()
        self.__id = id
        self.__preferences = preferences
        self.__capturer = capturer
        self.__store = store
        self.__signal = signal

    def run(self):
        '''
        Saves the snapshot to preferences.
        '''
        start = time.time()
        dat = self.__capturer()
        logger.info(f"Captured in {to_millis(start, time.time())}ms")
        prefs = []
        if len(dat.keys()) > 0:
            for ip, v in dat.items():
                prefs.append(SetPreference(self.__preferences, f"{SNAPSHOT_GROUP}/{self.__id}/{ip}", v))
                self.__signal.emit(self.__id, ip, v)
        for p in prefs:
            QThreadPool.globalInstance().start(p, priority=-1)
        logger.info(f"Saved snapshot in {to_millis(start, time.time())}ms")


class SetPreference(QRunnable):
    def __init__(self, prefs, key, val):
        super().__init__()
        self.prefs = prefs
        self.key = key
        self.val = val

    def run(self):
        start = time.time()
        self.prefs.set(self.key, np_to_str(self.val))
        logger.info(f"Set preference in {to_millis(start, time.time())}ms")


def make_app():
    app = QApplication(sys.argv)
    if getattr(sys, 'frozen', False):
        icon_path = os.path.join(sys._MEIPASS, 'Icon.ico')
    else:
        icon_path = os.path.abspath(os.path.join(os.path.dirname('__file__'), '../icons/Icon.ico'))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    return app, Preferences(QSettings("3ll3d00d", "qvibe-analyser"))


if __name__ == '__main__':
    app, prefs = make_app()
    form = QVibe(app, prefs)
    # setup the error handler
    e_dialog = QErrorMessage(form)
    e_dialog.setWindowModality(QtCore.Qt.WindowModal)
    font = QFont()
    font.setFamily("Consolas")
    font.setPointSize(8)
    e_dialog.setFont(font)
    # add the exception handler so we can see the errors in a QErrorMessage
    sys._excepthook = sys.excepthook


    def dump_exception_to_log(exctype, value, tb):
        import traceback
        print(exctype, value, tb)
        global e_dialog
        if e_dialog is not None:
            formatted = traceback.format_exception(etype=exctype, value=value, tb=tb)
            e_dialog.setWindowTitle('Unexpected Error')
            url = 'https://github.com/3ll3d00d/qvibe-analyser/issues/new'
            msg = f"Unexpected Error detected, go to {url} to log the issue<p>{'<br>'.join(formatted)}"
            e_dialog.showMessage(msg)
            e_dialog.resize(1200, 400)


    sys.excepthook = dump_exception_to_log

    # show the form and exec the app
    form.show()
    app.exec_()


class PlotWidgetForSpectrum(pg.PlotWidget):
    def __init__(self, parent=None, background='default', **kargs):
        super().__init__(parent=parent,
                         background=background,
                         axisItems={
                             'bottom': MinorLevelsAxisItem(orientation='bottom'),
                             'left': MinorLevelsAxisItem(orientation='left')
                         },
                         **kargs)


class PlotWidgetWithDateAxis(pg.PlotWidget):
    def __init__(self, parent=None, background='default', **kargs):
        super().__init__(parent=parent,
                         background=background,
                         axisItems={
                             'bottom': TimeAxisItem(orientation='bottom'),
                             'left': MinorLevelsAxisItem(orientation='left')
                         },
                         **kargs)


class PlotWidgetForSpectrogram(pg.PlotWidget):
    def __init__(self, parent=None, background='default', **kargs):
        super().__init__(parent=parent,
                         background=background,
                         axisItems={'left': Inverse(orientation='left')},
                         **kargs)


class Inverse(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super(Inverse, self).__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        return values[::-1]


class MinorLevelsAxisItem(pg.AxisItem):

    def tickSpacing(self, minVal, maxVal, size):
        return bump_tick_levels(super(), minVal, maxVal, size)


class TimeAxisItem(MinorLevelsAxisItem):

    def tickStrings(self, values, scale, spacing):
        import datetime
        return [str(datetime.timedelta(seconds=value)).split('.')[0] for value in values]
