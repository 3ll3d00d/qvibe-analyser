# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'preferences.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_preferencesDialog(object):
    def setupUi(self, preferencesDialog):
        preferencesDialog.setObjectName("preferencesDialog")
        preferencesDialog.resize(643, 163)
        self.verticalLayout = QtWidgets.QVBoxLayout(preferencesDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.panes = QtWidgets.QVBoxLayout()
        self.panes.setObjectName("panes")
        self.systemPane = QtWidgets.QGridLayout()
        self.systemPane.setObjectName("systemPane")
        self.checkForUpdates = QtWidgets.QCheckBox(preferencesDialog)
        self.checkForUpdates.setChecked(True)
        self.checkForUpdates.setObjectName("checkForUpdates")
        self.systemPane.addWidget(self.checkForUpdates, 1, 0, 1, 1)
        self.checkForBetaUpdates = QtWidgets.QCheckBox(preferencesDialog)
        self.checkForBetaUpdates.setObjectName("checkForBetaUpdates")
        self.systemPane.addWidget(self.checkForBetaUpdates, 1, 1, 1, 1)
        self.systemLayoutLabel = QtWidgets.QLabel(preferencesDialog)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.systemLayoutLabel.setFont(font)
        self.systemLayoutLabel.setFrameShape(QtWidgets.QFrame.Box)
        self.systemLayoutLabel.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.systemLayoutLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.systemLayoutLabel.setObjectName("systemLayoutLabel")
        self.systemPane.addWidget(self.systemLayoutLabel, 0, 0, 1, 2)
        self.panes.addLayout(self.systemPane)
        self.verticalLayout.addLayout(self.panes)
        self.buttonBox = QtWidgets.QDialogButtonBox(preferencesDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.RestoreDefaults|QtWidgets.QDialogButtonBox.Save)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(preferencesDialog)
        self.buttonBox.accepted.connect(preferencesDialog.accept)
        self.buttonBox.rejected.connect(preferencesDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(preferencesDialog)

    def retranslateUi(self, preferencesDialog):
        _translate = QtCore.QCoreApplication.translate
        preferencesDialog.setWindowTitle(_translate("preferencesDialog", "Preferences"))
        self.checkForUpdates.setText(_translate("preferencesDialog", "Check for Updates on startup?"))
        self.checkForBetaUpdates.setText(_translate("preferencesDialog", "Include Beta Versions?"))
        self.systemLayoutLabel.setText(_translate("preferencesDialog", "System"))
