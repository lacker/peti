#!/usr/bin/env python
"""
Tools to analyze the .dat file format, for example turboseti output.
"""

import os
import random
import time

DIR = os.path.dirname(os.path.realpath(__file__))

DAT_LIST = os.path.join(DIR, "dats.txt")
H5_ROOT = "/datag/pipeline"

NUM_ROWS = 16


class DatFile(object):
    def __init__(self, filename):
        self.filename = filename

        # self.groups[coarse index] is a list of (first column, last column) pairs.
        self.hits = {}

        for line in open(self.filename):

            if line.startswith("#"):
                if "DELTAT" in line:
                    parts = line.strip().split()
                    a, b, deltat, c, deltaf = parts[:5]
                    assert a == "#"
                    assert b == "DELTAT:"
                    assert c == "DELTAF(Hz):"
                    self.drift_per_pixel = deltat / deltaf / NUM_ROWS
                continue

            parts = line.split()
            if len(parts) != 12:
                raise ValueError("unexpected dat file format")
            drift_rate = parts[1]
            top_fine_index = parts[5]
            coarse_index = parts[10]

            delta_pixels = drift_rate / self.drift_per_pixel
            int_delta_pixels = round(delta_pixels)
            assert abs(delta_pixels - int_delta_pixels) < 0.1
            
            bottom_fine_index = top_find_index + int_delta_pixels
            first_column, last_column = sorted((top_fine_index, bottom_fine_index))
            if coarse_index not in self.hits:
                self.hits[coarse_index] = []
            self.hits[coarse_index].append((first_column, last_column))

            
    def h5_filename(self):
        """
        The filename of the h5 file corresponding to this dat file.
        This relies on the name being parallel and existing in a parallel directory structure.
        """
        parts = self.filename.split("/")
        session_looking_pairs = [pair for pair in zip(parts, parts[1:]) if re.match(".GBT", pair[0])]
        assert len(session_looking_pairs) == 1
        session, machine_name = session_looking_parts[0]
        base = parts[-1]
        assert base.endswith(".dat")
        return os.path.join(H5_ROOT, session, machine_name, base[-4:] + ".h5")
    

    def has_hits(self):
        return len(self.hits) > 0

    
    def random_coarse_index(self):
        """
        Return a random coarse index from among all the coarse indices that have hits.
        Raises an exception if there are no hits.
        """
        assert self.has_hits()
        return random.choice(self.hits.keys())


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
        return random.choice(choices)
