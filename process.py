#!/usr/bin/env python3
# Entrypoint/script to process events from a pickle file to build a ROS model

import sys
import pickle
from tracetools_analysis.analysis.ros import *

def main(argv=sys.argv):
    if len(argv) != 2:
        print('usage: pickle_file')
        exit(1)
    
    pickle_filename = sys.argv[1]
    with open(pickle_filename, 'rb') as f:
        events = _get_events_from_pickled_file(f)
        print(f'imported {len(events)} events')
        ros_process(events)

def _get_events_from_pickled_file(file):
    p = pickle.Unpickler(file)
    events = []
    while True:
        try:
            events.append(p.load())
        except EOFError as _:
            break  # we're done
    return events
