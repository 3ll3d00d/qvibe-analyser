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
        MainWindow.resize(1426, 729)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.mainLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.mainLayout.setObjectName("mainLayout")
        self.chartControlLayout = QtWidgets.QVBoxLayout()
        self.chartControlLayout.setObjectName("chartControlLayout")
        self.controlsBox = QtWidgets.QToolBox(self.centralwidget)
        self.controlsBox.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.controlsBox.setFrameShadow(QtWidgets.QFrame.Plain)
        self.controlsBox.setObjectName("controlsBox")
        self.measurementBox = QtWidgets.QWidget()
        self.measurementBox.setGeometry(QtCore.QRect(0, 0, 199, 420))
        self.measurementBox.setObjectName("measurementBox")
        self.measurementLayout = QtWidgets.QVBoxLayout(self.measurementBox)
        self.measurementLayout.setObjectName("measurementLayout")
        self.visibleCurvesLabel = QtWidgets.QLabel(self.measurementBox)
        self.visibleCurvesLabel.setObjectName("visibleCurvesLabel")
        self.measurementLayout.addWidget(self.visibleCurvesLabel)
        self.visibleCurves = QtWidgets.QListWidget(self.measurementBox)
        self.visibleCurves.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.visibleCurves.setResizeMode(QtWidgets.QListView.Fixed)
        self.visibleCurves.setObjectName("visibleCurves")
        item = QtWidgets.QListWidgetItem()
        self.visibleCurves.addItem(item)
        item = QtWidgets.QListWidgetItem()
        self.visibleCurves.addItem(item)
        item = QtWidgets.QListWidgetItem()
        self.visibleCurves.addItem(item)
        item = QtWidgets.QListWidgetItem()
        self.visibleCurves.addItem(item)
        self.measurementLayout.addWidget(self.visibleCurves)
        self.loadMeasurementButton = QtWidgets.QPushButton(self.measurementBox)
        self.loadMeasurementButton.setObjectName("loadMeasurementButton")
        self.measurementLayout.addWidget(self.loadMeasurementButton)
        self.saveSnapshotLabel = QtWidgets.QLabel(self.measurementBox)
        self.saveSnapshotLabel.setObjectName("saveSnapshotLabel")
        self.measurementLayout.addWidget(self.saveSnapshotLabel)
        self.snapshotLayout = QtWidgets.QHBoxLayout()
        self.snapshotLayout.setObjectName("snapshotLayout")
        self.saveSnapshotButton = QtWidgets.QToolButton(self.measurementBox)
        self.saveSnapshotButton.setObjectName("saveSnapshotButton")
        self.snapshotLayout.addWidget(self.saveSnapshotButton)
        self.snapSlotSelector = QtWidgets.QComboBox(self.measurementBox)
        self.snapSlotSelector.setObjectName("snapSlotSelector")
        self.snapSlotSelector.addItem("")
        self.snapSlotSelector.addItem("")
        self.snapSlotSelector.addItem("")
        self.snapshotLayout.addWidget(self.snapSlotSelector)
        self.measurementLayout.addLayout(self.snapshotLayout)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.measurementLayout.addItem(spacerItem)
        self.controlsBox.addItem(self.measurementBox, "")
        self.limitsBox = QtWidgets.QWidget()
        self.limitsBox.setGeometry(QtCore.QRect(0, 0, 199, 420))
        self.limitsBox.setObjectName("limitsBox")
        self.extraControlsLayout = QtWidgets.QGridLayout(self.limitsBox)
        self.extraControlsLayout.setObjectName("extraControlsLayout")
        self.magRangeLabel = QtWidgets.QLabel(self.limitsBox)
        self.magRangeLabel.setObjectName("magRangeLabel")
        self.extraControlsLayout.addWidget(self.magRangeLabel, 2, 0, 2, 1)
        self.magMax = QtWidgets.QSpinBox(self.limitsBox)
        self.magMax.setSuffix("")
        self.magMax.setMaximum(150)
        self.magMax.setProperty("value", 150)
        self.magMax.setObjectName("magMax")
        self.extraControlsLayout.addWidget(self.magMax, 4, 0, 1, 1)
        self.freqLayout = QtWidgets.QHBoxLayout()
        self.freqLayout.setObjectName("freqLayout")
        self.freqMin = QtWidgets.QSpinBox(self.limitsBox)
        self.freqMin.setSuffix("")
        self.freqMin.setMinimum(1)
        self.freqMin.setMaximum(1000)
        self.freqMin.setObjectName("freqMin")
        self.freqLayout.addWidget(self.freqMin)
        self.freqMax = QtWidgets.QSpinBox(self.limitsBox)
        self.freqMax.setSuffix("")
        self.freqMax.setMinimum(1)
        self.freqMax.setMaximum(1000)
        self.freqMax.setProperty("value", 1)
        self.freqMax.setObjectName("freqMax")
        self.freqLayout.addWidget(self.freqMax)
        self.extraControlsLayout.addLayout(self.freqLayout, 1, 0, 1, 1)
        self.magMin = QtWidgets.QSpinBox(self.limitsBox)
        self.magMin.setSuffix("")
        self.magMin.setMaximum(150)
        self.magMin.setObjectName("magMin")
        self.extraControlsLayout.addWidget(self.magMin, 5, 0, 1, 1)
        self.freqLabel = QtWidgets.QLabel(self.limitsBox)
        self.freqLabel.setObjectName("freqLabel")
        self.extraControlsLayout.addWidget(self.freqLabel, 0, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.extraControlsLayout.addItem(spacerItem1, 6, 0, 1, 1)
        self.controlsBox.addItem(self.limitsBox, "")
        self.dataCaptureBox = QtWidgets.QWidget()
        self.dataCaptureBox.setGeometry(QtCore.QRect(0, 0, 199, 420))
        self.dataCaptureBox.setObjectName("dataCaptureBox")
        self.dataCaptureLayout = QtWidgets.QGridLayout(self.dataCaptureBox)
        self.dataCaptureLayout.setObjectName("dataCaptureLayout")
        self.elapsedTime = QtWidgets.QTimeEdit(self.dataCaptureBox)
        self.elapsedTime.setReadOnly(True)
        self.elapsedTime.setCurrentSection(QtWidgets.QDateTimeEdit.MinuteSection)
        self.elapsedTime.setObjectName("elapsedTime")
        self.dataCaptureLayout.addWidget(self.elapsedTime, 4, 1, 1, 1)
        self.bufferSizeLabel = QtWidgets.QLabel(self.dataCaptureBox)
        self.bufferSizeLabel.setObjectName("bufferSizeLabel")
        self.dataCaptureLayout.addWidget(self.bufferSizeLabel, 1, 0, 1, 1)
        self.fps = QtWidgets.QSpinBox(self.dataCaptureBox)
        self.fps.setMinimum(1)
        self.fps.setMaximum(50)
        self.fps.setProperty("value", 20)
        self.fps.setObjectName("fps")
        self.dataCaptureLayout.addWidget(self.fps, 2, 1, 1, 1)
        self.actualFPSLabel = QtWidgets.QLabel(self.dataCaptureBox)
        self.actualFPSLabel.setObjectName("actualFPSLabel")
        self.dataCaptureLayout.addWidget(self.actualFPSLabel, 3, 0, 1, 1)
        self.fpsLabel = QtWidgets.QLabel(self.dataCaptureBox)
        self.fpsLabel.setObjectName("fpsLabel")
        self.dataCaptureLayout.addWidget(self.fpsLabel, 2, 0, 1, 1)
        self.resolutionHz = QtWidgets.QComboBox(self.dataCaptureBox)
        self.resolutionHz.setObjectName("resolutionHz")
        self.resolutionHz.addItem("")
        self.resolutionHz.addItem("")
        self.resolutionHz.addItem("")
        self.resolutionHz.addItem("")
        self.resolutionHz.addItem("")
        self.dataCaptureLayout.addWidget(self.resolutionHz, 0, 1, 1, 1)
        self.label = QtWidgets.QLabel(self.dataCaptureBox)
        self.label.setObjectName("label")
        self.dataCaptureLayout.addWidget(self.label, 4, 0, 1, 1)
        self.actualFPS = QtWidgets.QSpinBox(self.dataCaptureBox)
        self.actualFPS.setEnabled(False)
        self.actualFPS.setMaximum(120)
        self.actualFPS.setObjectName("actualFPS")
        self.dataCaptureLayout.addWidget(self.actualFPS, 3, 1, 1, 1)
        self.bufferSize = QtWidgets.QSpinBox(self.dataCaptureBox)
        self.bufferSize.setMinimum(1)
        self.bufferSize.setMaximum(240)
        self.bufferSize.setProperty("value", 30)
        self.bufferSize.setObjectName("bufferSize")
        self.dataCaptureLayout.addWidget(self.bufferSize, 1, 1, 1, 1)
        self.resolutionHzLabel = QtWidgets.QLabel(self.dataCaptureBox)
        self.resolutionHzLabel.setObjectName("resolutionHzLabel")
        self.dataCaptureLayout.addWidget(self.resolutionHzLabel, 0, 0, 1, 1)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.dataCaptureLayout.addItem(spacerItem2, 5, 1, 1, 1)
        self.controlsBox.addItem(self.dataCaptureBox, "")
        self.sensorConfigBox = QtWidgets.QWidget()
        self.sensorConfigBox.setGeometry(QtCore.QRect(0, 0, 199, 420))
        self.sensorConfigBox.setObjectName("sensorConfigBox")
        self.targetConfigLayout = QtWidgets.QGridLayout(self.sensorConfigBox)
        self.targetConfigLayout.setObjectName("targetConfigLayout")
        self.applyTargetButton = QtWidgets.QToolButton(self.sensorConfigBox)
        self.applyTargetButton.setObjectName("applyTargetButton")
        self.targetConfigLayout.addWidget(self.applyTargetButton, 2, 1, 1, 1)
        self.resetTargetButton = QtWidgets.QToolButton(self.sensorConfigBox)
        self.resetTargetButton.setObjectName("resetTargetButton")
        self.targetConfigLayout.addWidget(self.resetTargetButton, 4, 1, 1, 1)
        self.targetBatchSizeLabel = QtWidgets.QLabel(self.sensorConfigBox)
        self.targetBatchSizeLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.targetBatchSizeLabel.setObjectName("targetBatchSizeLabel")
        self.targetConfigLayout.addWidget(self.targetBatchSizeLabel, 3, 0, 1, 1)
        self.targetGyroLayout = QtWidgets.QVBoxLayout()
        self.targetGyroLayout.setObjectName("targetGyroLayout")
        self.targetGyroEnabled = QtWidgets.QCheckBox(self.sensorConfigBox)
        self.targetGyroEnabled.setObjectName("targetGyroEnabled")
        self.targetGyroLayout.addWidget(self.targetGyroEnabled)
        self.targetGyroSens = QtWidgets.QComboBox(self.sensorConfigBox)
        self.targetGyroSens.setObjectName("targetGyroSens")
        self.targetGyroSens.addItem("")
        self.targetGyroSens.addItem("")
        self.targetGyroSens.addItem("")
        self.targetGyroSens.addItem("")
        self.targetGyroLayout.addWidget(self.targetGyroSens)
        self.targetConfigLayout.addLayout(self.targetGyroLayout, 8, 0, 1, 1)
        self.targetBatchSize = QtWidgets.QSpinBox(self.sensorConfigBox)
        self.targetBatchSize.setMinimum(1)
        self.targetBatchSize.setMaximum(100)
        self.targetBatchSize.setProperty("value", 50)
        self.targetBatchSize.setObjectName("targetBatchSize")
        self.targetConfigLayout.addWidget(self.targetBatchSize, 4, 0, 1, 1)
        self.targetSampleRateLabel = QtWidgets.QLabel(self.sensorConfigBox)
        self.targetSampleRateLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.targetSampleRateLabel.setObjectName("targetSampleRateLabel")
        self.targetConfigLayout.addWidget(self.targetSampleRateLabel, 0, 0, 1, 1)
        self.targetAccelerometerLayout = QtWidgets.QVBoxLayout()
        self.targetAccelerometerLayout.setObjectName("targetAccelerometerLayout")
        self.targetAccelEnabled = QtWidgets.QCheckBox(self.sensorConfigBox)
        self.targetAccelEnabled.setChecked(True)
        self.targetAccelEnabled.setObjectName("targetAccelEnabled")
        self.targetAccelerometerLayout.addWidget(self.targetAccelEnabled)
        self.targetAccelSens = QtWidgets.QComboBox(self.sensorConfigBox)
        self.targetAccelSens.setObjectName("targetAccelSens")
        self.targetAccelSens.addItem("")
        self.targetAccelSens.addItem("")
        self.targetAccelSens.addItem("")
        self.targetAccelSens.addItem("")
        self.targetAccelerometerLayout.addWidget(self.targetAccelSens)
        self.targetConfigLayout.addLayout(self.targetAccelerometerLayout, 6, 0, 1, 1)
        self.gyroLabel = QtWidgets.QLabel(self.sensorConfigBox)
        self.gyroLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.gyroLabel.setObjectName("gyroLabel")
        self.targetConfigLayout.addWidget(self.gyroLabel, 7, 0, 1, 1)
        self.accelerometerLabel = QtWidgets.QLabel(self.sensorConfigBox)
        self.accelerometerLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.accelerometerLabel.setObjectName("accelerometerLabel")
        self.targetConfigLayout.addWidget(self.accelerometerLabel, 5, 0, 1, 1)
        self.targetSampleRate = QtWidgets.QSpinBox(self.sensorConfigBox)
        self.targetSampleRate.setMinimum(100)
        self.targetSampleRate.setMaximum(1000)
        self.targetSampleRate.setProperty("value", 500)
        self.targetSampleRate.setObjectName("targetSampleRate")
        self.targetConfigLayout.addWidget(self.targetSampleRate, 2, 0, 1, 1)
        spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.targetConfigLayout.addItem(spacerItem3, 9, 0, 1, 1)
        self.controlsBox.addItem(self.sensorConfigBox, "")
        self.recorderStatusBox = QtWidgets.QWidget()
        self.recorderStatusBox.setGeometry(QtCore.QRect(0, 0, 199, 420))
        self.recorderStatusBox.setObjectName("recorderStatusBox")
        self.recordersLayout = QtWidgets.QVBoxLayout(self.recorderStatusBox)
        self.recordersLayout.setObjectName("recordersLayout")
        self.controlsBox.addItem(self.recorderStatusBox, "")
        self.chartControlLayout.addWidget(self.controlsBox)
        self.connectButtonsLayout = QtWidgets.QHBoxLayout()
        self.connectButtonsLayout.setObjectName("connectButtonsLayout")
        self.connectAllButton = QtWidgets.QPushButton(self.centralwidget)
        self.connectAllButton.setObjectName("connectAllButton")
        self.connectButtonsLayout.addWidget(self.connectAllButton)
        self.disconnectAllButton = QtWidgets.QPushButton(self.centralwidget)
        self.disconnectAllButton.setObjectName("disconnectAllButton")
        self.connectButtonsLayout.addWidget(self.disconnectAllButton)
        self.chartControlLayout.addLayout(self.connectButtonsLayout)
        self.resetButton = QtWidgets.QPushButton(self.centralwidget)
        self.resetButton.setObjectName("resetButton")
        self.chartControlLayout.addWidget(self.resetButton)
        self.mainLayout.addLayout(self.chartControlLayout)
        self.chartLayout = QtWidgets.QGridLayout()
        self.chartLayout.setContentsMargins(-1, -1, 0, -1)
        self.chartLayout.setObjectName("chartLayout")
        self.chartTabs = QtWidgets.QTabWidget(self.centralwidget)
        self.chartTabs.setObjectName("chartTabs")
        self.vibrationTab = QtWidgets.QWidget()
        self.vibrationTab.setObjectName("vibrationTab")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.vibrationTab)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.rightMarkerLabel = QtWidgets.QLabel(self.vibrationTab)
        self.rightMarkerLabel.setObjectName("rightMarkerLabel")
        self.gridLayout_3.addWidget(self.rightMarkerLabel, 0, 3, 1, 1)
        self.vibrationAnalysis = QtWidgets.QComboBox(self.vibrationTab)
        self.vibrationAnalysis.setObjectName("vibrationAnalysis")
        self.vibrationAnalysis.addItem("")
        self.vibrationAnalysis.addItem("")
        self.vibrationAnalysis.addItem("")
        self.gridLayout_3.addWidget(self.vibrationAnalysis, 0, 0, 1, 1)
        self.zoomInButton = QtWidgets.QToolButton(self.vibrationTab)
        self.zoomInButton.setObjectName("zoomInButton")
        self.gridLayout_3.addWidget(self.zoomInButton, 0, 5, 1, 1)
        self.timeRange = QtWidgets.QDoubleSpinBox(self.vibrationTab)
        self.timeRange.setEnabled(False)
        self.timeRange.setDecimals(3)
        self.timeRange.setSingleStep(0.001)
        self.timeRange.setObjectName("timeRange")
        self.gridLayout_3.addWidget(self.timeRange, 0, 8, 1, 1)
        self.leftMarkerLabel = QtWidgets.QLabel(self.vibrationTab)
        self.leftMarkerLabel.setObjectName("leftMarkerLabel")
        self.gridLayout_3.addWidget(self.leftMarkerLabel, 0, 1, 1, 1)
        self.timeRangeLabel = QtWidgets.QLabel(self.vibrationTab)
        self.timeRangeLabel.setObjectName("timeRangeLabel")
        self.gridLayout_3.addWidget(self.timeRangeLabel, 0, 7, 1, 1)
        self.findPeaksButton = QtWidgets.QPushButton(self.vibrationTab)
        self.findPeaksButton.setObjectName("findPeaksButton")
        self.gridLayout_3.addWidget(self.findPeaksButton, 0, 9, 1, 1)
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_3.addItem(spacerItem4, 0, 10, 1, 1)
        self.leftMarker = QtWidgets.QDoubleSpinBox(self.vibrationTab)
        self.leftMarker.setDecimals(3)
        self.leftMarker.setSingleStep(0.001)
        self.leftMarker.setObjectName("leftMarker")
        self.gridLayout_3.addWidget(self.leftMarker, 0, 2, 1, 1)
        self.zoomOutButton = QtWidgets.QToolButton(self.vibrationTab)
        self.zoomOutButton.setObjectName("zoomOutButton")
        self.gridLayout_3.addWidget(self.zoomOutButton, 0, 6, 1, 1)
        self.rightMarker = QtWidgets.QDoubleSpinBox(self.vibrationTab)
        self.rightMarker.setDecimals(3)
        self.rightMarker.setSingleStep(0.001)
        self.rightMarker.setObjectName("rightMarker")
        self.gridLayout_3.addWidget(self.rightMarker, 0, 4, 1, 1)
        self.liveVibrationChart = PlotWidgetWithDateAxis(self.vibrationTab)
        self.liveVibrationChart.setMidLineWidth(0)
        self.liveVibrationChart.setObjectName("liveVibrationChart")
        self.gridLayout_3.addWidget(self.liveVibrationChart, 1, 0, 1, 11)
        self.chartTabs.addTab(self.vibrationTab, "")
        self.rtaTab = QtWidgets.QWidget()
        self.rtaTab.setObjectName("rtaTab")
        self.rtaLayout = QtWidgets.QVBoxLayout(self.rtaTab)
        self.rtaLayout.setObjectName("rtaLayout")
        self.rtaControlsLayout = QtWidgets.QHBoxLayout()
        self.rtaControlsLayout.setObjectName("rtaControlsLayout")
        self.rtaViewLabel = QtWidgets.QLabel(self.rtaTab)
        self.rtaViewLabel.setObjectName("rtaViewLabel")
        self.rtaControlsLayout.addWidget(self.rtaViewLabel)
        self.rtaView = QtWidgets.QComboBox(self.rtaTab)
        self.rtaView.setObjectName("rtaView")
        self.rtaView.addItem("")
        self.rtaView.addItem("")
        self.rtaView.addItem("")
        self.rtaControlsLayout.addWidget(self.rtaView)
        self.holdTimeLabel = QtWidgets.QLabel(self.rtaTab)
        self.holdTimeLabel.setObjectName("holdTimeLabel")
        self.rtaControlsLayout.addWidget(self.holdTimeLabel)
        self.holdSecs = QtWidgets.QDoubleSpinBox(self.rtaTab)
        self.holdSecs.setDecimals(1)
        self.holdSecs.setMinimum(0.5)
        self.holdSecs.setMaximum(30.0)
        self.holdSecs.setSingleStep(0.1)
        self.holdSecs.setProperty("value", 2.0)
        self.holdSecs.setObjectName("holdSecs")
        self.rtaControlsLayout.addWidget(self.holdSecs)
        self.showLive = QtWidgets.QPushButton(self.rtaTab)
        self.showLive.setCheckable(True)
        self.showLive.setChecked(True)
        self.showLive.setObjectName("showLive")
        self.rtaControlsLayout.addWidget(self.showLive)
        self.showPeak = QtWidgets.QPushButton(self.rtaTab)
        self.showPeak.setCheckable(True)
        self.showPeak.setObjectName("showPeak")
        self.rtaControlsLayout.addWidget(self.showPeak)
        self.showAverage = QtWidgets.QPushButton(self.rtaTab)
        self.showAverage.setCheckable(True)
        self.showAverage.setObjectName("showAverage")
        self.rtaControlsLayout.addWidget(self.showAverage)
        self.showTarget = QtWidgets.QPushButton(self.rtaTab)
        self.showTarget.setCheckable(True)
        self.showTarget.setObjectName("showTarget")
        self.rtaControlsLayout.addWidget(self.showTarget)
        self.targetAdjust = QtWidgets.QDoubleSpinBox(self.rtaTab)
        self.targetAdjust.setDecimals(1)
        self.targetAdjust.setMinimum(-150.0)
        self.targetAdjust.setMaximum(150.0)
        self.targetAdjust.setSingleStep(0.1)
        self.targetAdjust.setObjectName("targetAdjust")
        self.rtaControlsLayout.addWidget(self.targetAdjust)
        self.smoothRta = QtWidgets.QPushButton(self.rtaTab)
        self.smoothRta.setCheckable(True)
        self.smoothRta.setObjectName("smoothRta")
        self.rtaControlsLayout.addWidget(self.smoothRta)
        self.sgWindowLength = QtWidgets.QSpinBox(self.rtaTab)
        self.sgWindowLength.setMinimum(1)
        self.sgWindowLength.setMaximum(201)
        self.sgWindowLength.setSingleStep(2)
        self.sgWindowLength.setProperty("value", 101)
        self.sgWindowLength.setObjectName("sgWindowLength")
        self.rtaControlsLayout.addWidget(self.sgWindowLength)
        self.sgPolyOrder = QtWidgets.QSpinBox(self.rtaTab)
        self.sgPolyOrder.setMinimum(1)
        self.sgPolyOrder.setMaximum(11)
        self.sgPolyOrder.setProperty("value", 7)
        self.sgPolyOrder.setObjectName("sgPolyOrder")
        self.rtaControlsLayout.addWidget(self.sgPolyOrder)
        spacerItem5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.rtaControlsLayout.addItem(spacerItem5)
        self.exportFRD = QtWidgets.QToolButton(self.rtaTab)
        self.exportFRD.setObjectName("exportFRD")
        self.rtaControlsLayout.addWidget(self.exportFRD)
        self.rtaLayout.addLayout(self.rtaControlsLayout)
        self.rtaChart = PlotWidgetForSpectrum(self.rtaTab)
        self.rtaChart.setObjectName("rtaChart")
        self.rtaLayout.addWidget(self.rtaChart)
        self.refCurveLayout = QtWidgets.QHBoxLayout()
        self.refCurveLayout.setObjectName("refCurveLayout")
        self.refCurveLabel = QtWidgets.QLabel(self.rtaTab)
        self.refCurveLabel.setObjectName("refCurveLabel")
        self.refCurveLayout.addWidget(self.refCurveLabel)
        self.refCurve = QtWidgets.QComboBox(self.rtaTab)
        self.refCurve.setObjectName("refCurve")
        self.refCurveLayout.addWidget(self.refCurve)
        spacerItem6 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.refCurveLayout.addItem(spacerItem6)
        self.rtaLayout.addLayout(self.refCurveLayout)
        self.chartTabs.addTab(self.rtaTab, "")
        self.spectrogramTab = QtWidgets.QWidget()
        self.spectrogramTab.setObjectName("spectrogramTab")
        self.gridLayout = QtWidgets.QGridLayout(self.spectrogramTab)
        self.gridLayout.setObjectName("gridLayout")
        self.spectrogramView = GraphicsLayoutWidget(self.spectrogramTab)
        self.spectrogramView.setObjectName("spectrogramView")
        self.gridLayout.addWidget(self.spectrogramView, 0, 0, 1, 1)
        self.chartTabs.addTab(self.spectrogramTab, "")
        self.chartLayout.addWidget(self.chartTabs, 0, 0, 1, 1)
        self.mainLayout.addLayout(self.chartLayout)
        self.mainLayout.setStretch(0, 1)
        self.mainLayout.setStretch(1, 6)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1426, 30))
        self.menubar.setObjectName("menubar")
        self.menuSettings = QtWidgets.QMenu(self.menubar)
        self.menuSettings.setObjectName("menuSettings")
        self.menu_Help = QtWidgets.QMenu(self.menubar)
        self.menu_Help.setObjectName("menu_Help")
        self.menu_File = QtWidgets.QMenu(self.menubar)
        self.menu_File.setObjectName("menu_File")
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
        self.actionSave_Chart = QtWidgets.QAction(MainWindow)
        self.actionSave_Chart.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        self.actionSave_Chart.setObjectName("actionSave_Chart")
        self.actionExport_Wav = QtWidgets.QAction(MainWindow)
        self.actionExport_Wav.setShortcutContext(QtCore.Qt.ApplicationShortcut)
        self.actionExport_Wav.setObjectName("actionExport_Wav")
        self.actionToggle_2 = QtWidgets.QAction(MainWindow)
        self.actionToggle_2.setCheckable(True)
        self.actionToggle_2.setObjectName("actionToggle_2")
        self.actionToggle_1 = QtWidgets.QAction(MainWindow)
        self.actionToggle_1.setCheckable(True)
        self.actionToggle_1.setObjectName("actionToggle_1")
        self.actionToggle_3 = QtWidgets.QAction(MainWindow)
        self.actionToggle_3.setCheckable(True)
        self.actionToggle_3.setObjectName("actionToggle_3")
        self.actionSave_Signal = QtWidgets.QAction(MainWindow)
        self.actionSave_Signal.setObjectName("actionSave_Signal")
        self.actionLoad_Signal = QtWidgets.QAction(MainWindow)
        self.actionLoad_Signal.setObjectName("actionLoad_Signal")
        self.actionExport_FRD = QtWidgets.QAction(MainWindow)
        self.actionExport_FRD.setObjectName("actionExport_FRD")
        self.menuSettings.addAction(self.action_Preferences)
        self.menu_Help.addAction(self.actionShow_Logs)
        self.menu_Help.addAction(self.actionRelease_Notes)
        self.menu_File.addAction(self.actionLoad_Signal)
        self.menu_File.addAction(self.actionSave_Signal)
        self.menu_File.addSeparator()
        self.menu_File.addAction(self.actionExport_Wav)
        self.menu_File.addSeparator()
        self.menu_File.addAction(self.actionSave_Chart)
        self.menubar.addAction(self.menu_File.menuAction())
        self.menubar.addAction(self.menuSettings.menuAction())
        self.menubar.addAction(self.menu_Help.menuAction())

        self.retranslateUi(MainWindow)
        self.controlsBox.setCurrentIndex(0)
        self.chartTabs.setCurrentIndex(0)
        self.resetTargetButton.clicked.connect(MainWindow.reset_target)
        self.applyTargetButton.clicked.connect(MainWindow.apply_target)
        self.targetSampleRate.valueChanged['int'].connect(MainWindow.update_target)
        self.targetBatchSize.valueChanged['int'].connect(MainWindow.update_target)
        self.targetAccelEnabled.stateChanged['int'].connect(MainWindow.update_target)
        self.targetAccelSens.currentIndexChanged['int'].connect(MainWindow.update_target)
        self.targetGyroEnabled.stateChanged['int'].connect(MainWindow.update_target)
        self.targetGyroSens.currentIndexChanged['int'].connect(MainWindow.update_target)
        self.bufferSize.valueChanged['int'].connect(MainWindow.set_buffer_size)
        self.chartTabs.currentChanged['int'].connect(MainWindow.set_visible_chart)
        self.resetButton.clicked.connect(MainWindow.reset_recording)
        self.visibleCurves.itemSelectionChanged.connect(MainWindow.set_visible_curves)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        MainWindow.setTabOrder(self.targetAccelEnabled, self.targetAccelSens)
        MainWindow.setTabOrder(self.targetAccelSens, self.targetGyroEnabled)
        MainWindow.setTabOrder(self.targetGyroEnabled, self.targetGyroSens)
        MainWindow.setTabOrder(self.targetGyroSens, self.resetButton)
        MainWindow.setTabOrder(self.resetButton, self.visibleCurves)
        MainWindow.setTabOrder(self.visibleCurves, self.freqMin)
        MainWindow.setTabOrder(self.freqMin, self.freqMax)
        MainWindow.setTabOrder(self.freqMax, self.resolutionHz)
        MainWindow.setTabOrder(self.resolutionHz, self.bufferSize)
        MainWindow.setTabOrder(self.bufferSize, self.fps)
        MainWindow.setTabOrder(self.fps, self.actualFPS)
        MainWindow.setTabOrder(self.actualFPS, self.elapsedTime)
        MainWindow.setTabOrder(self.elapsedTime, self.chartTabs)
        MainWindow.setTabOrder(self.chartTabs, self.vibrationAnalysis)
        MainWindow.setTabOrder(self.vibrationAnalysis, self.liveVibrationChart)
        MainWindow.setTabOrder(self.liveVibrationChart, self.rtaChart)
        MainWindow.setTabOrder(self.rtaChart, self.rtaView)
        MainWindow.setTabOrder(self.rtaView, self.spectrogramView)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "QVibe Analyser"))
        self.visibleCurvesLabel.setText(_translate("MainWindow", "Visible Curves"))
        __sortingEnabled = self.visibleCurves.isSortingEnabled()
        self.visibleCurves.setSortingEnabled(False)
        item = self.visibleCurves.item(0)
        item.setText(_translate("MainWindow", "x"))
        item = self.visibleCurves.item(1)
        item.setText(_translate("MainWindow", "y"))
        item = self.visibleCurves.item(2)
        item.setText(_translate("MainWindow", "z"))
        item = self.visibleCurves.item(3)
        item.setText(_translate("MainWindow", "sum"))
        self.visibleCurves.setSortingEnabled(__sortingEnabled)
        self.loadMeasurementButton.setText(_translate("MainWindow", "Load"))
        self.saveSnapshotLabel.setText(_translate("MainWindow", "Snapshots"))
        self.snapSlotSelector.setItemText(0, _translate("MainWindow", "1"))
        self.snapSlotSelector.setItemText(1, _translate("MainWindow", "2"))
        self.snapSlotSelector.setItemText(2, _translate("MainWindow", "3"))
        self.controlsBox.setItemText(self.controlsBox.indexOf(self.measurementBox), _translate("MainWindow", "Measurement Selector"))
        self.magRangeLabel.setText(_translate("MainWindow", "Magnitude (dB)"))
        self.freqLabel.setText(_translate("MainWindow", "Freq (Hz)"))
        self.controlsBox.setItemText(self.controlsBox.indexOf(self.limitsBox), _translate("MainWindow", "Chart Limits"))
        self.elapsedTime.setDisplayFormat(_translate("MainWindow", "mm:ss.zzz"))
        self.bufferSizeLabel.setText(_translate("MainWindow", "Buffer"))
        self.actualFPSLabel.setText(_translate("MainWindow", "Actual FPS"))
        self.fpsLabel.setText(_translate("MainWindow", "Target FPS"))
        self.resolutionHz.setItemText(0, _translate("MainWindow", "0.25 Hz"))
        self.resolutionHz.setItemText(1, _translate("MainWindow", "0.5 Hz"))
        self.resolutionHz.setItemText(2, _translate("MainWindow", "1.0 Hz"))
        self.resolutionHz.setItemText(3, _translate("MainWindow", "2.0 Hz"))
        self.resolutionHz.setItemText(4, _translate("MainWindow", "4.0 Hz"))
        self.label.setText(_translate("MainWindow", "Elapsed"))
        self.bufferSize.setSuffix(_translate("MainWindow", " s"))
        self.resolutionHzLabel.setText(_translate("MainWindow", "Resolution"))
        self.controlsBox.setItemText(self.controlsBox.indexOf(self.dataCaptureBox), _translate("MainWindow", "Data Capture"))
        self.applyTargetButton.setText(_translate("MainWindow", "..."))
        self.resetTargetButton.setText(_translate("MainWindow", "..."))
        self.targetBatchSizeLabel.setText(_translate("MainWindow", "Batch Size"))
        self.targetGyroEnabled.setText(_translate("MainWindow", "Enabled?"))
        self.targetGyroSens.setItemText(0, _translate("MainWindow", "250"))
        self.targetGyroSens.setItemText(1, _translate("MainWindow", "500"))
        self.targetGyroSens.setItemText(2, _translate("MainWindow", "1000"))
        self.targetGyroSens.setItemText(3, _translate("MainWindow", "2000"))
        self.targetSampleRateLabel.setText(_translate("MainWindow", "Sample Rate"))
        self.targetAccelEnabled.setText(_translate("MainWindow", "Enabled?"))
        self.targetAccelSens.setItemText(0, _translate("MainWindow", "2"))
        self.targetAccelSens.setItemText(1, _translate("MainWindow", "4"))
        self.targetAccelSens.setItemText(2, _translate("MainWindow", "8"))
        self.targetAccelSens.setItemText(3, _translate("MainWindow", "16"))
        self.gyroLabel.setText(_translate("MainWindow", "Gyro"))
        self.accelerometerLabel.setText(_translate("MainWindow", "Accelerometer"))
        self.targetSampleRate.setSuffix(_translate("MainWindow", " Hz"))
        self.controlsBox.setItemText(self.controlsBox.indexOf(self.sensorConfigBox), _translate("MainWindow", "Sensor Config"))
        self.controlsBox.setItemText(self.controlsBox.indexOf(self.recorderStatusBox), _translate("MainWindow", "Recorder Status"))
        self.connectAllButton.setToolTip(_translate("MainWindow", "Connects all available recorders"))
        self.connectAllButton.setText(_translate("MainWindow", "Connect"))
        self.disconnectAllButton.setToolTip(_translate("MainWindow", "Disconnects all recorders"))
        self.disconnectAllButton.setText(_translate("MainWindow", "Disconnect"))
        self.resetButton.setText(_translate("MainWindow", "Reset"))
        self.rightMarkerLabel.setText(_translate("MainWindow", "Right:"))
        self.vibrationAnalysis.setItemText(0, _translate("MainWindow", "Vibration"))
        self.vibrationAnalysis.setItemText(1, _translate("MainWindow", "Tilt"))
        self.vibrationAnalysis.setItemText(2, _translate("MainWindow", "Raw"))
        self.zoomInButton.setText(_translate("MainWindow", "..."))
        self.leftMarkerLabel.setText(_translate("MainWindow", "Left:"))
        self.timeRangeLabel.setText(_translate("MainWindow", "Range:"))
        self.findPeaksButton.setText(_translate("MainWindow", "Find Peaks"))
        self.zoomOutButton.setText(_translate("MainWindow", "..."))
        self.chartTabs.setTabText(self.chartTabs.indexOf(self.vibrationTab), _translate("MainWindow", "By Time"))
        self.rtaViewLabel.setText(_translate("MainWindow", "View"))
        self.rtaView.setItemText(0, _translate("MainWindow", "avg"))
        self.rtaView.setItemText(1, _translate("MainWindow", "peak"))
        self.rtaView.setItemText(2, _translate("MainWindow", "psd"))
        self.holdTimeLabel.setText(_translate("MainWindow", "Hold Time:"))
        self.holdSecs.setToolTip(_translate("MainWindow", "Seconds of data to include in peak calculation"))
        self.holdSecs.setSuffix(_translate("MainWindow", " s"))
        self.showLive.setText(_translate("MainWindow", "Live"))
        self.showPeak.setText(_translate("MainWindow", "Peak"))
        self.showAverage.setText(_translate("MainWindow", "Average"))
        self.showTarget.setText(_translate("MainWindow", "Target"))
        self.targetAdjust.setSuffix(_translate("MainWindow", " dB"))
        self.smoothRta.setText(_translate("MainWindow", "Smooth"))
        self.exportFRD.setText(_translate("MainWindow", "..."))
        self.refCurveLabel.setText(_translate("MainWindow", "Reference: "))
        self.chartTabs.setTabText(self.chartTabs.indexOf(self.rtaTab), _translate("MainWindow", "RTA"))
        self.chartTabs.setTabText(self.chartTabs.indexOf(self.spectrogramTab), _translate("MainWindow", "Spectrogram"))
        self.menuSettings.setTitle(_translate("MainWindow", "&Settings"))
        self.menu_Help.setTitle(_translate("MainWindow", "&Help"))
        self.menu_File.setTitle(_translate("MainWindow", "&File"))
        self.action_Preferences.setText(_translate("MainWindow", "&Preferences"))
        self.action_Preferences.setShortcut(_translate("MainWindow", "Ctrl+P"))
        self.actionShow_Logs.setText(_translate("MainWindow", "Show &Logs"))
        self.actionShow_Logs.setShortcut(_translate("MainWindow", "Ctrl+L"))
        self.actionRelease_Notes.setText(_translate("MainWindow", "Release &Notes"))
        self.actionSave_Chart.setText(_translate("MainWindow", "Save &Chart"))
        self.actionSave_Chart.setShortcut(_translate("MainWindow", "Ctrl+Shift+S"))
        self.actionExport_Wav.setText(_translate("MainWindow", "Export &WAV"))
        self.actionExport_Wav.setShortcut(_translate("MainWindow", "Ctrl+W"))
        self.actionToggle_2.setText(_translate("MainWindow", "Toggle &2"))
        self.actionToggle_2.setShortcut(_translate("MainWindow", "Ctrl+S, Ctrl+2"))
        self.actionToggle_1.setText(_translate("MainWindow", "Toggle &1"))
        self.actionToggle_1.setShortcut(_translate("MainWindow", "Ctrl+S, Ctrl+1"))
        self.actionToggle_3.setText(_translate("MainWindow", "Toggle &3"))
        self.actionToggle_3.setShortcut(_translate("MainWindow", "Ctrl+S, Ctrl+3"))
        self.actionSave_Signal.setText(_translate("MainWindow", "&Save Signal"))
        self.actionSave_Signal.setShortcut(_translate("MainWindow", "Ctrl+S"))
        self.actionLoad_Signal.setText(_translate("MainWindow", "&Load Signal"))
        self.actionLoad_Signal.setShortcut(_translate("MainWindow", "Ctrl+O"))
        self.actionExport_FRD.setText(_translate("MainWindow", "Export &FRD"))
        self.actionExport_FRD.setShortcut(_translate("MainWindow", "Ctrl+F"))
from pyqtgraph import GraphicsLayoutWidget
from qvibe import PlotWidgetForSpectrum, PlotWidgetWithDateAxis
