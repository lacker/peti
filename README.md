# peti

Petabyte-scale search for Extra-Terrestrial Intelligence

# Strategy

The traditional architecture for SETI algorithms is like

* think of an algorithm that seems good
* apply it to a bunch of huge data files
* inspect the results
* repeat as needed

The problem is that this is

* Too slow - running a new algorithm on all our data takes months in theory, and in practice has been impossible on the largest datasets.
* Silencing false negatives - when our algorithm is missing a category of interesting signal, we just never see it.

The strategy behind PETI is to break this analysis down into stages.

Stage 1: filter.
Take the large input data and note that 99% of it is "obviously nothing". If we find anything interesting at all that this stage filters out, it's an error. The goal is to make rerunning subsequent stages fast and to do most iteration there, while keeping the algorithm simple enough to avoid false negatives here. The output data of this stage should be small enough that you can store it without really taking up any space relative to the data files themselves.

Stage 2: hit classification.
We care about whether signals are linear, just noise, or something else entirely. This classification isn't straightforward and I don't know the best way to do it yet. So, we want this stage to be fast to rerun, so that we can experiment here a lot. The goal is to do all complicated image analysis in this stage, and to surface false negatives through random inspection.

Stage 3: event classification.
This stage uses cadence analysis to highlight events to look at that cross different files. The goal is to provide the output that is scientifically interesting, while being simple and transparent enough that errors in stage 3 output can be traced back to errors in stage 2 output. It's okay if the data output of this stage is small, because we can improve algorithm quality by inspecting the output of stage 2.

# Tactics

There are a few specific problems with the "Taylor tree" approach of looking for lines that show Doppler drift.

* Handling noise. When we normalize noise according to a large frequency range, noisy regions show up as a lot of hits. This means we need to set the SNR threshold fairly high, at 10, 20, or 25, to avoid getting gigabytes of hits from noisy regions. Noise should be calculated in a small region so that a noisy region does not result in many hits. Equivalently, many hits that are near each other can just be counted as one large hit.

* Curvy lines. Rather than searching for straight lines, if we search each spectrum for signals separately during the filtering phase, then curvy lines will still be available to be classified in stage 2.

* More-horizontal-than-vertical lines. Scientifically we think that valid signals might be smeared across around multiple pixels in a single line. It works but it's very slow to rerun the entire algorithm on a horizontally compressed copy of the data, too slow to run in practice.

The current peti approach is to look for signals in each spectrum separately using a calculation over a sliding window, which includes signals that span multiple pixels. Then analyzing spectra for linear signals can be done during "stage 2". In the recent past, we haven't been fully saturating our GPUs, we are often just limited by the speed of loading data from disk. So we have extra GPU power to spare here to improve algorithmic performance. I think we should be able to measure both a local measure of noise and a local measure of signal, across different window sizes, in a single pass.
