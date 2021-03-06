import json
import logging
import math
import time
from collections import Sequence

import numpy as np
import qtawesome as qta
from qtpy import QtWidgets
from qtpy.QtCore import QObject, Signal, QThreadPool
from qtpy.QtWidgets import QMessageBox
from twisted.internet.protocol import connectionDone
from twisted.protocols.basic import LineReceiver

from common import RingBuffer
from model.log import to_millis

logger = logging.getLogger('qvibe.recorders')


class RecorderSignals(QObject):
    on_status_change = Signal(str, bool)


class Recorder:

    def __init__(self, ip_address, idx, parent_layout, parent, target_config, reactor):
        ''' Adds widgets to the main screen to display another recorder. '''
        self.__ip_address = ip_address
        self.__target_config = target_config
        self.signals = RecorderSignals()
        self.__reset_on_snap = False
        self.__name = None
        self.__reactor = reactor
        self.__listener = None
        self.__snap_idx = 0
        self.__buffer = []
        self.__parent_layout = parent_layout
        # init the widgets on screen which control it
        self.__recorder_layout = QtWidgets.QVBoxLayout()
        self.__recorder_layout.setObjectName(f"recorders_layout_{idx}")
        self.__connect_button = QtWidgets.QPushButton(parent)
        self.__connect_button.setText('Connect')
        self.__connect_button.setObjectName(f"connect_recorder_button_{idx}")
        self.__connect_button.clicked.connect(self.connect)
        self.__connect_button.setIcon(qta.icon('fa5s.sign-in-alt'))
        self.__disconnect_button = QtWidgets.QPushButton(parent)
        self.__disconnect_button.setText('Disconnect')
        self.__disconnect_button.setObjectName(f"disconnect_recorder_button_{idx}")
        self.__disconnect_button.clicked.connect(self.disconnect)
        self.__disconnect_button.setIcon(qta.icon('fa5s.sign-out-alt'))
        self.__disconnect_button.setEnabled(False)
        self.__ip_address_label = QtWidgets.QLabel(parent)
        self.__ip_address_label.setObjectName(f"ip_address_{idx}")
        self.__ip_address_label.setText(ip_address)
        self.__connected = QtWidgets.QCheckBox(parent)
        self.__connected.setObjectName(f"connected_{idx}")
        self.__connected.setText('Connected?')
        self.__connected.setEnabled(False)
        self.__recording = QtWidgets.QCheckBox(parent)
        self.__recording.setObjectName(f"recording_{idx}")
        self.__recording.setText('Recording?')
        self.__recording.setEnabled(False)
        self.__button_layout = QtWidgets.QHBoxLayout()
        self.__recorder_layout.addWidget(self.__ip_address_label)
        self.__button_layout.addWidget(self.__connect_button)
        self.__button_layout.addWidget(self.__disconnect_button)
        self.__recorder_layout.addLayout(self.__button_layout)
        self.__checkbox_layout = QtWidgets.QHBoxLayout()
        self.__checkbox_layout.addWidget(self.__connected)
        self.__checkbox_layout.addWidget(self.__recording)
        self.__recorder_layout.addLayout(self.__checkbox_layout)
        self.__parent_layout.addLayout(self.__recorder_layout)

    def __handle_status_change(self):
        ''' Updates various fields to reflect recorder status. '''
        is_connected = self.__connected.isChecked()
        self.__connect_button.setEnabled(not is_connected)
        self.__disconnect_button.setEnabled(is_connected)
        self.signals.on_status_change.emit(self.ip_address, is_connected)

    @property
    def ip_address(self):
        return self.__ip_address

    @property
    def name(self):
        return self.__name

    @property
    def target_config(self):
        return self.__target_config

    @target_config.setter
    def target_config(self, target_config):
        if target_config != self.__target_config:
            self.__target_config = target_config
            if self.__listener is not None:
                self.__listener.signals.send_target(target_config)

    @property
    def connected(self):
        return self.__connected.isChecked()

    @connected.setter
    def connected(self, connected):
        if connected != self.__connected.isChecked():
            logger.info(f"Connected state changing from {self.__connected.isChecked()} to {connected}")
            self.__connected.setChecked(connected)
            self.__handle_status_change()

    @property
    def recording(self):
        return self.__recording.isChecked()

    @recording.setter
    def recording(self, recording):
        if recording != self.__recording.isChecked():
            logger.info(f"Recording state changing from {self.__recording.isChecked()} to {recording}")
            self.__recording.setChecked(recording)

    def connect(self):
        ''' Creates a RecorderListener if required and then connects it. '''
        logger.info(f"Connecting to {self.ip_address}")
        if self.__listener is None:
            self.__listener = RecorderTwistedBridge(self.__reactor)
            self.__listener.signals.on_socket_state_change.connect(self.__on_state_change)
            self.__listener.signals.on_data.connect(self.__handle_data)
            self.__listener.ip = self.ip_address
        if self.connected is False:
            self.__reactor.callFromThread(self.__listener.connect)

    def __on_state_change(self, new_state):
        '''
        Reacts to connection state changes to determine if we are connected or not
        propagates that status via a signal
        '''
        if new_state == 1:
            self.connected = True
        else:
            self.connected = False
            self.recording = False
            if new_state != 0:
                msg_box = QMessageBox()
                msg_box.setText(f"Failed to connect to: \n\n {self.ip_address}")
                msg_box.setIcon(QMessageBox.Critical)
                msg_box.setWindowTitle('Connection Failed')
                msg_box.exec()

    def __handle_data(self, data):
        '''
        Main protocol handler which can react to data updates by recording them in the buffer and config updates by
        validating device state to enable recording to start or sending new config if required.
        '''
        rcv = data
        cmd = rcv[0:3]
        dat = data[4:]
        if cmd == 'DAT':
            if self.recording is True:
                if len(dat) > 0:
                    records = np.array([np.fromstring(r, sep='#', dtype=np.float64) for r in dat.split('|')])
                    if records.size > 0:
                        logger.debug(f"Buffering DAT {records[0,0]} - {records[-1,0]}")
                        # if the last record has a sample idx less than the first one then it must have suffered an overflow
                        if len(self.__buffer) > 0 and records[:, 0][-1] <= records[:, 0][0]:
                            logger.error(f"Sensor {self.ip_address} has overflowed")
                            self.__reset_on_snap = True
                        self.__buffer.extend(records)
                    else:
                        logger.error(f"Received empty array {dat}")
                        self.__reset_on_snap = True
                else:
                    logger.error(f"Received empty array {dat}")
                    self.__reset_on_snap = True
        elif cmd == 'DST':
            logger.info(f"Received DST {dat}")
            if RecorderConfig.from_dict(json.loads(dat)[0]) == self.__target_config:
                self.recording = True
            else:
                self.recording = False
                self.__listener.signals.send_target.emit(self.__target_config)
        elif cmd == 'STR':
            pass
        elif rcv == 'ERROR':
            logger.error(f"Received ERROR from {self.ip_address}")
            self.__reset_on_snap = True
        else:
            logger.error(f"Received unknown payload from {self.ip_address} - {rcv}")

    def disconnect(self):
        ''' Disconnects the listener if we have one. '''
        if self.__listener is not None:
            logger.info(f"Disconnecting from {self.ip_address}")
            self.__listener.kill()
            self.__listener = None
            QThreadPool.globalInstance().releaseThread()
            logger.info(f"Disconnected from {self.ip_address}")

    def snap(self):
        '''
        :return: a 5 entry tuple with
        - the ip of the recorder
        - data since the last snap
        - the snap idx
        - whether the sensor has overflowed since the last snap
        '''
        errored = self.__reset_on_snap
        if self.__reset_on_snap is True:
            self.__reset_on_snap = False
        start = time.time()
        b = np.array(self.__buffer)
        self.__buffer = []
        self.__snap_idx += 1
        end = time.time()
        logger.debug(f"Snap {self.__snap_idx} : {b.shape[0]} in {to_millis(start, end)}ms")
        return self.ip_address, b, self.__snap_idx, errored

    def reset(self):
        self.__buffer = []

    def destroy(self):
        logger.info(f"Destroying {self.ip_address}")
        self.disconnect()
        self.signals.disconnect()
        self.__parent_layout.removeItem(self.__recorder_layout)

    def replace(self, data):
        '''
        Replaces the current data with the supplied data. Intended to be used by loading.
        :param data: the data.
        '''
        self.reset()
        self.__buffer.extend(data)


