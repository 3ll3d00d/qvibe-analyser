import json
import logging
import time

import numpy as np
import qtawesome as qta
from qtpy.QtCore import QRunnable, QObject, Signal, QByteArray
from qtpy.QtNetwork import QTcpSocket, QAbstractSocket
from qtpy.QtWidgets import QDialog

from common import block_signals, RingBuffer
from model.preferences import RECORDER_TARGET_FS, RECORDER_TARGET_SAMPLES_PER_BATCH, RECORDER_TARGET_ACCEL_ENABLED, \
    RECORDER_TARGET_ACCEL_SENS, RECORDER_TARGET_GYRO_ENABLED, RECORDER_TARGET_GYRO_SENS, RECORDER_SAVED_IPS
from ui.recorders import Ui_recordersDialog

logger = logging.getLogger('qvibe.recorders')


class RecorderStore:
    def __init__(self):
        self.__recorders = []

    def connect(self, ip_address, port, target_config):
        rec = Recorder(ip_address, port, target_config)
        self.__recorders.append(rec)
        rec.connect()

    def disconnect(self, ip_address):
        rec = next((r for r in self.__recorders if r.ip_address == ip_address), None)
        if rec is not None:
            rec.disconnect()


class RecorderConfig:
    def __init__(self):
        self.__fs = None
        self.__value_len = 2
        self.__samples_per_batch = None
        self.__accelerometer_enabled = False
        self.__accelerometer_sens = None
        self.__gyro_enabled = False
        self.__gyro_sens = None

    def to_dict(self):
        return {
            'fs': self.fs,
            'sPB': self.samples_per_batch,
            'aOn': self.accelerometer_enabled,
            'aSens': self.accelerometer_sens,
            'gOn': self.gyro_enabled,
            'gSens': self.gyro_sens
        }

    @staticmethod
    def from_dict(d):
        rc = RecorderConfig()
        if 'fs' in d:
            rc.__fs = d['fs']
        if 'sPB' in d:
            rc.__samples_per_batch = d['sPB']
        if 'aOn' in d:
            rc.__accelerometer_enabled = d['aOn']
        if 'aSens' in d:
            rc.__accelerometer_sens = d['aSens']
        if 'gOn' in d:
            rc.__gyro_enabled = d['gOn']
        if 'gSens' in d:
            rc.__gyro_sens = d['gSens']
        return rc

    @property
    def fs(self):
        return self.__fs

    @fs.setter
    def fs(self, fs):
        self.__fs = fs

    @property
    def samples_per_batch(self):
        return self.__samples_per_batch

    @samples_per_batch.setter
    def samples_per_batch(self, samples_per_batch):
        self.__samples_per_batch = samples_per_batch

    @property
    def accelerometer_enabled(self):
        return self.__accelerometer_enabled

    @accelerometer_enabled.setter
    def accelerometer_enabled(self, accelerometer_enabled):
        self.__accelerometer_enabled = accelerometer_enabled

    @property
    def accelerometer_sens(self):
        return self.__accelerometer_sens

    @accelerometer_sens.setter
    def accelerometer_sens(self, accelerometer_sens):
        self.__accelerometer_sens = accelerometer_sens
        self.__recalc_len()

    @property
    def gyro_enabled(self):
        return self.__gyro_enabled

    @gyro_enabled.setter
    def gyro_enabled(self, gyro_enabled):
        self.__gyro_enabled = gyro_enabled
        self.__recalc_len()

    @property
    def gyro_sens(self):
        return self.__gyro_sens

    @gyro_sens.setter
    def gyro_sens(self, gyro_sens):
        self.__gyro_sens = gyro_sens

    def __recalc_len(self):
        self.__value_len = 2 \
                           + (3 if self.accelerometer_enabled else 0) \
                           + (3 if self.gyro_enabled else 0)

    @property
    def value_len(self):
        return self.__value_len

    def __eq__(self, other):
        if not isinstance(other, RecorderConfig):
            return NotImplemented
        return self.fs == other.fs \
               and self.samples_per_batch == other.samples_per_batch \
               and self.accelerometer_enabled == other.accelerometer_enabled \
               and self.accelerometer_sens == other.accelerometer_sens \
               and self.gyro_enabled == other.gyro_enabled \
               and self.gyro_sens == other.gyro_sens


