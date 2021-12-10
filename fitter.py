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

        self.num_pixels is the number of pixels in the signal
        self.start_index is the index the signal begins at
        self.drift_rate is the rate of signal drift (in horizontal pixels per vertical pixel)
        self.mse is the mean squared error (horizontal distance) from the fit line to the signal pixel
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

        # Do a linear regression
        row_indexes, col_indexes = xp.where(xp.logical_not(self.mask))
        self.num_pixels = len(row_indexes)
        inputs = xp.vstack([row_indexes, xp.ones(len(row_indexes))]).T
        solution, residual, _, _ = xp.linalg.lstsq(inputs, col_indexes, rcond=None)
        self.drift_rate, self.start_index = solution
        self.mse = residual / self.num_pixels

