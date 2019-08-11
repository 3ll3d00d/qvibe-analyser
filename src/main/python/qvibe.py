import logging
import os
import sys

# matplotlib.use("Qt5Agg")
from model.rta import RTA
from model.vibration import Vibration

os.environ['QT_API'] = 'pyqt5'
# os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt5'
if sys.platform == 'win32' and getattr(sys, '_MEIPASS', False):
    # Workaround for PyInstaller being unable to find Qt5Core.dll on PATH.
    # See https://github.com/pyinstaller/pyinstaller/issues/4293
    os.environ['PATH'] = sys._MEIPASS + os.pathsep + os.environ['PATH']

import pyqtgraph as pg
import qtawesome as qta

from qtpy import QtCore
from qtpy.QtCore import QTimer, QSettings, QThreadPool, QUrl, Qt, QRunnable
from qtpy.QtGui import QIcon, QFont, QDesktopServices
from qtpy.QtWidgets import QMainWindow, QApplication, QErrorMessage, QMessageBox
from common import block_signals, ReactorRunner
from model.preferences import SYSTEM_CHECK_FOR_BETA_UPDATES, SYSTEM_CHECK_FOR_UPDATES, SCREEN_GEOMETRY, \
    SCREEN_WINDOW_STATE, PreferencesDialog, Preferences, BUFFER_SIZE, ANALYSIS_RESOLUTION
from model.checker import VersionChecker, ReleaseNotesDialog
from model.log import RollingLogger
from model.preferences import RECORDER_TARGET_FS, RECORDER_TARGET_SAMPLES_PER_BATCH, RECORDER_TARGET_ACCEL_ENABLED, \
    RECORDER_TARGET_ACCEL_SENS, RECORDER_TARGET_GYRO_ENABLED, RECORDER_TARGET_GYRO_SENS, RECORDER_SAVED_IPS
from ui.app import Ui_MainWindow

from model.recorders import RecorderStore, RecorderConfig

logger = logging.getLogger('qvibe')
# logging.getLogger('matplotlib').setLevel(logging.WARNING)


