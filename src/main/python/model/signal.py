import abc
import logging
import time

import numpy as np
from scipy import signal
from scipy.interpolate import PchipInterpolator

from model.log import to_millis
from model.preferences import SUM_X_SCALE, SUM_Y_SCALE, SUM_Z_SCALE, ANALYSIS_DETREND
from common import np_to_str

SAVGOL_WINDOW_LENGTH = 101
SAVGOL_POLYORDER = 7

ADJUST_BY_3DB = 1 / (2 ** 0.5)
# 1 micro m/s2 in G produces 0dB means 1G = ~140dB, 0.1G = ~120dB, 0.01G = ~100dB, 0.001G = ~80dB and 0.0001G = ~60dB
REF_ACCELERATION_IN_G = (10 ** -6) / 9.80665
X_RESOLUTION = 32769

logger = logging.getLogger('qvibe.signal')


class TriAxisSignal:

    def __init__(self, preferences, measurement_name, data, fs, resolution_shift, idx=-1, mode='vibration',
                 pre_calc=False, view_mode='avg'):
        self.__raw = data
        self.__mode = mode
        self.__view = view_mode
        self.__idx = idx
        self.__measurement_name = measurement_name
        self.__fs = fs
        self.__shape = data[:, 2].shape
        self.__x = Signal(measurement_name, 'x', preferences, data[:, 2], fs, resolution_shift, idx=idx,
                          mode=mode, pre_calc=pre_calc, view_mode=view_mode)
        self.__y = Signal(measurement_name, 'y', preferences, data[:, 3], fs, resolution_shift, idx=idx,
                          mode=mode, pre_calc=pre_calc, view_mode=view_mode)
        self.__z = Signal(measurement_name, 'z', preferences, data[:, 4], fs, resolution_shift, idx=idx,
                          mode=mode, pre_calc=pre_calc, view_mode=view_mode)
        self.__sum = SummedSignal(measurement_name, 'sum', preferences, fs, self.__x, self.__y, self.__z, idx=idx,
                                  pre_calc=pre_calc, view_mode=view_mode)

    @staticmethod
    def decode(prefs, shift, str_format, mode, view):
        '''
        Decodes a signal encoded via encode
        :param prefs: the preferences.
        :param shift: the resolution shift.
        :param str_format: the raw data in str form.
        :param mode: the active mode
        :param view: the active view.
        :return: a TriAxisSignal
        '''
        try:
            measurement_name, idx, dtype, fs, dat = str_format.split('#', maxsplit=5)
            import io
            raw = np.loadtxt(io.StringIO(dat), dtype=dtype, ndmin=2)
            return TriAxisSignal(prefs, measurement_name, raw, int(fs), shift,
                                 idx=int(idx), mode=mode, view_mode=view, pre_calc=True)
        except:
            logger.exception(f"Unable to decode to signal")
            return None

    def encode(self):
        '''
        encodes the minimal data required to persist this signal
        :return: the signal encoded as a string.
        '''
        return f"{self.measurement_name}#{self.__idx}#{self.__raw.dtype}#{self.__fs}#{np_to_str(self.__raw)}"

    @property
    def shape(self):
        return self.__shape

    @property
    def view(self):
        return self.__view

    def set_view(self, view, recalc=True):
        self.__view = view
        self.__x.set_view(view, recalc=recalc)
        self.__y.set_view(view, recalc=recalc)
        self.__z.set_view(view, recalc=recalc)
        self.__sum.set_view(view, recalc=recalc)

    def set_mode(self, mode, recalc=True):
        self.__mode = mode
        self.__x.set_mode(mode, recalc=recalc)
        self.__y.set_mode(mode, recalc=recalc)
        self.__z.set_mode(mode, recalc=recalc)

    def has_data(self, view):
        return self.__x.has_data(view) and self.__y.has_data(view) and self.__z.has_data(view)

    @property
    def measurement_name(self):
        return self.__measurement_name

    @property
    def time(self):
        return self.__raw[:, 0]

    @property
    def x(self):
        return self.__x

    @property
    def y(self):
        return self.__y

    @property
    def z(self):
        return self.__z

    @property
    def sum(self):
        return self.__sum

    @property
    def idx(self):
        return self.__idx

    def recalc(self):
        self.x.recalc()
        self.y.recalc()
        self.z.recalc()
        self.sum.recalc()


