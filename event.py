#!/usr/bin/env python
"""
Information for an event candidate.
"""

from astropy.time import Time
from datetime import datetime

from config import MARGIN, make_plot_filename
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
            self.tstarts = [hit_map.tstart for hit_map in hit_maps]
            self.fch1 = hit_maps[0].fch1
            self.foff = hit_maps[0].foff
            self.nchans = hit_maps[0].nchans
            self.source_name = hit_maps[0].source_name
            self.coarse_channels = hit_maps[0].coarse_channels
        
        # Lazily populated
        self.chunks = None

    def first_column(self):
        """
        Relative to the coarse channel.
        """
        return min(h.first_column for h in self.hits if h)

    def last_column(self):
        """
        Relative to the coarse channel.
        """
        return max(h.last_column for h in self.hits if h)

    def session(self):
        """
        Heuristic. Returns None if it can't figure it out.
        """
        for part in self.h5_filenames[0].split("/"):
            if "GBT" in part:
                return part
        return None
    
    def offset(self):
        coarse_channel_size = self.nchans // self.coarse_channels
        return self.coarse_channel * coarse_channel_size
    
    def plot_filename(self):
        return make_plot_filename(self.h5_filenames[0], self.offset() + self.first_column())
    
    def frequency_range(self):
        """
        Returns (first_freq, last_freq) that corresponds to the first and last column.
        """
        first_index = self.offset() + self.first_column()
        last_index = self.offset() + self.last_column()
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

    def start_times(self):
        return [datetime.utcfromtimestamp(Time(tstart, format="mjd").unix) for tstart in self.tstarts]
            
    def readable_day_range(self):
        times = self.start_times()
        first_dt = times[0]
        last_dt = times[-1]
        first_phrase = first_dt.strftime("%Y %b ") + str(first_dt.day)
        if last_dt.day == first_dt.day:
            return first_phrase
        if last_dt.month == first_dt.month:
            return f"{first_phrase}-{last_dt.day}"
        return f"{first_phrase} - {last_dt.strftime('%b')} {last_dt.day}"
            
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
    def combine_cadence(filenames):
        """
        Combines hitmaps for a cadence into events.
        Returns an iterator for the events.
        """
        scanners = [Scanner(f) for f in filenames]
        hitmaps = [s.hitmap for s in scanners]
        for i in range(scanners[0].num_chunks()):
            for scanner in scanners:
                scanner.scan_chunk(i)
            for event in Event.find_events(hitmaps, coarse_channel=i):
                yield event
