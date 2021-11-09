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
    

def calculate_window_snr(array, window_size):
    """
    array is 2d, where the second dimension is the one we are windowing along.
    The window SNR is calculated using three windows:
    AAAAAABBBBBBCCCCCC
    window_size is the size of each one of these three windows.
    The SNR for the B window is the average of the B area, divided by the average of the A and C areas.
    So this defines the SNR for a *window*.
    The SNR for a *pixel* is the maximum SNR of any window containing it.

    This returns an array of the same size as the input array. For edge pixels where we can't fit in a full window,
    we just report a SNR of zero.
    """
    num_rows, num_cols = array.shape
    array_size = num_rows * num_cols
    flattened = xp.reshape(array, (array_size,))

    signal_kernel = [0] * window_size + [2] * window_size + [0] * window_size
    noise_kernel = [1] * window_size + [0] * window_size + [1] * window_size
    signal = xp.convolve(flattened, signal_kernel, "valid")
    noise = xp.convolve(flattened, noise_kernel, "valid")
    signal /= noise

    # The length of the signal and noise arrays here is slightly smaller than the length of flattened:
    #   (array_size - 3 * window_size + 1)
    # The value at index i in the signal array reflects the signal of a window whose first pixel is at
    # index (i + window_size) in the flattened array.
    # We want to create an output array where that value is at index (i + window_size).
    # The apply_max_window process will spread out values up to (window_size - 1) spots leftwards.
    # So we pad flattened by (2 * window_size - 1) on the left. This leaves (window_size) padding on the right.
    # Intuitively, the first and last window_size pixels we cannot get any SNR for, because there is no room to
    # put the full noise window on one side of them.
    flattened_output = xp.pad(signal, (2 * window_size - 1, window_size), "constant", constant_values=(0, 0))
    
    # Give each pixel the best score from any window it belongs to
    apply_max_window(flattened_output, window_size)
    
    output = xp.reshape(flattened_output, (num_rows, num_cols))
    
    # Since we did the convolutions in a flattened array, we have some signal values where we combined
    # multiple rows. These values are basically garbage, so we just want to zero them out.
    output[:, :window_size] = 0
    output[:, -window_size:] = 0
    return output


class File(object):
    def __init__(self, filename):
        assert h5py.is_hdf5(filename)
        self.h5file = h5py.File(filename, "r")
        self.data = self.h5file["data"]
        self.height, _, self.width = self.data.shape
        self.num_chunks = 64
        assert self.width % self.num_chunks == 0
        self.chunk_size = self.width // self.num_chunks

    def get_chunk(self, i):
        assert 0 <= i < self.num_chunks
        array = xp.array(self.data[:, 0, (i * self.chunk_size):((i+1) * self.chunk_size)])

        # Blank out the exact middle, that's the DC spike
        midpoint = self.chunk_size // 2
        array[:, midpoint] = (array[:, midpoint - 1] + array[:, midpoint + 1]) / 2

        return array
        
    def process_array(self, array):
        """
        Returns a list of hits. A hit is a tuple:
          (row, first_column, last_column)
        so that the hit matches:
          array[row, first_column : (last_column + 1)]
        """
        min_snr = 2
        window_snr = calculate_window_snr(array, 1)
        rows, cols = xp.where(window_snr > min_snr)
        interesting_pixels = list(zip(rows, cols))
        print(f"  {len(interesting_pixels)} interesting pixels")
        return interesting_pixels


    def process_all(self):
        for i in range(self.num_chunks):
            print(f"chunk {i}")
            array = self.get_chunk(i)
            print(self.process_array(array))

    
if __name__ == "__main__":
    filename = sys.argv[1]
    f = File(filename)
    f.process_all()

