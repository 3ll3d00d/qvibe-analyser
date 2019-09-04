import gzip
import json
import logging

import numpy as np
import qtawesome as qta
from qtpy import QtWidgets, QtCore
from qtpy.QtWidgets import QFileDialog
from qtpy.QtCore import QObject, Signal

from common import np_to_str
from model.preferences import SNAPSHOT_GROUP

logger = logging.getLogger('qvibe.measurements')


class MeasurementStoreSignals(QObject):
    data_changed = Signal(object)
    visibility_changed = Signal(object)
    measurement_added = Signal(object)
    measurement_deleted = Signal(object)


class MeasurementStore:
    def __init__(self, parent_layout, parent_widget, preferences):
        self.signals = MeasurementStoreSignals()
        self.preferences = preferences
        self.__parent_layout = parent_layout
        self.__parent_widget = parent_widget
        self.__measurements = []
        self.__uis = []
        self.__spacer_item = QtWidgets.QSpacerItem(20, 40,
                                                   QtWidgets.QSizePolicy.Minimum,
                                                   QtWidgets.QSizePolicy.Expanding)
        self.__parent_layout.addItem(self.__spacer_item)

    def __iter__(self):
        return iter(self.__measurements)

    def load_snapshots(self):
        '''
        Loads snapshots from preferences into the measurement store.
        '''
        self.preferences.enter(SNAPSHOT_GROUP)
        for id in self.preferences.get_children():
            self.preferences.enter(id)
            for ip in self.preferences.get_children():
                import io
                self.add_snapshot(id, ip, np.loadtxt(io.StringIO(self.preferences.get(ip)), dtype=np.float64, ndmin=2))
            self.preferences.exit()
        self.preferences.exit()

    def get_visible_measurements(self):
        '''
        :return: the key for each visible measurement.
        '''
        return [m.key for m in self.__measurements if m.visible is True]

    def add_snapshot(self, id, ip, data):
        self.add(f"snapshot{id}", ip, data)

    def add(self, name, ip, data, data_idx=-1):
        '''
        Puts the named measurement in the store.
        :param name: the measurement name.
        :param ip: the ip address.
        :param data: the associated data.
        '''
        idx = next((idx for idx, m in enumerate(self) if m.name == name and m.ip == ip), None)
        if idx is not None:
            self.__measurements[idx].idx = data_idx
            self.__measurements[idx].data = data
        else:
            m = Measurement(name, ip, data, data_idx, self.signals)
            self.__measurements.append(m)
            self.__parent_layout.removeItem(self.__spacer_item)
            if len(self.__uis) >= len(self.__measurements):
                ui = self.__uis[len(self.__measurements) - 1]
                ui.render(m)
            else:
                ui = MeasurementUI(self.__parent_layout, self.__parent_widget, self.__delete, self.__export)
                ui.render(m)
                self.__uis.append(ui)
            self.__parent_layout.addItem(self.__spacer_item)
            self.signals.measurement_added.emit(m)

    def remove(self, name, ip):
        '''
        Deletes the measurement.
        :param name: the measurement name.
        :param ip: the ip.
        '''
        to_remove = [m for m in self if m.name == name and m.ip == ip]
        for m in to_remove:
            self.__delete(m)

    def __delete(self, measurement):
        '''
        Deletes the measurement.
        :param measurement: the measurement.
        '''
        idx = self.__measurements.index(measurement)
        if idx > -1:
            m = self.__measurements.pop(idx)
            logger.info(f"Deleted {m.key}")
            ui = self.__uis.pop(idx)
            ui.delete()
            self.__uis.append(ui)
            self.signals.measurement_deleted.emit(m)
            if measurement.name.startswith('snapshot'):
                self.preferences.clear(f"{SNAPSHOT_GROUP}/{m.name[8:]}/{m.ip}")

    def __export(self, measurement):
        '''
        Exports the measurement to a file.
        :param measurement: the measurement.
        '''
        file_name = QFileDialog.getSaveFileName(caption='Export Signal', directory=f"{measurement.name}.qvibe", filter="QVibe Signals (*.qvibe)")
        file_name = str(file_name[0]).strip()
        if len(file_name) > 0:
            with gzip.open(file_name, 'wb+') as outfile:
                outfile.write(json.dumps({measurement.ip: np_to_str(measurement.data)}).encode('utf-8'))


