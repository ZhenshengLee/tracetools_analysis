import collections.abc

from .search_tree import SearchTree, Path
from .data_type import Histogram
from .util import Util, Counter
from .callback import SubscribeCallback, CallbackFactory, CallbackCollection, CallbackPath
from .sched import Sched, SchedCollection
from .publish import Publish, PublishCollection


class Node():
    def __init__(self, name=None, ns=None, start_node=False, end_node=False):
        super().__init__()
        self.name = name
        self.ns = ns
        self.start_node = start_node
        self.end_node = end_node
        self.callbacks = CallbackCollection()
        self.scheds = SchedCollection()
        self.pubs = PublishCollection()
        self.__paths = []

    @property
    def subs (self):
        return [cb for cb in self.callbacks if isinstance(cb, SubscribeCallback)]

    @property
    def paths(self):
        return self.__paths

    @property
    def publish_topics(self):
        return [pub.topic_name for pub in self.publishes()]

    @property
    def publishes(self):
        return self.pubs

    def get_info(self):
        info = {
            'name': self.name,
            'namespace': self.ns,
            'callbacks': [
                cb.get_info() for cb in self.callbacks],
            'callback_dependency': self.scheds.get_info(),
            'publish': self.pubs.get_info(),
            'start_node': self.start_node,
            'end_node': self.end_node
        }
        return info

    def update_paths(self):
        self.__paths = self._search_paths()

    def _search_paths(self):
        if self.end_node is True:
            paths_ = []
            for callback in self.callbacks.get_subscription():
                paths_.append(NodePath([callback.path], self, self.start_node, self.end_node))
            return paths_

        paths_callback_only = Util.flatten(
            ([SearchTree.search(_.path) for _ in self.callbacks]))

        # create path object and insert sched latency
        paths_ = []
        for path_callback_only in paths_callback_only:
            paths_.append(NodePath(path_callback_only, self, self.start_node, self.end_node))

        return paths_


class NodeCollection(collections.abc.Iterable):
    def __init__(self):
        self._nodes = []

    @property
    def paths(self):
        return Util.flatten([node.paths for node in self._nodes])

    def get_root_paths(self):
        return list(filter(lambda x: x.start_node, self.paths))

    def get_subsequent_paths(self, node_path):
        assert(isinstance(node_path, NodePath))

        subsequent_paths = []
        tail_callback = node_path.child[-1]
        for pub in tail_callback.publishes:
            for node_path_ in self.paths:
                head_callback = node_path_.child[0]
                if head_callback.topic_name == pub.topic_name:
                    subsequent_paths.append(node_path_)
        return subsequent_paths

    def append(self, node):
        self._nodes.append(node)

    def __iter__(self):
        return NodeCollectionIterator(self)

    def __len__(self):
        return len(self._nodes)

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
            node.callbacks.append(CallbackFactory.create(callback_info, node))

        for depend_from_symbol, depend_to_symbol in node_info['callback_dependency'].items():
            if depend_from_symbol == '':
                continue
            depend_from = node.callbacks.get_from_symbol(depend_from_symbol)
            depend_to = node.callbacks.get_from_symbol(depend_to_symbol)
            assert depend_from is not None, f'Failed to get {depend_from_symbol}'
            assert depend_to is not None, f'Failed to get {depend_to_symbol}'
            node.scheds.append(Sched(depend_from, depend_to))

        for topic_name, cb_symbol in node_info['publish'].items():
            if topic_name == '':
                continue
            callback = node.callbacks.get_from_symbol(cb_symbol)
            node.pubs.append(Publish(topic_name=topic_name, callback=callback))

        import itertools
        for cb, sched in itertools.product(node.callbacks, node.scheds):
            if cb == sched.callback_in:
                cb.path.subsequent.append(sched)
            if sched.callback_out == cb:
                sched.subsequent.append(cb.path)

        node.update_paths()
        return node


class NodePath(Path):
    counter = Counter()

    def __init__(self, child, node, start_node, end_node):
        super().__init__(child)
        self.__node = node
        self.__start_node = start_node
        self.__end_node = end_node
        self.counter.add(self, node.name)
        self._index = self.counter.get_count(self, node.name)

    @property
    def hist(self):
        return Histogram.sum([_.hist for _ in self.child])

    @property
    def node(self):
        return self.__node

    def same_publish(self, node_path):
        return self.child[-1] == node_path.child[-1]

    def same_subscription(self, node_path):
        return self.child[0] == node_path.child[0]

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
    def child_names(self):
        return '--'.join([_.name for _ in self._get_callback_latencies()])

    @property
    def name(self):
        return '{}_{}'.format(self.__node.name, self._index)

    @property
    def publish_topics(self):
        return [pub.topic_name for pub in self.child[-1].publishes]

    @property
    def subscribe_topic(self):
        head_callback = self.child[0]
        return head_callback.topic_name

    def _get_callback_latencies(self):
        return list(filter(lambda x: isinstance(x, CallbackPath), self.child))

    def is_target(self):
        return self.end_node


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
