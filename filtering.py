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


# Standard image width to display
WIDTH = 60

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
    

def calculate_pixel_snr(array, window_size):
    """
    pixel snr is the signal of a particular pixel, compared to the "noise" as defined by
    a window either to the left or the right of the pixel.
    window_size is the size of the window to use for noise.
    array is 2d, where the second dimension is the one we are windowing along.
    snr is the number of standard deviations from the mean it would be, using the noise population
    to define mean and standard deviation.
    The snr of a pixel is the higher of its left and right snr.
    """
    window_means, window_devs = calculate_window_stats(array, window_size)

    # left_snr is the snr calculated with noise using a window to the left
    left_snr = xp.zeros_like(array)
    left_snr[:, window_size:] = (array[:, window_size:] - window_means[:, :-1]) / window_devs[:, :-1]

    # right_snr is the snr calculated with noise using a window to the right
    right_snr = xp.zeros_like(array)
    right_snr[:, :-window_size] = (array[:, :-window_size] - window_means[:, 1:]) / window_devs[:, 1:]

    output = xp.maximum(left_snr, right_snr)
    return output


def calculate_two_pixel_snr(array, window_size):
    """
    two-pixel snr is like pixel snr, except we calculate the signal as the average over two consecutive pixels.
    """
    window_means, window_devs = calculate_window_stats(array, window_size)

    # First, in spot i we calculate signal for the pixel pair indexed with (i, i+1).
    # signal is thus one column shorter than array.
    signal = (array[:, :-1] + array[:, 1:]) / 2

    # left_snr is the snr for the pixel pair indexed with (i, i+1) calculated with a noise window to the left.
    # thus the first window_size columns, and the last column, are zeros.
    left_snr = xp.zeros_like(array)
    left_snr[:, window_size:-1] = (signal[:, window_size:] - window_means[:, :-2]) / window_devs[:, :-2]

    # right_snr is the snr for the pixel pair indexed with (i, i+1) calculated with a noise window to the right.
    # thus the last (window_size+1) columns are zeros.
    right_snr = xp.zeros_like(array)
    right_snr[:, :-(window_size+1)] = (signal[:, :-window_size] - window_means[:, 2:]) / window_devs[:, 2:]

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

        # Blur out the exact middle, that's the DC spike
        midpoint = self.chunk_size // 2
        array[:, midpoint] = (array[:, midpoint - 1] + array[:, midpoint + 1]) / 2

        return array.view()

    def find_groups(self, chunk, new=False):
        pixel_snr = calculate_pixel_snr(chunk, 30)
        mask = pixel_snr > 6

        if new:
            window_snr = calculate_two_pixel_snr(chunk, 30)
            mask |= window_snr > 4

        hits = find_hits(mask)            
        groups = group_hits(chunk, hits, 10)
        return [g for g in groups if not g.is_blip()]
        
    def process_all(self):
        total = 0
        for i in range(self.num_chunks):
            chunk = self.get_chunk(i)
            groups = self.find_groups(chunk)
            print(f"chunk {i} has {len(groups)} groups:")
            print(" ", groups)
            total += len(groups)
        print(f"{total} hit groups total")


def group_hits(data, hits, margin):
    """
    Return a list of HitGroup objects.
    A hit is a (row, first_column, last_column) tuple.
    When the number of empty columns between two groups is less than margin, they are combined into one hit group.
    A margin of zero will combine only the hit groups with overlapping columns.
    """
    # sort by first_column
    sorted_hits = sorted(hits, key=lambda hit: hit[1])

    groups = []
    pending_group = None
    pending_last_column = None
    for hit in sorted_hits:
        _, first_column, last_column = hit
        if pending_last_column is None:
            # This is the first hit. Make a pending group
            pending_group = [hit]
            pending_last_column = last_column
        elif pending_last_column + margin >= first_column:
            # Combine this hit into the previous hit group
            pending_group.append(hit)
            pending_last_column = max(pending_last_column, last_column)
        else:
            # This hit goes into its own group
            groups.append(HitGroup(data, pending_group))
            pending_group = [hit]
            pending_last_column = last_column

    if pending_group is not None:
        # Turn the last pending group into a full group
        groups.append(HitGroup(data, pending_group))

    return groups


class HitGroup(object):
    def __init__(self, data, hits):
        """
        data is a slice of the h5 file. indexes are relative to data.
        hits is a list of hits.
        """
        self.data = data
        self.hits = hits
        self.first_column = min(first_column for _, first_column, _ in hits)
        self.last_column = max(last_column for _, _, last_column in hits)

    def __str__(self):
        if len(self.hits) == 1:
            row, col, _ = self.hits[0]
            return f"blip({row}, {col})"

        if self.first_column != self.last_column:
            range_str = f"{self.first_column}-{self.last_column}"
        else:
            range_str = str(self.first_column)
        return f"{len(self.hits)} hits @ {range_str}"

    def __repr__(self):
        return str(self)

    def is_blip(self):
        """
        A "blip" is any signal that only occurs at one point in time.
        """
        return len(self.hits) == 1

    def num_columns(self):
        return self.last_column - self.first_column + 1

    def is_big(self):
        return self.num_columns() > WIDTH
    
    def find_offset(self, width):
        """
        Finds an offset so that self.data[:, offset : offset + width] has this hit group centered.
        """
        center = (self.first_column + self.last_column) / 2
        ideal_offset = center - (width - 1) / 2
        return int(ideal_offset)
 
    def region(self):
        """
        A normalized region around this hit.
        """
        width = WIDTH
        offset = self.find_offset(width)
        region = self.data[:, offset:offset+width]
        rmin = region.min()
        rmax = region.max()
        normal = (region - rmin) / (rmax - rmin)
        return normal

    def __lt__(self, other):
        return self.last_column < other.first_column

    def overlaps(self, other):
        if self < other:
            return False
        if other < self:
            return False
        return True

    def overlaps_list(self, other_list):
        for other in other_list:
            if self.overlaps(other):
                return True
        return False

    
def diff(list1, list2):
    """
    Takes two lists of hit groups.
    list2 must be sorted.
    Returns the groups that are in list1 but do not overlap any groups in list2.
    """
    if not list2:
        return list1
    
    # We will recursively split list2
    mid_index = len(list2) // 2
    mid_group = list2[mid_index]
    
    before_mid_group = []
    after_mid_group = []
    for group in list1:
        if group < mid_group:
            before_mid_group.append(group)
        if mid_group < group:
            after_mid_group.append(group)

    return diff(before_mid_group, list2[:mid_index]) + diff(after_mid_group, list2[mid_index+1:])


if __name__ == "__main__":
    filename = sys.argv[1]
    f = File(filename)
    f.process_all()

