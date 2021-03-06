#!/usr/bin/env python
"""
The HitInfo collects information about a hit.
The hit could come from different sources - a scanning algorithm, deserializing a hitmap, parsing a .dat file - so the information
we have in these different cases is somewhat different.
"""

import cp    
import numpy as np

from config import MARGIN

HIT_INFO_SCHEMA = {
    "type": "record",
    "name": "HitInfo",
    "fields": [{
        "name": "first_column",
        "type": "int",
    }, {
        "name": "last_column",
        "type": "int",
    }, {
        "name": "drift_rate",
        "type": "float",
    }, {
        "name": "drift_start",
        "type": "double",
    }, {
        "name": "snr",
        "type": "float",
    }, {
        "name": "mse",
        "type": "float",
    }, {
        "name": "area",
        "type": "float",
    }]
}


class HitInfo(object):
    normal_fields = ["drift_rate", "drift_start", "snr", "mse", "area"]
    
    def __init__(self, coarse_channel, coarse_channel_size, first_column, last_column, hit_windows=None, data=None):
        """
        required data:
        first_column and last_column are indexes relative to their coarse channel.
        coarse_channel is the index of the coarse channel, and coarse_channel_size is the size of each coarse channel for this file.

        optional data:
        hit_windows is a list of (row, first_column, last_column) tuples.
        data is a DataRange for the coarse channel, to which the indexes are relative.
        """
        self.coarse_channel = coarse_channel
        self.coarse_channel_size = coarse_channel_size
        self.offset = self.coarse_channel * self.coarse_channel_size
        self.first_column = first_column
        self.last_column = last_column
        self.hit_windows = hit_windows
        self.data = data
        if self.data is not None:
            assert self.data.offset == self.offset            

        # These get populated once we do a linear fit, or copy over its data from a serialized HitInfo
        self.drift_rate = None
        self.drift_start = None
        self.snr = None
        self.mse = None
        self.area = None

        
    def attach_chunk(self, chunk):
        assert self.data is None
        assert self.offset == chunk.offset
        self.data = offset

        
    @staticmethod
    def from_plain(plain, coarse_channel_size):
        """
        We need to know the coarse channel size because HitInfo objects are relative to their coarse channel, while
        hit data is stored relative to the overall file.
        """
        absolute_first_column = plain["first_column"]
        first_column = absolute_first_column % coarse_channel_size
        offset = absolute_first_column - first_column
        coarse_channel = offset // coarse_channel_size
        info = HitInfo(coarse_channel, coarse_channel_size, first_column, plain["last_column"] - offset)

        for field in HitInfo.normal_fields:
            setattr(info, field, plain[field])
        return info


    def to_plain(self):
        """
        first_column and last_column are stored without offset, so we have to convert.
        We can only convert a field to plain once linear_fit has been called.
        """
        assert self.drift_rate is not None, "HitInfo to_plain can only be called with linear fit data"
        plain = {
            "first_column": self.offset + self.first_column,
            "last_column": self.offset + self.last_column,
        }
        for field in HitInfo.normal_fields:
            plain[field] = getattr(self, field)
        return plain
        
        
    @staticmethod
    def from_hit_windows(hit_windows, coarse_channel, data):
        """
        Construct a HitInfo from a list of hit windows.
        A hit window is a (row, first_column, last_column) tuple.
        """
        first_column = min(first_column for _, first_column, _ in hit_windows)
        last_column = max(last_column for _, _, last_column in hit_windows)
        return HitInfo(coarse_channel, len(data), first_column, last_column, hit_windows=hit_windows, data=data)
    
    def plausible_next_column(self):
        """
        Guess how far after last_column we should look to find the next hit.
        Returns a single column value.
        """
        width = self.last_column - self.first_column
        return self.last_column + 2 * width + MARGIN
    
    def linear_fit(self, alpha=3.5, max_columns=1000):
        """
        Do sigma clipping to fit a Gaussian noise model to this data.
        That means we model the data's mean and standard deviation. Then remove all points more than alpha standard
        deviations above the mean.
        Repeat until this converges.
        We use the hit windows to determine which points are in the initial noise model, so we can only run linear fitting
        on hits where we have the original hit windows.
        If the data to analyze would be larger than max_columns, we don't do linear fitting and in practice we just
        conclude it's a noisy region.

        This stores extra data on the hit.
        self.fit_data stores the data we are modeling, as a *numpy* array.
        self.fit_offset stores the offset of fit_data on the coarse channel
        self.mask stores which points are modeled by noise.
        self.mean, self.std store the noise model.
        self.drift_start is the index the signal begins at, relative to the whole input file.
        self.drift_rate is the rate of drift, measured in horizontal pixels per vertical pixels.
        self.mse is the mean squared error (horizontal distance) from the fit line, measured in pixels.
        self.area is the number of pixels in the signal
        self.snr is the strength of the signal, measured in standard deviations above the mean.
        """
        assert self.hit_windows is not None
        if self.last_column - self.first_column >= max_columns:
            return
        self.fit_offset = max(self.first_column - MARGIN, 0)
        self.fit_data = cp.asnumpy(self.data.array[:, self.fit_offset : self.last_column + MARGIN + 1])
        
        # Start by masking out the strongest pixel for each hit window
        self.mask = np.full(self.fit_data.shape, True, dtype=bool)
        for row, first_column, last_column in self.hit_windows:
            begin = first_column - self.fit_offset
            end = last_column - self.fit_offset + 1
            max_index = self.fit_data[row][begin:end].argmax()
            self.mask[row][begin + max_index] = False
            
        in_bounds = self.fit_data[self.mask]

        while True:
            self.mean = in_bounds.mean().item()
            self.std = in_bounds.std().item()
            threshold = self.mean + alpha * self.std
            self.mask = np.logical_and(self.mask, self.fit_data < threshold)
            new_in_bounds = self.fit_data[self.mask]

            if new_in_bounds.size < in_bounds.size:
                # We clipped some stuff out. Keep looping
                in_bounds = new_in_bounds
                continue

            if new_in_bounds.size == in_bounds.size:
                # We have converged.
                break

            # The logical_and should prevent this
            raise ValueError(f"coding error")

        # Do a linear regression
        row_indexes, col_indexes = np.where(np.logical_not(self.mask))
        self.area = len(row_indexes)
        inputs = np.vstack([row_indexes, np.ones(len(row_indexes))]).T
        solution, residual, _, _ = np.linalg.lstsq(inputs, col_indexes, rcond=None)
        drift_rate_array, fit_start = solution
        self.drift_rate = drift_rate_array.item()
        self.drift_start = self.fit_offset + self.data.offset + fit_start.item()
        if len(residual) == 0:
            self.mse = 0
        else:
            self.mse = residual.item() / self.area

        # Calculate SNR by taking one pixel per row
        unnormalized_signal = np.amax(self.fit_data, axis=1).mean().item()
        self.snr = (unnormalized_signal - self.mean) / self.std


    def can_join(self, other, check_distance=False):
        """
        Whether self is followed by other closely enough to join them.
        This is ordered, self should come before other.
        A precondition for calling is that these two hits are in the same coarse channel.
        """
        assert self.coarse_channel == other.coarse_channel
        assert self.coarse_channel_size == other.coarse_channel_size
        assert self.offset == other.offset
        if not check_distance:
            return True
        return self.last_column + MARGIN >= other.first_column


    def join(self, other):
        """
        Join two HitInfo.
        When we join two hits, any data about their linear fit is lost, because they aren't really a linear fit any more.
        """
        assert self.can_join(other)
        info = HitInfo(self.coarse_channel, self.coarse_channel_size, self.first_column, other.last_column)
        return info

    
    def distance(self, other):
        """
        Distance from this hit to the next one.
        """
        assert self.last_column <= other.first_column
        return other.first_column - self.last_column

    def is_good(self):
        """
        Just a guess.
        """
        return self.mse <= 1 and self.area >= 3
    
    def __str__(self):
        return f"hit({self.first_column}, {self.last_column})"

    def __repr__(self):
        return str(self)


