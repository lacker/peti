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
for i in range(num_chunks):
    array = data[:, 0, (i * chunk_size):((i+1) * chunk_size)]
    mean = np.mean(array)
    factor = 2
    over = (array > (factor * mean)).sum()
    print(f"chunk {i} has mean {mean:.1f} and {over} pixels over {factor}x the mean")
