from dataclasses import dataclass, field
from typing import Dict, Tuple
from tkinter.ttk import Frame, Notebook
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

from drawing import mapdraw as map
from window.headers import GestorHeaderAFM
from window.footers import GestorFooterAFM
from window.labels import create_frame
from drawing.arrows import FletxaEstatica
from process import images as zoom
from process.converter import pixel_to_coords, coords_to_pixel
from classes.channel import ChannelData

@dataclass 
class FileData: # Crea pestanyes per a cada fitxer o mapa o canal.
    channel: Dict[str, ChannelData]
    N: Tuple[int, int]
    _midaBase: Tuple[float, float]
    rotation: int = field(default=0, repr=False)  # intern
    flip: bool = False
    laser: float = None
    profile: Dict[int, ProfileData] = None

    def create_gui(self, name, folder, notebook):
        self.name = name
        self.folder = folder
        self.frame = create_frame(notebook, self.name)
        self.notebook = Notebook(self.frame)

        # 1. Crea les pestanyes per a cada canal del fitxer.
        for chKey, ch in self.channel.items():
            ch.frame = Frame(self.notebook)
            self.notebook.add(ch.frame, text=chKey)

        self.notebook.grid(row=1, column=0, sticky='ew')
        self.current_channel = next(iter(self.channel.values()))

        # 2. Configuració inicial del mapa
        ch = self.current_channel
        self.figure, self.axis, self.image, self.cbar = map.create_map(ch.name, ch.Z, ch.lims, ch.units, self.midaBase)
        self.escala = map.Escala(self.axis)

        # 3. Canvas Tkinter + Interaccions
        self.connect_interaction()

        if self.profile is not None:
            for num, prof in enumerate(self.profile.values()): prof.create_arrow(num, self.axis, self.midaBase)

        # 4. Crea la capçalera i el peu de figura amb les dades del fitxer.
        self.capçalera = GestorHeaderAFM(self)
        self.peu = GestorFooterAFM(self)

    def connect_interaction(self):
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.frame)
        canvas_widget = self.canvas.get_tk_widget()

        canvas_widget.grid(row=3, column=0, sticky='nsew')
        canvas_widget.config(bg='#2e2e2e', highlightthickness=0, bd=0)

        self.frame.rowconfigure(3, weight=1)
        self.frame.columnconfigure(0, weight=1)
        
        self.zoom = InteraccioFigura(self.axis, self.image, self.escala, self.cbar, self.midaBase)

        self.notebook.bind("<<NotebookTabChanged>>", self._on_channel_changed)

    def _on_channel_changed(self, event):
        notebook = event.widget
        tab_id = notebook.select()
        if not tab_id: return
        channel = self.channel[notebook.tab(tab_id, "text")]
        self.current_channel = channel
        self.image.set_cmap(channel.color.cmap)
        
        self.cbar.limInf.set_color(channel.color.limInf)
        self.cbar.limSup.set_color(channel.color.limSup)
        
        self.capçalera.set_channel(self.current_channel)
        self.redraw()

    def redraw(self, ch = None):
        if not ch: ch = self.current_channel
        
        map.update_map(self.image, ch.color.cmap, ch.Z, ch.lims, ch.units, mida = self.midaBase, colLims = ch.color.lims, cbar = self.cbar)
        self.escala.color = ch.color.scale
        self.image.set_clim(*ch.lims)
        self.canvas.draw_idle()

    @property
    def rot(self):
        return self.rotation

    @rot.setter
    def rot(self, value):
        self.rotation = value % 4
    
    @property
    def midaBase(self):
        return self._midaBase
    
    @midaBase.setter
    def midaBase(self, value):
        self._midaBase = value
        self.zoom.midaBase = value

    @property
    def limit_pixels(self):
        coord0, coord1 = coords_to_pixel((self.zoom.xlims, self.zoom.ylims), self.N, self.midaBase)
        x0, y0 = coord0; x1, y1 = coord1

        return x0, x1, y0, y1

