#!/usr/bin/env python

from config import xp

class Fitter(object):
    def __init__(self, data):
        self.data = data

    def fit_linear(self):
        # Model the noise as gaussian
        mean = xp.mean(self.data)
        std = xp.std(self.data)
