import logging
import time
from collections import Sequence
from contextlib import contextmanager

import numpy as np
import pyqtgraph as pg
from qtpy import QtCore
from qtpy.QtCore import QRunnable, QRect, QSize, QPoint, Qt
from qtpy.QtGui import QCursor, QFont
from qtpy.QtWidgets import QApplication, QFileDialog, QLayout, QSizePolicy

logger = logging.getLogger('qvibe.common')


class ReactorRunner(QRunnable):
    def __init__(self, reactor):
        super().__init__()
        self.__reactor = reactor

    def run(self):
        self.__reactor.run(installSignalHandlers=False)

    def stop(self):
        self.__reactor.callFromThread(self.__reactor.stop)
        time.sleep(0.5)


@contextmanager
def wait_cursor(msg=None):
    '''
    Allows long running functions to show a busy cursor.
    :param msg: a message to put in the status bar.
    '''
    try:
        QApplication.setOverrideCursor(QCursor(QtCore.Qt.WaitCursor))
        yield
    finally:
        QApplication.restoreOverrideCursor()


@contextmanager
def block_signals(widget):
    '''
    blocks signals on a given widget
    :param widget: the widget.
    '''
    try:
        widget.blockSignals(True)
        yield
    finally:
        widget.blockSignals(False)


class RingBuffer(Sequence):
    def __init__(self, capacity, dtype=np.float64):
        """
        Create a new ring buffer with the given capacity and element type

        Parameters
        ----------
        capacity: int
            The maximum capacity of the ring buffer
        dtype: data-type, optional
            Desired type of buffer elements. Use a type like (float, 2) to
            produce a buffer with shape (N, 2)
        """
        self.__buffer = np.empty(capacity, dtype)
        self.__left_idx = 0
        self.__right_idx = 0
        self.__capacity = capacity
        self.__event_count = 0

    def unwrap(self):
        """ Copy the data from this buffer into unwrapped form """
        return np.concatenate((
            self.__buffer[self.__left_idx:min(self.__right_idx, self.__capacity)],
            self.__buffer[:max(self.__right_idx - self.__capacity, 0)]
        ))

    def take_event_count(self, if_multiple=None):
        '''
        :param if_multiple: if set, only take the event count if it is a multiple of the supplied value.
        :return: the count of items added since the last take if the count is taken.
        '''
        count = self.__event_count
        if if_multiple is None or count % if_multiple == 0:
            self.__event_count = 0
            return count
        else:
            return None

    def _fix_indices(self):
        """
        Enforce our invariant that 0 <= self._left_index < self._capacity
        """
        if self.__left_idx >= self.__capacity:
            self.__left_idx -= self.__capacity
            self.__right_idx -= self.__capacity
        elif self.__left_idx < 0:
            self.__left_idx += self.__capacity
            self.__right_idx += self.__capacity

    @property
    def idx(self):
        return self.__left_idx, self.__right_idx

    @property
    def is_full(self):
        """ True if there is no more space in the buffer """
        return len(self) == self.__capacity

    # numpy compatibility
    def __array__(self):
        return self.unwrap()

    @property
    def dtype(self):
        return self.__buffer.dtype

    @property
    def shape(self):
        return (len(self),) + self.__buffer.shape[1:]

    @property
    def maxlen(self):
        return self.__capacity

    def append(self, value):
        if self.is_full:
            if not len(self):
                return
            else:
                self.__left_idx += 1

        self.__buffer[self.__right_idx % self.__capacity] = value
        self.__right_idx += 1
        self.__event_count += 1
        self._fix_indices()

    def peek(self):
        if len(self) == 0:
            return None
        idx = (self.__right_idx % self.__capacity) - 1
        logger.debug(f"Peeking at idx {idx}")
        res = self.__buffer[idx]
        return res

    def append_left(self, value):
        if self.is_full:
            if not len(self):
                return
            else:
                self.__right_idx -= 1

        self.__left_idx -= 1
        self._fix_indices()
        self.__buffer[self.__left_idx] = value
        self.__event_count += 1

    def extend(self, values):
        lv = len(values)
        if len(self) + lv > self.__capacity:
            if not len(self):
                return
        if lv >= self.__capacity:
            # wipe the entire array! - this may not be threadsafe
            self.__buffer[...] = values[-self.__capacity:]
            self.__right_idx = self.__capacity
            self.__left_idx = 0
            return

        ri = self.__right_idx % self.__capacity
        sl1 = np.s_[ri:min(ri + lv, self.__capacity)]
        sl2 = np.s_[:max(ri + lv - self.__capacity, 0)]
        self.__buffer[sl1] = values[:sl1.stop - sl1.start]
        self.__buffer[sl2] = values[sl1.stop - sl1.start:]
        self.__right_idx += lv

        self.__left_idx = max(self.__left_idx, self.__right_idx - self.__capacity)
        self.__event_count += len(values)
        self._fix_indices()

    def extend_left(self, values):
        lv = len(values)
        if len(self) + lv > self.__capacity:
            if not len(self):
                return
        if lv >= self.__capacity:
            # wipe the entire array! - this may not be threadsafe
            self.__buffer[...] = values[:self.__capacity]
            self.__right_idx = self.__capacity
            self.__left_idx = 0
            return

        self.__left_idx -= lv
        self._fix_indices()
        li = self.__left_idx
        sl1 = np.s_[li:min(li + lv, self.__capacity)]
        sl2 = np.s_[:max(li + lv - self.__capacity, 0)]
        self.__buffer[sl1] = values[:sl1.stop - sl1.start]
        self.__buffer[sl2] = values[sl1.stop - sl1.start:]

        self.__right_idx = min(self.__right_idx, self.__left_idx + self.__capacity)
        self.__event_count += len(values)

    def __len__(self):
        return self.__right_idx - self.__left_idx

    def __getitem__(self, item):
        # handle simple (b[1]) and basic (b[np.array([1, 2, 3])]) fancy indexing specially
        if not isinstance(item, tuple):
            item_arr = np.asarray(item)
            if issubclass(item_arr.dtype.type, np.integer):
                item_arr = (item_arr + self.__left_idx) % self.__capacity
                return self.__buffer[item_arr]

        # for everything else, get it right at the expense of efficiency
        return self.unwrap()[item]

    def __iter__(self):
        # alarmingly, this is comparable in speed to using itertools.chain
        return iter(self.unwrap())

    # Everything else
    def __repr__(self):
        return '<RingBuffer of {!r}>'.format(np.asarray(self))


