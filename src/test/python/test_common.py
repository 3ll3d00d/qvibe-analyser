import numpy as np

from common import RingBuffer


def test_sizes():
    r = RingBuffer(5, dtype=(int, 2))
    assert r.maxlen == 5
    assert len(r) == 0
    assert r.shape == (0, 2)

    r.append([0, 0])
    assert r.maxlen == 5
    assert len(r) == 1
    assert r.shape == (1,2)


def test_append():
    r = RingBuffer(5)

    r.append(1)
    np.testing.assert_equal(r, np.array([1]))
    assert len(r) == 1

    r.append(2)
    np.testing.assert_equal(r, np.array([1, 2]))
    assert len(r) == 2

    r.append(3)
    r.append(4)
    r.append(5)
    np.testing.assert_equal(r, np.array([1, 2, 3, 4, 5]))
    assert len(r) == 5

    r.append(6)
    np.testing.assert_equal(r, np.array([2, 3, 4, 5, 6]))
    assert len(r) == 5

    assert r[4] == 6
    assert r[-1] == 6


def test_getitem():
    r = RingBuffer(5)
    r.extend([1, 2, 3])
    r.extend_left([4, 5])
    expected = np.array([4, 5, 1, 2, 3])
    np.testing.assert_equal(r, expected)

    for i in range(r.maxlen):
        assert expected[i] == r[i]

    ii = [0, 4, 3, 1, 2]
    np.testing.assert_equal(r[ii], expected[ii])


def test_append_left():
    r = RingBuffer(5)

    r.append_left(1)
    np.testing.assert_equal(r, np.array([1]))
    assert len(r) == 1

    r.append_left(2)
    np.testing.assert_equal(r, np.array([2, 1]))
    assert len(r) == 2

    r.append_left(3)
    r.append_left(4)
    r.append_left(5)
    np.testing.assert_equal(r, np.array([5, 4, 3, 2, 1]))
    assert len(r) == 5

    r.append_left(6)
    np.testing.assert_equal(r, np.array([6, 5, 4, 3, 2]))
    assert len(r) == 5


def test_extend():
    r = RingBuffer(5)
    r.extend([1, 2, 3])
    np.testing.assert_equal(r, np.array([1, 2, 3]))
    r.pop_left()
    r.extend([4, 5, 6])
    np.testing.assert_equal(r, np.array([2, 3, 4, 5, 6]))
    r.extend_left([0, 1])
    np.testing.assert_equal(r, np.array([0, 1, 2, 3, 4]))

    r.extend_left([1, 2, 3, 4, 5, 6, 7])
    np.testing.assert_equal(r, np.array([1, 2, 3, 4, 5]))

    r.extend([1, 2, 3, 4, 5, 6, 7])
    np.testing.assert_equal(r, np.array([3, 4, 5, 6, 7]))


def test_pops():
    r = RingBuffer(3)
    r.append(1)
    r.append_left(2)
    r.append(3)
    np.testing.assert_equal(r, np.array([2, 1, 3]))

    assert r.pop() == 3
    np.testing.assert_equal(r, np.array([2, 1]))

    assert r.pop_left() == 2
    np.testing.assert_equal(r, np.array([1]))

    # test empty pops
    empty = RingBuffer(1)
    # with self.assertRaisesRegex(IndexError, "pop from an empty RingBuffer"):
    #     empty.pop()
    # with self.assertRaisesRegex(IndexError, "pop from an empty RingBuffer"):
    #     empty.pop_left()


def test_2d():
    r = RingBuffer(5, dtype=(np.float, 2))

    r.append([1, 2])
    np.testing.assert_equal(r, np.array([[1, 2]]))
    assert len(r) == 1
    assert np.shape(r), (1 == 2)

    r.append([3, 4])
    np.testing.assert_equal(r, np.array([[1, 2], [3, 4]]))
    assert len(r) == 2
    assert np.shape(r), (2 == 2)

    r.append_left([5, 6])
    np.testing.assert_equal(r, np.array([[5, 6], [1, 2], [3, 4]]))
    assert len(r) == 3
    assert np.shape(r), (3 == 2)

    np.testing.assert_equal(r[0], [5, 6])
    np.testing.assert_equal(r[0,:], [5, 6])
    np.testing.assert_equal(r[:,0], [5, 1, 3])


def test_iter():
    r = RingBuffer(5)
    for i in range(5):
        r.append(i)
    for i, j in zip(r, range(5)):
        assert i == j


def test_repr():
    r = RingBuffer(5, dtype=np.int)
    for i in range(5):
        r.append(i)

    assert repr(r), '<RingBuffer of array([0, 1, 2, 3 == 4])>'


def test_degenerate():
    r = RingBuffer(0)
    np.testing.assert_equal(r, np.array([]))

    # this does not error with deque(maxlen=0), so should not error here
    try:
        r.append(0)
        r.append_left(0)
    except IndexError:
        assert True is False
