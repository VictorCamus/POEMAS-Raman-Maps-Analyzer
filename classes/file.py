from dataclasses import dataclass, field
from typing import Dict, Tuple
from tkinter.ttk import Notebook, Frame

from window.labels import create_tab
from process.converter import coords_to_pixel
from classes.channel import ChannelData
from classes.views import MapView, SpecView
from classes.objects import ObjectData

@dataclass 
class FileData: # Crea pestanyes per a cada fitxer o mapa o canal.
    channel: Dict[str, ChannelData]
    geometry: Geometry
    objects: ObjectData = None
    laser: float = None

    def __post_init__(self):
        self.current_channel = next(iter(self.channel.values()))

class FileView:
    def __init__(self, notebook, controller):
        self.controller = controller
        self.tab = create_tab(notebook, self.controller.name)
        self.tab.columnconfigure(0, weight=1)
        self.tab.rowconfigure(1, weight=1)

        self.selector = Notebook(self.tab)
        self.selector.grid(row=0, column=0, sticky="ew")

        for name, ch in self.controller.channel.items(): ch.tab = create_tab(self.selector, name)

        self.content = Frame(self.tab)
        self.content.grid(row=1, column=0, sticky="nsew")

        # Dues columnes: mapa i espectre
        self.content.rowconfigure(0, weight=0)
        self.content.rowconfigure(1, weight=1)
        self.content.rowconfigure(2, weight=0)

        self.content.columnconfigure(0, weight=1)

        self.map = MapView(self, column = 0)

        if any(ch.spectra is not None for ch in self.controller.channel.values()):
            self.content.columnconfigure(1, weight=1)
            self.map.figure.subplots_adjust(right=0.85)
            self.spectrum = SpecView(self, column = 1)

        self.selector.bind("<<NotebookTabChanged>>", self._on_channel_changed)

    @property
    def channel(self):
        return self.controller.current_channel

    @property
    def geometry(self):
        return self.controller.geometry

    @property
    def objects(self):
        return self.controller.objects

    def _on_channel_changed(self, event):
        notebook = event.widget
        tab = notebook.select()

        if not tab: return

        name = notebook.tab(tab, "text")

        self.controller.current_channel = self.controller.channel[name]
        self.map.update_channel()

@dataclass
class Geometry:
    N: Tuple[int, int]
    midaBase: Tuple[float, float]
    rotation: int = field(default=0, repr=False)  # intern
    flip: bool = field(default=False, repr=False)

    xlims: tuple[float, float] = None
    ylims: tuple[float, float] = None

    def __post_init__(self):
        if self.xlims is None or self.ylims is None: self.reset_zoom()

    def reset_zoom(self):
        self.xlims = (0, self.midaBase[0])
        self.ylims = (0, self.midaBase[1])

    @property
    def xylims(self):
        return self.xlims, self.ylims

    @xylims.setter
    def xylims(self, value):
        self.xlims, self.ylims = value

    @property
    def mida(self):
        return (self.xlims[1] - self.xlims[0], self.ylims[1] - self.ylims[0])

    @property
    def rect(self):
        return self.mida[1] / self.mida[0]

    def rotate(self, rotation, flip):
        Lx, Ly = self.midaBase
        xlims, ylims = self.xylims

        match rotation:
            case 0: xnew, ynew = xlims, ylims
            case 1: xnew, ynew = ylims, (Ly - xlims[1], Ly - xlims[0])
            case 2: xnew, ynew = (Lx - xlims[1], Lx - xlims[0]), (Ly - ylims[1], Ly - ylims[0])
            case 3: xnew, ynew = (Lx - ylims[1], Lx - ylims[0]), xlims

        if flip: xnew = (Lx - xnew[1], Lx - xnew[0])

        self.xylims = xnew, ynew

    def limit_pixels(self):
        coords = [(self.xlims[0], self.ylims[0]), (self.xlims[1], self.ylims[1])]
        coord0, coord1 = coords_to_pixel(coords, self.N, self.midaBase)
        x0, y0 = coord0; x1, y1 = coord1

        return x0, x1, y0, y1