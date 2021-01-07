from tracetools_analysis.utils.ros2 import Ros2DataModelUtil
from tracetools_analysis.loading import load_file
from tracetools_analysis.processor.ros2 import Ros2Handler

from .util import Util
from .node import Node, NodePath, NodeFactory, NodeCollection
from .comm import CommCollection, Comm
from .callback import SubscribeCallback, TimerCallback, Callback
from .publish import Publish
from .search_tree import SearchTree, Path
from .data_type import Timeseries, Histogram

import pandas as pd


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
        self.comms = CommCollection()

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

    def import_trace(self, trace_dir):
        assert(self.nodes != [])
        events = load_file(trace_dir)
        for event in events:
            event['_timestamp'] = Util.ns_to_ms(event['_timestamp'])

        handler = Ros2Handler.process(events)

        self.data_util = Ros2DataModelUtil(handler.data)
        self._insert_runtime_data(self.data_util, self.nodes)

        self._import_callback_durations(handler.data.callback_instances)
        self._import_sched_durations(self._get_sched_instances(events))
        self._import_communication_instances(
            self._get_communication_instances(events))

    def export(self, path):
        import json
        with open(path, mode='w') as f:
            f.write(json.dumps(self.get_info(), indent=2))

    def _search_paths(self, nodes):
        node_paths = self.nodes.paths
        # find subsequent nodes
        for node_path in node_paths:
            for pub in node_path.child[-1].publishes:
                subsequent = self.nodes.get_subsequent_paths(pub)
                node_path.subsequent = subsequent

        # search all path
        paths_node_only = []
        for node_path in self.nodes.get_root_paths():
            paths_node_only += SearchTree.search(node_path)

        # create path objects and insert communication latency
        paths = []
        for path_node_only in paths_node_only:
            child = [path_node_only[0]]
            for node_pub, node_sub in zip(path_node_only[:-1], path_node_only[1:]):
                comm = Comm(node_pub, node_sub)
                self.comms.append(comm)
                child.append(comm)
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

    def _import_communication_instances(self, instances):
        for comm in self.comms:
            objects = comm.get_objects()
            duration_records = instances[
                (instances['publish_object'] == objects['publish']) &
                (instances['subscribe_object'] == objects['subscribe'])]

            comm.timeseries = Timeseries(duration_records['duration'].values)
            comm.hist = comm.timeseries.to_hist()

    def _get_communication_instances(self, events):
        class PublishRecord():
            def __init__(self, stamp, time):
                self.stamp = stamp
                self.time = time

        def get_publish_point(object, stamp) -> PublishRecord:
            publish_point = pub_time[object]
            if publish_point.stamp == stamp:
                return publish_point
            return None

        to_pub_node = {}
        for comm in self.comms:
            objects = comm.get_objects()
            to_pub_node[objects['subscribe']] = objects['publish']
        communication_instances = pd.DataFrame(columns=['publish_object',
                                                        'subscribe_object',
                                                        'timestamp',
                                                        'duration'])
        pub_time = {}
        for event in events:
            if event['_name'] == 'ros2:rclcpp_publish':
                pub_time[event['publisher_handle']] = PublishRecord(
                    event['stamp'],
                    event['_timestamp']
                )
            elif event['_name'] == 'ros2:rclcpp_subscribe':
                subscribe_object = event['callback']
                publish_object = to_pub_node[event['callback']]
                publish_point = get_publish_point(
                    publish_object, event['stamp'])
                if publish_point:
                    duration = event['_timestamp'] - publish_point.time
                    data = {
                        'publish_object': publish_object,
                        'subscribe_object': subscribe_object,
                        'timestamp': event['_timestamp'],
                        'duration': duration
                    }
                communication_instances = communication_instances.append(
                    data, ignore_index=True)
        return communication_instances.astype({'publish_object': 'int64', 'subscribe_object': 'int64'})

    def _get_sched_instances(self, events):
        callback_out_objects = [
            _.callback_out.callback.object for _ in self.scheds]
        callback_in_objects = [
            _.callback_in.callback.object for _ in self.scheds]

        to_in_object = {
            _.callback_out.callback.object: _.callback_in.callback.object for _ in self.scheds}
        sched_instances = pd.DataFrame(columns=[
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
                        'callback_in_object': callback_in_object,
                        'callback_out_object': callback_out_object,
                        'duration': duration
                    }
                    sched_instances = sched_instances.append(
                        data, ignore_index=True)

        sched_instances = sched_instances.astype(
            {'callback_in_object': 'int64',
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
