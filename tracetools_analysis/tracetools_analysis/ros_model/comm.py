import collections.abc

from .search_tree import Path
from .node import NodePath


class Comm(Path):
    def __init__(self, node_pub, node_sub):
        assert(isinstance(node_pub, NodePath))
        assert(isinstance(node_sub, NodePath))
        self.node_pub = node_pub
        self.node_sub = node_sub

    def get_objects(self):
        sub = self.node_sub.child[0].callback
        sub_topic_name = sub.topic_name

        for pub in self.node_pub.publishes:
            if pub.topic_name == sub_topic_name:
                return {'publish': pub.object, 'subscribe': sub.object}

    @property
    def name(self):
        return self.node_sub.subscribe_topic


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
