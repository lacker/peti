#!/usr/bin/env python
"""
This file controls global settings.
"""
import os

# Directory that h5 data is kept under
if os.path.exists("/datag"):
    H5_ROOT = "/datag/pipeline"
else:
    H5_ROOT = "/datax/dibas"

# Standard amount below which to combine hits
MARGIN = 10

# Standard image width to display
DISPLAY_WIDTH = 60

# Directory that generated files are placed in
PETIDATA = os.path.expanduser("~/petidata")

# Where generated images are stored
IMAGE_ROOT = f"{PETIDATA}/images"

# Where hitmaps are saved
HIT_MAP_ROOT = f"{PETIDATA}/hitmaps"

# Where config data is read from
CONFIG_ROOT = f"{PETIDATA}/config"

# Where event data is stored
EVENT_ROOT = f"{PETIDATA/events"


def front_replace(s, old, new):
    """
    Return a copy of s with old replace with new in precisely one place, the front.
    s must start with old.
    """
    assert s.startswith(old)
    return s.replace(old, new, 1)


def make_relative_filename(h5_filename, root_dir, new_suffix):
    assert h5_filename.endswith(".h5")
    assert new_suffix.startswith(".")
    return front_replace(h5_filename, H5_ROOT, root_dir)[:-3] + new_suffix


def make_hit_map_filename(h5_filename):
    return make_relative_filename(h5_filename, HIT_MAP_ROOT, ".hitmap")

def make_plot_filename(h5_filename, index):
    return make_relative_filename(h5_filename, IMAGE_ROOT, f".{index}.png")

