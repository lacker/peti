#!/usr/bin/env python
"""
Usage: ./make_one_cadence.py <id> <frequency> <six filenames>
"""
import json
import sys

cadence_id = int(sys.argv[1])
frequency = int(sys.argv[2])
filenames = sys.argv[3:]
assert len(filenames) == 6

print(json.dumps({
    "id": cadence_id,
    "frequency": frequency,
    "filenames": filenames,
}))
