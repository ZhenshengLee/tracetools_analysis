import collections.abc

from .search_tree import Path
from .publish import Publish

import numpy as np

class CallbackCollectionIterator(collections.abc.Iterator):
    def __init__(self, callback_collection):
        self._i = 0
        self._callback_collection = callback_collection

    def __next__(self):
        try:
            v = self._callback_collection._callbacks[self._i]
            self._i += 1
            return v
        except IndexError:
            raise StopIteration


class CallbackCollection(collections.abc.Iterable):
    def __init__(self):
        self._callbacks = []

    def append(self, callback):
        assert(isinstance(callback, Callback))
        self._callbacks.append(callback)

    def get_from_symbol(self, symbol):
        for callback in self._callbacks:
            if callback.symbol == symbol:
                return callback
        return None

    def __getitem__(self, key):
        return self._callbacks[key]

    def get_timer(self):
        return list(filter(lambda x: isinstance(x, TimerCallback), self._callbacks))

    def get_subscription(self):
        return list(filter(lambda x: isinstance(x, SubscribeCallback), self._callbacks))

    def __iter__(self):
        return CallbackCollectionIterator(self)


class CallbackFactory():
    ignore_topic_name = ['/rosout', '/parameter_events']

    @classmethod
    def create(cls, callback_info):
        if callback_info['type'] == 'timer_callback':
            callback = TimerCallback(
                period=callback_info['period'], symbol=callback_info['symbol'])
        elif callback_info['type'] == 'subscribe_callback':
            if callback_info['topic_name'] in CallbackFactory.ignore_topic_name:
                return
            callback = SubscribeCallback(
                topic_name=callback_info['topic_name'], symbol=callback_info['symbol'])

        for topic_name in callback_info['publish_topic_names']:
            if topic_name in CallbackFactory.ignore_topic_name:
                continue
            callback.publishes.append(Publish(topic_name=topic_name))

        return callback


class Callback():
    def __init__(self, symbol=None, object=None):
        self.publishes = []
        self.symbol = symbol
        self.object = object
        self.latency = CallbackPath(self)

    def has_publish(self, topic_name=None):
        if topic_name is None:
            return len(self.publishes) > 0
        return topic_name in [pub.topic_name for pub in self.publishes]

    @property
    def hist(self):
        return self.latency.hist

    @property
    def timeseries(self):
        return self.latency.timeseries

    @property
    def name(self):
        return self.symbol

    def get_info(self):
        pass

    def get_stats(self):
        data = {
            'min': np.min(self.timeseries.raw_nan_removed),
            'max': np.max(self.timeseries.raw_nan_removed),
            'median': np.median(self.timeseries.raw_nan_removed),
            'avg': np.mean(self.timeseries.raw_nan_removed)
        }
        return data


class CallbackPath(Path):
    def __init__(self, callback):
        super().__init__()
        self.child = []
        self._callback = callback

    def is_target(self):
        return self._callback.has_publish()

    @property
    def object(self):
        return self._callback.object

    @property
    def publishes(self):
        return self._callback.publishes

    @property
    def name(self):
        return self._callback.name

    @property
    def topic_name(self):
        if not isinstance(self._callback, SubscribeCallback):
            return ''
        return self._callback.topic_name


class TimerCallback(Callback):
    def __init__(self, period=None, symbol=None):
        super().__init__(symbol)
        self.period = period
        self.publishes = []

    def get_info(self):
        info = {
            'type': 'timer_callback',
            'period': self.period,
            'symbol': self.symbol,
            'subsequent_callback_symbols': [cb.symbol for cb in self.latency.subsequent],
            'publish_topic_names': [pub.topic_name for pub in self.publishes],
        }
        return info


class SubscribeCallback(Callback):
    def __init__(self, topic_name=None, symbol=None):
        super().__init__(symbol)
        self.topic_name = topic_name
        self.publishes = []

    def get_info(self):
        info = {
            'type': 'subscribe_callback',
            'topic_name': self.topic_name,
            'symbol': self.symbol,
            'publish_topic_names': [pub.topic_name for pub in self.publishes],
            'subsequent_callback_symbols': [cb.symbol for cb in self.latency.subsequent]
        }
        return info
