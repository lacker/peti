#!/usr/bin/env python
"""
Tools to analyze the .dat file format, for example turboseti output.
"""

import os
import random
import re
import time

DIR = os.path.dirname(os.path.realpath(__file__))

DAT_LIST = os.path.join(DIR, "dats.txt")
H5_ROOT = "/datag/pipeline"


class DatFile(object):
    def __init__(self, filename):
        self.filename = filename

        # self.groups[coarse index] is a list of fine indices.
        self.hits = {}

        for line in open(self.filename):

            if line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) != 12:
                raise ValueError("unexpected dat file format")
            # drift_rate = float(parts[1])
            fine_index = int(parts[5])
            coarse_index = int(parts[10])

            if coarse_index not in self.hits:
                self.hits[coarse_index] = []
            self.hits[coarse_index].append(fine_index)

            
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

    
    def random_hits(self):
        """
        Returns (coarse index, list of fine indexes), chosen randomly from the coarse channels with hits.
        Raises an exception if there are no hits.
        """
        assert self.has_hits()
        return random.choice(list(self.hits.items()))


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
