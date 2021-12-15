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


