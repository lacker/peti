#!/usr/bin/env python
"""
This file controls global settings.
"""
import os

# Directory that h5 data is kept under
H5_ROOT = "/datag/pipeline"

# Standard amount below which to combine hits
MARGIN = 10

# Standard image width to display
DISPLAY_WIDTH = 60

# Where generated images are stored
IMAGE_ROOT = os.path.expanduser("~/images")

# Where hitmaps are saved
HIT_MAP_ROOT = os.path.expanduser("~/hitmaps")


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

