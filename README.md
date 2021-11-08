# peti

Petabyte-scale search for Extra-Terrestrial Intelligence

# Strategy

The traditional architecture for SETI algorithms (and for most astronomy) is like

* think of an algorithm that seems good
* apply it to some raw or mildly preprocessed data
* inspect the results
* repeat as needed

The problem is that this is

* Too slow - running a new algorithm on all our data takes months in theory, and in practice has been impossible on the largest datasets.
* Silencing false negatives - when our algorithm is missing a category of interesting signal, we just never see it. This also means we do not have real data sets on which to train ML techniques.

The strategy behind PETI is to break this analysis down into stages.

Stage 1: filter.
Take the large input data and note that 99% of it is "obviously nothing". If we find anything interesting at all that this stage filters out, it's an error. The goal is to make rerunning subsequent stages fast and to do most iteration there, while keeping the algorithm simple enough to avoid false negatives here.

Stage 2: hit classification.
Traditionally hits are measured by signal to noise ratio. Peti instead categorizes hits into (?) linear, nonlinear, noise and gives % confidence for each. The goal is to do all complicated image analysis in this stage, and to surface false negatives through random inspection. This stage is where ML techniques make sense.

Stage 3: event classification.
This stage uses cadence analysis to highlight events to look at. The goal is to provide the output that is scientifically interesting, while being simple and transparent enough that errors in stage 3 output can be traced back to errors in stage 2 output.

# Tactics

There are a few specific problems with the approach of looking for lines that show Doppler drift.

* Handling noise. When we normalize noise according to a large frequency range, noisy regions show up as a lot of hits. This means we need to set the SNR threshold fairly high, at 10, 20, or 25, to avoid getting gigabytes of hits from noisy regions. Noise should be calculated in a small region so that a noisy region does not result in many hits.

* Curvy lines. Rather than searching for straight lines, if we search each spectrum for signals separately during the filtering phase, then curvy lines will still be visible.

* Close-to-horizontal lines. Scientifically we think that valid signals might be smeared across around multiple pixels in a single line. It works but its very slow to rerun the entire algorithm on a horizontally compressed copy of the data, too slow to run in practice.

The current peti approach is to look for signals in each spectrum separately, and to allow signals that span multiple pixels. Then analyzing spectra for linear signals can be done during "stage 2". It is an open question whether this can be done efficiently, but hopefully optimizing the algorithm for the modern GPU era can give us this performance lift.
