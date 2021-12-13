#!/usr/bin/env python
"""
The "hit" data structure is a horizontal sequence of adjacent pixels defined by a tuple:
      (row, first_column, last_column)
"""

# Standard image width to display
WIDTH = 60

# Standard amount below which to combine hit groups
MARGIN = 10

class HitGroup(object):
    def __init__(self, hits):
        """
        All indices are relative to a particular coarse channel, aka "chunk".
        hits is a list of hits.
        """
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

    def __len__(self):
        return len(self.hits)
    
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
        Finds an offset so that chunk[:, offset : offset + width] has this hit group centered.
        """
        center = (self.first_column + self.last_column) / 2
        ideal_offset = center - (width - 1) / 2
        return int(ideal_offset)
 
    def region(self, chunk):
        """
        A normalized region around this hit.
        """
        width = WIDTH
        offset = self.find_offset(width)
        region = chunk[:, offset:offset+width]
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

    
def group_hits(hits):
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