def group_hit_windows(hit_windows, coarse_channel, data):
    """
    Return a list of HitInfo objects.
    A hit window is a (row, first_column, last_column) tuple.

    When the number of empty columns between two groups is less than margin, they are combined into one hit group.
    To understand margin, the idea is that a margin of zero would combine only the hit groups with overlapping columns.

    Hit groups are also combined to keep the data small in noisy areas, so that we have a certain limit for the number of
    hit groups per coarse channel.
    """
    # sort by first_column
    sorted_hit_windows = sorted(hit_windows, key=lambda hit: hit[1])

    groups = []
    pending_group = None
    pending_last_column = None
    for hit in sorted_hit_windows:
        _, first_column, last_column = hit
        if pending_last_column is None:
            # This is the first hit. Make a pending group
            pending_group = [hit]
            pending_last_column = last_column
        elif pending_last_column + MARGIN >= first_column:
            # Combine this hit into the previous hit group
            pending_group.append(hit)
            pending_last_column = max(pending_last_column, last_column)
        else:
            # This hit goes into its own group
            groups.append(HitInfo.from_hit_windows(pending_group, coarse_channel, data))
            pending_group = [hit]
            pending_last_column = last_column

    if pending_group is not None:
        # Turn the last pending group into a full group
        groups.append(HitInfo.from_hit_windows(pending_group, coarse_channel, data))

    max_groups = 1000
    if len(groups) > max_groups:
        distances = [x.distance(y) for x, y in zip(groups, groups[1:])]
        distances.sort()
        # Distances must be over threshold to be included
        threshold = distances[-max_groups]
        new_groups = [groups[0]]
        for new_group in groups[1:]:
            if new_groups[-1].distance(new_group) <= threshold:
                new_groups[-1] = new_groups[-1].join(new_group)
            else:
                new_groups.append(new_group)
        assert len(new_groups) <= max_groups        
        groups = new_groups
        
    return groups
    
    
def diff(list1, list2):
    """
    Takes two lists of hits.
    A hit can be anything with .first_column and .last_column on it.
    list2 must be sorted.
    Returns the groups that are in list1 but do not overlap any groups in list2.
    """
    if not list2:
        return list1
    
    # We will recursively split list2
    mid_index = len(list2) // 2
    mid_hit = list2[mid_index]
    
    before_mid_hit = []
    after_mid_hit = []
    for hit in list1:
        if hit.last_column < mid_hit.first_column:
            before_mid_hit.append(hit)
        if mid_hit.last_column < hit.first_column:
            after_mid_hit.append(hit)

    return diff(before_mid_hit, list2[:mid_index]) + diff(after_mid_hit, list2[mid_index+1:])


