import os


class Util():
    @classmethod
    def flatten(cls, x):
        import itertools
        return list(itertools.chain.from_iterable(x))

    @classmethod
    def ext(cls, path):
        import os
        _, ext = os.path.splitext(path)
        return ext[1:]

    @classmethod
    def ns_to_ms(cls, x):
        return x * 1.0e-6

    @classmethod
    def get_ext(cls, path):
        return os.path.basename(path).split('.')[-1]
