#!/usr/bin/env python
"""
Given a json file of cadence information, creates any hit maps that have not been created yet.
"""

import json
import os
import sys

import scanner
from hit_map import make_hit_map_filename

def load_cadences():
    answer = []
    for line in open("/home/obs/cadences.json"):
        info = json.loads(line)
        filenames = info["filenames"]
        dirs = [f.split("/")[-2] for f in filenames]
        if min(dirs) != max(dirs):
            continue
        answer.append(filenames)
    return answer

if __name__ == "__main__":
    # Process lots of cadences
    json_filename = sys.argv[1]
    assert json_filename.endswith(".json")
    for line in open(json_filename):
        info = json.loads(line.strip())
        for h5_filename in info["filenames"]:
            if os.path.exists(make_hit_map_filename(h5_filename)):
                continue
            scanner.scan(h5_filename)
