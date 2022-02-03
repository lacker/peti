#!/usr/bin/env python
"""
Usage: random_loading_test.py <filename>

Tests a bunch of random accesses of the data in an h5 file.
"""

import h5py

import numpy as np
import random
import sys
import time

assert __name__ == "__main__"

filename = sys.argv[1]
assert h5py.is_hdf5(filename)
f = h5py.File(filename, "r")
data = f["data"]
height, _, width = data.shape

num_loads = 1000
print(filename, ": testing", num_loads, "random loads")

start_time = time.time()
for i in range(num_loads):
    part_start_time = time.time()

    w = random.randrange(width)
    part = data[:, 0, w : w + 50]
    np.sum(part)
    
    part_end_time = time.time()
    if i % (num_loads // 10) == 0 and False:
        print(f"load {i} took {part_end_time-part_start_time:.3f}s")

end_time = time.time()
print(f"total time elapsed: {end_time-start_time:.2f}s")
print()
