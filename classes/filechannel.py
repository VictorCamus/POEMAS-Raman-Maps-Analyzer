from dataclasses import dataclass, field
from typing import Dict, Tuple
from tkinter.ttk import Frame
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from process import images as zoom
from drawing import mapdraw as map
from window.gestor_capçalera import GestorCapçalera
import classes.diccionaris as dicc

@dataclass 
class FileData: # Crea pestanyes per a cada fitxer o mapa o canal.
    frame: object
    notebook: object
    folder: str
    name: str
    channel: Dict[str, "ChannelData"]
    N: Tuple[int]
    _midaBase: Tuple[float, float]
    rotation: int = field(default=0, repr=False)  # intern
    
    def __post_init__(self):
        # 1. Crea les pestanyes per a cada canal del fitxer.
        for chKey, ch in self.channel.items():
            ch.frame = Frame(self.notebook)
            self.notebook.add(ch.frame, text=chKey)

        self.notebook.grid(row=0, column=0, sticky='ew')
        self.current_channel = next(iter(self.channel.values()))

        # 2. Configuració inicial del mapa
        ch = self.current_channel
        self.figure, self.axis, self.image, self.cbar = map.create_map(ch.tipus, ch.Z, ch.lims, ch.dades.units, self.midaBase, interp = ch.dades.interp)
        self.escala = map.Escala(self.axis)
        
        # 3. Crea la capçalera amb les dades del fitxer.
        self.capçalera = GestorCapçalera(self)
        
        # 4. Canvas Tkinter
        self.connect_interaction()

    def connect_interaction(self):
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.frame)
        canvas_widget = self.canvas.get_tk_widget()

        canvas_widget.grid(row=2, column=0, sticky='nsew')
        canvas_widget.config(bg='#2e2e2e', highlightthickness=0, bd=0)

        self.frame.rowconfigure(2, weight=1)
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
        
        map.update_map(self.image, ch.color.cmap, ch.Z, ch.lims, ch.dades.units, mida = self.midaBase, colLims = ch.color.lims, cbar = self.cbar, interp = ch.dades.interp)
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
        x0 = int(self.zoom.xlims[0]/self.midaBase[0]*self.N[0])
        x1 = int(self.zoom.xlims[1]/self.midaBase[0]*self.N[0])
        y0 = int(self.zoom.ylims[0]/self.midaBase[1]*self.N[1])
        y1 = int(self.zoom.ylims[1]/self.midaBase[1]*self.N[1])
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
class ChannelData:  # Crea canals per a cada tipus de mapa dins d'un fitxer.
    tipus: str
    name: str
    Z: object
    lims: list[float] = None
    mult: bool = False
    
    def __post_init__(self):
        self.dades = dicc.map_info(self.tipus)
        self.color = dicc.color_info(self.tipus)
        
        if self.mult: self.Z *= self.dades.mult
        if self.lims is None: self.lims, self.Z = dicc.lims(self.Z, self.tipus)