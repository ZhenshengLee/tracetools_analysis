import numpy as np

class SearchNode():
    def __init__(self):
        self.__subsequent = []

    def is_target(self):
        return False

    @property
    def subsequent(self):
        return self.__subsequent

    @subsequent.setter
    def subsequent(self, subsequent_):
        self.__subsequent = subsequent_


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

        if self.child != []:
            self.subsequent = child[-1].subsequent

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
    def max_ms(self):
        tmp_raw = np.trim_zeros(self.hist.raw, 'b')
        return len(tmp_raw)-1

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
