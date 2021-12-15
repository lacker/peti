#!/usr/bin/env python
"""
Tools to analyze the .dat file format, for example turboseti output.
"""

import os
import random
import re
import time

from config import H5_ROOT, MARGIN
from hit_group import group_hit_windows

DIR = os.path.dirname(os.path.realpath(__file__))

DAT_LIST = os.path.join(DIR, "dats.txt")


class DatHit(object):
    """
    Information for a hit that is read from the dat file.
    """
    def __init__(self, first_column, last_column):
        self.first_column = first_column
        self.last_column = last_column


class DatFile(object):
    """
    self.hits maps coarse index to a list of (first column, last column) pairs.
    """
    def __init__(self, filename):
        self.filename = filename

        # self.groups[coarse index] is a list of fine indices.
        self.hits = {}

        header = {}

        for line in open(self.filename):

            if line.startswith("#"):
                parts = line.split()
                pairs = zip(parts, parts[1:])
                for key_colon, value in pairs:
                    if not key_colon.endswith(":"):
                        continue
                    key = key_colon.strip(":")
                    header[key] = value
                continue

            # Calculate how much drift rate you need to drift one pixel
            deltaf = float(header["DELTAF(Hz)"])
            obs_length = float(header["obs_length"])
            drift_rate_per_pixel = deltaf / obs_length
            
            parts = line.split()
            if len(parts) != 12:
                raise ValueError("unexpected dat file format")
            drift_rate = float(parts[1])
            start_fine_index = int(parts[5])
            coarse_index = int(parts[10])

            # Calculate how many pixels this signal drifted by
            # Can be positive or negative
            float_drift_pixels = drift_rate / drift_rate_per_pixel
            drift_pixels = round(float_drift_pixels)
            assert abs(float_drift_pixels - drift_pixels) < 0.01
            end_fine_index = start_fine_index + drift_pixels

            first_column, last_column = sorted([start_fine_index, end_fine_index])
            
            if coarse_index not in self.hits:
                self.hits[coarse_index] = []
            self.hits[coarse_index].append(DatHit(first_column, last_column))

            
    def h5_filename(self):
        """
        The filename of the h5 file corresponding to this dat file.
        This relies on the name being parallel and existing in a parallel directory structure.
        """
        parts = self.filename.split("/")
        session_looking_pairs = [pair for pair in zip(parts, parts[1:]) if re.match(".GBT", pair[0])]
        assert len(session_looking_pairs) == 1
        session, machine_name = session_looking_pairs[0]
        base = parts[-1]
        assert base.endswith(".dat")
        return os.path.join(H5_ROOT, session, machine_name, base[:-4] + ".h5")
    

    def has_hits(self):
        return len(self.hits) > 0

    
    def coarse_list(self):
        """
        Returns a list of which coarse channels have hits.
        """
        return list(self.hits.keys())


    @staticmethod
    def random():
        """
        Fetch a dat file chosen randomly from DAT_LIST.
        """
        choices = []
        for line in open(DAT_LIST):
            s = line.strip()
            if s.endswith(".dat"):
                choices.append(s)
        filename = random.choice(choices)
        return DatFile(filename)


    def get_hits(self, coarse_index):
        """
        Returns a list of DatHit objects for the given coarse index.
        Combines hits within MARGIN.
        """
        assert self.has_hits()
        answer = []
        for hit in self.hits[coarse_index]:
            if answer and answer[-1].last_column + MARGIN >= hit.first_column:
                answer[-1] = DatHit(answer[-1].first_column, hit.last_column)
            else:
                answer.append(hit)
        return answer

