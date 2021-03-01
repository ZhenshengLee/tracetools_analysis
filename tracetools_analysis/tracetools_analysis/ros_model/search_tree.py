import numpy as np
import collections.abc

class SearchNode():
    def __init__(self):
        self._subsequent = []

    def is_target(self):
        return False

    @property
    def subsequent(self):
        return self._subsequent

    @subsequent.setter
    def subsequent(self, subsequent_):
        self._subsequent = subsequent_


class SearchTree():
    @classmethod
    def search(cls, root_node):
        assert(isinstance(root_node, SearchNode))
        result_routes = []
        route = [root_node]
        cls.recursive_search(root_node, route, result_routes)
        return result_routes

    @classmethod
    def recursive_search(cls, node, route, result_routes):
        if node.is_target():
            result_routes.append(route)
        for node_ in node.subsequent:
            route_ = route + [node_]
            cls.recursive_search(node_, route_, result_routes)


class Path(SearchNode):
    def __init__(self, child=[]):
        super().__init__()

        self._hist = None
        self._timeseries = None
        self.child = child

    @property
    def child(self):
        return self._child

    @property
    def name(self):
        return '-'

    @child.setter
    def child(self, child):
        self._child = child

    @property
    def hist(self):
        return self._hist

    @hist.setter
    def hist(self, hist):
        self._hist = hist

    @property
    def timeseries(self):
        return self._timeseries

    @timeseries.setter
    def timeseries(self, timeseries):
        self._timeseries = timeseries
        self._hist = timeseries.to_hist()

    def has_hist(self, child):
        for path in child:
            if path._hist is None:
                return False
        return True

    def get_stats(self):
        return

class PathCollection(collections.abc.Iterable):
    def __init__(self):
        self._paths = []

    def __getitem__(self, key):
        return self._paths[key]

    def __len__(self):
        return len(self._paths)

    def __iter__(self):
        return PathsCollectionIterator(self)

    def append(self, path):
        assert(isinstance(path, Path))
        self._paths.append(path)

    def has(self, child):
        for path in self._paths:
            if child == path.child:
                return True
        return False


class PathsCollectionIterator(collections.abc.Iterator):
    def __init__(self, paths_collection):
        self._i = 0
        self._paths_collection = paths_collection

    def __next__(self):
        try:
            v = self._paths_collection._paths[self._i]
            self._i += 1
            return v
        except IndexError:
            raise StopIteration
