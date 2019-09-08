import os

from qtpy.QtWidgets import QFileDialog, QDialog, QMessageBox
import numpy as np

from ui.export import Ui_exportDialog


class ExportDialog(QDialog, Ui_exportDialog):

    def __init__(self, parent, data):
        super(ExportDialog, self).__init__(parent)
        self.setupUi(self)
        self.__data = data
        for d in self.__data.keys():
            self.measurementSelector.addItem(d)

    def accept(self):
        '''
        Exports the measurement as an frd.
        :param measurement: the measurement.
        '''
        m = self.__data[self.measurementSelector.currentText()]
        dir_name = QFileDialog(self).getExistingDirectory(self,
                                                          'Export FRD',
                                                          os.path.expanduser('~'),
                                                          QFileDialog.ShowDirsOnly)
        if len(dir_name) > 0:
            for axis in ['x', 'y', 'z', 'sum']:
                sig = getattr(m, axis)
                if sig.has_data(sig.view_mode):
                    d = sig.get_analysis()
                    header = self.__make_header(sig)
                    name = os.path.join(dir_name, f"{sig.measurement_name}_{sig.axis}_{sig.view_mode}.frd")
                    np.savetxt(name, np.transpose([d.x, d.y]), fmt='%8.3f', header=header)
        QDialog.accept(self)

    @staticmethod
    def __make_header(to_export):
        import datetime
        return '\n'.join(['Exported by qvibe-analyser',
                          f"name: {to_export.measurement_name}",
                          f"axis: {to_export.axis}",
                          f"fs: {to_export.fs}",
                          f"view: {to_export.view_mode}",
                          f"idx: {to_export.idx}",
                          f"time: {datetime.datetime.now()}",
                          'frequency magnitude'])
