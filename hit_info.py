#!/usr/bin/env python
"""
The HitInfo collects information about a hit.
The hit could come from different sources - a scanning algorithm, deserializing a hitmap, parsing a .dat file - so the information
we have in these different cases is somewhat different.
"""

import cupy as cp
from config import MARGIN


class HitInfo(object):
    def __init__(self, first_column, last_column, hit_windows=None, data=None, offset=None):
        """
        first_column and last_column are relative indexes. They are the only mandatory elements of a hit.
        After the HitInfo is constructed, self.offset will describe what these column indexes are relative to.
        hit_windows is a list of (row, first_column, last_column) tuples.
        data is a DataRange for the coarse channel, to which the indexes are relative.
        offset is the amount the indexes are offset, if we don't have data.
        """
        self.first_column = first_column
        self.last_column = last_column
        self.hit_windows = hit_windows

        if data is not None and offset is not None:
            raise RuntimeError("you cannot provide both data and offset to HitInfo")

        self.data = data
        if self.data is None:
            assert offset is not None
            self.offset = offset
        else:
            self.offset = self.data.offset


    def attach_chunk(self, chunk):
        assert self.data is None
        assert self.offset == 0
        if not chunk.contains_range(self.first_column, self.last_column + 1):
            raise RuntimeError(f"{chunk.offset=} {len(chunk)=} {self.first_column=} {self.last_column=}")
        assert self.hit_windows is None
        self.data = chunk
        self.offset = chunk.offset
        self.first_column -= self.offset
        self.last_column -= self.offset

        
    @staticmethod
    def from_plain(plain):
        info = HitInfo(plain["first_column"], plain["last_column"], offset=0)
        for field in ["drift_rate", "drift_start", "snr", "mse", "area"]:
            setattr(info, field, plain[field])
        return info


    def to_plain(self):
        """
        Plain conversion is straightforward, except that first_column and last_column are stored without
        any offset, so we have to convert.
        """
        plain = {
            "first_column": self.offset + self.first_column,
            "last_column": self.offset + self.last_column,
        }
        for field in ["drift_rate", "drift_start", "snr", "mse", "area"]:
            if hasattr(self, field):
                plain[field] = getattr(self, field)
        return plain
        
        
    @staticmethod
    def from_hit_windows(hit_windows, data):
        """
        Construct a HitInfo from a list of hit windows.
        A hit window is a (row, first_column, last_column) tuple.
        """
        first_column = min(first_column for _, first_column, _ in hit_windows)
        last_column = max(last_column for _, _, last_column in hit_windows)
        return HitInfo(first_column, last_column, hit_windows=hit_windows, data=data)
    

    def linear_fit(self, alpha=3.5):
        """
        Do sigma clipping to fit a Gaussian noise model to this data.
        That means we model the data's mean and standard deviation. Then remove all points more than alpha standard
        deviations above the mean.
        Repeat until this converges.
        We use the hit windows to determine which points are in the initial noise model, so we can only run linear fitting
        on hits where we have the original hit windows.

        This stores extra data on the hit.
        self.fit_data stores the data we are modeling, as a cupy array.
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
        self.fit_offset = max(self.first_column - MARGIN, 0)
        self.fit_data = self.data.array[:, self.fit_offset : self.last_column + MARGIN + 1]
        
        # Start by masking out the strongest pixel for each hit window
        self.mask = cp.full(self.fit_data.shape, True, dtype=bool)
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
            self.mask = cp.logical_and(self.mask, self.fit_data < threshold)
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
        row_indexes, col_indexes = cp.where(cp.logical_not(self.mask))
        self.area = len(row_indexes)
        inputs = cp.vstack([row_indexes, cp.ones(len(row_indexes))]).T
        solution, residual, _, _ = cp.linalg.lstsq(inputs, col_indexes, rcond=None)
        self.drift_rate, fit_start = solution
        self.drift_start = self.fit_offset + self.data.offset + fit_start.item()
        if len(residual) == 0:
            self.mse = 0
        else:
            self.mse = residual.item() / self.area

        # Calculate SNR by taking one pixel per row
        unnormalized_signal = cp.amax(self.fit_data, axis=1).mean().item()
        self.snr = (unnormalized_signal - self.mean) / self.std


    def can_join(self, other):
        """
        Whether self is followed by other closely enough to join them.
        This is ordered, self should come before other.
        A precondition for calling is that these two hits are in the same coarse channel.
        """
        assert self.offset == other.offset
        return self.last_column + MARGIN >= other.first_column


    def join(self, other):
        """
        Join two HitInfo for which can_join is true.
        """
        assert self.can_join(other)
        return HitInfo(self.first_column, other.last_column, offset=self.offset)
    
    
    def __str__(self):
        return f"hit({self.first_column}, {self.last_column})"

    def __repr__(self):
        return str(self)


def group_hit_windows(hit_windows, data):
    """
    Return a list of HitInfo objects.
    A hit window is a (row, first_column, last_column) tuple.
    When the number of empty columns between two groups is less than margin, they are combined into one hit group.
    We drop any group with less than three windows.
    A margin of zero will combine only the hit groups with overlapping columns.
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
            groups.append(HitInfo.from_hit_windows(pending_group, data))
            pending_group = [hit]
            pending_last_column = last_column

    if pending_group is not None:
        # Turn the last pending group into a full group
        groups.append(HitInfo.from_hit_windows(pending_group, data))

    return [group for group in groups if len(group.hit_windows) > 2]
    
    
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


