#!/usr/bin/env python
"""
The .hitmap file format stores the hits found in a single h5 file, along with some other metadata.
This uses fastavro to serialize with the avro format.
It is not human-readable like dat files but the size of the hit files does become an issue sometimes, and it's
convenient to have an extensible, schema-defined format as well.
"""

import json
import os
from pathlib import Path
import sys

from fastavro import parse_schema, reader, writer

from config import H5_ROOT

HIT_MAP_ROOT = os.path.expanduser("~/hitmaps")

SCHEMA = {
    "namespace": "peti",
    "type": "record",
    "name": "HitMap",
    "fields": [{
        "name": "h5_filename",
        "type": "string",
    }, {
        "name": "fch1",
        "type": "float",
    }, {
        "name": "coarse_channels",
        "type": "int",
    }]
}

PARSED_SCHEMA = parse_schema(SCHEMA)


def front_replace(s, old, new):
    """
    Return a copy of s with old replace with new in precisely one place, the front.
    s must start with old.
    """
    assert s.startswith(old)
    return s.replace(old, new, 1)


def make_hit_map_filename(h5_filename):
    """
    The hitmap filename corresponding to an h5 filename
    """
    assert h5_filename.endswith(".h5")
    return front_replace(h5_filename, H5_ROOT, HIT_MAP_ROOT)[:-3] + ".hitmap"



class HitMap(object):
    def __init__(self, h5_filename, fch1, coarse_channels, hits=None):
        """
        h5_filename is the full path to the h5 file this hitmap is storing data for.
        coarse_channels is the total number of coarse channels in this file.
        hits is an optional list of HitInfo objects.
        If hits is not provided, this makes an empty HitMap.
        """
        self.h5_filename = h5_filename
        self.fch1 = fch1
        self.coarse_channels = coarse_channels
        if hits is None:
            self.hits = []
        else:
            self.hits = hits

    @staticmethod
    def from_h5_file(f):
        """
        Create a HitMap with no hits but the metadata from a provided h5 file.
        """
        return HitMap(f.filename(), f.get_attr("fch1"), f.num_chunks)
            
    def add_hits(self, new_hits):
        """
        hits is a list of HitInfo objects.
        """
        self.hits.extend(new_hits)

    def to_plain(self):
        return {
            "h5_filename": self.h5_filename,
            "fch1": self.fch1,
            "coarse_channels": self.coarse_channels,
        }
        
    @staticmethod
    def from_plain(plain):
        return HitMap(plain["h5_filename"], plain["fch1"], plain["coarse_channels"])

    def save(self):
        """
        Returns the filename we saved to.
        """
        hit_map_filename = make_hit_map_filename(self.h5_filename)
        dirname = os.path.dirname(hit_map_filename)
        Path(dirname).mkdir(parents=True, exist_ok=True)

        plain = self.to_plain()
        with open(hit_map_filename, "wb") as outfile:
            writer(outfile, PARSED_SCHEMA, [plain])

        return hit_map_filename

    @staticmethod
    def load(filename):
        with open(filename, "rb") as infile:
            records = list(reader(infile))
            assert len(records) == 1
            return HitMap.from_plain(records[0])

    def __repr__(self):
        plain = self.to_plain()
        return json.dumps(plain, indent=2)
        

if __name__ == "__main__":
    fname = sys.argv[1]
    assert fname.endswith(".hitmap")
    hitmap = HitMap.load(fname)
    print(hitmap)
