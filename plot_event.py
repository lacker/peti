"""
Plotting-specific code for events.
"""

import matplotlib
from matplotlib import pyplot as plt

import os
from pathlib import Path

def readable_frequency_range(low, high):
    max_digits = 8
    for digits in range(1, max_digits + 1):
        formatter = f".{digits}f"
        low_string = format(low, formatter)
        high_string = format(high, formatter)
        candidate_string = low_string + " - " + high_string
        if low_string != high_string or digits >= max_digits:
            return candidate_string
    raise RuntimeError("control should not reach here")

def make_event_plot(event, maybe_reuse_chunks=None):
    """
    Uses pyplot to draw a plot for this event.
    It does not show or save the figure so callers can pick what they want to do with it.
    The figure is left "open" so the caller should call plt.close() when it's done.

    For efficiency, you can pass the chunks if they are already loaded, in maybe_reuse_chunks.
    This function will safely ignore them if they are the wrong chunks.
    """
    first_freq, last_freq = event.frequency_range()
    start_times = event.start_times()
    if maybe_reuse_chunks:
        if event.safe_set_chunks(maybe_reuse_chunks):
            print("reusing chunks")
    event.populate_chunks()
    first_column = event.first_column()
    last_column = event.last_column()
    fig, axs = plt.subplots(nrows=len(event.chunks), figsize=(80, 20))
    for i, (ax, chunk, start_time) in enumerate(zip(axs, event.chunks, start_times)):
        region = chunk.display_region(first_column, last_column)
        ax.imshow(region, rasterized=True, interpolation="nearest", cmap="viridis")
        ax.tick_params(axis="both", 
                       which="both",
                       left=False,
                       bottom=False,
                       labelleft=False,
                       labelbottom=False)            

        ax.tick_params(axis="y", left=True, labelleft=True)
        ax.set_yticks([0])
        ax.set_yticklabels([start_time.strftime("%H:%M:%S")], fontsize=16)
        
        if i == 0:
            title = f"{event.source_name}, frequency {readable_frequency_range(first_freq, last_freq)}"
            ax.set_title(title, size=24, pad=24)
            
            
    plt.subplots_adjust(hspace=0)


def save_event_plot(event, maybe_reuse_chunks=None):
    plot_filename = event.plot_filename()
    dirname = os.path.dirname(plot_filename)
    Path(dirname).mkdir(parents=True, exist_ok=True)
    make_event_plot(event, maybe_reuse_chunks=maybe_reuse_chunks)
    plt.savefig(plot_filename, bbox_inches="tight")
    print("saved plot to", plot_filename)
    plt.close()
