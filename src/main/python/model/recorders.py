import json
import logging
import time

import numpy as np
from qtpy.QtCore import QRunnable, QObject, Signal, QTimer
from qtpy.QtNetwork import QTcpSocket

from common import RingBuffer

logger = logging.getLogger('qvibe.recorders')


class RecorderStore:
    def __init__(self):
        self.__recorders = []

    def connect(self, ip_address, target_config):
        rec = self.__get_recorder(ip_address)
        if rec is None:
            rec = Recorder(ip_address, target_config)
            self.__recorders.append(rec)
        rec.connect()
        return rec

    def disconnect(self, ip_address):
        rec = self.__get_recorder(ip_address)
        if rec is not None:
            rec.disconnect()

    def __get_recorder(self, ip_address):
        rec = next((r for r in self.__recorders if r.ip_address == ip_address), None)
        return rec

    def snap(self):
        # TODO support n recorders
        if len(self.__recorders) > 0:
            rec = self.__recorders[0]
            if rec.connected is True:
                return rec.snap()
        return None


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


class RecorderSignals(QObject):
    on_status_change = Signal(bool, bool)


class Recorder:

    def __init__(self, ip_address, target_config):
        self.signals = RecorderSignals()
        self.__timer = QTimer()
        self.__ip_address = ip_address
        self.__target_config = target_config
        self.__name = None
        self.__config = None
        self.__connected = False
        self.__listener = None
        self.__recording = False
        # TODO get duration to keep
        self.__buffer = self.__make_new_buffer()

    def __make_new_buffer(self):
        return RingBuffer(self.__target_config.fs * 30, dtype=(np.float64, self.__target_config.value_len))

    @property
    def ip_address(self):
        return self.__ip_address

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
            self.__emit_status()

    def __emit_status(self):
        self.signals.on_status_change.emit(self.__connected, self.__recording)

    def connect(self):
        logger.info(f"Connecting to {self.ip_address}")
        if self.__listener is None:
            self.__listener = RecorderListener()
            self.__listener.signals.on_state_change.connect(self.__on_state_change)
            self.__listener.signals.on_data.connect(self.__handle_data)
            self.__listener.ip = self.ip_address
        if self.__connected is False:
            self.__listener.connect()

    def __on_state_change(self, new_state):
        if new_state == 3:
            self.__connected = True
        else:
            self.__connected = False
            self.recording = False
        self.__emit_status()

    def __handle_data(self, data):
        rcv = data
        cmd = rcv[0:3]
        dat = data[4:]
        if cmd == 'DAT':
            if self.__recording is True:
                records = np.array([np.fromstring(r, sep='#', dtype=np.float64) for r in dat.split('|')])
                self.__buffer.extend(records)
                # TODO record no of events received in last x seconds, calculate actual sample rate
                # if self.__buffer.is_full:
                #     if self.__buffer.idx[1] % 100 == 0:
                        # self.signals.on_status_change.emit(self.__format_status())
                # elif len(self.__buffer) % 100 == 0:
                #     self.signals.on_status_change.emit(self.__format_status())
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
            logger.info(f"Disconnecting from {self.ip_address}")
            self.__listener.kill()
            logger.info(f"Disconnected from {self.ip_address}")

    def snap(self):
        '''
        :return: a copy of the current data.
        '''
        return self.__buffer.unwrap()


class RecorderListenerSignals(QObject):
    on_state_change = Signal(int)
    on_data = Signal(str)
    send_target = Signal(RecorderConfig)


class RecorderListener(QRunnable):

    def __init__(self):
        super().__init__()
        self.__ip = None
        self.signals = RecorderListenerSignals()
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

    def connect(self):
        if self.__ip is not None:
            ip, port = self.__ip.split(':')
            self.__socket.connectToHost(ip, int(port))

    def __on_state_change(self, new_state):
        if self.__state != new_state:
            logger.info(f"Connection state change from {self.__state} to {new_state}")
            # TODO 0 unconnected, 3 connected, 6 closing
            self.__state = new_state
            self.signals.on_state_change.emit(new_state)

    def run(self):
        while self.__run:
            time.sleep(1)

    def __on_data(self):
        while self.__socket.canReadLine():
            self.signals.on_data.emit(str(self.__socket.readLine().data(), encoding='utf-8'))

    def __send_target_state(self, target_state):
        msg = f"SET|{json.dumps(target_state.to_dict())}\r\n'".encode()
        logger.info(f"Sending {msg} to {self.ip}")
        res = self.__socket.write(msg)
        if self.__socket.flush() is True:
            logger.info(f"Sent {res} byte SET msg to {self.ip}")
        else:
            logger.warning(f"SET message was not sent to {self.ip}, {res} bytes sent")

    def kill(self):
        self.__run = False
        self.__socket.disconnectFromHost()