class PlotWidgetWithDateAxis(pg.PlotWidget):
    def __init__(self, parent=None, background='default', **kargs):
        super().__init__(parent=parent,
                         background=background,
                         axisItems={'bottom': TimeAxisItem(orientation='bottom')},
                         **kargs)


class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        import datetime
        return [str(datetime.timedelta(seconds=value)).split('.')[0] for value in values]


def bump_tick_levels(axis, minVal, maxVal, size):
    ''' a workaround for not being able to control grid line alpha directly. '''
    real_levels = axis.tickSpacing(minVal, maxVal, size)
    if len(real_levels) == 3:
        return [
            real_levels[2],
            real_levels[2],
            real_levels[2]
        ]
    else:
        return real_levels

def format_pg_plotitem(plot, x_lim, y_lim, x_range=None, y_range=None):
    '''
    Applies a standard format to a pyqtgraph chart.
    :param plot: the plot item.
    :param x_lim: the x axis limits.
    :param y_lim: the y axis limits.
    :param x_range: the visible x limits.
    :param y_range: the visible y limits.
    '''
    label_font = QFont()
    label_font.setPointSize(9)
    label_font.setFamily('DejaVu Sans')
    for name in ['left', 'right', 'bottom', 'top']:
        plot.getAxis(name).setTickFont(label_font)
    plot.showGrid(x=True, y=True, alpha=0.5)
    plot.disableAutoRange()
    plot.setLimits(xMin=x_lim[0], xMax=x_lim[1], yMin=y_lim[0], yMax=y_lim[1])
    plot.setXRange(*x_lim, padding=0.0)
    if x_range is None:
        plot.setXRange(*x_lim, padding=0.0)
    else:
        plot.setXRange(*x_range, padding=0.0)
    if y_range is None:
        plot.setYRange(*y_lim, padding=0.0)
    else:
        plot.setYRange(*y_range, padding=0.0)
    plot.setDownsampling(ds=False)
    plot.layout.setContentsMargins(10, 20, 30, 20)


