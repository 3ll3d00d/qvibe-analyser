# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'target.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_targetCurveDialog(object):
    def setupUi(self, targetCurveDialog):
        targetCurveDialog.setObjectName("targetCurveDialog")
        targetCurveDialog.resize(754, 517)
        self.gridLayout = QtWidgets.QGridLayout(targetCurveDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.preview = PlotWidgetForSpectrum(targetCurveDialog)
        self.preview.setObjectName("preview")
        self.gridLayout.addWidget(self.preview, 3, 0, 1, 7)
        self.magnitude = QtWidgets.QDoubleSpinBox(targetCurveDialog)
        self.magnitude.setDecimals(1)
        self.magnitude.setMinimum(-120.0)
        self.magnitude.setMaximum(0.0)
        self.magnitude.setSingleStep(0.1)
        self.magnitude.setObjectName("magnitude")
        self.gridLayout.addWidget(self.magnitude, 0, 3, 1, 1)
        self.frequencyLabel = QtWidgets.QLabel(targetCurveDialog)
        self.frequencyLabel.setObjectName("frequencyLabel")
        self.gridLayout.addWidget(self.frequencyLabel, 0, 0, 1, 1)
        self.magnitudeLabel = QtWidgets.QLabel(targetCurveDialog)
        self.magnitudeLabel.setObjectName("magnitudeLabel")
        self.gridLayout.addWidget(self.magnitudeLabel, 0, 2, 1, 1)
        self.deleteHingeButton = QtWidgets.QToolButton(targetCurveDialog)
        self.deleteHingeButton.setObjectName("deleteHingeButton")
        self.gridLayout.addWidget(self.deleteHingeButton, 1, 4, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(targetCurveDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Close|QtWidgets.QDialogButtonBox.Save)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 4, 6, 1, 1)
        self.frequency = QtWidgets.QDoubleSpinBox(targetCurveDialog)
        self.frequency.setDecimals(0)
        self.frequency.setMaximum(24000.0)
        self.frequency.setObjectName("frequency")
        self.gridLayout.addWidget(self.frequency, 0, 1, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 0, 6, 1, 1)
        self.hinges = QtWidgets.QComboBox(targetCurveDialog)
        self.hinges.setObjectName("hinges")
        self.gridLayout.addWidget(self.hinges, 1, 1, 1, 3)
        self.label = QtWidgets.QLabel(targetCurveDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)
        self.addHingeButton = QtWidgets.QToolButton(targetCurveDialog)
        self.addHingeButton.setObjectName("addHingeButton")
        self.gridLayout.addWidget(self.addHingeButton, 0, 4, 1, 1)
        self.loadIsoTarget = QtWidgets.QPushButton(targetCurveDialog)
        self.loadIsoTarget.setObjectName("loadIsoTarget")
        self.gridLayout.addWidget(self.loadIsoTarget, 1, 5, 1, 1)

        self.retranslateUi(targetCurveDialog)
        self.buttonBox.accepted.connect(targetCurveDialog.accept)
        self.buttonBox.rejected.connect(targetCurveDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(targetCurveDialog)

    def retranslateUi(self, targetCurveDialog):
        _translate = QtCore.QCoreApplication.translate
        targetCurveDialog.setWindowTitle(_translate("targetCurveDialog", "Create Target Curve"))
        self.frequencyLabel.setText(_translate("targetCurveDialog", "Frequency"))
        self.magnitudeLabel.setText(_translate("targetCurveDialog", "Magnitude"))
        self.deleteHingeButton.setText(_translate("targetCurveDialog", "..."))
        self.label.setText(_translate("targetCurveDialog", "Hinge Points"))
        self.addHingeButton.setText(_translate("targetCurveDialog", "..."))
        self.loadIsoTarget.setText(_translate("targetCurveDialog", "Load IsoPerception"))
from qvibe import PlotWidgetForSpectrum
