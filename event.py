#!/usr/bin/env python
"""
Information for an event candidate.
"""

from astropy.time import Time
from datetime import datetime
import os

from fastavro import parse_schema, reader, writer

from config import MARGIN, make_plot_filename
from hit_info import HitInfo, HIT_INFO_SCHEMA
from scanner import Scanner


EVENT_SCHEMA = {
    "namespace": "peti",
    "type": "record",
    "name": "Event",
    "fields": [{
        "name": "h5_filenames",
        "type": {
            "type": "array",
            "items": "string",
        },
    }, {
        "name": "source_name",
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
        "name": "tstarts",
        "type": {
            "type": "array",
            "items": "float",
        },
    }, {
        "name": "coarse_channels",
        "type": "int",
    }, {
        "name": "hits",
        "type": {
            "type": "array",
            "items": ["null", HIT_INFO_SCHEMA],
        },
    }]        
}

PARSED_EVENT_SCHEMA = parse_schema(EVENT_SCHEMA)


class Event(object):
    normal_fields = ["h5_filenames", "source_name", "fch1", "foff", "nchans", "tstarts", "coarse_channels"]

    def __init__(self, hits, hit_maps=None):
        """
        Since an event may correspond to no hit at all in a particular input, the hits list can have a None.
        It can't be all None though.
        If hit_maps is provided, it must be parallel to hits.
        So there must be a hitmap for each entry even if the corresponding hit is None.
        There cannot be multiple hits per file in a single event.
        """
        self.hits = hits
        self.hit_maps = hit_maps

        for hit in self.hits:
            if hit is not None:
                self.coarse_channel = hit.coarse_channel
                break
        else:
            raise RuntimeError("an all-None list of hits was passed to Event creation")
                
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

        # For now, the score is purely defined by how much the hits align with the ABACAD pattern.
        self.score = 0
        for i, hit in enumerate(self.hits):
            if hit is None:
                continue
            if i % 2 == 0:
                self.score += 1
            else:
                self.score -= 1
        
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

    def has_plot_file(self):
        return os.path.exists(self.plot_filename())
    
    def frequency_range(self):
        """
        Returns (first_freq, last_freq) that corresponds to the first and last column.
        """
        first_index = self.offset() + self.first_column()
        last_index = self.offset() + self.last_column()
        first_freq = self.fch1 + first_index * self.foff
        last_freq = self.fch1 + last_index * self.foff
        return (first_freq, last_freq)

    def safe_set_chunks(self, chunks):
        """
        Sets the chunks if they match.
        Does nothing if they do not.
        Returns whether they matched.
        """
        for chunk, filename in zip(chunks, self.h5_filenames):
            if chunk.filename() != filename:
                return False
            if chunk.offset != self.offset():
                return False
        self.chunks = chunks
        return True
    
    def populate_chunks(self):
        if self.chunks:
            return
        assert self.hit_maps, "Populating chunks requires the hit maps."
        self.chunks = []
        for hit, hit_map in zip(self.hits, self.hit_maps):
            chunk = hit_map.get_chunk(self.coarse_channel)
            self.chunks.append(chunk)

    def detach_chunks(self):
        """
        Removes references to the chunks and returns them to the caller.
        """
        answer = self.chunks
        self.chunks = None
        return answer
            
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
        plausible_next_column = None
        for index, hit in labeled_hits:
            if not current_group:
                # Make a new group with only this hit
                current_group.append((index, hit))
                plausible_next_column = hit.plausible_next_column()
                continue
            if plausible_next_column >= hit.first_column:
                # Add this hit to the group
                current_group.append((index, hit))
                plausible_next_column = max(plausible_next_column, hit.plausible_next_column())
                continue
            # Make current group into a group and start a new group with this hit
            groups.append(current_group)
            current_group = [(index, hit)]
            plausible_next_column = hit.plausible_next_column()
        if current_group:
            groups.append(current_group)


        groups = [g for g in groups if len(g) > 1]
        if not groups:
            return

        # Construct events for this coarse channel
        for group in groups:
            hits = [None] * len(hit_maps)
            for (index, hit) in group:
                if hits[index] is None:
                    hits[index] = hit
                else:
                    hits[index] = hits[index].join(hit, check_distance=False)

            # Filter out groups with only one hit
            if len([hit for hit in hits if hit is not None]) <= 1:
                continue

            # print(hits)
            yield Event(hits, hit_maps=hit_maps)


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


    def to_plain(self):
        hits = []
        for hit in self.hits:
            if hit is None:
                hits.append(None)
            else:
                hits.append(hit.to_plain())
        plain = {"hits": hits}
        for field in Event.normal_fields:
            plain[field] = getattr(self, field)
        return plain

    @staticmethod
    def from_plain(plain):
        chunk_size = plain["nchans"] // plain["coarse_channels"]
        hits = []
        for plain_hit in plain["hits"]:
            if plain_hit is None:
                hits.append(None)
            else:
                hits.append(HitInfo.from_plain(plain_hit, chunk_size))
        event = Event(hits)
        for field in Event.normal_fields:
            setattr(event, field, plain[field])
        return event

    @staticmethod
    def save_list(events, filename):
        filename = os.path.expanduser(filename)
        assert filename.endswith(".events")
        plain = [event.to_plain() for event in events]
        with open(filename, "wb") as outfile:
            writer(outfile, PARSED_EVENT_SCHEMA, plain)

    @staticmethod
    def load_list(filename):
        """
        Returns a list of Event objects.
        """
        filename = os.path.expanduser(filename)
        assert filename.endswith(".events")
        with open(filename, "rb") as infile:
            return [Event.from_plain(plain) for plain in reader(infile)]
        
        
