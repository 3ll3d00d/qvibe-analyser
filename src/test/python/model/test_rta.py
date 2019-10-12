import numpy as np

from model.rta import ChunkCalculator

min_nperseg = 512


def test_first_data_is_too_small():
    cc = ChunkCalculator(min_nperseg)
    data = np.arange(384).reshape(3, 128).transpose()
    chunks = cc.recalc('test', data)
    assert chunks is None
    assert 'test' not in cc.last_idx


def test_first_data_is_exactly_one_chunk():
    cc = ChunkCalculator(min_nperseg)
    data = np.arange(min_nperseg * 3).reshape(3, min_nperseg).transpose()
    chunks = cc.recalc('test', data)
    assert chunks is not None
    assert len(chunks) == 1
    assert chunks[0][:, 0][0] == 0
    assert chunks[0][:, 0][-1] == min_nperseg - 1
    assert 'test' in cc.last_idx
    assert cc.last_idx['test'] == min_nperseg - 1


def test_first_data_is_more_than_a_chunk():
    cc = ChunkCalculator(min_nperseg)
    data = np.arange(min_nperseg * 3 + 384).reshape(3, min_nperseg + 128).transpose()
    chunks = cc.recalc('test', data)
    assert chunks is not None
    assert len(chunks) == 1
    assert chunks[0][:, 0][0] == 0
    assert chunks[0][:, 0][-1] == min_nperseg - 1
    assert 'test' in cc.last_idx
    assert cc.last_idx['test'] == min_nperseg - 1


def test_first_data_is_many_chunks():
    cc = ChunkCalculator(min_nperseg)
    data = np.arange(min_nperseg * 3 * 3).reshape(3, min_nperseg * 3).transpose()
    chunks = cc.recalc('test', data)
    assert chunks is not None
    assert len(chunks) == 3
    assert chunks[0][:, 0][0] == 0
    assert chunks[0][:, 0][-1] == min_nperseg - 1
    assert chunks[1][:, 0][0] == min_nperseg
    assert chunks[1][:, 0][-1] == (min_nperseg * 2) - 1
    assert chunks[2][:, 0][0] == min_nperseg * 2
    assert chunks[2][:, 0][-1] == (min_nperseg * 3) - 1
    assert 'test' in cc.last_idx
    assert cc.last_idx['test'] == (min_nperseg * 3) - 1


def test_next_data_is_less_than_chunk():
    cc = ChunkCalculator(min_nperseg)
    cc.last_idx['test'] = 64
    data = np.arange(384).reshape(3, 128).transpose()
    chunks = cc.recalc('test', data)
    assert chunks is None
    assert 'test' in cc.last_idx
    assert cc.last_idx['test'] == 64


def test_next_data_fills_a_chunk():
    cc = ChunkCalculator(min_nperseg)
    cc.last_idx['test'] = 384
    data = np.arange(min_nperseg * 3).reshape(3, min_nperseg).transpose()
    chunks = cc.recalc('test', data)
    assert chunks is not None
    assert len(chunks) == 1
    assert chunks[0][:, 0][0] == 0
    assert chunks[0][:, 0][-1] == min_nperseg - 1
    assert 'test' in cc.last_idx
    assert cc.last_idx['test'] == min_nperseg - 1


def test_next_data_is_between_chunks():
    cc = ChunkCalculator(min_nperseg)
    cc.last_idx['test'] = 384
    data = np.arange(min_nperseg * 3 + 384).reshape(3, min_nperseg + 128).transpose()
    chunks = cc.recalc('test', data)
    assert chunks is not None
    assert len(chunks) == 1
    assert chunks[0][:, 0][0] == 128
    assert chunks[0][:, 0][-1] == min_nperseg - 1 + 128
    assert 'test' in cc.last_idx
    assert cc.last_idx['test'] == min_nperseg - 1 + 128


def test_next_data_is_many_chunks():
    cc = ChunkCalculator(min_nperseg)
    cc.last_idx['test'] = 128
    data = np.arange(min_nperseg * 3 * 3).reshape(3, min_nperseg * 3).transpose()
    chunks = cc.recalc('test', data)
    assert chunks is not None
    assert len(chunks) == 3
    assert chunks[0][:, 0][0] == 0
    assert chunks[0][:, 0][-1] == min_nperseg - 1
    assert chunks[1][:, 0][0] == min_nperseg
    assert chunks[1][:, 0][-1] == (min_nperseg * 2) - 1
    assert chunks[2][:, 0][0] == min_nperseg * 2
    assert chunks[2][:, 0][-1] == (min_nperseg * 3) - 1
    assert 'test' in cc.last_idx
    assert cc.last_idx['test'] == (min_nperseg * 3) - 1
