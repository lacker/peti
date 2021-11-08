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

    # First we apply a subwindows, then we take the max of two of them.
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


def process_file(filename):
    assert h5py.is_hdf5(filename)
    h5file = h5py.File(filename, "r")

    data = h5file["data"]
    height, _, width = data.shape
    num_chunks = 64
    assert width % num_chunks == 0
    chunk_size = width // num_chunks
    print("chunk size:", pretty_number(chunk_size))

    total_col = 0
    total_local = 0
    total_window = 0
    
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
        local_diff = array.copy()
        local_diff -= xp.roll(array, -1, axis=1)
        local_diff -= xp.roll(array, 1, axis=1)
        local_mask = local_diff > 0
        local_pixel = local_mask.sum()
        total_local += local_pixel
        print(f"  {local_pixel} interesting pixels, according to local scan")

        # Now what?
        window_snr = calculate_window_snr(array, 1)
        window_mask = window_snr > factor
        window_pixel = window_mask.sum()
        total_window += window_pixel
        print(f"  {window_pixel} interesting pixels, according to window snr")

        assert local_pixel == window_pixel

        
    print()
    print(f"{total_col} interesting columns in total")
    print(f"{total_local} local pixels in total")
    print(f"{total_window} window pixels in total")

    
if __name__ == "__main__":
    filename = sys.argv[1]
    process_file(filename)

