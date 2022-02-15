#!/usr/bin/env python
"""
Given a directory with h5 files in it, construct a cadences.json file in that directory, suitable for scan_cadences to use.

The format created is one json object per line, with each line having:
filenames: list of filenames

Usage: ./detect_cadences.py <directory>
"""

import json
import os
import sys

from h5_file import H5File


def detect_cadences(directory):
    print("detecting cadences in", directory)
    contents = os.listdir(directory)

    # (timestamp, source_name, filename) tuples
    info = []

    for basename in contents:
        filename = os.path.join(directory, basename)
        if not filename.endswith(".0000.h5"):
            continue
        h5_file = H5File(filename)
        timestamp = h5_file.timestamp()
        source_name = h5_file.source_name()
        data = (timestamp, source_name, filename)
        info.append(data)

    info.sort()

    cadences = []
    
    while len(info) >= 6:
        candidates = info[:6]
        target = candidates[0][1]
        if target == candidates[2][1] == candidates[4][1] and target not in [candidates[i][1] for i in (1, 3, 5)]:
            cadences.append({"filenames": [filename for _, _, filename in candidates]})
            info = info[6:]
        else:
            info = info[1:]

    cadence_file = os.path.join(directory, "cadences.json")
    with open(cadence_file, "w") as outfile:
        for cadence in cadences:
            outfile.write(json.dumps(cadence) + "\n")
    print(f"{len(cadences)} cadences detected. writing information to {cadence_file}")
            

if __name__ == "__main__":
    directory = sys.argv[1]
    detect_cadences(directory)
