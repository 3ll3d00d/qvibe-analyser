import numpy as np

from common import RingBuffer


class Signal:

    def __init__(self, data, fs):
        self.__data = data
        self.__fs = fs

    @staticmethod
    def create(rb, config):
        return Signal(np.require(rb.unwrap(), requirements='O'), config.fs)


class SignalStore:

    def __init__(self):
        self.__signals = {}

    def store(self, device, signal):
        if device not in self.__signals:
            self.__signals[device] = RingBuffer(20, dtype=np.object)
        self.__signals[device].append(signal)
