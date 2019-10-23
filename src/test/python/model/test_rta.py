import numpy as np

from model.rta import ChunkCalculator

min_nperseg = 512
stride = 25

def test_first_data_is_too_small():
    cc = ChunkCalculator(min_nperseg, stride)
    data = np.arange(60).reshape(3, 20).transpose()
    chunks = cc.recalc('test', data)
    assert chunks is None
    assert 'test' not in cc.last_idx


def test_first_data_is_exactly_one_chunk():
    cc = ChunkCalculator(min_nperseg, stride)
    data = np.arange(min_nperseg * 3).reshape(3, min_nperseg).transpose()
    chunks = cc.recalc('test', data)
    assert chunks is not None
    assert len(chunks) == 1
    assert chunks[0][:, 0][0] == 0
    assert chunks[0][:, 0][-1] == min_nperseg - 1
    assert 'test' in cc.last_idx
    assert cc.last_idx['test'] == min_nperseg - 1


def test_first_data_is_more_than_a_chunk():
    cc = ChunkCalculator(min_nperseg, stride)
    data = np.arange((min_nperseg + 20) * 3).reshape(3, min_nperseg + 20).transpose()
    chunks = cc.recalc('test', data)
    assert chunks is not None
    assert len(chunks) == 1
    assert chunks[0][:, 0][0] == 0
    assert chunks[0][:, 0][-1] == min_nperseg - 1
    assert 'test' in cc.last_idx
    assert cc.last_idx['test'] == min_nperseg - 1


def test_first_data_is_many_chunks():
    cc = ChunkCalculator(min_nperseg, stride)
    data = np.arange((min_nperseg + 105) * 3).reshape(3, min_nperseg + 105).transpose()
    chunks = cc.recalc('test', data)
    assert chunks is not None
    assert len(chunks) == 5
    last = min_nperseg - 1
    first = 0
    for i in range(0, 5):
        assert chunks[i][:, 0][0] == first
        assert chunks[i][:, 0][-1] == last
        first += stride
        last += stride
    assert 'test' in cc.last_idx
    assert cc.last_idx['test'] == min_nperseg - 1 + 100


def test_next_data_is_less_than_chunk():
    cc = ChunkCalculator(min_nperseg, stride)
    cc.last_idx['test'] = min_nperseg - 1
    data = np.arange((min_nperseg + 20) * 3).reshape(3, min_nperseg + 20).transpose()
    chunks = cc.recalc('test', data)
    assert chunks is None
    assert 'test' in cc.last_idx
    assert cc.last_idx['test'] == min_nperseg - 1


def test_next_data_fills_a_chunk():
    cc = ChunkCalculator(min_nperseg, stride)
    cc.last_idx['test'] = min_nperseg - 1
    data = np.arange((min_nperseg + stride) * 3).reshape(3, min_nperseg + stride).transpose()
    chunks = cc.recalc('test', data)
    assert chunks is not None
    assert len(chunks) == 1
    assert chunks[0][:, 0][0] == stride
    assert chunks[0][:, 0][-1] == min_nperseg - 1 + stride
    assert 'test' in cc.last_idx
    assert cc.last_idx['test'] == min_nperseg - 1 + stride


def test_next_data_is_between_chunks():
    cc = ChunkCalculator(min_nperseg, stride)
    cc.last_idx['test'] = min_nperseg - 1
    data = np.arange((min_nperseg + stride + 10) * 3).reshape(3, min_nperseg + stride + 10).transpose()
    chunks = cc.recalc('test', data)
    assert chunks is not None
    assert len(chunks) == 1
    assert chunks[0][:, 0][0] == stride
    assert chunks[0][:, 0][-1] == min_nperseg - 1 + stride
    assert 'test' in cc.last_idx
    assert cc.last_idx['test'] == min_nperseg - 1 + stride


def test_next_data_is_many_chunks():
    cc = ChunkCalculator(min_nperseg, stride)
    cc.last_idx['test'] = min_nperseg - 1
    data = np.arange((min_nperseg + stride * 3 + 10) * 3).reshape(3, min_nperseg + stride * 3 + 10).transpose()
    chunks = cc.recalc('test', data)
    assert chunks is not None
    assert len(chunks) == 3
    assert chunks[0][:, 0][0] == stride
    assert chunks[0][:, 0][-1] == min_nperseg - 1 + stride
    assert chunks[1][:, 0][0] == stride * 2
    assert chunks[1][:, 0][-1] == stride * 2 - 1 + min_nperseg
    assert chunks[2][:, 0][0] == stride * 3
    assert chunks[2][:, 0][-1] == stride * 3 - 1 + min_nperseg
    assert 'test' in cc.last_idx
    assert cc.last_idx['test'] == stride * 3 - 1 + min_nperseg
