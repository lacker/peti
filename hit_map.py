#!/usr/bin/env python
"""
The .hitmap file format stores the hits found in a single h5 file, along with some other metadata.
It's JSON, so it should be extensible.
"""

import json
import os

from config import H5_ROOT

HIT_MAP_ROOT = os.path.expanduser("~/hitmaps")


def front_replace(s, old, new):
    """
    Return a copy of s with old replace with new in precisely one place, the front.
    s must start with old.
    """
    assert s.startswith(old)
    return s.replace(old, new, 1)


class HitMap(object):
    def __init__(self, h5_filename, coarse_channels, hits=None):
        """
        h5_filename is the full path to the h5 file this hitmap is storing data for.
        coarse_channels is the total number of coarse channels in this file.
        hits maps coarse index to a sorted list of (first column, last column) pairs for all coarse indices with hits.
        If hits is not provided, this makes an empty HitMap.
        """
        self.h5_filename = h5_filename
        self.coarse_channels = coarse_channels
        if hits is None:
            self.hits = {}
        else:
            self.hits = hits

    def add_groups(self, coarse_index, groups):
        """
        groups is a list of HitGroups
        """
        if coarse_index in self.hits:
            raise ValueError("you can only call add_groups once per coarse channel")
        self.hits[coarse_index] = [(g.first_column, g.last_column) for g in groups]

    def to_plain(self):
        """
        Converts the hitmap to "plain object" format, with just nested dicts, strings, lists, numbers.
        """
        return {
            "coarse_channels": self.coarse_channels,
            "h5_filename": self.h5_filename,
            "hits": self.hits,
        }

    @staticmethod
    def from_plain(plain):
        return HitMap(plain["h5_filename"], plain["coarse_channels"], hits=plain["hits"])

    def save(self):
        hit_map_filename = front_replace(self.h5_filename, H5_ROOT, HIT_MAP_ROOT)
        with open(hit_map_filename, "w") as outfile:
            # Should be deterministic because we use sort_keys
            json.dump(self.to_plain(), outfile, indent=2, sort_keys=True)

    @staticmethod
    def load(filename):
        with open(filename) as infile:
            plain = json.load(infile)
        h5_filename = plain["h5_filename"]
        assert h5_filename == front_replace(filename, HIT_MAP_ROOT, H5_ROOT)
        return HitMap(h5_filename, plain["coarse_channels"], hits=plain["hits"])

    def num_hits():
        """
        How many hits we have across all coarse channels.
        """
        return sum(len(value) for value in self.hits.values())