class SpectroValues:

    def __init__(self, f, t, Sxx):
        self.f = f
        self.t = t
        self.sxx = Sxx


class Analysis:
    def __init__(self, values):
        self.__x = values[0]
        self.__y_raw = values[1]
        self.__y = values[2]

    @property
    def x(self):
        return self.__x

    @property
    def y(self):
        return self.__y

    @property
    def y_raw(self):
        return self.__y_raw


class AnalysableSignal:
    def __init__(self, measurement_name, axis, preferences, fs, idx=-1, view_mode='avg'):
        self.__measurement_name = measurement_name
        self.__axis = axis
        self.__preferences = preferences
        self.__fs = fs
        self.__view_mode = view_mode
        self.__idx = idx
        self.__output = {}

    @property
    def fs(self):
        return self.__fs

    @property
    def measurement_name(self):
        return self.__measurement_name

    @property
    def axis(self):
        return self.__axis

    @property
    def idx(self):
        return self.__idx

    @abc.abstractmethod
    def recalc(self):
        pass

    @property
    def view_mode(self):
        return self.__view_mode

    @property
    def prefs(self):
        return self.__preferences

    def has_data(self, view):
        return view in self.__output

    def set_view(self, view, recalc=True):
        '''
        Analyses the raw data in the specified mode.
        :param mode: the mode.
        :param recalc: if true, trigger a recalc.
        '''
        self.__view_mode = view
        if recalc is True:
            self.recalc()

    def get_analysis(self, view_name=None):
        '''
        :param view_name: the named analysis view.
        :return: the analysis if any.
        '''
        if view_name is None:
            view_name = self.__view_mode
        if view_name not in self.__output:
            self.recalc()
        val = self.__output.get(view_name, None)
        return val

    def set_analysis(self, analysis):
        '''
        Updates the current view.
        :param analysis: the analysis.
        '''
        self.__output[self.__view_mode] = analysis


class SummedSignal(AnalysableSignal):

    def __init__(self, measurement_name, axis, preferences, fs, x, y, z, idx=-1, pre_calc=False, view_mode='avg'):
        super().__init__(measurement_name, axis, preferences, fs, idx=idx, view_mode=view_mode)
        self.__x = x
        self.__y = y
        self.__z = z
        self.__scales = [
            self.prefs.get(SUM_X_SCALE),
            self.prefs.get(SUM_Y_SCALE),
            self.prefs.get(SUM_Z_SCALE)
        ]
        if pre_calc is True:
            self.recalc()

    def recalc(self):
        if self.__can_sum():
            x = self.__x.get_analysis(self.view_mode)
            y = self.__y.get_analysis(self.view_mode)
            z = self.__z.get_analysis(self.view_mode)
            x_s, y_s, z_s = self.__scales
            if x is not None and y is not None and z is not None:
                Psum = (scale_sq(x, x_s) + scale_sq(y, y_s) + scale_sq(z, z_s)) ** 0.5
                if self.view_mode == 'avg':
                    Psum = np.sqrt(Psum)
                Psum_db = amplitude_to_db(Psum, ref=ADJUST_BY_3DB * REF_ACCELERATION_IN_G)
                self.set_analysis(Analysis((x.x, Psum, Psum_db)))

    def __can_sum(self):
        return self.view_mode == 'avg' or self.view_mode == 'peak'


def scale_sq(data, scale):
    return (data.y_raw * scale) ** 2


