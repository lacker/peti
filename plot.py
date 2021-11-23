"""
Tools for plotting hit groups and the like.
Only works inside a Jupyter notebook.
"""

import matplotlib
matplotlib.rc("figure", max_open_warning=0)
from matplotlib import pyplot as plt

from IPython.display import display
import random

import filtering


def show(group):
    region = group.region()
    fig, ax = plt.subplots(figsize=region.shape)
    ax.imshow(region, rasterized=True, interpolation="nearest", cmap="viridis")
    display(fig)
    plt.close()

    
def show_list(groups):
    for i, group in list(enumerate(groups))[:100]:
        print(f"group {i} / {len(groups)}. {len(group)} hits.")
        show(group)


def truncate(alist, n):
    """
    Select a random sublist of length n if alist is longer.
    """
    if len(alist) <= n:
        return alist
    return random.sample(alist, n)
    
        
def diff_chunk(filename, i, chunk=None):
    """
    Generate differences between experiment=True and experiment=False on the provided chunk.
    Returns how many diffs we displayed.
    """
    if chunk is None:
        f = File(filename)
        chunk = f.get_chunk(i)

    # Show a limited number of images if there are lots for a single chunk
    limit = 5
        
    base = filtering.find_groups(chunk, experiment=False)
    exp = filtering.find_groups(chunk, experiment=True)

    base_not_exp = filtering.diff(base, exp)
    exp_not_base = filtering.diff(exp, base)

    if not base_not_exp and not exp_not_base:
        return 0
    
    print(f"analyzing chunk {i} of {filename}")
    print(f"baseline has {len(base)} groups")
    print(f"experiment has {len(exp)} groups")

    if base_not_exp:
        print(f"{len(base_not_exp)} groups in baseline but not experiment:")
        base_not_exp = truncate(base_not_exp, limit)
        show_list(base_not_exp)
    
    if exp_not_base:
        print(f"{len(exp_not_base)} groups in experiment but not baseline:")
        exp_not_base = truncate(exp_not_base, limit)
        show_list(exp_not_base)

    return len(base_not_exp) + len(exp_not_base)


def sxs(seed=None, n=10):
    """
    Generate differences between experiment=True and experiment=False until we have at least n of them to display.
    """
    fetcher = filtering.ChunkFetcher(seed=seed)

    count = 0
    while count < n:
        filename, i, chunk = fetcher.fetch()
        count += diff_chunk(filename, i, chunk=chunk)
    print("sxs done")
