import logging
import os
import sys
# matplotlib.use("Qt5Agg")
from contextlib import contextmanager

os.environ['QT_API'] = 'pyqt5'
# os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt5'
if sys.platform == 'win32' and getattr(sys, '_MEIPASS', False):
    # Workaround for PyInstaller being unable to find Qt5Core.dll on PATH.
    # See https://github.com/pyinstaller/pyinstaller/issues/4293
    os.environ['PATH'] = sys._MEIPASS + os.pathsep + os.environ['PATH']

import pyqtgraph as pg

from qtpy import QtCore
from qtpy.QtCore import QSettings, QThreadPool, QUrl
from qtpy.QtGui import QIcon, QFont, QCursor, QDesktopServices
from qtpy.QtWidgets import QMainWindow, QApplication, QErrorMessage, QMessageBox
from model.preferences import SYSTEM_CHECK_FOR_BETA_UPDATES, SYSTEM_CHECK_FOR_UPDATES, SCREEN_GEOMETRY, \
    SCREEN_WINDOW_STATE, PreferencesDialog, Preferences
from model.checker import VersionChecker, ReleaseNotesDialog
from model.log import RollingLogger
from ui.app import Ui_MainWindow

logger = logging.getLogger('qvibe')
# logging.getLogger('matplotlib').setLevel(logging.WARNING)


@contextmanager
def wait_cursor(msg=None):
    '''
    Allows long running functions to show a busy cursor.
    :param msg: a message to put in the status bar.
    '''
    try:
        QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
        yield
    finally:
        QApplication.restoreOverrideCursor()


class QVibe(QMainWindow, Ui_MainWindow):
    '''
    The main UI.
    '''

    def __init__(self, app, prefs, parent=None):
        super(QVibe, self).__init__(parent)
        self.logger = logging.getLogger('qvibe')
        self.app = app
        self.preferences = prefs
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
        self.setupUi(self)
        # logs
        self.logViewer = RollingLogger(self.preferences, parent=self)
        self.actionShow_Logs.triggered.connect(self.logViewer.show_logs)
        self.action_Preferences.triggered.connect(self.showPreferences)

    def show_release_notes(self):
        ''' Shows the release notes '''
        QThreadPool.globalInstance().start(VersionChecker(self.preferences.get(SYSTEM_CHECK_FOR_BETA_UPDATES),
                                                          self.__alert_on_old_version,
                                                          self.__alert_on_version_check_fail,
                                                          self.__version,
                                                          signal_anyway=True))

    def show_help(self):
        ''' Opens the user guide in a browser '''
        QDesktopServices.openUrl(QUrl('https://beqdesigner.readthedocs.io/en/latest'))

    def __alert_on_version_check_fail(self, message):
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

    def showPreferences(self):
        '''
        Shows the preferences dialog.
        '''
        PreferencesDialog(self.preferences, self.__style_path_root, parent=self).exec()

    def showAbout(self):
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
            url = 'https://github.com/3ll3d00d/beqdesigner/issues/new'
            msg = f"Unexpected Error detected, go to {url} to log the issue<p>{'<br>'.join(formatted)}"
            e_dialog.showMessage(msg)
            e_dialog.resize(1200, 400)


    sys.excepthook = dump_exception_to_log

    # show the form and exec the app
    form.show()
    app.exec_()


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
