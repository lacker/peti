"""
The DataRange represents a part of an underlying H5 file.
"""

import cp

from config import DISPLAY_WIDTH, MARGIN

class DataRange(object):
    def __init__(self, h5_file, offset, array):
        """
        offset is the horizontal offset in the h5 file.
        """
        self.h5_file = h5_file
        self.offset = offset
        self.array = array

    def __len__(self):
        return self.array.shape[1]

    def contains_range(self, begin, end):
        """
        Whether this chunk contains the [begin, end) range of indices.
        begin and end are relative to the underlying file.
        """
        assert begin <= end
        return self.offset <= begin and end <= self.offset + len(self)
    
    def get_range(self, begin, end, strict=True):
        """
        begin and end are relative to this DataRange object.
        """
        if strict and end > len(self):
            raise ValueError(f"in get_range, end ({end}) > len(self) ({len(self)})")
        new_offset = self.offset + begin
        answer = DataRange(self.h5_file, new_offset, self.array[:, begin:end])

    def display_region(self, first, last):
        """
        A region to display, centered around the [first:last] range, inclusive.
        first and last are relative to this DataRange object.
        Always returns a numpy array, not a cupy array.
        """
        display_width = max(DISPLAY_WIDTH, last - first + 2 * MARGIN)
        center = (first + last) / 2
        ideal_display_offset = center - (display_width - 1) / 2
        display_offset = int(ideal_display_offset)
        region = self.array[:, display_offset : display_offset + display_width]
        return cp.asnumpy(region)

    def filename(self):
        return self.h5_file.filename()
