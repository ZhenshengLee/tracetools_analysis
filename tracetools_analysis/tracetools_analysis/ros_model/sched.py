import collections.abc

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

    def __iter__(self):
        return SchedCollectionIterator(self)


class Sched(Path):
    def __init__(self, callback_in, callback_out):
        super().__init__()
        self.callback_in = callback_in
        self.callback_out = callback_out

    @property
    def name(self):
        return '{} -> {}'.format(self.callback_in.name, self.callback_out.name)
