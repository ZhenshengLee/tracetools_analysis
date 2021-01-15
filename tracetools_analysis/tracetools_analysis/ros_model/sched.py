import collections.abc
import numpy as np

from .callback import Callback, CallbackPath
from .search_tree import Path

class SchedCollectionIterator(collections.abc.Iterator):
    def __init__(self, sched_collection):
        self._i = 0
        self._sched_collection = sched_collection

    def __next__(self):
        try:
            v = self._sched_collection._scheds[self._i]
            self._i += 1
            return v
        except IndexError:
            raise StopIteration


class SchedCollection(collections.abc.Iterable):
    def __init__(self):
        self._scheds = []

    def append(self, sched):
        assert(isinstance(sched, Sched))
        self._scheds.append(sched)

    def get(self, callback_in, callback_out):
        def f(x):
            return x.callback_in == callback_in and x.callback_out == callback_out

        scheds = list(filter(lambda x: f(x), self._scheds))
        return scheds[0]

    def has(self, callback_in, callback_out):
        for sched in self._scheds:
            if sched.callback_in == callback_in and sched.callback_out == callback_out:
                return True
        return False

    def get(self, callback_in, callback_out):
        assert isinstance(callback_in, Callback) or isinstance(callback_in, CallbackPath)
        assert isinstance(callback_out, Callback) or isinstance(callback_in, CallbackPath)

        for sched in self._scheds:
            if sched.callback_in == callback_in and sched.callback_out == callback_out:
                return sched

        raise KeyError('failed to find sched object. callback_in:{} callback_out:{}'.format(callback_in.name, callback_out.name))

    def __iter__(self):
        return SchedCollectionIterator(self)

    def __getitem__(self, key):
        return self._scheds[key]


class Sched(Path):
    def __init__(self, callback_in, callback_out):
        assert isinstance(callback_in, CallbackPath)
        assert isinstance(callback_out, CallbackPath)

        super().__init__()
        self.callback_in = callback_in
        self.callback_out = callback_out


    @property
    def name(self):
        return '{}--{}'.format(self.callback_in.name, self.callback_out.name)

    def get_stats(self):
        data = {
            'min': np.min(self.timeseries.raw_nan_removed),
            'max': np.max(self.timeseries.raw_nan_removed),
            'median': np.median(self.timeseries.raw_nan_removed),
            'avg': np.mean(self.timeseries.raw_nan_removed),
            'send': len(self.timeseries.raw),
            'lost': len(self.timeseries.raw)-len(self.timeseries.raw_nan_removed)
        }
        return data
