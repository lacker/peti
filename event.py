#!/usr/bin/env python
"""
Information for an event candidate.
"""

from config import MARGIN
from scanner import Scanner


class Event(object):
    def __init__(self, hits, coarse_channel, hit_maps=None):
        """
        Since an event may correspond to no hit at all in a particular input, the hits list can have a None.
        It can't be all None though.
        If hit_maps is provided, it must be parallel to hits.
        So there must be a hitmap for each entry even if the corresponding hit is None.
        There cannot be multiple hits per file in a single event.
        """
        self.hits = hits
        self.coarse_channel = coarse_channel
        self.hit_maps = hit_maps
        
        # Populate metadata from the hitmaps
        if hit_maps is not None:
            self.h5_filenames = [hit_map.h5_filename for hit_map in hit_maps]
            self.fch1 = hit_maps[0].fch1
            self.foff = hit_maps[0].foff
            self.nchans = hit_maps[0].nchans
            self.coarse_channels = hit_maps[0].coarse_channels
        
        # Lazily populated
        self.chunks = None

    def first_column(self):
        return min(h.first_column for h in self.hits if h)

    def last_column(self):
        return max(h.last_column for h in self.hits if h)

    def image_filename(self):
        return make_png_filename(self.h5_filenames[0])
    
    def frequency_range(self):
        """
        Returns (first_freq, last_freq) that corresponds to the first and last column.
        """
        coarse_channel_size = self.nchans // self.coarse_channels
        
        first_index = self.coarse_channel * coarse_channel_size + self.first_column()
        last_index = self.coarse_channel * coarse_channel_size + self.last_column()
        first_freq = self.fch1 + first_index * self.foff
        last_freq = self.fch1 + last_index * self.foff
        return (first_freq, last_freq)
    
    def populate_chunks(self):
        if self.chunks:
            return
        assert self.hit_maps, "Populating chunks requires the hit maps."
        self.chunks = []
        for hit, hit_map in zip(self.hits, self.hit_maps):
            chunk = hit_map.get_chunk(self.coarse_channel)
            self.chunks.append(chunk)

            
    @staticmethod
    def find_events(hit_maps, coarse_channel=None):
        """
        Generate events from a list of hit maps.
        An event is currently defined as any two hits within MARGIN of each other.
        """
        if coarse_channel is None:
            for coarse_channel in range(hit_maps[0].coarse_channels):
                for event in Event.find_events(hit_maps, coarse_channel=coarse_channel):
                    yield event
            return

        # Entries in labeled_hits are
        # (hit_map_index, hit)
        # where the hit_map_index tracks which hit map the hit came from.
        labeled_hits = []
        for hit_map_index, hit_map in enumerate(hit_maps):
            hits = hit_map.hits_for_coarse_channel(coarse_channel, attach_chunk=False)
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
            yield Event(hits, coarse_channel, hit_maps=hit_maps)

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
            for event in Event.find_events(hitmaps, coarse_channel=i):
                yield event
