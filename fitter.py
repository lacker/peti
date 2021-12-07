#!/usr/bin/env python

from config import xp


def sigma_clip(data, alpha):
    """
    Model the data's mean and standard deviation. Then remove all points more than alpha standard deviations above the mean.
    Repeat until this converges.
    
    Returns (mean, stdev, mask) tuple, where the mask is the positions that were used in the final model.
    """
    # Start by considering all data to be in bounds
    in_bounds = data
    
    while True:
        mean = in_bounds.mean()
        std = in_bounds.std()
        threshold = mean + alpha * std
        mask = data < threshold
        new_in_bounds = data[mask]

        if new_in_bounds.size < in_bounds.size:
            # We clipped some stuff out. Keep looping
            in_bounds = new_in_bounds
            continue

        if new_in_bounds.size == in_bounds.size:
            # We have converged.
            return (mean, std, mask)

        raise ValueError(f"we went backwards during sigma clipping, from {in_bounds.size} points to {new_in_bounds.size} points")
        
    

class Fitter(object):
    def __init__(self, data):
        self.data = data

