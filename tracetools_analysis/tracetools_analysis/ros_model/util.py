import os
import pandas as pd

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


class DataFrameFilter():

    def __init__(self):
        self.min_limit = None
        self.max_limit = None

    def remove(self, df: pd.DataFrame, target_column_name: str):
        if self.min_limit is not None:
            df = df[df[target_column_name] > self.min_limit]

        if self.max_limit is not None:
            df = df[df[target_column_name] < self.max_limit]

        df.reset_index(inplace=True, drop=True)

        return df
