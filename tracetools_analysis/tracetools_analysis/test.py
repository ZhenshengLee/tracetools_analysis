import numpy as np
import fire
from enum import Enum

from tracetools_analysis.test_interface.common import Result, read_yaml, write_yaml, Unit
from tracetools_analysis.test_interface.test_case import TestCaseFactory, TestTarget
from tracetools_analysis.test_interface.graph import Histogram, Timeseries

from tracetools_analysis.ros_model import ApplicationFactory

class GraphType(Enum):
    HIST = 1,
    TIMESERIES = 2

def base_name_format(base_name):
    import re
    base_name = re.sub('^/', '', base_name)
    base_name = re.sub('/', '_', base_name)
    return base_name

def get_graph_path(export_dir, path_name, graph_type):
    import os
    assert isinstance(graph_type, GraphType)
    if graph_type == GraphType.HIST:
        file_name = '{}-hist.png'.format(base_name_format(path_name))
    elif graph_type == GraphType.TIMESERIES:
        file_name = '{}-timeseries.png'.format(base_name_format(path_name))
    graph_path = os.path.join(export_dir, 'graph', file_name)
    return graph_path

def test_target_parse(target):
    import re

    def path_name(target):
        result = re.match(r'(.*)\(.*\)', target)
        return result.group(1).strip()
    
    def unit(target):
        result = re.match(r'.*\((.*?)\)', target)
        unit_name = result.group(1)
        return Unit(unit_name)
    
    return path_name(target), unit(target)


class Analyzer():
    def __init__(self, app):
        self.app = app

    def parse_input_obj(self, input_obj):
        test_targets = []

        for test_target_str, test_target_yml in input_obj.items():
            path_name, unit = test_target_parse(test_target_str)

            path = self.app.find_path(path_name)
            test_target = TestTarget(unit, path)
            test_targets.append(test_target)
            factory = TestCaseFactory(unit, test_target)

            for test_case_name, criteria in test_target_yml.items():
                test_case = factory.create(test_case_name, criteria['desired'], criteria['acceptable'])
                test_target.add_test(test_case)

            if 'std' not in test_target_yml.items():
                test_case = factory.create('std')
                test_target.add_test(test_case)

        return test_targets

    def analyze_targets(self, test_targets, export_dir):
        import os
        output_obj = {}

        for target in test_targets:
            large_category_str = '{} ({})'.format(target.path.name, target.unit)
            output_obj[large_category_str] = {}
            large_category = output_obj[large_category_str]

            large_category['evaluation'] = str(target.judge())

            for test in target.tests:
                large_category[str(test)] = {}
                small_category = large_category[str(test)]
                small_category['value'] = str(round(test.get_stat(), 1))
                if test.judge() is not None:
                    small_category['evaluation'] = str(test.judge())

            large_category['graph-path'] = {}
            graph = large_category['graph-path']

            if target.path.hist is not None:
                graph_path = get_graph_path(export_dir, target.path.name, GraphType.HIST)
                graph_path_relative = os.path.relpath(graph_path, export_dir)
                graph['histogram'] = graph_path_relative

            if target.path.timeseries is not None:
                graph_path = get_graph_path(export_dir, target.path.name, GraphType.TIMESERIES)
                graph_path_relative = os.path.relpath(graph_path, export_dir)
                graph['timeseries'] = graph_path_relative

        return output_obj

    def analyze(self, input_obj, export_dir):
        test_targets = self.parse_input_obj(input_obj)
        output_obj = self.analyze_targets(test_targets, export_dir)
        return output_obj


def get_analysis_target():
    def run(trace_path:str, architecture_path:str):
        """get_analysis_target
        list up all analysis target.
        """
        app = ApplicationFactory.create(architecture_path)
        app.import_trace(trace_path)

        for path in app.get_path_list():
            print(path.name)

    fire.Fire(run)

def export_graph(app, export_dir):
    for path in app.get_path_list():
        if path.hist is not None:
            graph_path = get_graph_path(export_dir, path.name, GraphType.HIST)
            histogram = Histogram(path.hist.raw)
            histogram.export(graph_path)

        if path.timeseries is not None:
            graph_path = get_graph_path(export_dir, path.name, GraphType.TIMESERIES)
            timeseries = Timeseries(path.timeseries.raw)
            timeseries.export(graph_path)

def trace_analysis():
    def run(input_yaml_path: str, export_dir: str, trace_path: str, architecture_path: str):
        """get_analysis_target
        judges trace results.
        """
        import os

        app = ApplicationFactory.create(architecture_path)
        app.import_trace(trace_path)

        input_obj = read_yaml(input_yaml_path)

        analyzer = Analyzer(app)
        output_obj = analyzer.analyze(input_obj, export_dir)
        export_graph(app, export_dir)

        output_yaml_path = os.path.join(export_dir, 'output.yaml')
        write_yaml(output_yaml_path, output_obj)

    fire.Fire(run)
