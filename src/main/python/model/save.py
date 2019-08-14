import math
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter

from qtpy.QtWidgets import QDialog, QFileDialog

from common import block_signals
from ui.savechart import Ui_saveChartDialog


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

