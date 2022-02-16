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


def iter_scan_cadences(cadence_file):
    """
    Accepts either a json file, or a directory containing a cadences.json file.
    Pauses after each scan.
    """
    if not cadence_file.endswith(".json"):
        cadence_file = os.path.join(cadence_file, "cadences.json")

    for line in open(cadence_file):
        for h5_filename in info["filenames"]:
            if os.path.exists(make_hit_map_filename(h5_filename)):
                continue
            scanner.scan(h5_filename)
            yield
    print("scan_cadences complete")

    
def scan_cadences(cadence_file):
    for _ in iter_scan_cadences(cadence_file):
        pass
    
if __name__ == "__main__":
    # Process cadences based on the command line args
    input_name = sys.argv[1]
    scan_cadences(input_name)