class Signal(AnalysableSignal):

    def __init__(self, measurement_name, axis, preferences, data, fs, resolution_shift,
                 idx=-1, mode='vibration', pre_calc=False, view_mode='avg'):
        '''
        Creates a new signal.
        :param measurement_name: the measurement_name.
        :param axis: the axis.
        :param preferences: common prefs.
        :param data: the sample date.
        :param fs: the sample rate.
        :param resolution_shift: the analysis frequency resolution.
        :param mode: optional analysis mode, can be none (raw data), vibration or tilt.
        :param pre_calc: if True, calculate the required views.
        '''
        super().__init__(measurement_name, axis, preferences, fs, idx=idx, view_mode=view_mode)
        self.__raw_data = data
        self.__data = None
        self.__analyse_data(mode)
        self.__resolution_shift = resolution_shift
        if pre_calc is True:
            self.recalc()

    def __analyse_data(self, mode):
        if mode.lower() == 'vibration':
            self.__data = butter(self.fs, self.raw, 'high')
        elif mode.lower() == 'tilt':
            self.__data = butter(self.fs, self.raw, 'low')
        else:
            self.__data = self.raw

    def set_mode(self, mode, recalc=True):
        '''
        Analyses the raw data in the specified mode.
        :param mode: the mode.
        :param recalc: if true, trigger a recalc.
        '''
        self.__analyse_data(mode)
        if recalc is True:
            self.recalc()

    @property
    def raw(self):
        return self.__raw_data

    @property
    def data(self):
        return self.__data

    def recalc(self):
        start = time.time()
        self.set_analysis(self.__calculate())
        end = time.time()
        logger.debug(f"Recalc {self.measurement_name}:{self.axis}:{self.idx} in {to_millis(start, end)}ms")

    def __calculate(self):
        if self.view_mode == 'avg':
            from model.preferences import ANALYSIS_AVG_WINDOW
            avg_wnd = get_window(self.prefs, ANALYSIS_AVG_WINDOW)
            return Analysis(self.__avg_spectrum(resolution_shift=self.__resolution_shift, window=avg_wnd))
        elif self.view_mode == 'peak':
            from model.preferences import ANALYSIS_PEAK_WINDOW
            peak_wnd = get_window(self.prefs, ANALYSIS_PEAK_WINDOW)
            return Analysis(self.__peak_spectrum(resolution_shift=self.__resolution_shift, window=peak_wnd))
        elif self.view_mode == 'psd':
            from model.preferences import ANALYSIS_AVG_WINDOW
            avg_wnd = get_window(self.prefs, ANALYSIS_AVG_WINDOW)
            return Analysis(self.__psd(resolution_shift=self.__resolution_shift, window=avg_wnd))
        elif self.view_mode == 'spectrogram':
            return SpectroValues(*self.__spectrogram(resolution_shift=self.__resolution_shift))

    def __psd(self, ref=REF_ACCELERATION_IN_G, resolution_shift=0, window=None, **kwargs):
        """
        analyses the source to generate the PSD.
        :param ref: the reference value for dB purposes.
        :param resolution_shift: allows resolution to go down (if positive) or up (if negative).
        :return:
            f : ndarray
            Array of sample frequencies.
            Pxx : ndarray
            psd.
            Pxx_den_db : ndarray
            psd in dB
        """
        nperseg = get_segment_length(self.fs, resolution_shift=resolution_shift)
        detrend = False if self.prefs.get(ANALYSIS_DETREND) == 'none' else self.prefs.get(ANALYSIS_DETREND)
        f, Pxx_den = signal.welch(self.__data, self.fs, nperseg=nperseg, detrend=detrend,
                                  window=window if window else 'hann', **kwargs)
        Pxx_den_db = power_to_db(np.nan_to_num(np.sqrt(Pxx_den)), ref)
        return f, Pxx_den, Pxx_den_db

    def __avg_spectrum(self, ref=REF_ACCELERATION_IN_G, resolution_shift=0, window=None, **kwargs):
        """
        analyses the source to generate the linear spectrum.
        :param ref: the reference value for dB purposes.
        :param resolution_shift: allows resolution to go down (if positive) or up (if negative).
        :return:
            f : ndarray
            Array of sample frequencies.
            Pxx : ndarray
            linear spectrum.
            Pxx_db : ndarray
            linear spectrum in dB
        """
        nperseg = get_segment_length(self.fs, resolution_shift=resolution_shift)
        detrend = False if self.prefs.get(ANALYSIS_DETREND) == 'none' else self.prefs.get(ANALYSIS_DETREND)
        f, Pxx_spec = signal.welch(self.__data, self.fs, nperseg=nperseg, scaling='spectrum', detrend=detrend,
                                   window=window if window else 'hann', **kwargs)
        # a 3dB adjustment is required to account for the change in nperseg
        Pxx_spec_db = amplitude_to_db(np.nan_to_num(np.sqrt(Pxx_spec)), ADJUST_BY_3DB * ref)
        return f, Pxx_spec, Pxx_spec_db

    def __peak_spectrum(self, ref=REF_ACCELERATION_IN_G, resolution_shift=0, window=None):
        """
        analyses the source to generate the max values per bin per segment
        :param resolution_shift: allows resolution to go down (if positive) or up (if negative).
        :param window: window type.
        :return:
            f : ndarray
            Array of sample frequencies.
            Pxx : ndarray
            linear spectrum max values.
            Pxx_db : ndarray
            linear spectrum max values in dB.
        """
        nperseg = get_segment_length(self.fs, resolution_shift=resolution_shift)
        detrend = False if self.prefs.get(ANALYSIS_DETREND) == 'none' else self.prefs.get(ANALYSIS_DETREND)
        freqs, _, Pxy = signal.spectrogram(self.__data,
                                           self.fs,
                                           window=window if window else ('tukey', 0.25),
                                           nperseg=int(nperseg),
                                           noverlap=int(nperseg // 2),
                                           detrend=detrend,
                                           scaling='spectrum')
        Pxy_max = np.sqrt(Pxy.max(axis=-1).real)
        # a 3dB adjustment is required to account for the change in nperseg
        Pxy_max_db = amplitude_to_db(Pxy_max, ref=ADJUST_BY_3DB * ref)
        return freqs, Pxy_max, Pxy_max_db

    def __spectrogram(self, ref=REF_ACCELERATION_IN_G, resolution_shift=0, window=None):
        """
        analyses the source to generate a spectrogram
        :param resolution_shift: allows resolution to go down (if positive) or up (if negative).
        :return:
            f : ndarray
            Array of time slices.
            t : ndarray
            Array of sample frequencies.
            Pxx : ndarray
            linear spectrum values.
        """
        nperseg = get_segment_length(self.fs, resolution_shift=resolution_shift)
        detrend = False if self.prefs.get(ANALYSIS_DETREND) == 'none' else self.prefs.get(ANALYSIS_DETREND)
        f, t, Sxx = signal.spectrogram(self.__data,
                                       self.fs,
                                       window=window if window else ('tukey', 0.25),
                                       nperseg=nperseg,
                                       noverlap=int(nperseg // 2),
                                       detrend=detrend,
                                       scaling='spectrum')
        Sxx = amplitude_to_db(np.sqrt(Sxx), ref=ref * ADJUST_BY_3DB)
        return f, t, Sxx


def butter(fs, data, btype, f3=2, order=2):
    """
    Applies a digital butterworth filter via filtfilt at the specified f3 and order. Default values are set to
    correspond to apparently sensible filters that distinguish between vibration and tilt from an accelerometer.
    :param data: the data to filter.
    :param btype: high or low.
    :param f3: the f3 of the filter.
    :param order: the filter order.
    :return: the filtered signal.
    """
    b, a = signal.butter(order, f3 / (0.5 * fs), btype=btype)
    y = signal.filtfilt(b, a, data)
    return y


def get_window(preferences, key):
    '''
    Gets the preferred window for the given type with a default fallback if no preference is set.
    :param preferences: the preferences store.
    :param key: the preferences key.
    :return: the window.
    '''
    from model.preferences import ANALYSIS_WINDOW_DEFAULT
    window = preferences.get(key)
    if window is None or window == ANALYSIS_WINDOW_DEFAULT:
        window = None
    else:
        if window == 'tukey':
            window = (window, 0.25)
    return window


def amplitude_to_db(s, ref=1.0, amin=1e-10):
    '''
    Convert an amplitude spectrogram to dB-scaled spectrogram. Implementation taken from librosa to avoid adding a
    dependency on librosa for a few util functions.
    :param s: the amplitude spectrogram.
    :param ref: the reference value.
    :param amin: min value.
    :return: s_db : np.ndarray ``s`` measured in dB
    '''
    return power_to_db(np.square(np.abs(np.asarray(s))), ref=ref**2, amin=amin**2)


def power_to_db(s, ref=1.0, amin=1e-20):
    '''
    Convert an amplitude spectrogram to dB-scaled spectrogram. Implementation taken from librosa to avoid adding a
    dependency on librosa for a few util functions.
    :param s: the amplitude spectrogram.
    :param ref: the reference value.
    :param amin: min value.
    :return: s_db : np.ndarray ``s`` measured in dB
    '''
    magnitude = np.abs(np.asarray(s))
    ref_value = np.abs(ref)
    top_db = 80.0
    log_spec = 10.0 * np.log10(np.maximum(amin, magnitude))
    log_spec -= 10.0 * np.log10(np.maximum(amin, ref_value))
    log_spec = np.maximum(log_spec, log_spec.max() - top_db)
    return np.nan_to_num(log_spec)


def rescale_x(x, y):
    step = (x[-1] - x[0]) / X_RESOLUTION
    steps = np.arange(x[0], x[-1], step)
    if len(steps) == len(x):
        return x, y
    else:
        import time
        start = time.time()
        x2, y2 = interp(x, y, steps)
        end = time.time()
        logger.debug(f"Interpolation from {len(x)} to {len(x2)} in {to_millis(start, end)}ms")
        return x2, y2


def interp(x1, y1, x2, smooth=False):
    ''' Interpolates xy based on the preferred smoothing style. '''
    start = time.time()
    if smooth is True:
        cs = PchipInterpolator(x1, y1)
        y2 = cs(x2)
    else:
        y2 = np.interp(x2, x1, y1)
    end = time.time()
    logger.debug(f"Interpolation from {len(x1)} to {len(x2)} in {to_millis(start, end)}ms")
    return x2, y2


def get_segment_length(fs, resolution_shift=0):
    """
    Calculates a segment length such that the frequency resolution of the resulting analysis is in the region of
    ~1Hz subject to a lower limit of the number of samples in the signal.
    For example, if we have a 10s signal with an fs is 500 then we convert fs-1 to the number of bits required to
    hold this number in binary (i.e. 111110011 so 9 bits) and then do 1 << 9 which gives us 100000000 aka 512. Thus
    we have ~1Hz resolution.
    :param resolution_shift: shifts the resolution up or down by the specified number of bits.
    :return: the segment length.
    """
    return 1 << ((fs - 1).bit_length() - int(resolution_shift))


def smooth_savgol(x, y, wl=SAVGOL_WINDOW_LENGTH, poly=SAVGOL_POLYORDER):
    '''
    Performs Savitzky-Golay smoothing.
    :param x: frequencies.
    :param y: magnitude.
    :param wl: the window length.
    :param poly: the poly order.
    :return: the smoothed data.
    '''
    from scipy.signal import savgol_filter
    smoothed_y = savgol_filter(y, wl, poly)
    return x, smoothed_y
