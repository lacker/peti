"""
Plotting-specific code for events.
"""

import matplotlib
from matplotlib import pyplot as plt

import os
from pathlib import Path

def make_event_plot(event):
    """
    Uses pyplot to draw a plot for this event.
    It does not show or save the figure so callers can pick what they want to do with it.
    The figure is left "open" so the caller should call plt.close() when it's done.
    """
    first_freq, last_freq = event.frequency_range()
    print(f"frequency range: {first_freq:.6f} - {last_freq:.6f}")
    event.populate_chunks()
    first_column = event.first_column()
    last_column = event.last_column()
    fig, axs = plt.subplots(nrows=len(event.chunks))
    for i, (ax, chunk) in enumerate(zip(axs, event.chunks)):
        region = chunk.display_region(first_column, last_column)
        ax.imshow(region, rasterized=True, interpolation="nearest", cmap="viridis")
        ax.tick_params(axis="both", 
                       which="both",
                       left=False,
                       bottom=False,
                       labelleft=False,
                       labelbottom=False)
        if i + 1 == len(event.chunks):
            pass
    plt.subplots_adjust(hspace=0)    


def show_event(event):
    """
    Displays the plot for an event.
    Call from a notebook.
    """
    print(event.hits)
    make_event_plot(event)
    plt.show()
    plt.close()


def save_event_plot(event):
    plot_filename = event.plot_filename()
    dirname = os.path.dirname(plot_filename)
    Path(dirname).mkdir(parents=True, exist_ok=True)
    make_event_plot(event)
    plt.savefig(plot_filename)
    print("saved plot to", plot_filename)
    plt.close()
