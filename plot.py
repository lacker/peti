"""
Tools for plotting hit groups and the like.
Only works inside a Jupyter notebook.
"""

import matplotlib
matplotlib.rc("figure", max_open_warning=0)
from matplotlib import pyplot as plt

from IPython.display import display, Image
import random

import h5_file
import hit_info
import json
from plot_event import make_event_plot
import scanner


def show_event(event):
    print(event.hits)

    if event.has_plot_file():
        filename = event.plot_filename()
        print("showing plot from file:", filename)
        return Image(filename)
    else:
        print("making fresh plot")
        make_event_plot(event)
        plt.show()
        plt.close()
        

def show_hit(hit, chunk=None):
    if chunk is None:
        chunk = hit.data
    region = chunk.display_region(hit.first_column, hit.last_column)
    fig, ax = plt.subplots(figsize=region.shape)
    ax.imshow(region, rasterized=True, interpolation="nearest", cmap="viridis")
    display(fig)
    plt.close()

    
def show_hits(hits, chunk=None):
    for i, hit in list(enumerate(hits))[:100]:
        print(f"hit {i} / {len(hits)}.")
        show_hit(hit, chunk=chunk)


def show_fit(hit, mask=False):
    if mask:
        region = 1 - hit.mask.astype(float)
    else:
        region = hit.fit_data
    end_y = region.shape[0] - 1
    start_index = hit.drift_start - hit.data.offset - hit.fit_offset
    end_x = start_index + hit.drift_rate * end_y
    fig, ax = plt.subplots(figsize=region.shape)
    ax.imshow(region, rasterized=True, interpolation="nearest", cmap="viridis")
    ax.plot((start_index, end_x), (0, end_y), "r", lw=2)
    display(fig)
    plt.close()
        
        
def truncate(alist, n):
    """
    Select a random sublist of length n if alist is longer.
    """
    if len(alist) <= n:
        return alist
    return random.sample(alist, n)
    

def diff_chunk(chunk, baseline=None, experiment=None):
    """
    Generate differences between experiment=True and experiment=False on the provided chunk.
    Returns how many diffs we displayed.
    If baseline and/or experiment are provided, use it as the list of hits to compare against.
    If they aren't provided, use find_hits to find them.
    """
    if chunk is None:
        f = File(filename)
        chunk = f.get_chunk(i)

    # Show a limited number of images if there are lots for a single chunk
    limit = 5

    if baseline is None:
        base = scanner.find_hits(chunk, experiment=False)
    else:
        base = baseline

    if experiment is None:
        exp = scanner.find_hits(chunk, experiment=True)
    else:
        exp = experiment
    
    base_not_exp = hit_info.diff(base, exp)
    exp_not_base = hit_info.diff(exp, base)

    if not base_not_exp and not exp_not_base:
        print("baseline and experiment are identical")
        return 0
    
    print(f"baseline has {len(base)} hits")
    print(f"experiment has {len(exp)} hits")

    if base_not_exp:
        print(f"{len(base_not_exp)} hits in baseline but not experiment:")
        base_not_exp = truncate(base_not_exp, limit)
        show_hits(base_not_exp, chunk)
    
    if exp_not_base:
        print(f"{len(exp_not_base)} hits in experiment but not baseline:")
        exp_not_base = truncate(exp_not_base, limit)
        show_hits(exp_not_base, chunk)

    return len(base_not_exp) + len(exp_not_base)


def compare(seed=None, n=10):
    """
    Generate differences between experiment=True and experiment=False until we have at least n of them to display.
    """
    fetcher = h5_file.ChunkFetcher(seed=seed)

    count = 0
    while count < n:
        filename, i, chunk = fetcher.fetch()
        print(f"analyzing chunk {i} of {filename}")
        count += diff_chunk(chunk)
    print("comparison done")

    
def load_cadences():
    answer = []
    for line in open("/home/obs/cadences.json"):
        info = json.loads(line)
        filenames = info["filenames"]
        dirs = [f.split("/")[-2] for f in filenames]
        if min(dirs) != max(dirs):
            continue
        answer.append(filenames)
    return answer

    
