# peti

Petabyte-scale search for Extra-Terrestrial Intelligence

The traditional architecture for SETI algorithms (and for most astronomy) is like

* think of an algorithm that seems good
* apply it to some raw or mildly preprocessed data
* inspect the results
* repeat as needed

The problem is that this is

* Too slow - running a new algorithm on all our data takes months in theory, and in practice has been impossible on the largest datasets due to the accumulation of technical debt.
* Silencing false negatives - when our algorithm is missing a category of interesting signal, we just never see it. This also means we do not have real data sets on which to train ML techniques.

The strategy behind PETI is to break this analysis down into stages.

Stage 1: filter.
Take the large input data and note that 99% of it is "obviously nothing". If we find anything interesting at all that this stage filters out, it's an error. The goal is to make rerunning subsequent stages fast and to do most iteration there, while keeping the algorithm simple enough to avoid false negatives here.

Stage 2: hit classification.
Traditionally hits are measured by signal to noise ratio. Peti instead categorizes hits into (?) linear, nonlinear, noise and gives % confidence for each. The goal is to do all complicated image analysis in this stage, and to surface false negatives through random inspection. This stage is where ML techniques make sense.

Stage 3: event classification.
This stage uses cadence analysis to highlight events to look at. The goal is to provide the output that is scientifically interesting, while being simple and transparent enough that errors in stage 3 output can be traced back to errors in stage 2 output.

TODO: actually implement this
