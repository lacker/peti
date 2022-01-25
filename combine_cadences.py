#!/usr/bin/env python
"""
Given a json file of cadence data where we already have hitmaps, combine the data to find events
and plot it.
"""

import json
import sys

from event import Event
from hit_map import HitMap
from plot_event import save_event_plot

assert __name__ == "__main__"

# Process cadences based on the command line args
input_name = sys.argv[1]
if input_name.endswith(".json"):
    instream = open(input_name)
elif input_name == "-":
    instream = sys.stdin
else:
    raise RuntimeError("bad input name:", input_name)

for line in instream:
    info = json.loads(line.strip())
    hit_maps = [HitMap.load(f) for f in info["filenames"]]
    for event in Event.find_events(hit_maps):
        save_event_plot(event)
