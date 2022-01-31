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

output_name = sys.argv[2]
assert output_name.endswith(".events")

for line in instream:
    info = json.loads(line.strip())
    hit_maps = [HitMap.load(f) for f in info["filenames"]]
    events = list(Event.find_events(hit_maps))
    print(len(events), "events found")

    # When we save events we want to do it best-first
    events.sort(key=lambda e: -e.score)
    good_events = [e for e in events if e.score > 0]
    print(len(good_events), "good events found")
    Event.save_list(good_events, output_name)
    print("event list saved to", output_name)

    # Image loading for plot generation is faster to do it in frequency order
    good_events.sort(key=lambda e: e.frequency_range())
    for event in good_events:
        if not event.has_plot_file():
            save_event_plot(event)
            event.depopulate_chunks()
            
    print("for now, we are just processing one cadence")
    sys.exit(0)
