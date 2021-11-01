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

def pretty_number(n):
    powers_of_two = 0
    rest = n
    while rest % 2 == 0:
        rest = rest // 2
        powers_of_two += 1
    if powers_of_two < 2:
        return str(n)
    power_part = f"2^{powers_of_two}"
    if rest > 1:
        return f"{rest}*{power_part}"
    return power_part


assert __name__ == "__main__"

filename = sys.argv[1]

assert h5py.is_hdf5(filename)
h5file = h5py.File(filename, "r")

data = h5file["data"]
height, _, width = data.shape
num_chunks = 64
assert width % num_chunks == 0
chunk_size = width // num_chunks
print("chunk size:", pretty_number(chunk_size))

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
    classic_mask = array > threshold
    high_pixel = classic_mask.sum()
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
    window_diff = array.copy()
    window_diff -= xp.roll(array, -1, axis=1)
    window_diff -= xp.roll(array, 1, axis=1)
    window_mask = window_diff > 0
    window_pixel = window_mask.sum()
    print(f"  {window_pixel} interesting pixels, according to window scan")

    # Calculate window-based SNR
    sums = xp.cumsum(array, axis=1)

    # Now what?
    
    total_window += window_pixel
    
    
    
print()
print(f"{total_col} interesting columns in total")
print(f"{total_window} sig pixels in total")
