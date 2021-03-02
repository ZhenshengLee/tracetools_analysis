import numpy as np

class Histogram:
    pass

class Histogram:
    __normalize = True

    def __init__(self, raw: np.array):
        raw = [_ for _ in raw if not np.isnan(_)]
        self.__raw = np.trim_zeros(raw, 'b')

    @classmethod
    def normalize(cls, use):
        cls.__normalize = use

    @classmethod
    def sum(cls, histgrams):
        hist = Histogram(histgrams[0].raw)
        for histgram in histgrams[1:]:
            hist = hist + histgram
        return hist

    def __add__(self, hist_: Histogram):
        tmp = np.convolve(self.__raw, hist_.raw, mode='full')
        tmp = np.trim_zeros(tmp, "b")
        return self.__class__(tmp)

    @property
    def raw(self) -> np.ndarray:
        tmp_raw = np.append(self.__raw, 0)
        if Histogram.__normalize:
            sum = np.sum(tmp_raw)
            assert(sum != 0)
            return tmp_raw / sum
        return self.__raw

class Timeseries:
    def __init__(self, raw: np.array, time: np.array, clock=None):
        self.__raw = raw
        self._time = time
        self._clock = clock

    @property
    def raw(self) -> np.ndarray:
        return self.__raw

    @property
    def raw_nan_removed(self) -> np.ndarray:
        return np.array([_ for _ in self.__raw if not np.isnan(_)])

    @property
    def time(self):
        return self._time

    @property
    def clock(self):
        return self._clock

    def to_hist(self, binsize_ns):
        raw = self.raw_nan_removed / binsize_ns
        bins = int(np.ceil(np.max(raw))) + 1
        assert bins < 100000, 'too large bin size.'
        range_max = int(np.ceil(np.max(raw))) + 1
        hist_raw, _ = np.histogram(raw, bins=bins, range=(0, range_max))
        return Histogram(hist_raw)
