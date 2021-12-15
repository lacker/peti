"""
Random little stuff.
"""

from config import xp

def to_numpy(arr):
    if hasattr(xp, "asnumpy"):
        return xp.asnumpy(arr)
    else:
        return arr    
