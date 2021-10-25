#!/usr/bin/env python
"""
A tool to analyze files of shape (16, 1, 67108864) or similarly short-but-very-wide dimensions.
Reports which columns are "interesting".
"""

# These two dependencies must be imported in this order
import hdf5plugin
import h5py

import numpy as np
import sys

assert __name__ == "__main__"

filename = sys.argv[1]

assert h5py.is_hdf5(filename)
h5file = h5py.File(filename, "r")

data = h5file["data"]
height, _, width = data.shape
num_chunks = 64
assert width % num_chunks == 0
chunk_size = width // num_chunks

total_col = 0

for i in range(0, num_chunks):
    array = data[:, 0, (i * chunk_size):((i+1) * chunk_size)]

    # Blank out the exact middle, that's the DC spike
    array[:, chunk_size // 2] = 0

    mean = np.mean(array)
    factor = 2
    threshold = factor * mean
    high_pixel = (array > threshold).sum()
    colmax = array.max(axis=0)
    high_col = (colmax > threshold).sum()

    total_col += high_col

    if not high_pixel:
        continue
    
    print(f"chunk {i}")
    print(f"  mean: {mean:.1f}")
    print(f"  {high_pixel} interesting pixels, over {factor}x the mean")
    print(f"  {high_col} interesting columns")

print()
print(f"{total_col} interesting columns in total")
