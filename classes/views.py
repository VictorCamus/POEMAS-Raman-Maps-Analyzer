from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from abc import ABC, abstractmethod
import numpy as np

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
        self._create_objects()

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

    def _create_objects(self):
        pass

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

    def _create_header(self):
        self.header = HeaderMap(self)

    def _create_footer(self):
        self.footer = FooterMap(self)

    def _create_objects(self):
        self.profiles = ProfilePlot(self.objects.profiles, self.axis, self.geometry)

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

    @property
    def units(self):
        return self.header.view.widgets['units'].get()

    def _create_plot(self):
        self.figure, self.axis = base_plot(xtitle = 'λ (nm)', ytitle = 'Intensity (cts)')
        self.figure.subplots_adjust(left=0.2, right=0.95, bottom=0.2, top=0.8)

    def _create_header(self):
        self.header = HeaderSpec(self)

    def _create_footer(self):
        self.footer = FooterSpec(self)

    def _create_objects(self):
        ch = self.channel
        view = self.header.view

        units = view.widgets['units'].get()
        xdata = ch.xdata[units]
        ydata = np.full(xdata.shape, np.nan)

        self.line, = self.axis.plot(xdata, ydata, color="b")
        self.bkgline, = self.axis.plot(xdata, ydata, color="tab:blue")
        self.fitline = {}
        self.axis.set_xlim(view.widgets["left"].get(), view.widgets["right"].get())
        self.axis.set_ylim(bottom=0)

    def _connect(self):
        self.canvas.mpl_connect("key_press_event", lambda e: zoom.copy_figure(self.figure) if e.key == "ctrl+c" else None)

    def plot_pixel(self, px, py):
        self.coords = py, px
        self.axis.set_title(f"X={px + 1} Y={py + 1}", fontsize=16, pad=10)

        self.plot_data()

    def plot_data(self):
        ch = self.channel
        spec = ch.spectra[*self.coords]
        bkg = ch.spec_bkg[*self.coords]
        view = self.header.view

        units = view.widgets['units'].get()
        xdata = ch.xdata[units]

        if view.widgets["bkg"].get(): ydata = spec
        else:
            ydata = spec - bkg
            ydata[ydata < 0] = 0

        self.line.set_ydata(ydata)
        self.bkgline.set_ydata(bkg)

        ytotal = 0
        for fit in self.channel.fits.values():
            for name, peak in fit.peaks.items():
                ydata = peak.func(xdata, *(param[self.coords] for param in peak.params.values()))
                ytotal += ydata
                self.update_peak(name, xdata, ydata)

            if self.header.view.widgets["bkg"].get(): ytotal += bkg
            self.fitline['All'].set_ydata(ytotal)

        top = int(1.1*nanmax(spec))
        self.axis.set_ylim(top = top)
        view.widgets["top"].set(top)

        self.canvas.draw_idle()

    def update_peak(self, name, xdata, ydata):
        if self.header.view.widgets['bkg'].get():
            bkg = self.channel.spec_bkg[*self.coords]
            ydata = ydata + bkg
        else:
            bkg = np.zeros_like(ydata)

        verts = np.column_stack([np.r_[xdata, xdata[::-1]], np.r_[ydata, bkg[::-1]]])
        self.fitline[name].set_verts([verts])
        self.canvas.draw_idle()