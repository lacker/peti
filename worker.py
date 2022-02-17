#!/usr/bin/env python
"""
This is a worker script. The idea is that one worker script runs on each GPU-equipped machine. It expects data to
already be parceled out on the machine, and to be processing data local to its machine.

Usage:
./worker.py [<configfile>.json]
If not provided, the config file defaults to ~/peticonfig/<machine name>.json

The worker config file is json with the format:

machine: the machine name the config is intended for
directories: a list of directories the machine should process
stop: isoformat time string of what time the worker should stop at.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import sys
import time

import cupy as cp

from combine_cadences import iter_combine_cadences
from detect_cadences import detect_cadences
from scan_cadences import iter_scan_cadences


def log(message):
    print(f"[{datetime.now()}] {message}", flush=True)
        

class OutOfTimeException(Exception):
    pass


def sleep():
    time.sleep(600)

    
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
                    print(f"{donefile} exists, skipping directory")
                    continue

                detect_cadences(directory)
                self.check_time()

                for _ in iter_scan_cadences(directory):
                    self.check_time()

                for _ in iter_combine_cadences(directory):
                    self.check_time()
                    
                Path(donefile).touch()
                
        except OutOfTimeException as e:
            log(f"stop time is {self.stop} - sleeping...")
            sleep()

        log(f"done processing - sleeping...")
        sleep()

            
            
assert __name__ == "__main__"

if len(sys.argv) >= 2:
    filename = sys.argv[1]
else:
    machine = socket.gethostname()
    filename = os.path.expanduser(f"~/peticonfig/{machine}.json")

    
while True:
    if not os.path.exists(filename):
        # Workers with no config files just wait for config files to exist
        log(f"no config file exists at {filename} - sleeping...")
        sleep()
    else:
        conf = Config(filename)
        assert conf.machine == socket.gethostname()
        conf.run()