class Recorder:

    def __init__(self, ip_address, port, target_config):
        self.__ip_address = ip_address
        self.__port = port
        self.__target_config = target_config
        self.__name = None
        self.__config = None
        self.__connected = False
        self.__listener = None
        self.__recording = False
        # TODO get duration to keep
        self.__buffer = RingBuffer(target_config.fs * 30, dtype=(np.float64, self.__target_config.value_len))

    @property
    def ip_address(self):
        return self.__ip_address

    @property
    def port(self):
        return self.__port

    @property
    def name(self):
        return self.__name

    @property
    def config(self):
        return self.__config

    @property
    def connected(self):
        return self.__connected

    @property
    def recording(self):
        return self.__recording

    @recording.setter
    def recording(self, recording):
        if recording != self.__recording:
            logger.info(f"Recording state changing from {self.__recording} to {recording}")
        self.__recording = recording

    def connect(self):
        logger.info(f"Connecting to {self.ip_address}:{self.port}")
        self.__listener = RecorderListener()
        self.__listener.signals.on_state_change.connect(self.__on_state_change)
        self.__listener.signals.on_data.connect(self.__handle_data)
        self.__listener.ip = self.ip_address
        self.__listener.port = self.port
        self.__listener.connect()

    def __on_state_change(self, new_state):
        self.__connected = new_state
        # TODO callback to the dialog

    def __handle_data(self, data):
        rcv = data
        cmd = rcv[0:3]
        dat = data[4:]
        if cmd == 'DAT':
            if self.__recording is True:
                records = np.array([np.fromstring(r, sep='#', dtype=np.float64) for r in dat.split('|')])
                self.__buffer.extend(records)
        elif cmd == 'DST':
            if RecorderConfig.from_dict(json.loads(dat)[0]) == self.__target_config:
                self.recording = True
            else:
                self.recording = False
                self.__listener.signals.send_target.emit(self.__target_config)
        elif cmd == 'STR':
            pass
        elif rcv == 'ERROR':
            # TODO reset
            pass
        else:
            # TODO unknown
            pass

    def disconnect(self):
        if self.__listener is not None:
            logger.info(f"Disconnecting from {self.ip_address}:{self.port}")
            self.__listener.kill()
            logger.info(f"Disconnected from {self.ip_address}:{self.port}")