class RecorderStore(Sequence):
    '''
    Stores all recorders known to the system.
    '''
    def __init__(self, target_config, parent_layout, parent, reactor, measurement_store):
        self.signals = RecorderSignals()
        self.__measurement_store = measurement_store
        self.__parent_layout = parent_layout
        self.__spacer_item = QtWidgets.QSpacerItem(20, 40,
                                                   QtWidgets.QSizePolicy.Minimum,
                                                   QtWidgets.QSizePolicy.Expanding)
        self.__parent_layout.addItem(self.__spacer_item)
        self.__parent = parent
        self.__recorders = []
        self.__target_config = target_config
        self.__reactor = reactor

    @property
    def target_config(self):
        return self.__target_config

    @target_config.setter
    def target_config(self, target_config):
        self.__target_config = target_config
        for r in self:
            r.target_config = target_config

    def append(self, ip_address):
        ''' adds a new recorder. '''
        self.__parent_layout.removeItem(self.__spacer_item)
        rec = Recorder(ip_address, len(self.__recorders), self.__parent_layout, self.__parent, self.__target_config,
                       self.__reactor)
        self.__parent_layout.addItem(self.__spacer_item)
        rec.signals.on_status_change.connect(self.__on_recorder_connect_event)
        self.__recorders.append(rec)
        return rec

    def replace(self, ip, data):
        rec = next((r for r in self if r.ip_address == ip), None)
        if rec is None:
            logger.info(f"Loading new recorder at {ip}")
            rec = self.append(ip)
        rec.replace(data)

    def load(self, ip_addresses):
        ''' Creates recorders for all given IP addresses. '''
        for ip in ip_addresses:
            if next((r for r in self if r.ip_address == ip), None) is None:
                logger.info(f"Loading new recorder at {ip}")
                self.append(ip)
                self.__measurement_store.append('rta', ip, None)

        to_remove = [r for r in self if r.ip_address not in ip_addresses]
        for r in to_remove:
            logger.info(f"Discarding recorder from {r.ip_address}")
            self.__recorders.remove(r)
            self.__measurement_store.remove('rta', r.ip_address)
            r.destroy()

    def clear(self):
        ''' eliminates all recorders '''
        self.load([])

    def __getitem__(self, i):
        return self.__recorders[i]

    def __len__(self):
        return len(self.__recorders)

    def snap(self, connected_only=True):
        '''
        :return: current data for each recorder.
        '''
        return [r.snap() for r in self if connected_only is False or r.connected is True]

    def reset(self):
        ''' clears all cached data. '''
        for rec in self:
            rec.reset()

    def __on_recorder_connect_event(self, ip, connected):
        '''
        propagates a recorder status change.
        :param ip: the ip.
        :param connected: if it is connected.
        '''
        self.signals.on_status_change.emit(ip, connected)

    def any_connected(self):
        '''
        :return: True if any recorded is connected.
        '''
        return any(r.connected is True for r in self)

    def connect(self):
        ''' connects all recorders '''
        for r in self:
            r.connect()

    def disconnect(self):
        ''' disconnects all recorders '''
        for r in self:
            r.disconnect()


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


