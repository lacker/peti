#!/usr/bin/env python
"""
A script to analyze the efficiency of different dedoppler methods.

Usage: ./dedoppler.py <file.h5>
"""

import cp
import sys

from h5_file import H5File

assert __name__ == "__main__"


def get_stats(name, data):
    print(f"stats for {name}:")
    low, median, high = cp.percentile(data, [5, 50, 95])
    print(f"percentile 5: {low}")
    print(f"percentile 50: {median}")
    print(f"percentile 95: {high}")
    drop_high = data[data <= high]
    drop_outliers = drop_high[drop_high >= low]
    stdev = drop_outliers.std()
    print(f"stdev dropping outliers: {stdev}")
    return median, stdev


h5_filename = sys.argv[1]
h5_file = H5File(h5_filename)

for i in range(h5_file.num_chunks):
    print("chunk", i)
    chunk = h5_file.get_chunk(i)

    columns = chunk.array.sum(axis=0)
    column_median, column_stdev = get_stats("columns", columns)
    pixels = chunk.array.flatten()
    pixel_median, pixel_stdev = get_stats("pixels", pixels)
    print(f"c-to-p median ratio: {column_median / pixel_median}")
    print(f"c-to-p stdev ratio: {column_stdev / pixel_stdev}")
