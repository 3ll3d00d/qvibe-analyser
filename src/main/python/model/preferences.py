import os
import qtawesome as qta

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QDialog, QMessageBox, QDialogButtonBox, QFileDialog

from ui.preferences import Ui_preferencesDialog

DISPLAY_SMOOTH_GRAPHS = 'display/smooth_graphs'

STYLE_MATPLOTLIB_THEME_DEFAULT = 'beq_dark'
STYLE_MATPLOTLIB_THEME = 'style/matplotlib_theme'

LOGGING_LEVEL = 'logging/level'

SCREEN_GEOMETRY = 'screen/geometry'
SCREEN_WINDOW_STATE = 'screen/window_state'

SYSTEM_CHECK_FOR_UPDATES = 'system/check_for_updates'
SYSTEM_CHECK_FOR_BETA_UPDATES = 'system/check_for_beta_updates'

RECORDER_TARGET_FS = 'recorder/target/fs'
RECORDER_TARGET_SAMPLES_PER_BATCH = 'recorder/target/samples_per_batch'
RECORDER_TARGET_ACCEL_ENABLED = 'recorder/target/accel_enabled'
RECORDER_TARGET_ACCEL_SENS = 'recorder/target/accel_sens'
RECORDER_TARGET_GYRO_ENABLED = 'recorder/target/gyro_enabled'
RECORDER_TARGET_GYRO_SENS = 'recorder/target/gyro_sens'

RECORDER_SAVED_IPS = 'recorder/saved_ips'

BUFFER_SIZE = 'buffer/size'

ANALYSIS_RESOLUTION = 'analysis/resolution'
ANALYSIS_TARGET_FS = 'analysis/target_fs'
ANALYSIS_WINDOW_DEFAULT = 'Default'
ANALYSIS_AVG_WINDOW = 'analysis/avg_window'
ANALYSIS_PEAK_WINDOW = 'analysis/peak_window'

CHART_MAG_MIN = 'chart/mag_min'
CHART_MAG_MAX = 'chart/mag_max'
CHART_FREQ_MIN = 'chart/freq_min'
CHART_FREQ_MAX = 'chart/freq_max'

CHART_SPECTRO_SCALE_FACTOR = 'chart/spectro/scale_factor'
CHART_SPECTRO_SCALE_ALGO = 'chart/spectro/scale_algo'

SUM_X_SCALE = 'sum/x_scale'
SUM_Y_SCALE = 'sum/y_scale'
SUM_Z_SCALE = 'sum/z_scale'

WAV_DOWNLOAD_DIR = 'wav/download_dir'

SNAPSHOT_GROUP = 'snapshot'

DEFAULT_PREFS = {
    ANALYSIS_RESOLUTION: 1.0,
    ANALYSIS_TARGET_FS: 1000,
    ANALYSIS_AVG_WINDOW: ANALYSIS_WINDOW_DEFAULT,
    ANALYSIS_PEAK_WINDOW: ANALYSIS_WINDOW_DEFAULT,
    BUFFER_SIZE: 30,
    CHART_MAG_MIN: 40,
    CHART_MAG_MAX: 120,
    CHART_FREQ_MIN: 1,
    CHART_FREQ_MAX: 125,
    CHART_SPECTRO_SCALE_FACTOR: '8x',
    CHART_SPECTRO_SCALE_ALGO: 'Lanczos',
    DISPLAY_SMOOTH_GRAPHS: True,
    RECORDER_TARGET_FS: 500,
    RECORDER_TARGET_SAMPLES_PER_BATCH: 8,
    RECORDER_TARGET_ACCEL_ENABLED: True,
    RECORDER_TARGET_ACCEL_SENS: 4,
    RECORDER_TARGET_GYRO_ENABLED: False,
    RECORDER_TARGET_GYRO_SENS: 500,
    SUM_X_SCALE: 2.2,
    SUM_Y_SCALE: 2.4,
    SUM_Z_SCALE: 1.0,
    STYLE_MATPLOTLIB_THEME: STYLE_MATPLOTLIB_THEME_DEFAULT,
    SYSTEM_CHECK_FOR_UPDATES: True,
    SYSTEM_CHECK_FOR_BETA_UPDATES: False,
    WAV_DOWNLOAD_DIR: os.path.join(os.path.expanduser('~'), 'Music'),
}

TYPES = {
    ANALYSIS_RESOLUTION: float,
    ANALYSIS_TARGET_FS: int,
    BUFFER_SIZE: int,
    DISPLAY_SMOOTH_GRAPHS: bool,
    RECORDER_TARGET_FS: int,
    RECORDER_TARGET_SAMPLES_PER_BATCH: int,
    RECORDER_TARGET_ACCEL_ENABLED: bool,
    RECORDER_TARGET_ACCEL_SENS: int,
    RECORDER_TARGET_GYRO_ENABLED: bool,
    RECORDER_TARGET_GYRO_SENS: int,
    CHART_MAG_MIN: int,
    CHART_MAG_MAX: int,
    CHART_FREQ_MIN: int,
    CHART_FREQ_MAX: int,
    SUM_X_SCALE: float,
    SUM_Y_SCALE: float,
    SUM_Z_SCALE: float,
    SYSTEM_CHECK_FOR_UPDATES: bool,
    SYSTEM_CHECK_FOR_BETA_UPDATES: bool,
}


