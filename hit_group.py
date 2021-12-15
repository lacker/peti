#!/usr/bin/env python
"""
The "hit window" data structure is a horizontal sequence of adjacent pixels defined by a tuple:
      (row, first_column, last_column)

A hit group is a collection of hit windows.
"""


from config import MARGIN


class HitGroup(object):
    def __init__(self, hit_windows):
        """
        All indices are relative to a particular chunk.
        hit_windows is a list of hit windows.
        """
        self.hit_windows = hit_windows
        self.first_column = min(first_column for _, first_column, _ in hit_windows)
        self.last_column = max(last_column for _, _, last_column in hit_windows)

    def __str__(self):
        if len(self.hit_windows) == 1:
            row, col, _ = self.hit_windows[0]
            return f"blip({row}, {col})"

        if self.first_column != self.last_column:
            range_str = f"{self.first_column}-{self.last_column}"
        else:
            range_str = str(self.first_column)
        return f"{len(self.hit_windows)} windows @ {range_str}"

    def __repr__(self):
        return str(self)

    def __len__(self):
        return len(self.hit_windows)
    
    def is_blip(self):
        """
        A "blip" is any signal that only occurs at one point in time.
        """
        return len(self.hit_windows) == 1

    def num_columns(self):
        return self.last_column - self.first_column + 1

    def pixels(self):
        """
        Iterator of (row, column) pairs.
        """
        for row, first_column, last_column in self.hit_windows:
            for col in range(first_column, last_column + 1):
                yield row, col
    
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

    
def group_hit_windows(hit_windows):
    """
    Return a list of HitGroup objects.
    A hit window is a (row, first_column, last_column) tuple.
    When the number of empty columns between two groups is less than margin, they are combined into one hit group.
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
            groups.append(HitGroup(pending_group))
            pending_group = [hit]
            pending_last_column = last_column

    if pending_group is not None:
        # Turn the last pending group into a full group
        groups.append(HitGroup(pending_group))

    return groups
    
    
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


