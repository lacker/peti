#!/usr/bin/env python
"""
Usage: linear_loading_test.py <filename>

Just does a linear scan through all the data in an h5 file.
"""

import h5py

import numpy as np
import sys
import time

assert __name__ == "__main__"

filename = sys.argv[1]
assert h5py.is_hdf5(filename)
f = h5py.File(filename, "r")
data = f["data"]
height, _, width = data.shape

# Load it in 64 parts, to represent coarse channels
num_loads = 64
load_size = width // num_loads
print(filename, ": testing", num_loads, "linear loads")

start_time = time.time()
for i in range(num_loads):
    part_start_time = time.time()
    start = load_size * i
    part = data[:, 0, start : start + load_size]
    # Do something with the data to ensure that h5py isn't lazy-loading
    np.sum(part)
    part_end_time = time.time()
    # print(f"load {i} took {part_end_time-part_start_time:.1f}s")

end_time = time.time()
print(f"total time elapsed: {end_time-start_time:.1f}s")
print()