class InteraccioFigura:
    def __init__(self, axis, image, escala, cbar, mida):
        self.axis = axis
        self.image = image
        self.escala = escala
        self.cbar = cbar
        self.midaBase = mida

        self.figure = axis.figure
        self.canvas = axis.figure.canvas
        self.press = None
        
        self.canvas.mpl_connect('scroll_event', self._scroll)
        self.canvas.mpl_connect('button_press_event', self._press)
        self.canvas.mpl_connect('button_release_event', self._release)
        self.canvas.mpl_connect('motion_notify_event', self._motion)
        
        self.canvas.mpl_connect("key_press_event", lambda e: zoom.copy_figure(self.axis.figure) if e.key == "ctrl+c" else None)
        self.canvas.mpl_connect("key_press_event", lambda e: self._base_size() if e.key == "ctrl+z" else None)
        
    def _scroll(self, event):
        if not event.inaxes: return
        self.xylims = zoom.zoom(event, self.xylims, self.midaBase)
    
    def _press(self, event):
        if event.inaxes != self.axis: return
        self.press = event.xdata, event.ydata
    
    def _release(self, event):
        self.press = None
    
    def _motion(self, event):
        if event.inaxes != self.axis or not self.press: return
        self.xylims = zoom.on_motion(event, self.xylims, self.midaBase, self.press)
                
    def _resize(self, event = None):
        self.dimensions = map.get_dimensions(self.axis, self.rect)

    def _base_size(self, event = None):
        self.xylims = ((0, self.midaBase[0]), (0, self.midaBase[1]))
    
    @property
    def xlims(self):
        return self.axis.get_xlim()
                
    @xlims.setter
    def xlims(self, value: Tuple[float, float]):
        self.xylims = (value, self.axis.get_ylim())
        map.set_dimensions(self.canvas, self.escala, self.cbar, self.rect, *self.dimensions)

    @property
    def ylims(self):
        return self.axis.get_ylim()
    
    @ylims.setter
    def ylims(self, value: Tuple[float, float]):
        self.xylims = (self.axis.get_xlim(), value)
        map.set_dimensions(self.canvas, self.escala, self.cbar, self.rect, *self.dimensions)

    @property
    def xylims(self):
        return self.axis.get_xlim(), self.axis.get_ylim()

    @xylims.setter
    def xylims(self, value):
        xlims, ylims = value
        self.axis.set_xlim(xlims)
        self.axis.set_ylim(ylims)
        self.escala.actualitza(xlims, ylims)

        self.canvas.draw_idle()
    
    @property
    def mida(self):
        return (self.xlims[1] - self.xlims[0], self.ylims[1] - self.ylims[0])
    
    @property
    def rect(self):
        return self.mida[1]/self.mida[0]
    
    @property
    def dimensions(self):
        return self._dimensions

    @dimensions.setter
    def dimensions(self, value: Tuple[float]):
        self._dimensions = value
        map.set_dimensions(self.canvas, self.escala, self.cbar, self.rect, *value)

@dataclass
class ProfileData:
    line: list = None
    length: float = None

    def __post_init__(self):
        self.color = ['r', 'b', 'g', 'orange', 'y', 'cyan', 'pink', 'k']

    @property
    def lims(self):
        return self.line[0], self.line[-1]

    def create_arrow(self, num, ax, N, mida):
        start, end = pixel_to_coords(self.lims, N, mida)
        self.arrow = FletxaEstatica(ax, start, end, mida, num + 1, self.color[num % 8])

    def rotate(self, N, mida, rot, flip):
        self.line = self.rotate_object(self.line, N, rot, flip)

        self.arrow.elimina()
        self.arrow.start, self.arrow.end = pixel_to_coords(self.lims, N, mida)
        self.arrow.dibuixa()

    def plot(self, num, ax, data):
        coords = np.asarray(self.line)
        x_vals = coords[:, 0]
        y_vals = coords[:, 1]

        dades = data[y_vals, x_vals]
        zmin, zmax = dades.min(), dades.max()
        diff = (zmax - zmin) / 15
        punts = np.linspace(0, self.length, len(dades))

        profile, = ax.plot(punts, dades, color=self.color[num % 8])
        ax.set_xlim(0, self.length)
        ylims = (round(zmin - diff, 0), round(zmax + diff, 0))
        ax.set_ylim(*ylims)

        return punts, dades, profile

    @staticmethod
    def rotate_object(points, N, rotation, flip):
        Nx, Ny = N
        transformed = []

        for x, y in points:
            match rotation:
                case 0: pass
                case 1: x, y = y, Ny - 1 - x
                case 2: x, y = Nx - 1 - x, Ny - 1 - y
                case 3: x, y = Nx - 1 - y, x

            if flip: x = Nx - 1 - x

            transformed.append((x, y))

        return transformed