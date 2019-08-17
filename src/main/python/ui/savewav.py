# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'savewav.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_saveWavDialog(object):
    def setupUi(self, saveWavDialog):
        saveWavDialog.setObjectName("saveWavDialog")
        saveWavDialog.resize(393, 252)
        self.gridLayout = QtWidgets.QGridLayout(saveWavDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.axesLabel = QtWidgets.QLabel(saveWavDialog)
        self.axesLabel.setObjectName("axesLabel")
        self.gridLayout.addWidget(self.axesLabel, 1, 0, 1, 1)
        self.locationPicker = QtWidgets.QToolButton(saveWavDialog)
        self.locationPicker.setObjectName("locationPicker")
        self.gridLayout.addWidget(self.locationPicker, 2, 2, 1, 1)
        self.fileName = QtWidgets.QLineEdit(saveWavDialog)
        self.fileName.setObjectName("fileName")
        self.gridLayout.addWidget(self.fileName, 3, 1, 1, 2)
        self.buttonBox = QtWidgets.QDialogButtonBox(saveWavDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Save)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 4, 0, 1, 3)
        self.fileNameLabel = QtWidgets.QLabel(saveWavDialog)
        self.fileNameLabel.setObjectName("fileNameLabel")
        self.gridLayout.addWidget(self.fileNameLabel, 3, 0, 1, 1)
        self.recorder = QtWidgets.QComboBox(saveWavDialog)
        self.recorder.setObjectName("recorder")
        self.gridLayout.addWidget(self.recorder, 0, 1, 1, 2)
        self.axes = QtWidgets.QListWidget(saveWavDialog)
        self.axes.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.axes.setObjectName("axes")
        item = QtWidgets.QListWidgetItem()
        self.axes.addItem(item)
        item = QtWidgets.QListWidgetItem()
        self.axes.addItem(item)
        item = QtWidgets.QListWidgetItem()
        self.axes.addItem(item)
        self.gridLayout.addWidget(self.axes, 1, 1, 1, 2)
        self.location = QtWidgets.QLineEdit(saveWavDialog)
        self.location.setReadOnly(True)
        self.location.setObjectName("location")
        self.gridLayout.addWidget(self.location, 2, 1, 1, 1)
        self.localtionLabel = QtWidgets.QLabel(saveWavDialog)
        self.localtionLabel.setObjectName("localtionLabel")
        self.gridLayout.addWidget(self.localtionLabel, 2, 0, 1, 1)
        self.recorderLabel = QtWidgets.QLabel(saveWavDialog)
        self.recorderLabel.setObjectName("recorderLabel")
        self.gridLayout.addWidget(self.recorderLabel, 0, 0, 1, 1)

        self.retranslateUi(saveWavDialog)
        self.buttonBox.accepted.connect(saveWavDialog.accept)
        self.buttonBox.rejected.connect(saveWavDialog.reject)
        self.locationPicker.clicked.connect(saveWavDialog.select_location)
        self.fileName.textChanged['QString'].connect(saveWavDialog.validate_name)
        QtCore.QMetaObject.connectSlotsByName(saveWavDialog)

    def retranslateUi(self, saveWavDialog):
        _translate = QtCore.QCoreApplication.translate
        saveWavDialog.setWindowTitle(_translate("saveWavDialog", "Dialog"))
        self.axesLabel.setText(_translate("saveWavDialog", "Axes"))
        self.locationPicker.setText(_translate("saveWavDialog", "..."))
        self.fileNameLabel.setText(_translate("saveWavDialog", "Name"))
        __sortingEnabled = self.axes.isSortingEnabled()
        self.axes.setSortingEnabled(False)
        item = self.axes.item(0)
        item.setText(_translate("saveWavDialog", "x"))
        item = self.axes.item(1)
        item.setText(_translate("saveWavDialog", "y"))
        item = self.axes.item(2)
        item.setText(_translate("saveWavDialog", "z"))
        self.axes.setSortingEnabled(__sortingEnabled)
        self.localtionLabel.setText(_translate("saveWavDialog", "Location"))
        self.recorderLabel.setText(_translate("saveWavDialog", "Recorder"))
