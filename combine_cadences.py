#!/usr/bin/env python
"""
Given a json file of cadence data where we already have hitmaps, combine the data to find events
and plot it.

Usage: ./combine_cadences.py <cadencelist>.json <output>.events
"""

import cupy as cp
import json
import os
from pathlib import Path
import psutil
import socket
import sys

from config import EVENT_ROOT
from event import Event
from hit_map import HitMap
from plot_event import save_event_plot


def iter_combine_cadences(cadence_file, output_file=None):
    """
    Accepts either a json file, or a directory containing a cadences.json file.
    output is the name of a .events file to create. If not provided, we guess a default location:
      {EVENT_ROOT}/{session}/{machine}.events
    This is idempotent; if the events file already exists we just exit.
    Pauses after each chunk of work.
    """
    if not cadence_file.endswith(".json"):
        cadence_file = os.path.join(cadence_file, "cadences.json")

    if output_file is None:
        # Guess the session from the location of the cadence file
        parts = cadence_file.split("/")
        session_list = [s for s in parts if "GBT" in s]
        assert len(session_list) == 1, cadence_file
        session = session_list[0]

        session_dir = os.path.expanduser(f"{EVENT_ROOT}/{session}")
        if not os.path.isdir(session_dir):
            Path(session_dir).mkdir(parents=True, exist_ok=True)
        output_file = os.path.join(session_dir, f"{socket.gethostname()}.events")

    assert output_file.endswith(".events")        
    if os.path.exists(output_file):
        print("found existing events file:", output_file)
        return

    events = []
    for line in open(cadence_file):
        info = json.loads(line.strip())
        filenames = info["filenames"]
        hit_maps = [HitMap.load(f) for f in filenames]
        new_events = [e for e in Event.find_events(hit_maps) if e.score() > 0]
        print(f"{len(new_events)} events found in {filenames[0]} etc")
        if not new_events:
            continue
        
        # Generate plots one file at a time, for data loading efficiency
        chunks = None
        newly_saved = 0
        for event in new_events:
            if not event.has_plot_file():
                save_event_plot(event, maybe_reuse_chunks=chunks)
                newly_saved += 1
                mb_ram = psutil.Process().memory_info().rss // 10**6
                gb_gpu = cp.get_default_memory_pool().total_bytes() // 10**6
                print(f"memory usage: {mb_ram}M RAM, {gb_gpu}M GPU")
                chunks = event.detach_chunks()
            
        events.extend(new_events)
        if newly_saved == 0:
            print(f"plots for these {len(new_events)} events have already been generated")
        yield

    print(len(events), "total events found")
        
    # When we save events we want to do it best-first
    events.sort(key=lambda e: -e.score())
    Event.save_list(events, output_file)
    print("combine_cadences complete. event list saved to", output_file)

    
def combine_cadences(cadence_file, output_file=None):
    for _ in iter_combine_cadences(cadence_file, output_file=output_file):
        pass

    
if __name__ == "__main__":
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    combine_cadences(input_file, output_file=output_file)


