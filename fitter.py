#!/usr/bin/env python

from config import xp


class Fitter(object):
    def __init__(self, data, alpha=4):
        """
        Do sigma clipping to fit a Gaussian noise model to this data.
        Model the data's mean and standard deviation. Then remove all points more than alpha standard deviations above the mean.
        Repeat until this converges.

        self.data stores the data
        self.mean, self.std store the noise model
        self.mask stores which points are modeled by noise
        """
        self.data = data

        # Start by considering all data to be in bounds
        in_bounds = data

        while True:
            self.mean = in_bounds.mean()
            self.std = in_bounds.std()
            threshold = self.mean + alpha * self.std
            self.mask = self.data < threshold
            new_in_bounds = self.data[self.mask]

            if new_in_bounds.size < in_bounds.size:
                # We clipped some stuff out. Keep looping
                in_bounds = new_in_bounds
                continue

            if new_in_bounds.size == in_bounds.size:
                # We have converged.
                return

            raise ValueError(f"we went backwards during sigma clipping, from {in_bounds.size} points to {new_in_bounds.size} points")

