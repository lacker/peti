#!/usr/bin/env python
"""
This is a hack to be able to import cupy only in environments where it exists
"""
try:
    from cupy import *
except:
    pass
