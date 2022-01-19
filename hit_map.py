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
from h5_file import H5File
from hit_info import HitInfo

HIT_MAP_ROOT = os.path.expanduser("~/hitmaps")

HIT_INFO_SCHEMA = {
    "type": "record",
    "name": "HitInfo",
    "fields": [{
        "name": "first_column",
        "type": "int",
    }, {
        "name": "last_column",
        "type": "int",
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
        "name": "nchans",
        "type": "int",
    }, {
        "name": "tstart",
        "type": "float",
    }, {
        "name": "tsamp",
        "type": "float",
    }, {
        "name": "nsamples",
        "type": "int",
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

            
    def add_hits(self, new_hits, strip_data_reference=False):
        """
        hits is a list of HitInfo objects.
        """
        if strip_data_reference:
            for h in new_hits:
                h.data = None
        self.hits.extend(new_hits)

    def chunk_size(self):
        return self.nchans / self.coarse_channels
        
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
        """
        Loads an existing hitmap.
        Can take either the h5 filename or the hitmap filename.
        """
        if filename.endswith("h5"):
            filename = make_hit_map_filename(filename)
        with open(filename, "rb") as infile:
            records = list(reader(infile))
            assert len(records) == 1
            return HitMap.from_plain(records[0])


    def populate_h5_file(self):
        if not hasattr(self, "h5_file"):
            self.h5_file = H5File(self.h5_filename)

        
    def chunks(self):
        self.populate_h5_file()
        return sorted(list(set(hit.first_column // self.h5_file.chunk_size for hit in self.hits)))

    def get_chunk(self, i):
        self.populate_h5_file()
        return self.h5_file.get_chunk(i)

    def frequency_for_absolute_index(self, i):
        return self.fch1 + self.foff * i
        
    
    def hits_for_chunk(self, chunk_index, attach_chunk=True):
        """
        Returns the hits for the chunk with the given number.
        Attaches the chunk to the hits if it is not attached already.
        """
        self.populate_h5_file()

        # Find the hits that are in this chunk
        chunk_begin = self.h5_file.chunk_size * chunk_index
        chunk_end = chunk_begin + self.h5_file.chunk_size
        hits = [h for h in self.hits if chunk_begin <= h.first_column and h.last_column < chunk_end]
        if not attach_chunk or all(hit.data for hit in hits):
            return hits

        chunk = self.h5_file.get_chunk(chunk_index)
        for hit in hits:
            hit.attach_chunk(chunk)
        return hits

    
    def __repr__(self):
        plain = self.to_plain()
        return json.dumps(plain, indent=2)
        

if __name__ == "__main__":
    fname = sys.argv[1]
    assert fname.endswith(".hitmap")
    hitmap = HitMap.load(fname)
    print(hitmap)
