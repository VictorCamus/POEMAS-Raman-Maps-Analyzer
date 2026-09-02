from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from abc import ABC, abstractmethod
import numpy as np
from matplotlib.colors import TABLEAU_COLORS
import matplotlib.font_manager

from classes.objects import ProfilePlot
from classes.interactions import MapInteraction
from drawing import mapdraw
from drawing.plots import base_plot
from process import images as zoom
from process.basics import find_nearest
from window.headers import HeaderMap, HeaderSpec
from window.footers import FooterMap, FooterSpec

class FigureView(ABC):
    def __init__(self, model, column: int = 0):
        self.model = model

        self._create_header()
        self._create_plot()
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
                       colLims=ch.color.lims, cbar=self.cbar, mask = self.objects.mask)
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
    def xdata(self):
        return self.channel.spectra.x

    @property
    def bkg(self):
        spec = self.channel.spectra
        fit_key = self.header.view.fit_key

        bkg = spec.bkg.copy()

        if fit_key != 'rawdata':
            fit = spec.fits[fit_key]
            xfit = spec.x[fit.xrange]

            for i, (name, peak) in enumerate(fit.peaks.items()):
                if peak.bkg: bkg[fit.xrange] += peak.func(xfit, *(param[spec.coords] for param in peak.params.values()))

        return bkg

    def _create_plot(self):
        self.xlabels = {'nm': 'λ (nm)', 'eV': 'E (eV)', '1/cm': r'Raman Shift (cm⁻¹)'}

        self.figure, self.axis = base_plot(xtitle = self.xlabels[self.channel.spectra.units], ytitle = 'Intensity (cts)')
        self.figure.subplots_adjust(left=0.2, right=0.95, bottom=0.2, top=0.8)

    def _create_header(self):
        self.header = HeaderSpec(self)

    def _create_footer(self):
        self.footer = FooterSpec(self)

    def _create_objects(self):
        spec = self.channel.spectra

        self.line, = self.axis.plot(spec.x, spec.y, color="b")
        self.bkgline, = self.axis.plot(spec.x, spec.bkg, color="tab:blue")
        self.fitline = dict()
        self.etiquette = dict()

        self.axis.set_title(f"X={spec.coords[1] + 1} Y={spec.coords[0] + 1}", fontsize=20, pad=10, fontname = 'Consolas')
        self.axis.set_xlim(spec.lims)
        self.axis.set_ylim(bottom=0)

        self.header.view.fit = 'rawdata'

    def _connect(self):
        self.canvas.mpl_connect("key_press_event", lambda e: zoom.copy_figure(self.figure) if e.key == "ctrl+c" else None)

    def plot_pixel(self, px, py):
        self.channel.spectra.coords = py, px
        self.axis.set_title(f"X={px + 1} Y={py + 1}", fontsize=16, pad=10)

        self.plot_data()

    def plot_data(self):
        colors = list(TABLEAU_COLORS.values())
        spec = self.channel.spectra
        view = self.header.view
        bkg_on = view.widgets['bkg'].get()

        if bkg_on: ydata = spec.y
        else:
            ydata = spec.y - self.bkg
            ydata[ydata < 0] = 0

        ytotal = 0
        fit_key = self.header.view.fit_key

        for fitplot in self.fitline.values(): fitplot.remove()
        for etiq in self.etiquette.values(): etiq.remove()

        self.fitline = dict()
        self.etiquette = dict()

        if fit_key != 'rawdata':
            fit = spec.fits[fit_key]
            xfit = spec.x[fit.xrange]
            bkg = self.bkg[fit.xrange]

            for i, (name, peak) in enumerate(fit.peaks.items()):
                if not peak.bkg:
                    yfit = peak.func(xfit, *(param[spec.coords] for param in peak.params.values()))
                    ytotal += yfit

                    if 'x0' in peak.params:
                        x0 = peak.params['x0'][spec.coords]
                        idx = find_nearest(xfit, x0)

                        ycoord = peak.params['A'][spec.coords] + bkg[idx] if bkg_on else peak.params['A'][spec.coords]
                        self.etiquette[name] = self.axis.annotate(f'{peak.name}\n{x0:.2f}',
                                                xy=(x0, ycoord),
                                                xytext=(0, 10), textcoords='offset points', ha='center', color='k',
                                                fontweight = 'bold', family='Consolas', fontsize = 14)

                    for etiq in self.etiquette.values(): etiq.set_visible(self.header.view.widgets['etiq'].get())

                    if self.header.view.widgets['bkg'].get():
                        yfit += bkg
                        self.fitline[name] = self.axis.fill_between(xfit, yfit, bkg, color=colors[i + 1], alpha=0.6)
                    else: self.fitline[name] = self.axis.fill_between(xfit, yfit, 0, color=colors[i + 1], alpha=0.6)

            if self.header.view.widgets['bkg'].get(): ytotal += bkg
            self.fitline['All'], = self.axis.plot(xfit, ytotal, color = 'k')

        self.line.set_ydata(ydata)
        self.bkgline.set_ydata(self.bkg)

        top = int(1.25*np.nanmax(ydata[spec.xrange]))
        self.axis.set_ylim(top = top)
        view.widgets["top"].set(top)

        self.canvas.draw_idle()