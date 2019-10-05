import math

import qtawesome as qta
import numpy as np
from qtpy.QtWidgets import QDialog
from scipy.interpolate import interp1d

from common import format_pg_plotitem, np_to_str
from model.preferences import RTA_TARGET
from ui.target import Ui_targetCurveDialog


class CreateTargetDialog(QDialog, Ui_targetCurveDialog):
    '''
    Create Target dialog
    '''

    def __init__(self, parent, prefs, fs=500):
        super(CreateTargetDialog, self).__init__(parent)
        self.setupUi(self)
        self.__prefs = prefs
        self.__hinges = []
        self.__fs = fs
        self.loadIsoTarget.clicked.connect(self.__load_iso)
        self.addHingeButton.clicked.connect(self.__add_and_recalc)
        self.addHingeButton.setIcon(qta.icon('fa5s.plus'))
        self.deleteHingeButton.clicked.connect(self.__remove_and_recalc)
        self.deleteHingeButton.setIcon(qta.icon('fa5s.times'))
        format_pg_plotitem(self.preview.getPlotItem(),
                           (0, self.__fs / 2),
                           (-150, 5),
                           x_range=(0, min(100, int(self.__fs / 2))),
                           y_range=(-15, 5))
        self.__plot = self.preview.plot(np.array([0, self.__fs / 2]), np.array([0, 0]))

    def __load_iso(self):
        self.__hinges = []
        self.hinges.clear()
        self.__append(1, -2)
        self.__append(4, -5)
        self.__append(8, -5)
        self.__append(80, 0)
        self.__recalc()

    def __add_and_recalc(self):
        self.__append(self.frequency.value(), self.magnitude.value())
        self.__recalc()

    def __append(self, freq, mag):
        self.__hinges.append([freq, mag])
        self.hinges.addItem(f"{freq} : {mag:.1f}")

    def __recalc(self):
        if len(self.__hinges) > 1:
            self.__plot.setData(*self.__interpolate(np.array(self.__hinges)))
        else:
            self.__plot.setData(np.array([0, self.__fs / 2]), np.array([0, 0]))

    def __remove_and_recalc(self):
        self.__hinges.pop(self.hinges.currentIndex())
        self.hinges.removeItem(self.hinges.currentIndex())
        self.__recalc()

    def __interpolate(self, xy, max_x=500.0):
        '''
        Interpolates between a series of x-y points to produce a straight line on a log scaled x axis.
        :param xy: the hinge points.
        :return: the interpolated points.
        '''
        x = xy[:, 0]
        y = xy[:, 1]
        # extend as straight line from 0 to 500
        if not math.isclose(x[0], 0.0):
            x = np.insert(x, 0, 0.0000001)
            y = np.insert(y, 0, y[0])
        if not math.isclose(x[-1], max_x):
            x = np.insert(x, len(x), max_x)
            y = np.insert(y, len(y), y[-1])
        # convert the y axis dB values into a linear value
        y = 10 ** (y / 10)
        # perform a logspace interpolation
        f = self.log_interp1d(x, y)
        # remap to 0-max_x
        xnew = np.linspace(x[0], x[-1], num=int(max_x), endpoint=False)
        # and convert back to dB
        return xnew, 10 * np.log10(f(xnew))

    def log_interp1d(self, xx, yy, kind='linear'):
        """
        Performs a log space 1d interpolation.
        :param xx: the x values.
        :param yy: the y values.
        :param kind: the type of interpolation to apply (as per scipy interp1d)
        :return: the interpolation function.
        """
        logx = np.log10(xx)
        logy = np.log10(yy)
        lin_interp = interp1d(logx, logy, kind=kind)
        return lambda zz: np.power(10.0, lin_interp(np.log10(zz)))

    def accept(self):
        if len(self.__hinges) > 1:
            data = np.array(self.__interpolate(np.array(self.__hinges)))
            self.__prefs.set(RTA_TARGET, np_to_str(data))
        super().accept()