_tab20_data = (
    (0.12156862745098039, 0.4666666666666667,  0.7058823529411765  ),  # 1f77b4
    (0.6823529411764706,  0.7803921568627451,  0.9098039215686274  ),  # aec7e8
    (1.0,                 0.4980392156862745,  0.054901960784313725),  # ff7f0e
    (1.0,                 0.7333333333333333,  0.47058823529411764 ),  # ffbb78
    (0.17254901960784313, 0.6274509803921569,  0.17254901960784313 ),  # 2ca02c
    (0.596078431372549,   0.8745098039215686,  0.5411764705882353  ),  # 98df8a
    (0.8392156862745098,  0.15294117647058825, 0.1568627450980392  ),  # d62728
    (1.0,                 0.596078431372549,   0.5882352941176471  ),  # ff9896
    (0.5803921568627451,  0.403921568627451,   0.7411764705882353  ),  # 9467bd
    (0.7725490196078432,  0.6901960784313725,  0.8352941176470589  ),  # c5b0d5
    (0.5490196078431373,  0.33725490196078434, 0.29411764705882354 ),  # 8c564b
    (0.7686274509803922,  0.611764705882353,   0.5803921568627451  ),  # c49c94
    (0.8901960784313725,  0.4666666666666667,  0.7607843137254902  ),  # e377c2
    (0.9686274509803922,  0.7137254901960784,  0.8235294117647058  ),  # f7b6d2
    (0.4980392156862745,  0.4980392156862745,  0.4980392156862745  ),  # 7f7f7f
    (0.7803921568627451,  0.7803921568627451,  0.7803921568627451  ),  # c7c7c7
    (0.7372549019607844,  0.7411764705882353,  0.13333333333333333 ),  # bcbd22
    (0.8588235294117647,  0.8588235294117647,  0.5529411764705883  ),  # dbdb8d
    (0.09019607843137255, 0.7450980392156863,  0.8117647058823529  ),  # 17becf
    (0.6196078431372549,  0.8549019607843137,  0.8980392156862745),    # 9edae5
)

