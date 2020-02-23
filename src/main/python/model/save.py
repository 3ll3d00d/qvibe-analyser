import logging

import time

import math
import os

from pyqtgraph.exporters import ImageExporter
from qtpy.QtWidgets import QDialog, QFileDialog, QDialogButtonBox
from scipy.io import wavfile
from resampy import resample

from common import block_signals, wait_cursor
from model.preferences import WAV_DOWNLOAD_DIR
from ui.savechart import Ui_saveChartDialog
from ui.savewav import Ui_saveWavDialog
from model.log import to_millis

logger = logging.getLogger('qvibe.save')


class SaveChartDialog(QDialog, Ui_saveChartDialog):
    '''
    Save Chart dialog
    '''

    def __init__(self, parent, name, plot, statusbar=None):
        super(SaveChartDialog, self).__init__(parent)
        self.setupUi(self)
        self.name = name
        self.plot = plot
        self.exporter = ImageExporter(self.plot.getPlotItem())
        self.__x = self.plot.size().width()
        self.__y = self.plot.size().height()
        self.__aspectRatio = self.__x / self.__y
        self.widthPixels.setValue(self.__x)
        self.heightPixels.setValue(self.__y)
        self.statusbar = statusbar
        self.__dialog = QFileDialog(parent=self)

    def accept(self):
        formats = "Portable Network Graphic (*.png)"
        file_name = self.__dialog.getSaveFileName(self, 'Export Chart', f"{self.name}.png", formats)
        if file_name:
            output_file = str(file_name[0]).strip()
            if len(output_file) == 0:
                return
            else:
                self.exporter.parameters()['width'] = self.widthPixels.value()
                self.__force_to_int('height')
                self.__force_to_int('width')
                self.exporter.export(output_file)
                if self.statusbar is not None:
                    self.statusbar.showMessage(f"Saved {self.name} to {output_file}", 5000)
        QDialog.accept(self)

    def __force_to_int(self, param_name):
        h = self.exporter.params.param(param_name)
        orig_h = int(self.exporter.parameters()[param_name])
        with block_signals(h):
            h.setValue(orig_h + 0.1)
            h.setValue(orig_h)

    def set_height(self, newWidth):
        '''
        Updates the height as the width changes according to the aspect ratio.
        :param newWidth: the new width.
        '''
        self.heightPixels.setValue(int(math.floor(newWidth / self.__aspectRatio)))


class SaveWavDialog(QDialog, Ui_saveWavDialog):
    '''
    Save WAV dialog
    '''

    def __init__(self, parent, preferences, measurement_store, fs, sens, statusbar=None):
        super(SaveWavDialog, self).__init__(parent)
        self.setupUi(self)
        self.preferences = preferences
        self.measurement_store = measurement_store
        self.fs = fs
        self.sens = sens
        for m in self.measurement_store:
            self.measurement.addItem(m.key)
        self.statusbar = statusbar
        self.location.setText(self.preferences.get(WAV_DOWNLOAD_DIR))
        self.axes.selectAll()

    def select_location(self):
        dir_name = QFileDialog.getExistingDirectory(self, 'Export WAV', self.location.text(), QFileDialog.ShowDirsOnly)
        if len(dir_name) > 0:
            self.location.setText(dir_name)

    def validate_name(self, name):
        self.buttonBox.button(QDialogButtonBox.Save).setEnabled(len(name) > 0)

    def accept(self):
        name = self.fileName.text()
        if len(name) > 0:
            if name[-4:] == '.wav':
                name = name[:-4]
            m = next((m for m in self.measurement_store if m.key == self.measurement.currentText()), None)
            if m is not None:
                data = m.data
                output_fs = self.fs
                if self.outputFs.currentText() != 'Native':
                    output_fs = int(float(self.outputFs.currentText().split(' ')[0]) * 1000)
                for t in self.axes.selectedItems():
                    with wait_cursor():
                        d = data[:, self.__idx(t.text())] / self.sens
                        if output_fs != self.fs:
                            start = time.time()
                            d = resample(d, self.fs, output_fs)
                            end = time.time()
                            logger.debug(f"Resampled {self.measurement.currentText()}:{t.text()} in {to_millis(start, end)}ms")
                        output_file = os.path.join(self.location.text(), f"{name}_{t.text()}_{output_fs}.wav")
                        wavfile.write(output_file, output_fs, d)
                if self.statusbar is not None:
                    self.statusbar.showMessage(f"Saved {self.measurement.currentText()}", 5000)
            QDialog.accept(self)

    @staticmethod
    def __idx(axis):
        if axis == 'x':
            return 2
        elif axis == 'y':
            return 3
        elif axis == 'z':
            return 4
