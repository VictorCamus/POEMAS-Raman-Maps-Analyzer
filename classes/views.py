from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from abc import ABC, abstractmethod

from classes.objects import ProfilePlot
from classes.interactions import MapInteraction
from drawing import mapdraw
from drawing.plots import base_plot
from process import images as zoom
from window.headers import HeaderMap, HeaderSpec
from window.footers import FooterMap, FooterSpec
from numpy import nanmax

class FigureView(ABC):
    def __init__(self, model, column: int = 0):
        self.model = model

        self._create_plot()
        self._create_header()
        self._create_canvas()
        self._create_footer()

        self._layout(column = column)
        self._connect()

    @property
    def channel(self):
        return self.model.channel

    @property
    def geometry(self):
        return self.model.geometry

    @property
    def objects(self):
        return self.model.objects

    @abstractmethod
    def _create_plot(self):
        ...

    @abstractmethod
    def _create_header(self):
        ...

    def _create_canvas(self):
        self.canvas = FigureCanvasTkAgg(self.figure, self.model.content)

        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.config(bg="#2e2e2e", highlightthickness=0, bd=0)

    @abstractmethod
    def _create_footer(self):
        ...

    def _layout(self, column):
        self.header.frame.grid(row=0, column=column)
        self.header.frame.grid_configure(pady=5)

        self.canvas_widget.grid(row=1, column=column, sticky="nsew")

        self.footer.frame.grid(row=2, column=column)
        self.footer.frame.grid_configure(pady=5)

    @abstractmethod
    def _connect(self):
        ...

class MapView(FigureView):

    def _create_plot(self):
        self.figure, self.axis, self.image, self.cbar = mapdraw.create_map(self.channel.name, self.channel.Z,
                                                                       self.channel.lims, self.channel.units, self.geometry.midaBase)

        self.escala = mapdraw.Escala(self.axis)
        self.profiles = ProfilePlot(self.objects.profiles, self.axis, self.geometry)

    def _create_header(self):
        self.header = HeaderMap(self)

    def _create_footer(self):
        self.footer = FooterMap(self)

    def _connect(self):
        self.zoom = MapInteraction(self)
        self.refresh_geometry()

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

class SpecView(FigureView):

    def _create_plot(self):
        self.figure, self.axis = base_plot(xtitle = 'λ (nm)', ytitle = 'Intensity (cts)')
        self.figure.subplots_adjust(left=0.2, right=0.95, bottom=0.2, top=0.8)

    def _create_header(self):
        self.header = HeaderSpec(self)

    def _create_footer(self):
        self.footer = FooterSpec(self)

    def _connect(self):
        self.canvas.mpl_connect("key_press_event", lambda e: zoom.copy_figure(self.figure) if e.key == "ctrl+c" else None)

    def plot_pixel(self, px, py):
        ch = self.channel
        spec = ch.spectra[py, px]
        view = self.header.view

        if not hasattr(self, 'line'):
            self.line, = self.axis.plot(ch.xdata["nm"], spec, color="b")
            view.widgets_ylim["bottom"].value.set(0)
            self.axis.set_xlim(view.widgets_xlim["left"].value.get(), view.widgets_xlim["right"].value.get())
            self.axis.set_ylim(bottom = 0)
        else:
            self.line.set_ydata(spec)
            top = int(1.1*nanmax(spec))
            self.axis.set_ylim(top = top)
            view.widgets_ylim["top"].value.set(top)

        self.axis.set_title(f"X={px + 1} Y={py+1}", fontsize = 16, pad = 10)
        self.canvas.draw_idle()