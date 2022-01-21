"""
Plotting-specific code for events.
"""

import matplotlib
from matplotlib import pyplot as plt


def show_event(event):
    print(event.hits)
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
    plt.show()
    plt.close()
        
    
