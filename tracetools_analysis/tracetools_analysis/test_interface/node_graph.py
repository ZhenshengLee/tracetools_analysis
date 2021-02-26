import pygraphviz as pgv
from ..ros_model.application import Application

def lambda_pretty(func_name):
    import re
    m = re.search('^(.*?::).*(?<=\{)(.*)(?=\})', func_name)
    return  m.group(2)

def to_cluster_name(node):
    return f'cluster_{node.name}'

def draw_node_graph(app, png_path):
    assert isinstance(app, Application)
    assert isinstance(png_path, str)

    # app = ApplicationFactory.create_from_json(architecture_path)
    G = pgv.AGraph(directed=True, style='rounded', rankdir="LR", compound=True)
    G.node_attr['shape'] = 'rect'

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
            N.add_node(cb.symbol, label=lambda_pretty(cb.symbol))

    for comm in app.comms:
        arg = {}
        edge_to = comm.cb_sub.name

        if comm.cb_pub is None:
            edge_from = comm.node_pub.callbacks[0].name
            arg['color'] = 'red'
            arg['ltail'] = to_cluster_name(comm.node_pub)
        else:
            edge_from = comm.cb_pub.name
            arg['color'] = 'blue'

        G.add_edge(edge_from, edge_to, **arg)

    for sched in app.scheds:
        G.add_edge(sched.callback_in.name,
                   sched.callback_out.name,
                   color='blue', rank='same', constraint=False)

    print(f'{len(app.paths)} paths found.')

    if not app.has_start_node():
        print('Failed to find start node. Please set [/target_path/start_node_name].')
    if not app.has_end_node():
        print('Failed to find end node. Please set [/target_path/end_node_name].')
    unlinked = app.comms.get_unlinked()
    if len(unlinked) > 0:
        print(f'{len(unlinked)} communications have no callback name. Please set [/nodes/publish/topic].')

    G.draw("tmp.png", prog="dot")
