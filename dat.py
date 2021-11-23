#!/usr/bin/env python
"""
Tools to analyze the .dat file format, for example turboseti output.
"""

NUM_ROWS = 16

class DatFile(object):
    def __init__(self, filename):
        # self.groups[coarse index] is a list of (first column, last column) pairs.
        self.hits = {}

        for line in open(filename):

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
            
