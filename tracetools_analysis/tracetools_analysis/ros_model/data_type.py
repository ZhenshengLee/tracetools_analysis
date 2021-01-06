import numpy as np

class Histogram:
    pass

class Histogram:
    __normalize = True

    def __init__(self, raw: np.array):
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
        if Histogram.__normalize:
            sum = np.sum(self.__raw)
            assert(sum != 0)
            return self.__raw / sum
        return self.__raw


class Timeseries:
    def __init__(self, raw: np.array):
        self.__raw = raw

    @property
    def raw(self) -> np.ndarray:
        return self.__raw

    def to_hist(self):
        bins = int(np.ceil(np.max(self.__raw))) + 1
        assert bins < 10000, 'too large bin size.'
        range_max = int(np.ceil(np.max(self.__raw))) + 1
        hist_raw, _ = np.histogram(self.__raw, bins=bins, range=(0, range_max))
        return Histogram(hist_raw)
