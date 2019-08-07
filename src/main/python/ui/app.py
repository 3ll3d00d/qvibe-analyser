# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'app.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(972, 679)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 972, 30))
        self.menubar.setObjectName("menubar")
        self.menuSettings = QtWidgets.QMenu(self.menubar)
        self.menuSettings.setObjectName("menuSettings")
        self.menu_Help = QtWidgets.QMenu(self.menubar)
        self.menu_Help.setObjectName("menu_Help")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.action_Preferences = QtWidgets.QAction(MainWindow)
        self.action_Preferences.setObjectName("action_Preferences")
        self.actionShow_Logs = QtWidgets.QAction(MainWindow)
        self.actionShow_Logs.setObjectName("actionShow_Logs")
        self.actionRelease_Notes = QtWidgets.QAction(MainWindow)
        self.actionRelease_Notes.setObjectName("actionRelease_Notes")
        self.action_Recorders = QtWidgets.QAction(MainWindow)
        self.action_Recorders.setObjectName("action_Recorders")
        self.menuSettings.addAction(self.action_Recorders)
        self.menuSettings.addAction(self.action_Preferences)
        self.menu_Help.addAction(self.actionShow_Logs)
        self.menu_Help.addAction(self.actionRelease_Notes)
        self.menubar.addAction(self.menuSettings.menuAction())
        self.menubar.addAction(self.menu_Help.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "QVibe Analyser"))
        self.menuSettings.setTitle(_translate("MainWindow", "&Settings"))
        self.menu_Help.setTitle(_translate("MainWindow", "&Help"))
        self.action_Preferences.setText(_translate("MainWindow", "&Preferences"))
        self.actionShow_Logs.setText(_translate("MainWindow", "Show &Logs"))
        self.actionShow_Logs.setShortcut(_translate("MainWindow", "Ctrl+L"))
        self.actionRelease_Notes.setText(_translate("MainWindow", "Release &Notes"))
        self.action_Recorders.setText(_translate("MainWindow", "&Recorders"))
        self.action_Recorders.setShortcut(_translate("MainWindow", "Ctrl+R"))
