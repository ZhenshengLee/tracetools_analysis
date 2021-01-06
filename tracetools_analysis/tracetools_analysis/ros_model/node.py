import collections.abc

from .search_tree import SearchTree, Path
from .data_type import Histogram
from .util import Util
from .callback import SubscribeCallback, CallbackFactory, CallbackCollection
from .sched import Sched, SchedCollection
from .publish import Publish


class Node():
    def __init__(self, name=None, ns=None, start_node=False, end_node=False):
        super().__init__()
        self.name = name
        self.ns = ns
        self.start_node = start_node
        self.end_node = end_node
        self.callbacks = CallbackCollection()
        self.__scheds = SchedCollection()
        self.unlinked_publishes = []
        self.__paths = []

    @property
    def paths(self):
        return self.__paths

    @property
    def scheds(self):
        return self.__scheds

    @property
    def publish_topics(self):
        return [pub.topic_name for pub in self.publishes()]

    @property
    def subscribe_topics(self):
        return list(self.subscribe_callbacks.keys())

    @property
    def publishes(self):
        return Util.flatten([cb.publishes for cb in self.callbacks])

    def get_info(self):
        info = {
            'name': self.name,
            'namespace': self.ns,
            'start_node': self.start_node,
            'end_node': self.end_node,
            'callbacks': [
                cb.get_info() for cb in self.callbacks],
            'unlinked_publish_topic_names': [
                pub.topic_name for pub in self.unlinked_publishes]}
        return info

    def update_paths(self):
        self.__paths = self._search_paths()

    def _search_paths(self):
        if self.end_node is True:
            paths_ = []
            for callback in self.callbacks.get_subscription():
                path = Path(child=[callback.latency])
                paths_.append(
                    NodePath(path, self, self.start_node, self.end_node))
            return paths_

        paths_callback_only = Util.flatten(
            ([SearchTree.search(_.latency) for _ in self.callbacks]))

        # create path object and insert sched latency
        paths_ = []
        for path_callback_only in paths_callback_only:
            child = [path_callback_only[0]]
            for callback_write, callback_read in zip(
                    path_callback_only[:-1], path_callback_only[1:]):
                child.append(self.__scheds.get(callback_write, callback_read))
                child.append(callback_read)
            path = Path(child)
            paths_.append(NodePath(path, self, self.start_node, self.end_node))

        return paths_


class NodeCollection(collections.abc.Iterable):
    def __init__(self):
        self._nodes = []

    @property
    def paths(self):
        return Util.flatten([node.paths for node in self._nodes])

    def get_root_paths(self):
        return list(filter(lambda x: x.start_node, self.paths))

    def get_subsequent_paths(self, publisher):
        assert(isinstance(publisher, Publish))
        node_paths_ = []
        for node_path in self.paths:
            head_callback = node_path.child[0].callback
            if not isinstance(head_callback, SubscribeCallback):
                continue
            if head_callback.topic_name == publisher.topic_name:
                node_paths_.append(node_path)
        return node_paths_

    def append(self, node):
        self._nodes.append(node)

    def __iter__(self):
        return NodeCollectionIterator(self)

    def __getitem__(self, key):
        return self._nodes[key]


class NodeFactory():
    @classmethod
    def create(cls, node_info):
        node = Node(name=node_info['name'],
                    ns=node_info['namespace'],
                    start_node=node_info['start_node'],
                    end_node=node_info['end_node'],
                    )

        for callback_info in node_info['callbacks']:
            node.callbacks.append(CallbackFactory.create(callback_info))

        # find subsequent callback and insert sched object
        for callback_info in node_info['callbacks']:
            symbol = callback_info['symbol']
            for subsequent_callback_symbol in callback_info['subsequent_callback_symbols']:
                callback = node.callbacks.get_from_symbol(symbol).latency
                subsequent_callback = node.callbacks.get_from_symbol(
                    subsequent_callback_symbol).latency
                callback.subsequent.append(subsequent_callback)
                node.scheds.append(Sched(callback, subsequent_callback))

        node.update_paths()
        return node


class NodePath(Path):
    def __init__(self, path, node, start_node, end_node):
        super().__init__()
        self.child = path.child
        self.__node = node
        self.__path = path
        self.__start_node = start_node
        self.__end_node = end_node

    @property
    def hist(self):
        return Histogram.sum([_.hist for _ in self.child])

    @property
    def start_node(self):
        return self.__node.start_node

    @property
    def publishes(self):
        return self.child[-1].publishes

    @property
    def end_node(self):
        return self.__node.end_node

    @property
    def name(self):
        return self.__node.name

    @property
    def path(self):
        return self.__path

    @property
    def publish_topics(self):
        return [pub.topic_name for pub in self.__path.child[-1].publishes]

    @property
    def subscribe_topic(self):
        head_callback = self.__path.child[0].callback
        assert(isinstance(head_callback, SubscribeCallback))
        return head_callback.topic_name

    def is_target(self):
        return self.end_node

    def has_subscribe_callback(self):
        return isinstance(self.__path.child[0], SubscribeCallback)


class NodeCollectionIterator(collections.abc.Iterator):
    def __init__(self, node_collection):
        self._i = 0
        self._node_collection = node_collection

    def __next__(self):
        try:
            v = self._node_collection._nodes[self._i]
            self._i += 1
            return v
        except IndexError:
            raise StopIteration
