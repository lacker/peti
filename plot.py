"""
Tools for plotting hit groups and the like.
Only works inside a Jupyter notebook.
"""

import matplotlib
matplotlib.rc("figure", max_open_warning=0)
from matplotlib import pyplot as plt

from IPython.display import display


def show(group):
    region = group.region()
    fig, ax = plt.subplots(figsize=region.shape)
    ax.imshow(region, rasterized=True, interpolation="nearest", cmap="viridis")
    display(fig)

def show_list(groups):
    for i, group in list(enumerate(groups))[:100]:
        print(f"group {i} / {len(groups)}. {len(group)} hits.")
        show(group)
