from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from typing import Tuple

from process.converter import coords_to_pixel
from classes.object import ProfileView
from drawing import mapdraw
from process import images as zoom
from window.headers import GestorHeaderAFM
from window.footers import GestorFooterAFM

class MapView:
    def __init__(self, model):
        self.model = model

        self.figure, self.axis, self.image, self.cbar = mapdraw.create_map(self.channel.name, self.channel.Z,
                                                                       self.channel.lims, self.channel.units, self.geometry.midaBase)

        self.escala = mapdraw.Escala(self.axis)

        self.header = GestorHeaderAFM(self)
        self.canvas = FigureCanvasTkAgg(self.figure, self.model.content)
        widget = self.canvas.get_tk_widget()
        widget.config(bg="#2e2e2e", highlightthickness=0, bd=0)
        self.footer = GestorFooterAFM(self)

        self.zoom = MapInteraction(self)

        self.header.view.frame.grid(row=0, column=0)
        self.header.view.frame.grid_configure(pady=5)
        widget.grid(row=1, column=0, sticky="nsew")
        self.footer.view.frame.grid(row=2, column=0)
        self.footer.view.frame.grid_configure(pady=5)

        self.profiles = ProfileView(self.objects.profiles, self.axis, self.geometry)
        self.refresh_geometry()

    @property
    def channel(self):
        return self.model.channel

    @property
    def geometry(self):
        return self.model.geometry

    @property
    def objects(self):
        return self.model.objects

    def update_channel(self, event=None):
        self.header.set_channel(self.channel)
        self.refresh_map(self.channel)

    def refresh_map(self, ch=None):
        if not ch: ch = self.channel

        mapdraw.update_map(self.image, ch.color.cmap, ch.Z, ch.lims, ch.units, mida=self.geometry.midaBase,
                       colLims=ch.color.lims, cbar=self.cbar)
        self.escala.color = ch.color.scale
        self.image.set_clim(*ch.lims)
        self.canvas.draw_idle()

    def refresh_geometry(self):
        self.axis.set_xlim(self.geometry.xlims)
        self.axis.set_ylim(self.geometry.ylims)
        self.escala.actualitza(*self.geometry.xylims)

        self.canvas.draw_idle()

class MapInteraction:
    def __init__(self, map_view):
        self.map = map_view
        self.geometry = map_view.geometry

        self.press = None

        self.map.canvas.mpl_connect('scroll_event', self._scroll)
        self.map.canvas.mpl_connect('button_press_event', self._press)
        self.map.canvas.mpl_connect('button_release_event', self._release)
        self.map.canvas.mpl_connect('motion_notify_event', self._motion)

        self.map.canvas.mpl_connect("key_press_event", lambda e: zoom.copy_figure(self.map.figure) if e.key == "ctrl+c" else None)
        self.map.canvas.mpl_connect("key_press_event", lambda e: self.base_size() if e.key == "ctrl+z" else None)

    def _scroll(self, event):
        if not event.inaxes: return
        self.geometry.xylims = zoom.zoom(event, self.geometry.xylims, self.geometry.midaBase)
        self.map.refresh_geometry()

    def _press(self, event):
        if event.inaxes != self.map.axis: return
        self.press = event.xdata, event.ydata

        if event.xdata==None or event.ydata==None: return
        if not hasattr(self.map.model, "spectrum"): return

        pixels = coords_to_pixel([(event.xdata, event.ydata)], self.geometry.N, self.geometry.midaBase)[0]
        self.map.model.spectrum.plot_pixel(*pixels)

    def _release(self, event):
        self.press = None

    def _motion(self, event):
        if event.inaxes != self.map.axis or not self.press: return
        self.geometry.xylims = zoom.on_motion(event, self.geometry.xylims, self.geometry.midaBase, self.press)
        self.map.refresh_geometry()

    def resize(self, event=None):
        self.dimensions = mapdraw.get_dimensions(self.map.axis, self.geometry.rect)

    def base_size(self):
        self.geometry.reset_zoom()
        self.map.refresh_geometry()
        self.resize()

    @property
    def dimensions(self):
        return self._dimensions

    @dimensions.setter
    def dimensions(self, value: Tuple[float]):
        self._dimensions = value
        mapdraw.set_dimensions(self.map.canvas, self.map.escala, self.map.cbar, self.map.geometry.rect, *value)