class QVibe(QMainWindow, Ui_MainWindow):
    '''
    The main UI.
    '''

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
        if self.preferences.get(SYSTEM_CHECK_FOR_UPDATES):
            QThreadPool.globalInstance().start(VersionChecker(self.preferences.get(SYSTEM_CHECK_FOR_BETA_UPDATES),
                                                              self.__alert_on_old_version,
                                                              self.__alert_on_version_check_fail,
                                                              self.__version))

        # matplotlib_theme = self.preferences.get(STYLE_MATPLOTLIB_THEME)
        # if matplotlib_theme is not None:
        #     if matplotlib_theme.startswith('beq'):
        #         style.use(os.path.join(self.__style_path_root, 'style', 'mpl', f"{matplotlib_theme}.mplstyle"))
        #     else:
        #         style.use(matplotlib_theme)

        # pg.setConfigOption('background', matplotlib.colors.to_hex(matplotlib.rcParams['axes.facecolor']))
        # pg.setConfigOption('foreground', matplotlib.colors.to_hex(matplotlib.rcParams['axes.edgecolor']))
        # pg.setConfigOption('leftButtonPan', False)
        # UI initialisation
        self.setupUi(self)
        self.addRecorderButton.setIcon(qta.icon('fa5s.plus'))
        self.saveRecordersButton.setIcon(qta.icon('fa5s.save'))
        self.visibleCurves.selectAll()
        # run a twisted reactor as its responsiveness is embarrassingly better than QTcpSocket
        from twisted.internet import reactor
        self.__reactor = reactor
        runner = ReactorRunner(self.__reactor)
        QThreadPool.globalInstance().reserveThread()
        QThreadPool.globalInstance().start(runner)
        self.app.aboutToQuit.connect(runner.stop)
        # core domain stores
        self.__timer = None
        self.__target_config = self.__load_config()
        self.__display_target_config()
        self.__recorder_store = RecorderStore(self.__target_config,
                                              self.recordersLayout,
                                              self.centralwidget,
                                              self.__reactor)
        self.__recorder_store.signals.on_status_change.connect(self.__handle_recorder_connect_event)
        saved_recorders = self.preferences.get(RECORDER_SAVED_IPS)
        if saved_recorders is None:
            self.__recorder_store.append()
        else:
            self.__recorder_store.load(saved_recorders.split('|'))
        target_resolution = f"{self.preferences.get(ANALYSIS_RESOLUTION)} Hz"
        self.resolutionHz.setCurrentText(target_resolution)
        # menus
        self.log_viewer = RollingLogger(self.preferences, parent=self)
        self.actionShow_Logs.triggered.connect(self.log_viewer.show_logs)
        self.action_Preferences.triggered.connect(self.show_preferences)
        # buffer
        self.bufferSize.setValue(self.preferences.get(BUFFER_SIZE))
        # charts
        self.__analysers = {
            0: Vibration(self.liveVibrationChart, self.preferences, self.targetSampleRate, self.resolutionHz,
                         self.targetAccelSens, self.bufferSize, self.vibrationAnalysis),
            1: RTA(self.rtaChart, self.preferences, self.targetSampleRate, self.resolutionHz, self.fps,
                   self.rtaAverage, self.rtaView)
        }
        self.__start_analysers()

        self.applyTargetButton.setIcon(qta.icon('fa5s.check', color='green'))
        self.resetTargetButton.setIcon(qta.icon('fa5s.undo'))
        self.saveRecordersButton.setIcon(qta.icon('fa5s.save'))

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
        if len(self.activeRecorders.findItems(ip, Qt.MatchExactly)) == 0:
            self.activeRecorders.addItem(ip)
            for i in self.activeRecorders.findItems(ip, Qt.MatchExactly):
                i.setSelected(True)
        if any_connected is True:
            self.__start_timer()
        else:
            self.__stop_timer()

    def __start_timer(self):
        '''
        Starts the data collection timer.
        '''
        if self.__timer is None:
            self.__timer = QTimer()
            self.__timer.timeout.connect(self.__collect_signals)
        logger.info(f"Starting data collection timer at {self.fps.value()} fps")
        self.__timer.start(1000.0 / self.fps.value())

    def __stop_timer(self):
        if self.__timer is not None:
            logger.info('Stopping data collection timer')
            self.__timer.stop()

    def __collect_signals(self):
        ''' collects the latest signal and pushes it into the analysers. '''
        signal, count, idx = self.__recorder_store.snap()
        if signal is not None:
            if count > 0:
                for c in self.__analysers.values():
                    c.accept(signal, idx)

    def update_target(self):
        ''' updates the current target config from the UI values. '''
        self.__target_config.fs = self.targetSampleRate.value()
        self.__target_config.samples_per_batch = self.targetBatchSize.value()
        self.__target_config.accelerometer_enabled = self.targetAccelEnabled.isChecked()
        self.__target_config.accelerometer_sens = int(self.targetAccelSens.currentText())
        self.__target_config.gyro_enabled = self.targetGyroEnabled.isChecked()
        self.__target_config.gyro_sens = int(self.targetGyroSens.currentText())

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

    def add_new_recorder(self):
        self.__recorder_store.append()

    def save_recorders(self):
        ''' Saves the specified recorders to preferences. '''
        self.preferences.set(RECORDER_SAVED_IPS, '|'.join([r.ip_address for r in self.__recorder_store]))

    def set_buffer_size(self, val):
        self.preferences.set(BUFFER_SIZE, val)
        # TODO propagate to the recorders
        # self.__signal_store.length = val

    def set_visible_chart(self, idx):
        for c_idx, c in self.__analysers.items():
            c.visible = idx == c_idx

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
        PreferencesDialog(self.preferences, self.__style_path_root, parent=self).exec()

    def show_about(self):
        msg_box = QMessageBox()
        msg_box.setText(
            f"<a href='https://github.com/3ll3d00d/qvibe-analyser'>QVibe Analyser</a> v{self.__version} by 3ll3d00d")
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle('About')
        msg_box.exec()


def make_app():
    app = QApplication(sys.argv)
    if getattr(sys, 'frozen', False):
        icon_path = os.path.join(sys._MEIPASS, 'Icon.ico')
    else:
        icon_path = os.path.abspath(os.path.join(os.path.dirname('__file__'), '../icons/Icon.ico'))
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    prefs = Preferences(QSettings("3ll3d00d", "qvibe-analyser"))
    # if prefs.get(STYLE_MATPLOTLIB_THEME) == f"{STYLE_MATPLOTLIB_THEME_DEFAULT}_extra":
    #     import qdarkstyle
    #     style = qdarkstyle.load_stylesheet_from_environment()
    #     app.setStyleSheet(style)
    return app, prefs


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
        super().__init__(parent=parent, background=background, **kargs)


class PlotWidgetWithDateAxis(pg.PlotWidget):
    def __init__(self, parent=None, background='default', **kargs):
        super().__init__(parent=parent,
                         background=background,
                         axisItems={'bottom': TimeAxisItem(orientation='bottom')},
                         **kargs)


class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        import datetime
        return [str(datetime.timedelta(seconds=value)).split('.')[0] for value in values]
