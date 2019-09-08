# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'export.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_exportDialog(object):
    def setupUi(self, exportDialog):
        exportDialog.setObjectName("exportDialog")
        exportDialog.resize(397, 84)
        self.gridLayout = QtWidgets.QGridLayout(exportDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.measurementLabel = QtWidgets.QLabel(exportDialog)
        self.measurementLabel.setObjectName("measurementLabel")
        self.gridLayout.addWidget(self.measurementLabel, 0, 0, 1, 1)
        self.measurementSelector = QtWidgets.QComboBox(exportDialog)
        self.measurementSelector.setObjectName("measurementSelector")
        self.gridLayout.addWidget(self.measurementSelector, 0, 1, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(exportDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Save)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 1, 0, 1, 2)
        self.gridLayout.setColumnStretch(1, 1)

        self.retranslateUi(exportDialog)
        self.buttonBox.accepted.connect(exportDialog.accept)
        self.buttonBox.rejected.connect(exportDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(exportDialog)

    def retranslateUi(self, exportDialog):
        _translate = QtCore.QCoreApplication.translate
        exportDialog.setWindowTitle(_translate("exportDialog", "Export"))
        self.measurementLabel.setText(_translate("exportDialog", "Measurement:"))
