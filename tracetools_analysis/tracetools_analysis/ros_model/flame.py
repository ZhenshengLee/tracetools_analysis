from .comm import Comm
from .node import NodePath
from .application import End2End

class Flame():
    @classmethod
    def _collapse_node(cls, path) -> str:
        assert(isinstance(path, NodePath))
        collapsed = ''
        for child in path.child:
            collapsed += '{};{} {}\n'.format(path.name, child.name, child.max_ms)
        return collapsed

    @classmethod
    def _collapse_comm(cls, path) -> str:
        assert(isinstance(path, Comm))
        return '{} {}\n'.format(path.name, path.max_ms)

    @classmethod
    def _collapse_app(cls, path) -> str:
        assert(isinstance(path, End2End))
        collapsed = ''
        for child in path.child:
            if isinstance(child, Comm):
                collapsed += Flame._collapse_comm(child)
            elif isinstance(child, NodePath):
                collapsed += Flame._collapse_node(child)
        return collapsed

    @classmethod
    def collapse(cls, path, fd):
        collapsed = ''
        if isinstance(path, End2End):
            collapsed = Flame._collapse_app(path)
        elif isinstance(path, NodePath):
            collapsed = Flame._collapse_node(path)
        assert collapsed != ''

        fd.write(collapsed)



