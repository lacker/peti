#!/usr/bin/env python
"""
A tool to analyze files of shape (16, 1, 67108864) or similarly short-but-very-wide dimensions.
Reports which columns are "interesting".
"""

# These two dependencies must be imported in this order
import hdf5plugin
import h5py

import numpy as np
import cupy as cp
import sys

xp = np

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
total_sig = 0

for i in range(0, num_chunks):
    array = xp.array(data[:, 0, (i * chunk_size):((i+1) * chunk_size)])

    # Blank out the exact middle, that's the DC spike
    midpoint = chunk_size // 2
    array[:, midpoint] = 0

    mean = array.mean()
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

    # Find local signal
    signal = array.copy()
    signal -= xp.roll(array, -1, axis=1)
    signal -= xp.roll(array, 1, axis=1)
    sig_pixel = (signal > 0).sum()
    total_sig += sig_pixel
    print(f"  {sig_pixel} pixels with signal, according to the local scan algorithm")
    
    
print()
print(f"{total_col} interesting columns in total")
print(f"{total_sig} sig pixels in total")
