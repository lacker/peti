#!/usr/bin/env python

from config import MARGIN, xp

class Fitter(object):
    def __init__(self, group, chunk, alpha=3.5):
        """
        Do sigma clipping to fit a Gaussian noise model to this data.
        Model the data's mean and standard deviation. Then remove all points more than alpha standard deviations above the mean.
        Repeat until this converges.

        self.data stores the data we are fitting to
        self.offset is how much it is horizontally offset from the underlying chunk

        self.mean, self.std store the noise model
        self.mask stores which points are modeled by noise

        self.num_pixels is the number of pixels in the signal
        self.start_index is the index the signal begins at
        self.drift_rate is the rate of signal drift (in horizontal pixels per vertical pixel)
        self.mse is the mean squared error (horizontal distance) from the fit line to the signal pixel
        """
        self.offset = max(group.first_column - MARGIN, 0)
        self.data = chunk.array[:, self.offset : group.last_column + MARGIN + 1]
        
        # Start by masking out the strongest pixel for each hit window
        self.mask = xp.full(self.data.shape, True, dtype=bool)
        for row, first_column, last_column in group.hit_windows:
            begin = first_column - self.offset
            end = last_column - self.offset + 1
            max_index = self.data[row][begin:end].argmax()
            self.mask[row][begin + max_index] = False
            
        in_bounds = self.data[self.mask]

        while True:
            self.mean = in_bounds.mean().item()
            self.std = in_bounds.std().item()
            threshold = self.mean + alpha * self.std
            self.mask = xp.logical_and(self.mask, self.data < threshold)
            new_in_bounds = self.data[self.mask]

            if new_in_bounds.size < in_bounds.size:
                # We clipped some stuff out. Keep looping
                in_bounds = new_in_bounds
                continue

            if new_in_bounds.size == in_bounds.size:
                # We have converged.
                break

            # The logical_and should prevent this
            raise ValueError(f"coding error")

        # Do a linear regression
        row_indexes, col_indexes = xp.where(xp.logical_not(self.mask))
        self.num_pixels = len(row_indexes)
        inputs = xp.vstack([row_indexes, xp.ones(len(row_indexes))]).T
        solution, residual, _, _ = xp.linalg.lstsq(inputs, col_indexes, rcond=None)
        self.drift_rate, self.start_index = solution
        self.mse = residual.item() / self.num_pixels

        # Calculate SNR by taking one pixel per row
        signal = xp.amax(self.data, axis=1).mean().item()
        self.snr = (signal - self.mean) / self.std
