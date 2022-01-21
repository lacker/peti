#!/usr/bin/env python
"""
A tool to analyze files of shape (16, 1, 67108864) or similarly short-but-very-wide dimensions.
Reports which columns are "interesting".
"""

import os
import random
import sys
import time

import cupy as cp

from h5_file import H5File
from hit_info import group_hit_windows
from hit_map import HitMap

def calculate_window_mean(array, window_size):
    """
    The ith column of the output is the average of a size-i window starting at the ith column and extending right.
    Averages are by row.
    Output is (window_size - 1) fewer columns than array.
    """
    assert window_size >= 1
    sums = cp.empty_like(array, dtype="float64")
    cp.cumsum(array, axis=1, out=sums)
    sums[:, window_size:] -= sums[:, :-window_size]
    return sums[:, window_size-1:] / window_size


def calculate_window_stats(array, window_size):
    """
    Returns mean and standard deviation. Window sizing works just like calculate_window_mean.
    This is sample standard deviation so it uses the "n" denominator rather than "n-1" for an estimator.
    We nudge zero deviation to slightly positive to avoid divide-by-zero errors.
    """
    assert window_size >= 2
    
    # mean = E[X]
    mean = calculate_window_mean(array, window_size)
    # ex2 = E[X^2]
    ex2 = calculate_window_mean(array * array, window_size)
    # Variance = E[X^2] - E[X]^2
    variance = ex2 - (mean * mean)
    std_dev = cp.maximum(cp.sqrt(variance), 0.01)
    return mean, std_dev
    

def apply_max_window(vector, window_size):
    """
    The output value of pixel i is the maximum value in the window whose first pixel is i, with a size of window_size.
    This does not allocate new memory, it just overwrites the input vector.
    Output size is the same as input size, so some windows will run off the end.
    """
    if window_size == 1:
        return

    # First we apply subwindows, then we take the max of two of them.
    # We need to round up on subwindow size, to be sure that two subwindows together
    # can cover the original window.
    subwindow_size = (window_size + 1) // 2
    apply_max_window(vector, subwindow_size)

    # shift is how much we need to shift one subwindow to combine two of them.
    # shift is either the subwindow size, or one less if we are calculating an odd-size window
    # and thus the two subwindows overlap a bit.
    shift = window_size - subwindow_size

    cp.maximum(vector[:-shift], vector[shift:], out=vector[:-shift])
    

class WindowCalculator(object):
    def __init__(self, data, window_size):
        """
        window_size is the size of the window to use for noise.
        data is a DataRange.
        """
        self.array = data.array
        self.window_size = window_size
        self.means, self.devs = calculate_window_stats(self.array, window_size)

    def pixel_snr(self):        
        """
        pixel snr is the signal of a particular pixel, compared to the "noise" as defined by
        a window either to the left or the right of the pixel.
        snr is the number of standard deviations from the mean it would be, using the noise population
        to define mean and standard deviation.
        The snr of a pixel is the higher of its left and right snr.
        """
        # left_snr is the snr calculated with noise using a window to the left
        left_snr = cp.zeros_like(self.array)
        left_snr[:, self.window_size:] = (self.array[:, self.window_size:] - self.means[:, :-1]) / self.devs[:, :-1]

        # right_snr is the snr calculated with noise using a window to the right
        right_snr = cp.zeros_like(self.array)
        right_snr[:, :-self.window_size] = (self.array[:, :-self.window_size] - self.means[:, 1:]) / self.devs[:, 1:]

        output = cp.maximum(left_snr, right_snr)
        return output

    def two_pixel_snr(self):
        """
        two-pixel snr is like pixel snr, except we calculate the signal as the average over two consecutive pixels.
        """
        # First, in spot i we calculate signal for the pixel pair indexed with (i, i+1).
        # signal is thus one column shorter than array.
        signal = (self.array[:, :-1] + self.array[:, 1:]) / 2

        # left_snr is the snr for the pixel pair indexed with (i, i+1) calculated with a noise window to the left.
        # thus the first window_size columns, and the last column, are zeros.
        left_snr = cp.zeros_like(self.array)
        left_snr[:, self.window_size:-1] = (signal[:, self.window_size:] - self.means[:, :-2]) / self.devs[:, :-2]

        # right_snr is the snr for the pixel pair indexed with (i, i+1) calculated with a noise window to the right.
        # thus the last (window_size+1) columns are zeros.
        right_snr = cp.zeros_like(self.array)
        right_snr[:, :-(self.window_size+1)] = (signal[:, :-self.window_size] - self.means[:, 2:]) / self.devs[:, 2:]

        # Each pixel has four ways to get its best score: as the left or right member of the pair, and with a left or
        # right window.
        output = cp.maximum(left_snr, right_snr)
        cp.maximum(output[:, :-1], output[:, 1:], out=output[:, 1:])
        return output

    
