#!/usr/bin/env python
"""
Usage: ./clear_session.py <session>
"""

import os
import re
import shutil
import sys

from config import EVENT_ROOT, HIT_MAP_ROOT, IMAGE_ROOT

assert __name__ == "__main__"

session = sys.argv[1]
assert re.match("AGBT..._..._[0-9]*", session), f"bad session: {session}"

roots = [EVENT_ROOT, HIT_MAP_ROOT, IMAGE_ROOT]

for root in roots:
    data_dir = f"{root}/{session}"
    if os.path.exists(data_dir):
        print("deleting", data_dir)
        print("TODO: actually delete")
        # shutil.rmtree(data_dir)
