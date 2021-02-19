import matplotlib.pyplot as plt

class Graph():
    def __init__(self, data):
        self.data = data

    def export(self, path):
        pass

class Histogram(Graph):
    def export(self, path):
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)

        plt.plot(self.data, c='g', label='Result')
        plt.xlabel('Latency [ms]')
        plt.ylabel('Probablility')
        plt.savefig(path)
        plt.clf()

class Timeseries(Graph):
    def export(self, path):
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)

        x_max = len(self.data)
        plt.plot(range(x_max), self.data, c='g', label='Result')
        plt.xlabel('Sample')
        plt.ylabel('Latency [ms]')
        plt.savefig(path)
        plt.clf()