def find_hit_windows(mask):
    """
    Returns a list of hit windows. A hit window is a horizontal sequence of adjacent pixels defined by a tuple:
      (row, first_column, last_column)
    so that the hit matches:
      array[row, first_column : (last_column + 1)]
    mask is a boolean array of which spots to count as a hit.
    """
    rows, cols = cp.where(mask)

    # Group pixel hits into adjacent sequences
    hit_windows = []
    for row, col in sorted(zip(map(int, rows), map(int, cols))):
        if hit_windows:
            prev_row, prev_first_column, prev_last_column = hit_windows[-1]
            if prev_row == row and prev_last_column + 1 == col:
                # This pixel is an extension of the previous hit
                hit_windows[-1] = (prev_row, prev_first_column, col)
                continue
        # This pixel is the start of its own hit
        hit_windows.append((row, col, col))

    return hit_windows


def find_hits(coarse_channel, chunk, experiment=False):
    """
    Returns a list of HitInfo objects.
    """
    calc = WindowCalculator(chunk, 30)
    pixel_snr = calc.pixel_snr()
    two_pixel_snr = calc.two_pixel_snr()

    pixel_thresh = 6
    two_pixel_thresh = 4

    if experiment:
        pixel_thresh = 7
        
    mask = (pixel_snr > pixel_thresh) | (two_pixel_snr > two_pixel_thresh)

    hit_windows = find_hit_windows(mask)            
    hits = group_hit_windows(hit_windows, coarse_channel, chunk)
    return hits
        

class Scanner(object):
    def __init__(self, h5_filename):
        self.h5_file = H5File(h5_filename)
        self.hitmap = HitMap.from_h5_file(self.h5_file)
        print("loaded", h5_filename, flush=True)

    def num_chunks(self):
        return self.h5_file.num_chunks
        
    def scan_chunk(self, i):
        start_time = time.time()
        chunk = self.h5_file.get_chunk(i)
        mid_time = time.time()
        hits = find_hits(i, chunk)
        for hit in hits:
            hit.linear_fit()
        end_time = time.time()
        elapsed = end_time - start_time
        self.hitmap.add_hits(hits, strip_data_reference=True)
        gb = cp.get_default_memory_pool().total_bytes() / 10**9
        print(f"scanned chunk {i} in {elapsed:.1f}s, GPU mem {gb:.2f}G, finding {len(hits)} hits", flush=True)
        
    def scan_all(self):
        for i in range(self.num_chunks()):
            self.scan_chunk(i)

    def save(self):
        out = self.hitmap.save()
        print("wrote hitmap to", out)

        
def scan(h5_filename):
    file_start_time = time.time()
    scanner = Scanner(h5_filename)
    scanner.scan_all()
    file_end_time = time.time()
    file_elapsed = file_end_time - file_start_time
    print(f"scan of {h5_filename} complete")
    print(f"total scan time {file_elapsed:.1f}s")
    print(f"found {len(scanner.hitmap.hits)} hits", flush=True)    
    scanner.save()

    
if __name__ == "__main__":
    filename = sys.argv[1]
    hitmap = scan(filename)



