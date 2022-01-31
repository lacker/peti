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
    start_times = event.start_times()
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
            title = f"Cadence with target {event.source_name} on {event.readable_day_range()}"
            session = event.session()
            if session:
                title += f", session {session}"
            ax.set_title(title, size=24, pad=24)
            
        if i + 1 == len(event.chunks):
            ax.tick_params(axis="x", bottom=True, labelbottom=True, length=10)
            width = region.shape[1] - 1

            # Figure out which ticks we want based on steps
            digits = 4
            step = 1 / (10 ** digits)
            freq = int(first_freq / step) * step
            ticks = []
            labels = []
            while freq > last_freq:
                fraction = (freq - first_freq) / (last_freq - first_freq)
                ticks.append(fraction * width)
                if 0.05 < fraction < 0.95:
                    labels.append(f"%.{digits}f MHz" % freq)
                else:
                    labels.append("")
                freq -= step

            ax.set_xticks(ticks)
            ax.set_xticklabels(labels, fontsize=16)
            
    plt.subplots_adjust(hspace=0)


def save_event_plot(event):
    plot_filename = event.plot_filename()
    dirname = os.path.dirname(plot_filename)
    Path(dirname).mkdir(parents=True, exist_ok=True)
    make_event_plot(event)
    plt.savefig(plot_filename, bbox_inches="tight")
    print("saved plot to", plot_filename)
    plt.close()
