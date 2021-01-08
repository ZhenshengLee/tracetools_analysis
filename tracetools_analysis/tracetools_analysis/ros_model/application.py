from tracetools_analysis.utils.ros2 import Ros2DataModelUtil
from tracetools_analysis.loading import load_file
from tracetools_analysis.processor.ros2 import Ros2Handler

from .util import Util, DataFrameFilter
from .node import Node, NodePath, NodeFactory, NodeCollection
from .comm import CommCollection, Comm
from .callback import SubscribeCallback, TimerCallback, Callback
from .publish import Publish
from .search_tree import SearchTree, Path
from .data_type import Timeseries, Histogram

import pandas as pd
import numpy as np


class End2End(Path):
    def _get_node_latencies(self):
        return list(filter(lambda x: isinstance(x, NodePath), self.child))

    @property
    def hist(self):
        return Histogram.sum([_.hist for _ in self.child])

    @property
    def name(self):
        return '--'.join([_.name for _ in self._get_node_latencies()])


class Application():
    def __init__(self):
        self.nodes = NodeCollection()
        self.data_util = None
        self.__paths = None
        self.events = None
        self.comms = CommCollection()
        self.comm_instances = None
        self._filter = DataFrameFilter()

    @property
    def paths(self):
        return self.__paths

    @property
    def scheds(self):
        return Util.flatten([_.scheds for _ in self.nodes])

    def update_paths(self):
        self.__paths = self._search_paths(self.nodes)

    def get_info(self):
        info = {
            'nodes': [node.get_info() for node in self.nodes]
        }
        return info

    def import_trace(self, trace_dir, start_transition_ms=0, end_transition_ms=0):
        assert(self.nodes != [])
        events = load_file(trace_dir)
        self.events = events
        for event in events:
            event['_timestamp'] = Util.ns_to_ms(event['_timestamp'])

        handler = Ros2Handler.process(events)

        self.data_util = Ros2DataModelUtil(handler.data)
        self._insert_runtime_data(self.data_util, self.nodes)

        self._filter.min_limit = events[0]['_timestamp'] + start_transition_ms
        self._filter.max_limit = events[-1]['_timestamp'] - end_transition_ms

        callback_durations = handler.data.callback_instances
        callback_durations = self._filter.remove(callback_durations, 'timestamp')
        assert len(callback_durations) > 0, 'all instance are removed'
        self._import_callback_durations(callback_durations)

        sched_instances = self._get_sched_instances(events)
        sched_instances = self._filter.remove(sched_instances, 'timestamp')
        assert len(sched_instances) > 0, 'all instance are removed'
        self._import_sched_durations(sched_instances)

        comm_instances = self._get_comm_instances(events, self.comms)
        comm_instances = self._filter.remove(comm_instances, 'timestamp')
        self.comm_instances = comm_instances
        assert len(comm_instances) > 0, 'all instance are removed'
        self._import_comm_instances(comm_instances)

    def export(self, path):
        import json
        with open(path, mode='w') as f:
            f.write(json.dumps(self.get_info(), indent=2))

    def _search_paths(self, nodes):
        node_paths = self.nodes.paths
        # find subsequent nodes
        for node_path in node_paths:
            node_path.subsequent = self.nodes.get_subsequent_paths(node_path)

        # search all path
        paths_node_only = []
        for node_path in self.nodes.get_root_paths():
            paths_node_only += SearchTree.search(node_path)

        for path_node_only in paths_node_only:
            for node_pub, node_sub in zip(path_node_only[:-1], path_node_only[1:]):
                if not self.comms.has(node_pub, node_sub):
                    self.comms.append(Comm(node_pub, node_sub))

        # create path objects and insert communication latency
        paths = []
        for path_node_only in paths_node_only:
            child = [path_node_only[0]]
            for node_pub, node_sub in zip(path_node_only[:-1], path_node_only[1:]):
                child.append(self.comms.get(node_pub, node_sub))
                child.append(node_sub)
            paths.append(End2End(child))
        return paths

    def _import_callback_durations(self, callback_instances):
        for node in self.nodes:
            for callback in node.callbacks:
                callback_duration_records = callback_instances[
                    callback_instances['callback_object'] == callback.object]
                callback_durations = callback_duration_records['duration'].values
                callback.latency.timeseries = Timeseries(callback_durations)

    def _import_comm_instances(self, instances):
        for comm in self.comms:
            objects = comm.get_objects()
            duration_records = instances[
                (instances['publish_object'] == objects['publish']) &
                (instances['subscribe_object'] == objects['subscribe'])]

            comm.timeseries = Timeseries(duration_records['duration'].values)
            comm.hist = comm.timeseries.to_hist()

    def get_publish_instances(self, events):
        publish_instances = pd.DataFrame(columns=[
            'timestamp',
            'stamp',
            'publisher_handle'])

        for event in events:
            if event['_name'] == 'ros2:rclcpp_publish':
                data = {
                    'timestamp': event['_timestamp'],
                    'publisher_handle': event['publisher_handle'],
                    'stamp': event['stamp']
                }
                publish_instances = publish_instances.append(data, ignore_index=True)

        publish_instances = pd.merge(publish_instances,  self.data_util.get_publish_info() , on='publisher_handle')
        publish_instances.reset_index(inplace=True, drop=True)

        return publish_instances

    def get_subscribe_instances(self, events):
        subscribe_instances = pd.DataFrame(columns=[
            'timestamp',
            'stamp',
            'callback_object'])

        for event in events:
            if event['_name'] == 'ros2:rclcpp_subscribe':
                data = {
                    'timestamp': event['_timestamp'],
                    'stamp': event['stamp'],
                    'callback_object': event['callback']
                }
                subscribe_instances = subscribe_instances.append(data, ignore_index=True)

        subscribe_instances = pd.merge(subscribe_instances,  self.data_util.get_subscribe_info(), on='callback_object')
        subscribe_instances.reset_index(inplace=True, drop=True)

        return subscribe_instances

    def _get_comm_instances(self, events, comms):
        publish_instances = self.get_publish_instances(events)
        subscribe_instances = self.get_subscribe_instances(events)

        comm_instances = [self._get_specific_comm_instances(comm,
                                                  publish_instances,
                                                  subscribe_instances) \
                          for comm in comms]
        comm_instances = pd.concat(comm_instances)
        return comm_instances

    def _get_specific_comm_instances(self, comm, publish_df, subscribe_df):
        obj = comm.get_objects()

        publish_object = obj['publish']
        subscribe_object = obj['subscribe']

        comm_instances = pd.DataFrame(columns=['publish_object',
                                               'subscribe_object',
                                               'timestamp',
                                               'duration'])

        # filter specific records
        publish_df_ = publish_df[publish_df['publisher_handle'] == publish_object]
        publish_df_.reset_index(inplace=True, drop=True)
        subscribe_df_ = subscribe_df[subscribe_df['callback_object'] == subscribe_object] 
        subscribe_df_.reset_index(inplace=True, drop=True)

        for i, publish_record in publish_df_.iterrows():
            subscribe_record = subscribe_df_[subscribe_df_['stamp'] == publish_record['stamp']]
            duration = None
            if len(subscribe_record) == 1:
                duration = subscribe_record['timestamp'].values[0] - publish_record['timestamp']
            data = {
                'timestamp': publish_record['timestamp'],
                'publish_object': publish_object,
                'subscribe_object': subscribe_object,
                'duration': duration
            }
            comm_instances = comm_instances.append(data, ignore_index=True)

        # remove last records if values are NaN
        valid_messages_df = comm_instances[~(np.isnan(comm_instances['duration']))]
        last_valid_idx = valid_messages_df.index[-1]
        comm_instances = comm_instances.iloc[:last_valid_idx+1]

        return comm_instances

    def _get_sched_instances(self, events):
        callback_out_objects = [
            _.callback_out.callback.object for _ in self.scheds]
        callback_in_objects = [
            _.callback_in.callback.object for _ in self.scheds]

        to_in_object = {
            _.callback_out.callback.object: _.callback_in.callback.object for _ in self.scheds}
        sched_instances = pd.DataFrame(columns=[
            'timestamp',
            'callback_in_object',
            'callback_out_object',
            'duration'])

        schedule_instances = {}
        calculated_instances = {}
        for callback_out_object in callback_out_objects:
            calculated_instances[callback_out_object] = {}

        for event in events:
            if 'ros2:callback_end' in event['_name']:
                if event['callback'] in callback_in_objects:
                    schedule_instances[event['callback']] = event['_timestamp']

            elif 'ros2:callback_start' in event['_name']:
                if event['callback'] in callback_out_objects:
                    callback_out_object = event['callback']
                    callback_in_object = to_in_object[callback_out_object]
                    if calculated_instances[callback_out_object].get(callback_in_object) == schedule_instances.get(callback_in_object):
                        continue
                    duration = event['_timestamp'] - \
                        schedule_instances[callback_in_object]
                    calculated_instances[callback_out_object][callback_in_object] = schedule_instances[callback_in_object]
                    data = {
                        'timestamp': event['_timestamp'],
                        'callback_in_object': callback_in_object,
                        'callback_out_object': callback_out_object,
                        'duration': duration
                    }
                    sched_instances = sched_instances.append(
                        data, ignore_index=True)

        sched_instances = sched_instances.astype(
            {'timestamp': 'float64',
             'callback_in_object': 'int64',
             'callback_out_object': 'int64',
             'duration': 'float64'})
        return sched_instances

    def _import_sched_durations(self, sched_instances):
        for sched in self.scheds:
            duration_records = sched_instances[
                (sched_instances['callback_in_object'] == sched.callback_in.callback.object) &
                (sched_instances['callback_out_object']
                 == sched.callback_out.callback.object)
            ]
            duration_raw = duration_records['duration'].values
            sched.timeseries = Timeseries(duration_raw)

    def _insert_runtime_data(self, data_util, nodes):
        self._insert_callback_object(data_util)
        self._insert_publish_object(data_util, nodes)

    def _insert_publish_object(self, data_util, nodes):
        for node in nodes:
            for pub in node.publishes:
                pub.object = data_util.get_publish_object(node.name, pub.topic_name)

    def _insert_callback_object(self, data_util):
        # トレース結果のcallback objectを挿入
        for node in self.nodes:
            for callback in node.callbacks:
                if not isinstance(callback, Callback):
                    continue
                callback.object = data_util.get_callback_object(callback.symbol)
                assert callback.object is not None, 'failed to get callback_object'


