import glob
from pathlib import Path

from qtpy.QtWidgets import QDialog, QMessageBox, QDialogButtonBox

from ui.preferences import Ui_preferencesDialog

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

DEFAULT_PREFS = {
    STYLE_MATPLOTLIB_THEME: STYLE_MATPLOTLIB_THEME_DEFAULT,
    SYSTEM_CHECK_FOR_UPDATES: True,
    SYSTEM_CHECK_FOR_BETA_UPDATES: False,
    RECORDER_TARGET_FS: 500,
    RECORDER_TARGET_SAMPLES_PER_BATCH: 8,
    RECORDER_TARGET_ACCEL_ENABLED: True,
    RECORDER_TARGET_ACCEL_SENS: 4,
    RECORDER_TARGET_GYRO_ENABLED: False,
    RECORDER_TARGET_GYRO_SENS: 500
}

TYPES = {
    SYSTEM_CHECK_FOR_UPDATES: bool,
    SYSTEM_CHECK_FOR_BETA_UPDATES: bool,
    RECORDER_TARGET_FS: int,
    RECORDER_TARGET_SAMPLES_PER_BATCH: int,
    RECORDER_TARGET_ACCEL_ENABLED: bool,
    RECORDER_TARGET_ACCEL_SENS: int,
    RECORDER_TARGET_GYRO_ENABLED: bool,
    RECORDER_TARGET_GYRO_SENS: int
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

    def __init__(self, preferences, style_root, parent=None):
        super(PreferencesDialog, self).__init__(parent)
        self.__style_root = style_root
        self.setupUi(self)
        self.__preferences = preferences
        self.buttonBox.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.__reset)

        # self.init_combo(STYLE_MATPLOTLIB_THEME, self.themePicker)

        self.checkForUpdates.setChecked(self.__preferences.get(SYSTEM_CHECK_FOR_UPDATES))
        self.checkForBetaUpdates.setChecked(self.__preferences.get(SYSTEM_CHECK_FOR_BETA_UPDATES))

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

    def __init_themes(self):
        '''
        Adds all the available matplotlib theme names to a combo along with our internal theme names.
        '''
        for p in glob.iglob(f"{self.__style_root}/style/mpl/*.mplstyle"):
            self.themePicker.addItem(Path(p).resolve().stem)
        # for style_name in sorted(style.library.keys()):
        #     self.themePicker.addItem(style_name)

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
        # current_theme = self.__preferences.get(STYLE_MATPLOTLIB_THEME)
        # if current_theme is not None and current_theme != self.themePicker.currentText():
        #     self.alert_on_change('Theme Change')
        # self.__preferences.set(STYLE_MATPLOTLIB_THEME, self.themePicker.currentText())
        self.__preferences.set(SYSTEM_CHECK_FOR_UPDATES, self.checkForUpdates.isChecked())
        self.__preferences.set(SYSTEM_CHECK_FOR_BETA_UPDATES, self.checkForBetaUpdates.isChecked())

        QDialog.accept(self)

    def alert_on_change(self, title, text='Change will not take effect until the application is restarted',
                        icon=QMessageBox.Warning):
        msg_box = QMessageBox()
        msg_box.setText(text)
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.exec()

