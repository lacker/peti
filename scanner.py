#!/usr/bin/env python
"""
A tool to analyze files of shape (16, 1, 67108864) or similarly short-but-very-wide dimensions.
Reports which columns are "interesting".
"""

import os
import random
import sys

from config import xp
from h5_file import H5File
from hit_group import group_hits


def calculate_window_mean(array, window_size):
    """
    The ith column of the output is the average of a size-i window starting at the ith column and extending right.
    Averages are by row.
    Output is (window_size - 1) fewer columns than array.
    """
    assert window_size >= 1
    sums = xp.empty_like(array, dtype="float64")
    xp.cumsum(array, axis=1, out=sums)
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
    std_dev = xp.maximum(xp.sqrt(variance), 0.01)
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

    xp.maximum(vector[:-shift], vector[shift:], out=vector[:-shift])
    

class WindowCalculator(object):
    def __init__(self, array, window_size):
        """
        window_size is the size of the window to use for noise.
        array is 2d, where the second dimension is the one we are windowing along.
        """
        self.array = array
        self.window_size = window_size
        self.means, self.devs = calculate_window_stats(array, window_size)

    def pixel_snr(self):        
        """
        pixel snr is the signal of a particular pixel, compared to the "noise" as defined by
        a window either to the left or the right of the pixel.
        snr is the number of standard deviations from the mean it would be, using the noise population
        to define mean and standard deviation.
        The snr of a pixel is the higher of its left and right snr.
        """
        # left_snr is the snr calculated with noise using a window to the left
        left_snr = xp.zeros_like(self.array)
        left_snr[:, self.window_size:] = (self.array[:, self.window_size:] - self.means[:, :-1]) / self.devs[:, :-1]

        # right_snr is the snr calculated with noise using a window to the right
        right_snr = xp.zeros_like(self.array)
        right_snr[:, :-self.window_size] = (self.array[:, :-self.window_size] - self.means[:, 1:]) / self.devs[:, 1:]

        output = xp.maximum(left_snr, right_snr)
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
        left_snr = xp.zeros_like(self.array)
        left_snr[:, self.window_size:-1] = (signal[:, self.window_size:] - self.means[:, :-2]) / self.devs[:, :-2]

        # right_snr is the snr for the pixel pair indexed with (i, i+1) calculated with a noise window to the right.
        # thus the last (window_size+1) columns are zeros.
        right_snr = xp.zeros_like(self.array)
        right_snr[:, :-(self.window_size+1)] = (signal[:, :-self.window_size] - self.means[:, 2:]) / self.devs[:, 2:]

        # Each pixel has four ways to get its best score: as the left or right member of the pair, and with a left or
        # right window.
        output = xp.maximum(left_snr, right_snr)
        xp.maximum(output[:, :-1], output[:, 1:], out=output[:, 1:])
        return output

    
def find_hits(mask):
    """
    Returns a list of hits. A hit is a horizontal sequence of adjacent pixels defined by a tuple:
      (row, first_column, last_column)
    so that the hit matches:
      array[row, first_column : (last_column + 1)]
    mask is a boolean array of which spots to count as a hit.
    This "hit" tuple structure is used in other places too.
    """
    rows, cols = xp.where(mask)

    # Group pixel hits into adjacent sequences
    hits = []
    for row, col in sorted(zip(rows, cols)):
        if hits:
            prev_row, prev_first_column, prev_last_column = hits[-1]
            if prev_row == row and prev_last_column + 1 == col:
                # This pixel is an extension of the previous hit
                hits[-1] = (prev_row, prev_first_column, col)
                continue
        # This pixel is the start of its own hit
        hits.append((row, col, col))

    return hits


def find_groups(chunk, experiment=False):
    """
    Returns a list of HitGroup objects.
    """
    calc = WindowCalculator(chunk, 30)
    pixel_snr = calc.pixel_snr()
    two_pixel_snr = calc.two_pixel_snr()

    pixel_thresh = 6
    two_pixel_thresh = 4

    if experiment:
        pixel_thresh = 7
        
    mask = (pixel_snr > pixel_thresh) | (two_pixel_snr > two_pixel_thresh)

    hits = find_hits(mask)            
    groups = group_hits(hits)
    return [g for g in groups if len(g) > 2]
        

if __name__ == "__main__":
    filename = sys.argv[1]
    f = H5File(filename)
    f.process_all()

