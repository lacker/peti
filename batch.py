#!/usr/bin/env python
"""
Do some batch processing, converting h5 -> hitmap
"""

import os
import random
import sys

import hit_map
import scanner

assert __name__ == "__main__"
input_filename = sys.argv[1]

h5_filenames = [line.strip() for line in open(input_filename)]
random.shuffle(h5_filenames)

for h5_filename in h5_filenames:
    if os.path.exists(hit_map.make_hit_map_filename(h5_filename)):
        continue
    hitmap = scanner.scan(h5_filename)
    hitmap.save()