_inferno_data = [[0.001462, 0.000466, 0.013866],
                 [0.002267, 0.001270, 0.018570],
                 [0.003299, 0.002249, 0.024239],
                 [0.004547, 0.003392, 0.030909],
                 [0.006006, 0.004692, 0.038558],
                 [0.007676, 0.006136, 0.046836],
                 [0.009561, 0.007713, 0.055143],
                 [0.011663, 0.009417, 0.063460],
                 [0.013995, 0.011225, 0.071862],
                 [0.016561, 0.013136, 0.080282],
                 [0.019373, 0.015133, 0.088767],
                 [0.022447, 0.017199, 0.097327],
                 [0.025793, 0.019331, 0.105930],
                 [0.029432, 0.021503, 0.114621],
                 [0.033385, 0.023702, 0.123397],
                 [0.037668, 0.025921, 0.132232],
                 [0.042253, 0.028139, 0.141141],
                 [0.046915, 0.030324, 0.150164],
                 [0.051644, 0.032474, 0.159254],
                 [0.056449, 0.034569, 0.168414],
                 [0.061340, 0.036590, 0.177642],
                 [0.066331, 0.038504, 0.186962],
                 [0.071429, 0.040294, 0.196354],
                 [0.076637, 0.041905, 0.205799],
                 [0.081962, 0.043328, 0.215289],
                 [0.087411, 0.044556, 0.224813],
                 [0.092990, 0.045583, 0.234358],
                 [0.098702, 0.046402, 0.243904],
                 [0.104551, 0.047008, 0.253430],
                 [0.110536, 0.047399, 0.262912],
                 [0.116656, 0.047574, 0.272321],
                 [0.122908, 0.047536, 0.281624],
                 [0.129285, 0.047293, 0.290788],
                 [0.135778, 0.046856, 0.299776],
                 [0.142378, 0.046242, 0.308553],
                 [0.149073, 0.045468, 0.317085],
                 [0.155850, 0.044559, 0.325338],
                 [0.162689, 0.043554, 0.333277],
                 [0.169575, 0.042489, 0.340874],
                 [0.176493, 0.041402, 0.348111],
                 [0.183429, 0.040329, 0.354971],
                 [0.190367, 0.039309, 0.361447],
                 [0.197297, 0.038400, 0.367535],
                 [0.204209, 0.037632, 0.373238],
                 [0.211095, 0.037030, 0.378563],
                 [0.217949, 0.036615, 0.383522],
                 [0.224763, 0.036405, 0.388129],
                 [0.231538, 0.036405, 0.392400],
                 [0.238273, 0.036621, 0.396353],
                 [0.244967, 0.037055, 0.400007],
                 [0.251620, 0.037705, 0.403378],
                 [0.258234, 0.038571, 0.406485],
                 [0.264810, 0.039647, 0.409345],
                 [0.271347, 0.040922, 0.411976],
                 [0.277850, 0.042353, 0.414392],
                 [0.284321, 0.043933, 0.416608],
                 [0.290763, 0.045644, 0.418637],
                 [0.297178, 0.047470, 0.420491],
                 [0.303568, 0.049396, 0.422182],
                 [0.309935, 0.051407, 0.423721],
                 [0.316282, 0.053490, 0.425116],
                 [0.322610, 0.055634, 0.426377],
                 [0.328921, 0.057827, 0.427511],
                 [0.335217, 0.060060, 0.428524],
                 [0.341500, 0.062325, 0.429425],
                 [0.347771, 0.064616, 0.430217],
                 [0.354032, 0.066925, 0.430906],
                 [0.360284, 0.069247, 0.431497],
                 [0.366529, 0.071579, 0.431994],
                 [0.372768, 0.073915, 0.432400],
                 [0.379001, 0.076253, 0.432719],
                 [0.385228, 0.078591, 0.432955],
                 [0.391453, 0.080927, 0.433109],
                 [0.397674, 0.083257, 0.433183],
                 [0.403894, 0.085580, 0.433179],
                 [0.410113, 0.087896, 0.433098],
                 [0.416331, 0.090203, 0.432943],
                 [0.422549, 0.092501, 0.432714],
                 [0.428768, 0.094790, 0.432412],
                 [0.434987, 0.097069, 0.432039],
                 [0.441207, 0.099338, 0.431594],
                 [0.447428, 0.101597, 0.431080],
                 [0.453651, 0.103848, 0.430498],
                 [0.459875, 0.106089, 0.429846],
                 [0.466100, 0.108322, 0.429125],
                 [0.472328, 0.110547, 0.428334],
                 [0.478558, 0.112764, 0.427475],
                 [0.484789, 0.114974, 0.426548],
                 [0.491022, 0.117179, 0.425552],
                 [0.497257, 0.119379, 0.424488],
                 [0.503493, 0.121575, 0.423356],
                 [0.509730, 0.123769, 0.422156],
                 [0.515967, 0.125960, 0.420887],
                 [0.522206, 0.128150, 0.419549],
                 [0.528444, 0.130341, 0.418142],
                 [0.534683, 0.132534, 0.416667],
                 [0.540920, 0.134729, 0.415123],
                 [0.547157, 0.136929, 0.413511],
                 [0.553392, 0.139134, 0.411829],
                 [0.559624, 0.141346, 0.410078],
                 [0.565854, 0.143567, 0.408258],
                 [0.572081, 0.145797, 0.406369],
                 [0.578304, 0.148039, 0.404411],
                 [0.584521, 0.150294, 0.402385],
                 [0.590734, 0.152563, 0.400290],
                 [0.596940, 0.154848, 0.398125],
                 [0.603139, 0.157151, 0.395891],
                 [0.609330, 0.159474, 0.393589],
                 [0.615513, 0.161817, 0.391219],
                 [0.621685, 0.164184, 0.388781],
                 [0.627847, 0.166575, 0.386276],
                 [0.633998, 0.168992, 0.383704],
                 [0.640135, 0.171438, 0.381065],
                 [0.646260, 0.173914, 0.378359],
                 [0.652369, 0.176421, 0.375586],
                 [0.658463, 0.178962, 0.372748],
                 [0.664540, 0.181539, 0.369846],
                 [0.670599, 0.184153, 0.366879],
                 [0.676638, 0.186807, 0.363849],
                 [0.682656, 0.189501, 0.360757],
                 [0.688653, 0.192239, 0.357603],
                 [0.694627, 0.195021, 0.354388],
                 [0.700576, 0.197851, 0.351113],
                 [0.706500, 0.200728, 0.347777],
                 [0.712396, 0.203656, 0.344383],
                 [0.718264, 0.206636, 0.340931],
                 [0.724103, 0.209670, 0.337424],
                 [0.729909, 0.212759, 0.333861],
                 [0.735683, 0.215906, 0.330245],
                 [0.741423, 0.219112, 0.326576],
                 [0.747127, 0.222378, 0.322856],
                 [0.752794, 0.225706, 0.319085],
                 [0.758422, 0.229097, 0.315266],
                 [0.764010, 0.232554, 0.311399],
                 [0.769556, 0.236077, 0.307485],
                 [0.775059, 0.239667, 0.303526],
                 [0.780517, 0.243327, 0.299523],
                 [0.785929, 0.247056, 0.295477],
                 [0.791293, 0.250856, 0.291390],
                 [0.796607, 0.254728, 0.287264],
                 [0.801871, 0.258674, 0.283099],
                 [0.807082, 0.262692, 0.278898],
                 [0.812239, 0.266786, 0.274661],
                 [0.817341, 0.270954, 0.270390],
                 [0.822386, 0.275197, 0.266085],
                 [0.827372, 0.279517, 0.261750],
                 [0.832299, 0.283913, 0.257383],
                 [0.837165, 0.288385, 0.252988],
                 [0.841969, 0.292933, 0.248564],
                 [0.846709, 0.297559, 0.244113],
                 [0.851384, 0.302260, 0.239636],
                 [0.855992, 0.307038, 0.235133],
                 [0.860533, 0.311892, 0.230606],
                 [0.865006, 0.316822, 0.226055],
                 [0.869409, 0.321827, 0.221482],
                 [0.873741, 0.326906, 0.216886],
                 [0.878001, 0.332060, 0.212268],
                 [0.882188, 0.337287, 0.207628],
                 [0.886302, 0.342586, 0.202968],
                 [0.890341, 0.347957, 0.198286],
                 [0.894305, 0.353399, 0.193584],
                 [0.898192, 0.358911, 0.188860],
                 [0.902003, 0.364492, 0.184116],
                 [0.905735, 0.370140, 0.179350],
                 [0.909390, 0.375856, 0.174563],
                 [0.912966, 0.381636, 0.169755],
                 [0.916462, 0.387481, 0.164924],
                 [0.919879, 0.393389, 0.160070],
                 [0.923215, 0.399359, 0.155193],
                 [0.926470, 0.405389, 0.150292],
                 [0.929644, 0.411479, 0.145367],
                 [0.932737, 0.417627, 0.140417],
                 [0.935747, 0.423831, 0.135440],
                 [0.938675, 0.430091, 0.130438],
                 [0.941521, 0.436405, 0.125409],
                 [0.944285, 0.442772, 0.120354],
                 [0.946965, 0.449191, 0.115272],
                 [0.949562, 0.455660, 0.110164],
                 [0.952075, 0.462178, 0.105031],
                 [0.954506, 0.468744, 0.099874],
                 [0.956852, 0.475356, 0.094695],
                 [0.959114, 0.482014, 0.089499],
                 [0.961293, 0.488716, 0.084289],
                 [0.963387, 0.495462, 0.079073],
                 [0.965397, 0.502249, 0.073859],
                 [0.967322, 0.509078, 0.068659],
                 [0.969163, 0.515946, 0.063488],
                 [0.970919, 0.522853, 0.058367],
                 [0.972590, 0.529798, 0.053324],
                 [0.974176, 0.536780, 0.048392],
                 [0.975677, 0.543798, 0.043618],
                 [0.977092, 0.550850, 0.039050],
                 [0.978422, 0.557937, 0.034931],
                 [0.979666, 0.565057, 0.031409],
                 [0.980824, 0.572209, 0.028508],
                 [0.981895, 0.579392, 0.026250],
                 [0.982881, 0.586606, 0.024661],
                 [0.983779, 0.593849, 0.023770],
                 [0.984591, 0.601122, 0.023606],
                 [0.985315, 0.608422, 0.024202],
                 [0.985952, 0.615750, 0.025592],
                 [0.986502, 0.623105, 0.027814],
                 [0.986964, 0.630485, 0.030908],
                 [0.987337, 0.637890, 0.034916],
                 [0.987622, 0.645320, 0.039886],
                 [0.987819, 0.652773, 0.045581],
                 [0.987926, 0.660250, 0.051750],
                 [0.987945, 0.667748, 0.058329],
                 [0.987874, 0.675267, 0.065257],
                 [0.987714, 0.682807, 0.072489],
                 [0.987464, 0.690366, 0.079990],
                 [0.987124, 0.697944, 0.087731],
                 [0.986694, 0.705540, 0.095694],
                 [0.986175, 0.713153, 0.103863],
                 [0.985566, 0.720782, 0.112229],
                 [0.984865, 0.728427, 0.120785],
                 [0.984075, 0.736087, 0.129527],
                 [0.983196, 0.743758, 0.138453],
                 [0.982228, 0.751442, 0.147565],
                 [0.981173, 0.759135, 0.156863],
                 [0.980032, 0.766837, 0.166353],
                 [0.978806, 0.774545, 0.176037],
                 [0.977497, 0.782258, 0.185923],
                 [0.976108, 0.789974, 0.196018],
                 [0.974638, 0.797692, 0.206332],
                 [0.973088, 0.805409, 0.216877],
                 [0.971468, 0.813122, 0.227658],
                 [0.969783, 0.820825, 0.238686],
                 [0.968041, 0.828515, 0.249972],
                 [0.966243, 0.836191, 0.261534],
                 [0.964394, 0.843848, 0.273391],
                 [0.962517, 0.851476, 0.285546],
                 [0.960626, 0.859069, 0.298010],
                 [0.958720, 0.866624, 0.310820],
                 [0.956834, 0.874129, 0.323974],
                 [0.954997, 0.881569, 0.337475],
                 [0.953215, 0.888942, 0.351369],
                 [0.951546, 0.896226, 0.365627],
                 [0.950018, 0.903409, 0.380271],
                 [0.948683, 0.910473, 0.395289],
                 [0.947594, 0.917399, 0.410665],
                 [0.946809, 0.924168, 0.426373],
                 [0.946392, 0.930761, 0.442367],
                 [0.946403, 0.937159, 0.458592],
                 [0.946903, 0.943348, 0.474970],
                 [0.947937, 0.949318, 0.491426],
                 [0.949545, 0.955063, 0.507860],
                 [0.951740, 0.960587, 0.524203],
                 [0.954529, 0.965896, 0.540361],
                 [0.957896, 0.971003, 0.556275],
                 [0.961812, 0.975924, 0.571925],
                 [0.966249, 0.980678, 0.587206],
                 [0.971162, 0.985282, 0.602154],
                 [0.976511, 0.989753, 0.616760],
                 [0.982257, 0.994109, 0.631017],
                 [0.988362, 0.998364, 0.644924]]


