#!/usr/bin/env python
"""
Given a json file of cadence information, creates any hit maps that have not been created yet.

Usage: ./scan_cadences.py <cadencelist>.json
"""

import json
import os
import sys

import scanner
from hit_map import make_hit_map_filename


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
    for h5_filename in info["filenames"]:
        if os.path.exists(make_hit_map_filename(h5_filename)):
            continue
        scanner.scan(h5_filename)