class RecorderSocketBridgeSignals(QObject):
    on_socket_state_change = Signal(int)
    on_data = Signal(str)
    send_target = Signal(RecorderConfig)


class RecorderTwistedBridge:

    def __init__(self, reactor):
        super().__init__()
        self.__reactor = reactor
        self.__ip = None
        self.signals = RecorderSocketBridgeSignals()
        self.__endpoint = None
        self.__protocol = None
        self.__connect = None
        self.__state = 0
        self.signals.send_target.connect(self.__send_target_state)

    @property
    def ip(self):
        return self.__ip

    @ip.setter
    def ip(self, ip):
        self.__ip = ip

    def connect(self):
        ''' Runs the twisted reactor. '''
        from twisted.internet.endpoints import TCP4ClientEndpoint
        from twisted.internet.endpoints import connectProtocol
        logger.info(f"Starting Twisted endpoint on {self.ip}")
        ip, port = self.ip.split(':')
        self.__endpoint = TCP4ClientEndpoint(self.__reactor, ip, int(port))
        self.__protocol = RecorderProtocol(self.signals.on_data, self.__on_state_change)
        self.__connect = connectProtocol(self.__endpoint, self.__protocol)
        self.__reactor.callLater(1, self.__cancel_if_not_connected)

    def __cancel_if_not_connected(self):
        if self.__state != 1:
            logger.info(f"Cancelling connection to {self.ip} on timeout")
            self.__connect.cancel()
            self.__on_state_change(2)
            self.kill()
            self.__on_state_change(0)

    def __on_state_change(self, new_state):
        ''' socket connection state change handler '''
        if self.__state != new_state:
            logger.info(f"Connection state change from {self.__state} to {new_state}")
            self.__state = new_state
            self.signals.on_socket_state_change.emit(new_state)

    def __send_target_state(self, target_state):
        ''' writes a SET command to the socket. '''
        msg = f"SET|{json.dumps(target_state.to_dict())}\r\n'".encode()
        logger.info(f"Sending {msg} to {self.ip}")
        self.__protocol.write(msg)
        logger.info(f"Sent {msg} to {self.ip}")

    def kill(self):
        ''' Tells the reactor to stop running and disconnects the socket. '''
        if self.__protocol is not None:
            if self.__protocol.transport is not None:
                logger.info("Stopping the twisted protocol")
                self.__protocol.transport.loseConnection()
                logger.info("Stopped the twisted protocol")
            elif self.__connect is not None:
                logger.info("Cancelling connection attempt")
                self.__reactor.callFromThread(self.__connect.cancel)
                logger.info("Cancelled connection attempt")


class RecorderProtocol(LineReceiver):
    ''' Bridges the twisted network handler to/from Qt signals. '''

    def __init__(self, on_data, on_state_change):
        super().__init__()
        self.__on_data = on_data
        self.__on_state_change = on_state_change

    def rawDataReceived(self, data):
        pass

    def connectionMade(self):
        logger.info("Connection established, sending state change")
        self.transport.setTcpNoDelay(True)
        self.__on_state_change(1)

    def connectionLost(self, reason=connectionDone):
        logger.info(f"Connection lost because {reason}, sending state change")
        self.__on_state_change(0)

    def lineReceived(self, line):
        logger.debug("Emitting DAT")
        self.__on_data.emit(line.decode())

    def write(self, line):
        ''' writes a SET command to the socket. '''
        logger.debug("Sending SET")
        self.sendLine(line)
