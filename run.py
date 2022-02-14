#!/usr/bin/env python
"""
Usage:
./run.py <configfile>.json
"""

from datetime import datetime, timezone
import json
import os
import socket
import sys
import time

import cupy as cp


def log(message):
    print(f"[{datetime.now()}] {message}", flush=True)
        

class OutOfTimeException(Exception):
    pass

    
class Config(object):
    def __init__(self, filename):
        assert filename.endswith(".json")
        self.filename = filename
        self.load()

    def load(self):
        raw = open(self.filename).read()
        plain = json.loads(raw)
        self.machine = plain["machine"]
        self.directories = plain["directories"]
        self.stop = datetime.fromisoformat(plain["stop"])
        assert self.stop.tzinfo is timezone.utc, "PETI config requires UTC timestamps"

    def check_time(self):
        """
        Raises an OutOfTimeException if we are out of time.
        """
        now = datetime.now(timezone.utc)
        if now < self.stop:
            return

        # We should stop
        mempool = cp.get_default_memory_pool()
        if mempool.total_bytes > 1000000:
            mempool.free_all_blocks()
        if mempool.total_bytes > 1000000:
            log("could not free GPU memory")
            sys.exit(1)

        raise OutOfTimeException()

        
    def run(self):
        """
        Runs one step.
        Returns when we are done.
        """
        try:
            for directory in self.directories:
                donefile = os.path.join(directory, "peti.done")
                if os.path.exists(donefile):
                    continue

                cadencefile = os.path.join(directory, "cadences.json")
                if not os.path.exists(cadencefile):
                    raise RuntimeError("TODO: write detect_cadences")

                # TODO: scan_cadences
                # TODO: combine_cadences
                
        except OutOfTimeException as e:
            log(f"stop time is {self.stop} - sleeping...")
            time.sleep(600)

        log(f"done processing - sleeping...")
        time.sleep(600)

            
            
assert __name__ == "__main__"

filename = sys.argv[1]


while True:
    conf = Config(filename)
    assert conf.machine == socket.gethostname()
    conf.run()
