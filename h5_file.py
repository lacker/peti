"""
Utility functions for opening and doing things with h5 files
"""

# These two dependencies must be imported in this order
import logging
logging.getLogger("hdf5plugin").setLevel(logging.ERROR)
import hdf5plugin
import h5py

from astropy.time import Time
import cp
import os
import random

from data_range import DataRange

# This directory
DIR = os.path.dirname(os.path.realpath(__file__))


class H5File(object):
    def __init__(self, filename):
        assert h5py.is_hdf5(filename), f"{filename} does not appear to be an hdf5 file"
        self.h5file = h5py.File(filename, "r")
        self.data = self.h5file["data"]
        self.height, _, self.width = self.data.shape
        if self.width == 64 * 1048576:
            self.num_chunks = 64
        elif self.width == 1048576:
            self.num_chunks = 1
        elif self.width == 50331648:
            # ATA
            self.num_chunks = 192
        else:
            raise ValueError(f"unexpected data dimensions: {self.height} x {self.width}")
        assert self.width % self.num_chunks == 0
        self.chunk_size = self.width // self.num_chunks

    def get_attr(self, attr_name):
        attr = self.data.attrs[attr_name]
        if type(attr) is str:
            return attr
        return attr.item()
        
    def get_chunk(self, i):
        assert 0 <= i < self.num_chunks
        offset = i * self.chunk_size
        array = cp.array(self.data[:, 0, offset : offset + self.chunk_size])

        # Blur out the exact middle, that's the DC spike
        midpoint = self.chunk_size // 2
        array[:, midpoint] = (array[:, midpoint - 1] + array[:, midpoint + 1]) / 2

        return DataRange(self, offset, array.view())

    def get_range(self, begin, end):
        i = begin // self.chunk_size
        chunk = self.get_chunk(i)
        return chunk.get_range(begin - chunk.offset, end - chunk.offset)
 
    def filename(self):
        return self.h5file.filename

    def timestamp(self):
        return Time(self.get_attr("tstart"), format="mjd").unix

    def source_name(self):
        data = self.get_attr("source_name")
        if type(data) is bytes:
            return data.decode("utf-8")
        assert type(data) is str
        return data
    
    
class ChunkFetcher(object):
    def __init__(self, seed=None):
        if seed is None:
            digits = 6
            self.seed = random.randint(10 ** (digits - 1), 10 ** digits)
        else:
            self.seed = seed
        print("seed:", self.seed)
        self.rng = random.Random(self.seed)

        # Get a list of possible files to open
        lines = [line.strip() for line in open(os.path.join(DIR, "input.txt"))]
        self.filenames = [line for line in lines if line.endswith("h5")]

    def fetch(self):
        """
        Returns a (filename, chunk number, chunk) tuple.
        """
        filename = self.rng.choice(self.filenames)
        f = H5File(filename)
        i = self.rng.randrange(f.num_chunks)
        chunk = f.get_chunk(i)
        return (filename, i, chunk)

    def find(self, predicate):
        """
        Returns a (predicate(chunk), filename, chunk number, chunk) tuple where predicate(chunk) is truthy.
        """
        while True:
            filename, i, chunk = self.fetch()
            print(f"checking chunk {i} of {filename} ...")
            answer = predicate(chunk)
            if answer:
                return (answer, filename, i, chunk)


    
