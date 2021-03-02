import pygraphviz as pgv
from ..ros_model.application import Application
from ..ros_model.util import Util

def lambda_pretty(func_name):
    import re
    m = re.search('^(.*?::).*(?<=\{)(.*)(?=\})', func_name)
    return  m.group(2)

def to_cluster_name(node):
    return f'cluster_{node.name}'

def get_highlit_items(app, target_path):
    for path in app.paths:
        if path.name == target_path:
            comms = path.child[1::2]
            nodes = path.child[0::2]
            callback_paths = Util.flatten([_.child[0::2] for _ in nodes])
            highlight = {
                'comm': comms,
                'callback': Util.flatten([_.child[0::2] for _ in nodes]),
                'sched': Util.flatten([_.child[1::2] for _ in nodes])
            }
            return highlight

    for path in app.nodes.paths:
        if path.name == target_path:
            highlight = {
                'comm': [],
                'callback': path.child[0::2],
                'sched': path.child[1::2]
            }
            return highlight

    for callback in app.callbacks:
        if callback.name == target_path:
            highlight = {
                'comm': [],
                'callback': [callback],
                'sched': []
            }
            return highlight

    for sched in app.scheds:
        if sched.name == target_path:
            highlight = {
                'comm': [],
                'callback': [],
                'sched': [sched]
            }
            return highlight

    for comm in app.comms:
        dds = comm.child[0]
        if comm.name == target_path or dds.name == target_path:
            highlight = {
                'comm': [comm],
                'callback': [],
                'sched': []
            }
            return highlight

    highlight = {
        'comm': [],
        'callback': [],
        'sched': []
    }
    return highlight

def draw_node_graph(app, png_path, target_path):
    import os
    from .common import prepare_dir
    assert isinstance(app, Application)
    assert isinstance(png_path, str)

    G = pgv.AGraph(directed=True, style='rounded', rankdir="LR", compound=True, label=target_path)
    G.node_attr['shape'] = 'rect'

    highlight = get_highlit_items(app, target_path)

    for node in app.nodes:
        if node.start_node:
            N = G.add_subgraph([], name=to_cluster_name(node),
                               label=f'{node.name} (start)',
                               style='rounded, filled, solid',
                               color='black', fillcolor='lightblue1')
        elif node.end_node:
            N = G.add_subgraph([], name=to_cluster_name(node),
                               label=f'{node.name} (end)',
                               style='rounded, filled, solid',
                               color='black', fillcolor='bisque')
        else:
            N = G.add_subgraph([],
                               name=to_cluster_name(node),
                               label=node.name,
                               style='rounded')

        for cb in node.callbacks:
            arg = {}
            if cb in highlight['callback'] or cb.path in highlight['callback']:
                arg['fillcolor'] = 'rosybrown1'
                arg['style'] = 'filled'
                arg['color'] = 'red'
            N.add_node(cb.symbol, label=lambda_pretty(cb.symbol), **arg)

    for comm in app.comms:
        arg = {}
        edge_to = comm.cb_sub.name
        arg['label'] = comm.topic_name

        if comm.cb_pub is None:
            edge_from = comm.node_pub.callbacks[0].name
            arg['color'] = 'black'
            arg['style'] = 'dashed'
            arg['ltail'] = to_cluster_name(comm.node_pub)
        else:
            edge_from = comm.cb_pub.name
            arg['color'] = 'blue'

        if comm in highlight['comm']:
            arg['color'] = 'red'

        G.add_edge(edge_from, edge_to, **arg)

    for sched in app.scheds:
        arg = {
            'color': 'blue',
            'rank': 'same',
            'constraint': False
        }
        if sched in highlight['sched']:
            arg['color'] = 'red'

        G.add_edge(sched.callback_in.name,
                   sched.callback_out.name,
                   **arg)

    print(f'{len(app.paths)} end-to-end paths found.')
    print(f'{len(app.nodes)} nodes, {len(app.nodes.paths)} node paths found.')
    print(f'{len(app.comms)} communication found.')
    print(f'{len(app.callbacks)} callbacks found.')

    if not app.has_start_node():
        print('Failed to find start node. Please set [/target_path/start_node_name].')
    if not app.has_end_node():
        print('Failed to find end node. Please set [/target_path/end_node_name].')
    unlinked = app.comms.get_unlinked()
    if len(unlinked) > 0:
        print(f'{len(unlinked)} communications have no callback name. Please set [/nodes/publish/topic].')

    prepare_dir(png_path)

    G.draw(png_path, prog="dot")
