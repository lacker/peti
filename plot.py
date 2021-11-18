"""
Tools for plotting hit groups and the like.
Typically used as utilities from inside a Jupyter notebook.
"""

import matplotlib
matplotlib.rc("figure", max_open_warning=0)
from matplotlib import pyplot as plt

def show(group, title=None):
    region = group.region()
    plt.figure(figsize=region.shape)
    if title:
        plt.title(title)
    plt.imshow(region, rasterized=True, interpolation="nearest", cmap="viridis")

def show_list(groups):
    for i, group in list(enumerate(groups))[:100]:
        title = f"group {i} / {len(groups)}. {len(group)} hits."
        show(group, title=title)