def convert(data):
    indices = np.linspace(0., 1., len(data))
    scaled_rgb_tuples = [(rgbTuple[0] * 255, rgbTuple[1] * 255, rgbTuple[2] * 255) for rgbTuple in data]
    rgb_list = zip(indices, scaled_rgb_tuples)
    pyqt_cm = list([(pos, (int(r), int(g), int(b), 255)) for pos, (r, g, b) in rgb_list])
    return pyqt_cm


maps = {
    'inferno': convert(_inferno_data),
    'tab20': convert(_tab20_data)
}


def colourmap(name='inferno'):
    return maps[name]


def np_to_str(arr):
    '''
    Converts an ndarray to a string.
    :param arr: the array.
    :return: the string.
    '''
    import io
    out = io.StringIO()
    np.savetxt(out, arr)
    return out.getvalue()


def parse_file(filter, title, parsers):
    '''
    Presents a file dialog to the user so they can choose something to load.
    :return: a 2 entry tuple with the file name and loaded thing (if anything was loaded)
    '''
    dialog = QFileDialog()
    dialog.setFileMode(QFileDialog.ExistingFile)
    dialog.setNameFilter(filter)
    dialog.setWindowTitle(title)
    if dialog.exec():
        selected = dialog.selectedFiles()
        if len(selected) > 0:
            file_name = selected[0]
            for k,v in parsers.items():
                if file_name.endswith(k):
                    return v(file_name)
    return None, None


class FlowLayout(QLayout):

    def __init__(self, parent=None, margin=0, spacing=-1):
        super(FlowLayout, self).__init__(parent)

        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)

        self.setSpacing(spacing)

        self.item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.item_list.append(item)

    def count(self):
        return len(self.item_list)

    def itemAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list[index]

        return None

    def takeAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())

        margin, _, _, _ = self.getContentsMargins()

        size += QSize(2 * margin, 2 * margin)
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        line_height = 0

        for item in self.item_list:
            wid = item.widget()
            if wid is not None:
                space_x = self.spacing() + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
                space_y = self.spacing() + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)
                next_x = x + item.sizeHint().width() + space_x
                if next_x - space_x > rect.right() and line_height > 0:
                    x = rect.x()
                    y = y + line_height + space_y
                    next_x = x + item.sizeHint().width() + space_x
                    line_height = 0

                if not testOnly:
                    item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

                x = next_x
                line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()
