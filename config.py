#!/usr/bin/env python
"""
This file controls global settings.
"""

# Uncomment precisely one of these lines, to pick whether we are using the GPU or not.
# import numpy as xp
import cupy as xp

# Directory that h5 data is kept under
H5_ROOT = "/datag/pipeline"

# Standard amount below which to combine hits
MARGIN = 10

# Standard image width to display
DISPLAY_WIDTH = 60
