#!/usr/bin/env python
"""
Information for an event candidate.
"""

from config import MARGIN
from scanner import Scanner

class Event(object):
    def __init__(self, hits, chunk_index, hit_maps=None):
        """
        Since an event may correspond to no hit at all in a particular input, the hits list can have a None.
        It can't be all None though.
        If hitmaps are provided, they must be parallel to hits. There must be a hitmap for each entry even
        if the corresponding hit is None.
        There cannot be multiple hits per chunk.
        """
        self.hits = hits
        self.chunk_index = chunk_index
        self.hit_maps = hit_maps

        # Chunks will be lazily populated
        self.chunks = None

    def first_column(self):
        return min(h.first_column for h in self.hits if h)

    def last_column(self):
        return max(h.last_column for h in self.hits if h)

    def frequency_range(self):
        """
        Returns (first_freq, last_freq) that corresponds to the first and last column.
        """
        first_col = self.first_column()
        last_col = self.last_column()
        for hit_map in self.hit_maps:
            if hit_map is None:
                continue
            first_index = self.chunk_index * hit_map.chunk_size() + self.first_column()
            last_index = self.chunk_index * hit_map.chunk_size() + self.last_column()
            first_freq = hit_map.fch1 + first_index * hit_map.foff
            last_freq = hit_map.fch1 + last_index * hit_map.foff
            return (first_freq, last_freq)
            
        raise RuntimeError("all hit maps are None")
    
    def populate_chunks(self):
        if self.chunks:
            return
        assert self.hit_maps
        self.chunks = [hit_map.get_chunk(self.chunk_index) for hit_map in self.hit_maps]
    
    @staticmethod
    def find_events(hit_maps, chunk_index=None):
        """
        Generate events from a list of hit maps.
        An event is currently defined as any two hits within MARGIN of each other.
        """
        if chunk_index is None:
            for chunk_index in range(hit_maps[0].coarse_channels):
                for event in Event.find_events(hit_maps, chunk_index=chunk_index):
                    yield event
            return

        # Entries in labeled_hits are
        # (hit_map_index, hit)
        # where the hit_map_index tracks which hit map the hit came from.
        labeled_hits = []
        for hit_map_index, hit_map in enumerate(hit_maps):
            hits = hit_map.hits_for_chunk(chunk_index, attach_chunk=False)
            for hit in hits:
                labeled_hits.append((hit_map_index, hit))

        labeled_hits.sort(key=lambda x: x[1].first_column)

        # Group up the labeled hits
        groups = []
        current_group = []
        furthest_column = None
        for index, hit in labeled_hits:
            if not current_group:
                # Make a new group with only this hit
                current_group.append((index, hit))
                furthest_column = hit.last_column
                continue
            if furthest_column + MARGIN >= hit.first_column:
                # Add this hit to the group
                current_group.append((index, hit))
                furthest_column = max(furthest_column, hit.last_column)
                continue
            # Make current group into a group and start a new group with this hit
            groups.append(current_group)
            current_group = [(index, hit)]
            furthest_column = hit.last_column
        if current_group:
            groups.append(current_group)

        # Filter out groups with only one hit
        groups = [g for g in groups if len(g) > 1]
        if not groups:
            return

        # Construct events for this coarse channel
        for group in groups:
            hits = [None] * len(hit_maps)
            for (index, hit) in group:
                hits[index] = hit

            yield Event(hits, chunk_index, hit_maps=hit_maps)

    @staticmethod
    def scan_cadence(filenames):
        """
        Generates events
        """
        scanners = [Scanner(f) for f in filenames]
        hitmaps = [s.hitmap for s in scanners]
        for i in range(scanners[0].num_chunks()):
            for scanner in scanners:
                scanner.scan_chunk(i)
            for event in Event.find_events(hitmaps, chunk_index=i):
                yield event