singleton = None


class Preferences:
    def __init__(self, settings):
        self.__settings = settings
        global singleton
        singleton = self

    def has(self, key):
        '''
        checks for existence of a value.
        :param key: the key.
        :return: True if we have a value.
        '''
        return self.get(key) is not None

    def get(self, key, default_if_unset=True):
        '''
        Gets the value, if any.
        :param key: the settings key.
        :param default_if_unset: if true, return a default value.
        :return: the value.
        '''
        default_value = DEFAULT_PREFS.get(key, None) if default_if_unset is True else None
        value_type = TYPES.get(key, None)
        if value_type is not None:
            return self.__settings.value(key, defaultValue=default_value, type=value_type)
        else:
            return self.__settings.value(key, defaultValue=default_value)

    def enter(self, key):
        self.__settings.beginGroup(key)

    def get_children(self):
        return self.__settings.childKeys()

    def exit(self):
        self.__settings.endGroup()

    def get_all(self, prefix):
        '''
        Get all values with the given prefix.
        :param prefix: the prefix.
        :return: the values, if any.
        '''
        self.__settings.beginGroup(prefix)
        try:
            return set(filter(None.__ne__, [self.__settings.value(x) for x in self.__settings.childKeys()]))
        finally:
            self.__settings.endGroup()

    def set(self, key, value):
        '''
        sets a new value.
        :param key: the key.
        :param value:  the value.
        '''
        if value is None:
            self.__settings.remove(key)
        else:
            self.__settings.setValue(key, value)

    def clear_all(self, prefix):
        ''' clears all under the given group '''
        self.__settings.beginGroup(prefix)
        self.__settings.remove('')
        self.__settings.endGroup()

    def clear(self, key):
        '''
        Removes the stored value.
        :param key: the key.
        '''
        self.set(key, None)

    def reset(self):
        '''
        Resets all preferences.
        '''
        self.__settings.clear()


