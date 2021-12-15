"""
Tools for plotting hit groups and the like.
Only works inside a Jupyter notebook.
"""

import matplotlib
matplotlib.rc("figure", max_open_warning=0)
from matplotlib import pyplot as plt

from IPython.display import display
import random

from config import xp
import h5_file
import hit_group
import scanner
from util import to_numpy

    
def show(group, chunk):
    region = chunk.display_region(group.first_column, group.last_column)
    fig, ax = plt.subplots(figsize=region.shape)
    ax.imshow(region, rasterized=True, interpolation="nearest", cmap="viridis")
    display(fig)
    plt.close()

    
def show_list(groups, chunk):
    for i, group in list(enumerate(groups))[:100]:
        print(f"group {i} / {len(groups)}. {len(group)} hits.")
        show(group, chunk)


def show_fit(fitter, mask=False):
    if mask:
        region = to_numpy(1 - fitter.mask.astype(float))
    else:
        region = to_numpy(fitter.data)
    end_y = region.shape[0] - 1
    end_x = fitter.start_index + fitter.drift_rate * end_y
    fig, ax = plt.subplots(figsize=region.shape)
    ax.imshow(region, rasterized=True, interpolation="nearest", cmap="viridis")
    ax.plot((fitter.start_index, end_x), (0, end_y), "r", lw=2)
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
    If baseline and/or experiment are provided, use it as the list of groups to compare against.
    They should be lists of HitGroup objects.
    If they aren't provided, use find_groups to find them.
    """
    if chunk is None:
        f = File(filename)
        chunk = f.get_chunk(i)

    # Show a limited number of images if there are lots for a single chunk
    limit = 5

    if baseline is None:
        base = scanner.find_groups(chunk, experiment=False)
    else:
        base = baseline

    if experiment is None:
        exp = scanner.find_groups(chunk, experiment=True)
    else:
        exp = experiment

    base_not_exp = hit_group.diff(base, exp)
    exp_not_base = hit_group.diff(exp, base)

    if not base_not_exp and not exp_not_base:
        print("baseline and experiment are identical")
        return 0
    
    print(f"baseline has {len(base)} groups")
    print(f"experiment has {len(exp)} groups")

    if base_not_exp:
        print(f"{len(base_not_exp)} groups in baseline but not experiment:")
        base_not_exp = truncate(base_not_exp, limit)
        show_list(base_not_exp, chunk)
    
    if exp_not_base:
        print(f"{len(exp_not_base)} groups in experiment but not baseline:")
        exp_not_base = truncate(exp_not_base, limit)
        show_list(exp_not_base, chunk)

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
