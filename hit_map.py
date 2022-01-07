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

HIT_INFO_SCHEMA = {
    "type": "record",
    "name": "HitInfo",
    "fields": [{
        "name": "first_column",
        "type": "long",
    }, {
        "name": "last_column",
        "type": "long",
    }, {
        "name": "drift_rate",
        "type": "float",
    }, {
        "name": "drift_start",
        "type": "double",
    }, {
        "name": "snr",
        "type": "float",
    }, {
        "name": "mse",
        "type": "float",
    }, {
        "name": "area",
        "type": "float",
    }]
}

HIT_MAP_SCHEMA = {
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
        "name": "foff",
        "type": "float",
    }, {
        "name": "coarse_channels",
        "type": "int",
    }, {
        "name": "hits",
        "type": {
            "type": "array",
            "items": HIT_INFO_SCHEMA,
        },
    }]
}

PARSED_SCHEMA = parse_schema(HIT_MAP_SCHEMA)


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
    """
    To construct a HitMap, use from_h5_file or from_plain, rather than the default constructor.
    
    A HitMap should have the following fields:

    h5_filename: the full path to the h5 file this hitmap is storing data for.
    hits: a list of HitInfo objects.

    Additional metadata fields track the bldw format:
    fch1
    foff
    nchans
    tstart
    tsamp
    nsamples
    coarse_channels
    """
    normal_fields = ["h5_filename", "fch1", "foff", "nchans", "tstart", "tsamp", "nsamples", "coarse_channels"]
    
    @staticmethod
    def from_h5_file(f):
        """
        Create a HitMap with no hits but the metadata from a provided h5 file.
        """
        hitmap = HitMap()
        hitmap.h5_filename = f.filename()
        hitmap.hits = []
        hitmap.fch1 = f.get_attr("fch1")
        hitmap.foff = f.get_attr("foff")
        hitmap.nchans = f.get_attr("nchans")
        hitmap.tstart = f.get_attr("tstart")
        hitmap.tsamp = f.get_attr("tsamp")
        hitmap.nsamples = f.data.shape[0]
        hitmap.coarse_channels = f.num_chunks
        return hitmap

            
    def add_hits(self, new_hits):
        """
        hits is a list of HitInfo objects.
        """
        self.hits.extend(new_hits)

    def to_plain(self):
        plain = {
            "hits": [hit.to_plain() for hit in self.hits],
        }
        for field in HitMap.normal_fields:
            plain[field] = getattr(self, field)
        return plain
        
    @staticmethod
    def from_plain(plain):
        hitmap = HitMap()
        hitmap.hits = [HitInfo.from_plain(p) for p in plain["hits"]]
        for field in HitMap.normal_fields:
            setattr(hitmap, field, plain[field])
        return hitmap

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