class PreferencesDialog(QDialog, Ui_preferencesDialog):
    '''
    Allows user to set some basic preferences.
    '''

    def __init__(self, preferences, style_root, recorder_store, spectro, parent=None):
        super(PreferencesDialog, self).__init__(parent)
        self.__style_root = style_root
        self.__recorder_store = recorder_store
        self.setupUi(self)
        self.__preferences = preferences
        self.__spectro = spectro
        self.buttonBox.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.__reset)
        self.checkForUpdates.setChecked(self.__preferences.get(SYSTEM_CHECK_FOR_UPDATES))
        self.checkForBetaUpdates.setChecked(self.__preferences.get(SYSTEM_CHECK_FOR_BETA_UPDATES))
        self.xScale.setValue(self.__preferences.get(SUM_X_SCALE))
        self.yScale.setValue(self.__preferences.get(SUM_Y_SCALE))
        self.zScale.setValue(self.__preferences.get(SUM_Z_SCALE))
        self.magMin.setValue(self.__preferences.get(CHART_MAG_MIN))
        self.magMax.setValue(self.__preferences.get(CHART_MAG_MAX))
        self.magMin.valueChanged['int'].connect(self.__balance_mag)
        self.magMax.valueChanged['int'].connect(self.__balance_mag)
        self.freqMin.setValue(self.__preferences.get(CHART_FREQ_MIN))
        self.freqMax.setValue(self.__preferences.get(CHART_FREQ_MAX))
        self.freqMin.valueChanged['int'].connect(self.__balance_freq)
        self.freqMax.valueChanged['int'].connect(self.__balance_freq)
        self.wavSaveDir.setText(self.__preferences.get(WAV_DOWNLOAD_DIR))
        self.spectroScaleAlgo.setCurrentText(self.__preferences.get(CHART_SPECTRO_SCALE_ALGO))
        self.spectroScaleFactor.setCurrentText(self.__preferences.get(CHART_SPECTRO_SCALE_FACTOR))
        self.wavSaveDirPicker.setIcon(qta.icon('fa5s.folder-open'))
        self.addRecorderButton.setIcon(qta.icon('fa5s.plus'))
        self.deleteRecorderButton.setIcon(qta.icon('fa5s.times'))
        enable_delete = False
        if self.__preferences.get(RECORDER_SAVED_IPS) is not None:
            ips = self.__preferences.get(RECORDER_SAVED_IPS).split('|')
            for ip in ips:
                self.recorders.addItem(ip)
                enable_delete = True
        else:
            self.recorderIP.setFocus(Qt.OtherFocusReason)
        self.deleteRecorderButton.setEnabled(enable_delete)
        self.addRecorderButton.setEnabled(False)

    def __balance_mag(self, val):
        keep_range(self.magMin, self.magMax, 10)

    def __balance_freq(self, val):
        keep_range(self.freqMin, self.freqMax, 10)

    def validate_ip(self, ip):
        valid_ip = self.__is_valid_ip(ip)
        existing_ip = self.recorders.findText(ip, Qt.MatchExactly)
        self.addRecorderButton.setEnabled(valid_ip and existing_ip == -1)

    def add_recorder(self):
        self.recorders.addItem(self.recorderIP.text())
        self.recorderIP.clear()

    def delete_recorder(self):
        idx = self.recorders.currentIndex()
        if idx > -1:
            self.recorders.removeItem(idx)
            self.deleteRecorderButton.setEnabled(self.recorders.count() > 0)

    @staticmethod
    def __is_valid_ip(ip):
        ''' checks if the string is a valid ip:port. '''
        tokens = ip.split(':')
        if len(tokens) == 2:
            ip_tokens = tokens[0].split('.')
            if len(ip_tokens) == 4:
                try:
                    first, *nums = [int(i) for i in ip_tokens]
                    if 0 < first <= 255:
                        if all(0 <= i <= 255 for i in nums):
                            return 0 < int(tokens[1]) < 65536
                except Exception as e:
                    pass
        return False

    def __reset(self):
        '''
        Reset all settings
        '''
        result = QMessageBox.question(self,
                                      'Reset Preferences?',
                                      f"All preferences will be restored to their default values. This action is irreversible.\nAre you sure you want to continue?",
                                      QMessageBox.Yes | QMessageBox.No,
                                      QMessageBox.No)
        if result == QMessageBox.Yes:
            self.__preferences.reset()
            self.alert_on_change('Defaults Restored')
            self.reject()

    def init_combo(self, key, combo, translater=lambda a: a):
        '''
        Initialises a combo box from either settings or a default value.
        :param key: the settings key.
        :param combo: the combo box.
        :param translater: a lambda to translate from the stored value to the display name.
        '''
        stored_value = self.__preferences.get(key)
        idx = -1
        if stored_value is not None:
            idx = combo.findText(translater(stored_value))
        if idx != -1:
            combo.setCurrentIndex(idx)

    def accept(self):
        '''
        Saves the locations if they exist.
        '''
        self.__preferences.set(SYSTEM_CHECK_FOR_UPDATES, self.checkForUpdates.isChecked())
        self.__preferences.set(SYSTEM_CHECK_FOR_BETA_UPDATES, self.checkForBetaUpdates.isChecked())
        self.__preferences.set(SUM_X_SCALE, self.xScale.value())
        self.__preferences.set(SUM_Y_SCALE, self.yScale.value())
        self.__preferences.set(SUM_Z_SCALE, self.zScale.value())
        self.__preferences.set(WAV_DOWNLOAD_DIR, self.wavSaveDir.text())
        self.__preferences.set(CHART_MAG_MIN, self.magMin.value())
        self.__preferences.set(CHART_MAG_MAX, self.magMax.value())
        self.__preferences.set(CHART_FREQ_MIN, self.freqMin.value())
        self.__preferences.set(CHART_FREQ_MAX, self.freqMax.value())
        self.__preferences.set(CHART_SPECTRO_SCALE_ALGO, self.spectroScaleAlgo.currentText())
        self.__preferences.set(CHART_SPECTRO_SCALE_FACTOR, self.spectroScaleFactor.currentText())
        # TODO would be nicer to be able to listen to specific values
        self.__spectro.update_scale()
        if self.recorders.count() > 0:
            ips = [self.recorders.itemText(i) for i in range(self.recorders.count())]
            self.__preferences.set(RECORDER_SAVED_IPS, '|'.join(ips))
            self.__recorder_store.load(ips)
        else:
            self.__preferences.clear(RECORDER_SAVED_IPS)
            self.__recorder_store.clear()
        QDialog.accept(self)

    def pick_save_dir(self):
        dir_name = QFileDialog.getExistingDirectory(self, 'Export WAV', self.wavSaveDir.text(),
                                                    QFileDialog.ShowDirsOnly)
        if len(dir_name) > 0:
            self.wavSaveDir.setText(dir_name)

    def alert_on_change(self, title, text='Change will not take effect until the application is restarted',
                        icon=QMessageBox.Warning):
        msg_box = QMessageBox()
        msg_box.setText(text)
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.exec()


def keep_range(min_widget, max_widget, range):
    if min_widget.value() + range >= max_widget.value():
        min_widget.setValue(max_widget.value()-range)
    if max_widget.value() - range <= min_widget.value():
        max_widget.setValue(min_widget.value()+range)