class Measurement:

    def __init__(self, name, ip, data, idx, signals, visible=True):
        self.__name = name
        self.__ip = ip
        self.__data = data
        self.__visible = visible
        self.__idx = idx
        self.__signals = signals
        self.__ui = None

    @property
    def key(self):
        return f"{self.name} - {self.ip}"

    @property
    def name(self):
        return self.__name

    @property
    def ip(self):
        return self.__ip

    @property
    def data(self):
        return self.__data

    @data.setter
    def data(self, data):
        self.__data = data
        self.__signals.data_changed.emit(self)

    @property
    def idx(self):
        return self.__idx

    @idx.setter
    def idx(self, idx):
        self.__idx = idx

    @property
    def visible(self):
        return self.__visible

    @visible.setter
    def visible(self, visible):
        self.__visible = visible
        self.__signals.visibility_changed.emit(self)

    def __repr__(self):
        return f"{self.name}:{self.ip}:{self.idx}:{self.visible}"


class MeasurementUI:
    def __init__(self, parent_layout, parent_widget, delete_func, export_func):
        self.__measurement = None
        self.__delete_func = delete_func
        self.__export_func = export_func
        self.__parent_layout = parent_layout
        self.__parent_widget = parent_widget
        self.__frame = QtWidgets.QFrame(self.__parent_widget)
        self.__frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.__frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.__layout = QtWidgets.QVBoxLayout(self.__frame)
        self.__visible_button = QtWidgets.QPushButton(self.__frame)
        self.__visible_button.setText('Show Data')
        self.__visible_button.setCheckable(True)
        self.__delete_button = QtWidgets.QToolButton(self.__frame)
        self.__delete_button.setIcon(qta.icon('fa5s.times', color='red'))
        self.__export_button = QtWidgets.QToolButton(self.__frame)
        self.__export_button.setIcon(qta.icon('fa5s.download'))
        self.__button_layout = QtWidgets.QHBoxLayout()
        self.__label = QtWidgets.QLabel(self.__frame)
        self.__label.setAlignment(QtCore.Qt.AlignCenter)
        self.__layout.addWidget(self.__label)
        self.__layout.addLayout(self.__button_layout)
        self.__button_layout.addWidget(self.__visible_button)
        self.__button_layout.addWidget(self.__delete_button)
        self.__button_layout.addWidget(self.__export_button)
        self.__frame.setVisible(False)
        self.__parent_layout.addWidget(self.__frame)

    def render(self, measurement):
        '''
        renders the measurement on the screen.
        :param measurement: the measurement to render.
        '''
        if not self.__frame.isVisible():
            self.__parent_layout.addWidget(self.__frame)
            self.__frame.setVisible(True)
        if self.__measurement != measurement:
            self.__visible_button.disconnect()
            self.__delete_button.disconnect()
            self.__export_button.disconnect()

            def set_viz(t):
                measurement.visible = t
            self.__visible_button.toggled[bool].connect(set_viz)
            if measurement.visible is True:
                self.__visible_button.setChecked(True)
            self.__delete_button.setVisible(measurement.name != 'rta')
            is_snapshot = measurement.name.startswith('snapshot')
            self.__export_button.setVisible(is_snapshot)
            self.__export_button.setEnabled(is_snapshot)
            self.__export_button.clicked.connect(lambda: self.__export_func(measurement))
            self.__label.setText(measurement.key)
            self.__delete_button.clicked.connect(lambda: self.__delete_func(measurement))

    def delete(self):
        ''' hides the frame. '''
        self.__visible_button.setChecked(False)
        self.__frame.setVisible(False)
        self.__parent_layout.removeWidget(self.__frame)