class ApplicationFactory():
    @classmethod
    def create(cls, path):
        ext = Util.get_ext(path)
        if ext == 'json':
            return ApplicationFactory._create_from_json(path)
        else:
            return ApplicationFactory._create_from_trace(path)

    @classmethod
    def _create_from_json(cls, path):
        app = Application()
        import json
        with open(path, 'r') as f:
            app_info = json.load(f)

        for node_info in app_info['nodes']:
            app.nodes.append(NodeFactory.create(node_info))

        # find subsequent nodes
        node_latencies = Util.flatten([node.paths for node in app.nodes])
        for node in node_latencies:
            for node_ in node_latencies:
                if node_.has_subscribe_callback() and node_.subscribe_topic in node.publish_topics:
                    node.subsequent.append(node_)

        app.update_paths()
        return app

    @classmethod
    def _get_duplicate_num_max(cls, array):
        count_max = 0
        for element in list(set(array)):
            count_max = max(count_max, len(array[array == element]))
        return count_max

    @classmethod
    def _create_node(cls, node_info, data_util):
        timer_df = data_util.get_timer_info()
        sub_df = data_util.get_subscribe_info()
        pub_df = data_util.get_publish_info()

        node = Node(name=node_info['name'], ns=node_info['namespace'])

        timer_df_ = timer_df[timer_df['name'] == node.name]
        assert ApplicationFactory._get_duplicate_num_max(timer_df_['period'].values) <= 1,\
            '{} node has same period'.format(node.name)
        for i, (_, df) in enumerate(timer_df_.iterrows()):
            callback = TimerCallback(period=df['period'], symbol=df['symbol'])
            node.callbacks.append(callback)

        sub_df_ = sub_df[sub_df['name'] == node.name]
        assert ApplicationFactory._get_duplicate_num_max(sub_df_['topic_name'].values) <= 1, \
            '{} node has same topic_name'.format(node.name)
        for i, (_, df) in enumerate(sub_df_.iterrows()):
            if df['topic_name'] in ['/parameter_events']:
                continue
            callback = SubscribeCallback(
                topic_name=df['topic_name'], symbol=df['symbol'])
            node.callbacks.append(callback)

        pub_df_ = pub_df[pub_df['name'] == node.name]
        for _, df in pub_df_.iterrows():
            if df['topic_name'] in ['/rosout', '/parameter_events']:
                continue
            node.unlinked_publishes.append(
                Publish(topic_name=df['topic_name']))
        return node

    @classmethod
    def _create_app(cls, data_util):
        app = Application()
        for _, node_info in data_util.data.nodes.drop('timestamp', axis=1).iterrows():
            node = ApplicationFactory._create_node(node_info, data_util)
            app.nodes.append(node)
        return app

    @classmethod
    def _create_from_trace(cls, path):
        events = load_file(path)

        for event in events:
            event['_timestamp'] = Util.ns_to_ms(event['_timestamp'])

        handler = Ros2Handler.process(events)
        data_util = Ros2DataModelUtil(handler.data)
        app = ApplicationFactory._create_app(data_util)

        return app
