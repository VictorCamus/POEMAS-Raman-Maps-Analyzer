"""Configuració dels mapes de colors predeterminats per al programa."""

from typing import TYPE_CHECKING

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import colormaps as cm
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from numpy import linspace

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Literal

N = 255

hot = cm["hot"]
new_colors = hot(linspace(0, 1, 420))[:256]
newcmp = ListedColormap(new_colors)
cm.register(cmap=newcmp, name="SpecData", force=True)
cm.register(cmap=newcmp.reversed(), name="SpecData_r", force=True)

cmaps_custom: list[str] = [
    # Personalitzats
    "Height",
    "Mag",
    "Phase",
    "CPD",
    "Iprobe",
    "SPV",
    "Grain",
    "SpecData",
]

cmaps_matplotlib: list[str] = [
    # Moderns / perceptuals
    "viridis",
    "plasma",
    "inferno",
    "magma",
    "cividis",
    "turbo",
    # Sequential
    "greys",
    "purples",
    "blues",
    "greens",
    "oranges",
    "reds",
    # Sequential multi-color
    "YlGn",
    "YlGnBu",
    "GnBu",
    "BuGn",
    "PuBu",
    "PuRd",
    # Diverging
    "coolwarm",
    "bwr",
    "seismic",
    "RdBu",
    "RdYlBu",
    "Spectral",
    # Cyclic / especials
    "twilight",
    "hsv",
    # Clàssics
    "jet",
    "cool",
    "spring",
    "summer",
    "autumn",
    "winter",
    "gray",
    "bone",
    "hot",
]

cmaps: list[str] = cmaps_custom + cmaps_matplotlib
colors: dict[str, dict[Literal["red", "green", "blue", "alpha"], Sequence[tuple[float, ...]]]] = {
    "CPD": {
        "red": [
            (0 / N, 1 - 255 / N, 1 - 255 / N),
            (77 / N, 1 - 212 / N, 1 - 212 / N),
            (128 / N, 1 - 205 / N, 1 - 205 / N),
            (179 / N, 1 - 169 / N, 1 - 169 / N),
            (230 / N, 1 - 23 / N, 1 - 23 / N),
            (255 / N, 1 - 0 / N, 1 - 0 / N),
        ],
        "green": [
            (0 / N, 1 - 255 / N, 1 - 255 / N),
            (77 / N, 1 - 185 / N, 1 - 185 / N),
            (128 / N, 1 - 152 / N, 1 - 152 / N),
            (179 / N, 1 - 83 / N, 1 - 83 / N),
            (230 / N, 1 - 23 / N, 1 - 23 / N),
            (255 / N, 1 - 0 / N, 1 - 0 / N),
        ],
        "blue": [
            (0 / N, 1 - 255 / N, 1 - 255 / N),
            (77 / N, 1 - 130 / N, 1 - 130 / N),
            (123 / N, 1 - 100 / N, 1 - 100 / N),
            (179 / N, 1 - 59 / N, 1 - 59 / N),
            (230 / N, 1 - 23 / N, 1 - 23 / N),
            (255 / N, 1 - 0 / N, 1 - 0 / N),
        ],
    },
    "Height": {
        "red": [
            (0 / N, 1 - 255 / N, 1 - 255 / N),
            (32 / N, 1 - 136 / N, 1 - 136 / N),
            (94 / N, 1 - 57 / N, 1 - 57 / N),
            (152 / N, 1 - 17 / N, 1 - 17 / N),
            (188 / N, 1 - 6 / N, 1 - 6 / N),
            (255 / N, 1 - 6 / N, 1 - 6 / N),
        ],
        "green": [
            (0 / N, 1 - 255 / N, 1 - 255 / N),
            (17 / N, 1 - 255 / N, 1 - 255 / N),
            (47 / N, 1 - 234 / N, 1 - 234 / N),
            (106 / N, 1 - 159 / N, 1 - 159 / N),
            (182 / N, 1 - 47 / N, 1 - 47 / N),
            (232 / N, 1 - 7 / N, 1 - 7 / N),
            (255 / N, 1 - 6 / N, 1 - 6 / N),
        ],
        "blue": [
            (0 / N, 1 - 255 / N, 1 - 255 / N),
            (85 / N, 1 - 255 / N, 1 - 255 / N),
            (160 / N, 1 - 179 / N, 1 - 179 / N),
            (220 / N, 1 - 42 / N, 1 - 42 / N),
            (255 / N, 1 - 4 / N, 1 - 4 / N),
        ],
    },
    "Mag": {
        "red": [
            (0 / N, 1 - 255 / N, 1 - 255 / N),
            (26 / N, 1 - 219 / N, 1 - 219 / N),
            (51 / N, 1 - 184 / N, 1 - 184 / N),
            (77 / N, 1 - 148 / N, 1 - 148 / N),
            (102 / N, 1 - 113 / N, 1 - 113 / N),
            (128 / N, 1 - 76 / N, 1 - 76 / N),
            (153 / N, 1 - 41 / N, 1 - 41 / N),
            (179 / N, 1 - 5 / N, 1 - 5 / N),
            (204 / N, 1 - 0 / N, 1 - 0 / N),
            (230 / N, 1 - 0 / N, 1 - 0 / N),
            (255 / N, 1 - 0 / N, 1 - 0 / N),
        ],
        "green": [
            (0 / N, 1 - 255 / N, 1 - 255 / N),
            (26 / N, 1 - 255 / N, 1 - 255 / N),
            (51 / N, 1 - 255 / N, 1 - 255 / N),
            (77 / N, 1 - 255 / N, 1 - 255 / N),
            (102 / N, 1 - 255 / N, 1 - 255 / N),
            (128 / N, 1 - 255 / N, 1 - 255 / N),
            (153 / N, 1 - 185 / N, 1 - 185 / N),
            (179 / N, 1 - 113 / N, 1 - 113 / N),
            (204 / N, 1 - 43 / N, 1 - 43 / N),
            (230 / N, 1 - 0 / N, 1 - 0 / N),
            (255 / N, 1 - 0 / N, 1 - 0 / N),
        ],
        "blue": [
            (0 / N, 1 - 255 / N, 1 - 255 / N),
            (26 / N, 1 - 255 / N, 1 - 255 / N),
            (51 / N, 1 - 255 / N, 1 - 255 / N),
            (77 / N, 1 - 255 / N, 1 - 255 / N),
            (102 / N, 1 - 255 / N, 1 - 255 / N),
            (128 / N, 1 - 255 / N, 1 - 255 / N),
            (153 / N, 1 - 255 / N, 1 - 255 / N),
            (179 / N, 1 - 255 / N, 1 - 255 / N),
            (204 / N, 1 - 208 / N, 1 - 208 / N),
            (230 / N, 1 - 104 / N, 1 - 104 / N),
            (255 / N, 1 - 4 / N, 1 - 4 / N),
        ],
    },
    "SPV": {
        "red": [
            (0 / N, 1 - 255 / N, 1 - 255 / N),
            (127.5 / N, 1 - 200 / N, 1 - 200 / N),
            (180 / N, 1 - 0 / N, 1 - 0 / N),
            (255 / N, 1 - 0 / N, 1 - 0 / N),
        ],
        "green": [
            (0 / N, 1 - 0 / N, 1 - 0 / N),
            (67 / N, 1 - 130 / N, 1 - 130 / N),
            (101 / N, 1 - 196 / N, 1 - 196 / N),
            (127.5 / N, 1 - 200 / N, 1 - 200 / N),
            (255 / N, 1 - 0 / N, 1 - 0 / N),
        ],
        "blue": [
            (0 / N, 1 - 0 / N, 1 - 0 / N),
            (81 / N, 1 - 47 / N, 1 - 47 / N),
            (127.5 / N, 1 - 200 / N, 1 - 200 / N),
            (153 / N, 1 - 255 / N, 1 - 255 / N),
            (255 / N, 1 - 255 / N, 1 - 255 / N),
        ],
    },
}