class RecordersDialog(QDialog, Ui_recordersDialog):
    '''
    Allows user to add/remove recorders.
    '''

    def __init__(self, recorder_store, preferences, parent=None):
        super(RecordersDialog, self).__init__(parent)
        self.setupUi(self)
        self.__preferences = preferences
        self.__target_config = self.__load_config()
        address = self.__preferences.get(RECORDER_SAVED_IPS)
        if address is not None:
            tokens = address.split(':')
            if len(tokens) == 2:
                self.ipAddress.setText(tokens[0])
                self.port.setValue(int(tokens[1]))
            else:
                self.__preferences.clear(RECORDER_SAVED_IPS)
        self.__display_target_config()
        self.__store = recorder_store
        self.applyTargetButton.setIcon(qta.icon('fa5s.check', color='green'))
        self.resetTargetButton.setIcon(qta.icon('fa5s.undo'))
        self.saveRecordersButton.setIcon(qta.icon('fa5s.save'))
        # self.__recorder = Recorder()
        # self.__recorder.signals.on_data.connect(self.update_spinner)
        # QThreadPool.globalInstance().start(self.__recorder)

    def update_target(self):
        self.__target_config.fs = self.targetSampleRate.value()
        self.__target_config.samples_per_batch = self.targetBatchSize.value()
        self.__target_config.accelerometer_enabled = self.targetAccelEnabled.isChecked()
        self.__target_config.accelerometer_sens = int(self.targetAccelSens.currentText())
        self.__target_config.gyro_enabled = self.targetGyroEnabled.isChecked()
        self.__target_config.gyro_sens = int(self.targetGyroSens.currentText())

    def __load_config(self):
        config = RecorderConfig()
        config.fs = self.__preferences.get(RECORDER_TARGET_FS)
        config.samples_per_batch = self.__preferences.get(RECORDER_TARGET_SAMPLES_PER_BATCH)
        config.accelerometer_enabled = self.__preferences.get(RECORDER_TARGET_ACCEL_ENABLED)
        config.accelerometer_sens = self.__preferences.get(RECORDER_TARGET_ACCEL_SENS)
        config.gyro_enabled = self.__preferences.get(RECORDER_TARGET_GYRO_ENABLED)
        config.gyro_sens = self.__preferences.get(RECORDER_TARGET_GYRO_SENS)
        return config

    def __display_target_config(self):
        with block_signals(self.targetSampleRate):
            self.targetSampleRate.setValue(self.__target_config.fs)
        with block_signals(self.targetBatchSize):
            self.targetBatchSize.setValue(self.__target_config.samples_per_batch)
        with block_signals(self.targetAccelEnabled):
            self.targetAccelEnabled.setChecked(self.__target_config.accelerometer_enabled)
        with block_signals(self.targetAccelSens):
            self.targetAccelSens.setCurrentText(str(self.__target_config.accelerometer_sens))
        with block_signals(self.targetGyroEnabled):
            self.targetGyroEnabled.setChecked(self.__target_config.gyro_enabled)
        with block_signals(self.targetGyroSens):
            self.targetGyroSens.setCurrentText(str(self.__target_config.gyro_sens))

    def connect_recorder(self):
        self.__store.connect(self.ipAddress.text(), self.port.value(), self.__target_config)
        # self.ipAddress.setEnabled(False)

    def disconnect_recorder(self):
        self.__store.disconnect(self.ipAddress.text())
        # self.ipAddress.setEnabled(True)

    def reset_target(self):
        self.__target_config = self.__load_config()
        self.__display_target_config()

    def apply_target(self):
        self.__preferences.set(RECORDER_TARGET_FS, self.__target_config.fs)
        self.__preferences.set(RECORDER_TARGET_SAMPLES_PER_BATCH, self.__target_config.samples_per_batch)
        self.__preferences.set(RECORDER_TARGET_ACCEL_ENABLED, self.__target_config.accelerometer_enabled)
        self.__preferences.set(RECORDER_TARGET_ACCEL_SENS, self.__target_config.accelerometer_sens)
        self.__preferences.set(RECORDER_TARGET_GYRO_ENABLED, self.__target_config.gyro_enabled)
        self.__preferences.set(RECORDER_TARGET_GYRO_SENS, self.__target_config.gyro_sens)
        # TODO apply to connected recorders

    def update_spinner(self, val):
        self.recorderSampleIndex.setValue(val)

    def add_new_recorder(self):
        pass

    def save_recorders(self):
        self.__preferences.set(RECORDER_SAVED_IPS, f"{self.ipAddress.text()}:{self.port.value()}")


class RecorderSignals(QObject):
    on_state_change = Signal(bool)
    on_data = Signal(str)
    send_target = Signal(RecorderConfig)


class RecorderListener(QRunnable):

    def __init__(self):
        super().__init__()
        self.__ip = None
        self.__port = None
        self.signals = RecorderSignals()
        self.__socket = QTcpSocket()
        self.__state = QTcpSocket.UnconnectedState
        self.__run = True
        self.__socket.stateChanged.connect(self.__on_state_change)
        self.__socket.readyRead.connect(self.__on_data)
        self.signals.send_target.connect(self.__send_target_state)

    @property
    def ip(self):
        return self.__ip

    @ip.setter
    def ip(self, ip):
        self.__ip = ip

    @property
    def port(self):
        return self.__port

    @port.setter
    def port(self, port):
        self.__port = port

    def connect(self):
        if self.__ip is not None and self.__port is not None:
            self.__socket.connectToHost(self.__ip, self.__port)

    def __on_state_change(self, new_state):
        logger.info(f"Connection state change from {self.__state} to {new_state}")
        # TODO 0 unconnected, 3 connected, 6 closing
        self.__state = new_state

    def run(self):
        while self.__run:
            time.sleep(1)

    def __on_data(self):
        while self.__socket.canReadLine():
            self.signals.on_data.emit(str(self.__socket.readLine().data(), encoding='utf-8'))

    def __send_target_state(self, target_state):
        msg = f"SET|{json.dumps(target_state.to_dict())}\r\n'".encode()
        logger.info(f"Sending {msg} to {self.ip}:{self.port}")
        res = self.__socket.write(msg)
        if self.__socket.flush() is True:
            logger.info(f"Sent {res} byte SET msg to {self.ip}:{self.port}")
        else:
            logger.warning(f"SET message was not sent to {self.ip}:{self.port}, {res} bytes sent")

    def kill(self):
        self.__run = False
        self.__socket.disconnectFromHost()
