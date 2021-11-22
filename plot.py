"""
Tools for plotting hit groups and the like.
Only works inside a Jupyter notebook.
"""

import matplotlib
matplotlib.rc("figure", max_open_warning=0)
from matplotlib import pyplot as plt

from IPython.display import display

import filtering


def show(group):
    region = group.region()
    fig, ax = plt.subplots(figsize=region.shape)
    ax.imshow(region, rasterized=True, interpolation="nearest", cmap="viridis")
    display(fig)

    
def show_list(groups):
    for i, group in list(enumerate(groups))[:100]:
        print(f"group {i} / {len(groups)}. {len(group)} hits.")
        show(group)


def diff_chunk(filename, i, chunk=None):
    """
    Generate differences between experiment=True and experiment=False on the provided chunk.
    Returns how many diffs we displayed.
    """
    if chunk is None:
        f = File(filename)
        chunk = f.get_chunk(i)

    base = filtering.find_groups(chunk, experiment=False)
    exp = filtering.find_groups(chunk, experiment=True)
    print(f"analyzing chunk {i} of {filename}")
    print(f"baseline has {len(base)} groups")
    print(f"experiment has {len(exp)} groups")

    base_not_exp = filtering.diff(base, exp)
    if base_not_exp:
        print(f"{len(base_not_exp)} groups in baseline but not experiment:")
        show_list(base_not_exp)
    
    exp_not_base = filtering.diff(exp, base)
    if exp_not_base:
        print(f"{len(exp_not_base)} groups in experiment but not baseline:")
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
    plt.close()