def load_colormaps() -> None:
    """Registre dels mapes de colors predeterminats a mpl.colormaps."""
    for name, channels in colors.items():
        segmented_cmap = LinearSegmentedColormap(name, channels, N)
        mpl.colormaps.register(cmap=segmented_cmap, force=True)
        mpl.colormaps.register(cmap=segmented_cmap.reversed(), force=True)

    # Assign standard colormaps to aliases
    mpl.colormaps.register(cmap=plt.get_cmap("plasma"), name="Phase", force=True)
    mpl.colormaps.register(cmap=plt.get_cmap("plasma_r"), name="Phase_r", force=True)
    mpl.colormaps.register(cmap=plt.get_cmap("seismic"), name="Iprobe", force=True)
    mpl.colormaps.register(cmap=plt.get_cmap("seismic_r"), name="Iprobe_r", force=True)

    # Sequential
    sequential = [
        "Greys",
        "Purples",
        "Blues",
        "Greens",
        "Oranges",
        "Reds",
    ]

    # Register inverted standard colormaps under their normal names
    for name in sequential:
        cmap = mpl.colormaps[name]
        cmap_r = mpl.colormaps[name].reversed()
        mpl.colormaps.register(cmap=cmap_r, name=name.lower(), force=True)
        mpl.colormaps.register(cmap=cmap, name=f"{name.lower()}_r", force=True)

    # Custom ListedColormap
    grain_cmap = ListedColormap(["black", "tab:orange"], name="Grain")
    mpl.colormaps.register(cmap=grain_cmap, force=True)

    grain_cmap_r = ListedColormap(["tab:orange", "black"], name="Grain_r")
    mpl.colormaps.register(cmap=grain_cmap_r, force=True)
