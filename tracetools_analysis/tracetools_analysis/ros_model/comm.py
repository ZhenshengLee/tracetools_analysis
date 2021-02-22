import collections.abc

from .search_tree import Path
from .node import NodePath
from .util import Counter

import numpy as np

class DDS(Path):
    counter = Counter()

    def __init__(self, node_pub, node_sub):
        assert(isinstance(node_pub, NodePath))
        assert(isinstance(node_sub, NodePath))
        self.node_pub = node_pub
        self.node_sub = node_sub
        self.child = []

        topic_name = self.node_sub.child[0].topic_name
        self.counter.add(self, topic_name)
        self._index = self.counter.get_count(self, topic_name)

    def get_objects(self):
        sub = self.node_sub.child[0]
        sub_topic_name = sub.topic_name

        for pub in self.node_pub.publishes:
            if pub.topic_name == sub_topic_name:
                return {'publish': pub.object, 'subscribe': sub.object}

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

    @property
    def name(self):
        return '{}_dds_{}'.format(self.node_sub.subscribe_topic, self._index)


class Comm(Path):
    counter = Counter()

    def __init__(self, node_pub, node_sub):
        assert(isinstance(node_pub, NodePath))
        assert(isinstance(node_sub, NodePath))
        self.node_pub = node_pub
        self.node_sub = node_sub
        self.child = [DDS(node_pub, node_sub)]

        topic_name = self.node_sub.child[0].topic_name
        self.counter.add(self, topic_name)
        self._index = self.counter.get_count(self, topic_name)

    def get_objects(self):
        sub = self.node_sub.child[0]
        sub_topic_name = sub.topic_name

        for pub in self.node_pub.publishes:
            if pub.topic_name == sub_topic_name:
                return {'publish': pub.object, 'subscribe': sub.object}

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


    @property
    def name(self):
        return '{}_{}'.format(self.node_sub.subscribe_topic, self._index)


class CommCollectionIterator(collections.abc.Iterator):
    def __init__(self, inter_node_collection):
        self._i = 0
        self._inter_node_collection = inter_node_collection

    def __next__(self):
        try:
            v = self._inter_node_collection._comms[self._i]
            self._i += 1
            return v
        except IndexError:
            raise StopIteration


class CommCollection(collections.abc.Iterable):
    def __init__(self):
        self._comms = []

    def append(self, inter_node):
        self._comms.append(inter_node)

    def __iter__(self):
        return CommCollectionIterator(self)

    def __getitem__(self, key):
        return self._comms[key]

    def __len__(self):
        return len(self._comms)

    def has(self, node_pub, node_sub):
        assert isinstance(node_pub, NodePath)
        assert isinstance(node_sub, NodePath)

        return self.get(node_pub, node_sub) is not None

    def get(self, node_pub, node_sub):
        for comm in self._comms:
            if comm.node_pub.same_publish(node_pub) and \
               comm.node_sub.same_subscription(node_sub):
                return comm
        return None
