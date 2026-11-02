"""Objectes visuals de l'aplicació."""

from __future__ import annotations

from abc import ABC, abstractmethod
from tkinter import Event, ttk
from typing import TYPE_CHECKING, Self, cast

import numpy as np

from classes.interactions import MapInteraction
from drawing import mapdraw
from drawing.arrows import FletxaBase
from drawing.plots import base_plot, create_canvas, get_verts
from process import images as zoom
from process.basics import find_nearest
from process.converter import pixel_to_coords
from window.footers import FooterMap, FooterSpec
from window.headers import HeaderMap, HeaderSpec

if TYPE_CHECKING:
    from pathlib import Path
    from tkinter import Misc

    from matplotlib.axes import Axes
    from matplotlib.collections import FillBetweenPolyCollection
    from matplotlib.colorbar import Colorbar
    from matplotlib.figure import Figure
    from matplotlib.image import AxesImage
    from matplotlib.lines import Line2D
    from matplotlib.text import Annotation, Text
    from numpy.typing import NDArray

    from classes.data import ChannelData, FileData, GeometryData, ObjectData, PeakData, ProfileData, SpecData
    from classes.protocols import InfSup, NotebookProtocol, SpecUnits, TkCanvasProtocol
    from window.footers import Footer
    from window.headers import Header


class FileView:
    """Controla les operacions i interaccions visuals d'un fitxer."""

    def __init__(self, data: FileData, name: str, folder: Path, notebook: NotebookProtocol) -> None:
        """Afig els objectes visuals a un fitxer de dades.

        Parameters
        ----------
        data: FileData
            Dades del fitxer
        name: str
            Nom del fitxer
        folder: Path:
            Drecera on es troba el fitxer
        notebook: NotebookProtocol
            Requadre de l'aplicació principal al que s'associen la resta d'objectes visuals del fitxer

        """
        self.data = data
        self.name = name
        self.folder = folder

        self.current_channel = next(iter(self.data.channel.values()))
        self.tab = create_tab(notebook, name)
        self.tab.columnconfigure(0, weight=1)
        self.tab.rowconfigure(1, weight=1)

        self.notebook: NotebookProtocol = cast("NotebookProtocol", ttk.Notebook(self.tab))
        self.notebook.grid(row=0, column=0, sticky="ew")

        self.channel_tabs = {name: create_tab(self.notebook, name) for name in self.data.channel}

        self.content = ttk.Frame(self.tab)
        self.content.grid(row=1, column=0, sticky="nsew")

        # Dues columnes: mapa i espectre
        self.content.rowconfigure(0, weight=0)
        self.content.rowconfigure(1, weight=1)
        self.content.rowconfigure(2, weight=0)

        self.content.columnconfigure(0, weight=1)

        self.mapview = MapView(self, column=0)

        # Crea una finestra d'espectra només si hi existeixen dades.
        if any(ch.spectra is not None for ch in self.data.channel.values()):
            self.content.columnconfigure(1, weight=1)
            self.mapview.figure.subplots_adjust(right=0.85)
            self.specview = SpecView(self, column=1)

        self.notebook.bind("<<NotebookTabChanged>>", self._on_channel_changed)

    @property
    def geometry(self) -> GeometryData:
        """Retorna la geometria del fitxer."""
        return self.data.geometry

    @property
    def objects(self) -> ObjectData:
        """Retorna els objectes del fitxer."""
        return self.data.objects

    @property
    def channel(self) -> dict[str, ChannelData]:
        """Retorna el diccionari de canals del fitxer."""
        return self.data.channel

    def _on_channel_changed(self, event: Event) -> None:
        notebook = cast("NotebookProtocol", event.widget)
        tab_id = notebook.select()

        if not tab_id:
            return

        name = notebook.tab(tab_id, "text")

        self.current_channel = self.data.channel[name]
        self.mapview.update_channel(self.current_channel)


class FigureView(ABC):
    """Classe base que controla i crea les figures del fitxer."""

    figure: Figure
    axis: Axes
    canvas: TkCanvasProtocol
    header: Header[Self]
    footer: Footer[Self]

    def __init__(self, file: FileView, column: int = 0) -> None:
        """Crea els objectes de la figura i connecta les interaccions possibles.

        Parameters
        ----------
        file: FileView
            Objecte visual del fitxer
        column: int = 0
            Columna on se situarà el requadre de la classe.

        """
        self.file: FileView = file

        self._create_header()
        self._create_plot()
        self._create_canvas()
        self._create_footer()
        self._create_objects()

        self._layout(column=column)
        self._connect()

    @property
    def channel(self) -> ChannelData:
        """Retorna el canal actual mostrat en pantalla."""
        return self.file.current_channel

    @abstractmethod
    def _create_plot(self) -> None:
        """Crea la figura i els eixos de la classe."""

    @abstractmethod
    def _create_header(self) -> None:
        """Crea la capçalera de la classe."""

    def _create_canvas(self) -> None:
        """Connecta la figura al requadre visual de la classe."""
        self.canvas = create_canvas(self.figure, self.file.content)
        self.canvas.get_tk_widget().configure({"bg": "#2e2e2e", "highlightthickness": 0, "bd": 0})

    @abstractmethod
    def _create_footer(self) -> None:
        """Crea el peu de figura de la classe."""

    @abstractmethod
    def _create_objects(self) -> None:
        """Crea la resta d'objectes visuals corresponents a la figura."""

    def _layout(self, column: int) -> None:
        """Disposa els objectes de la classe en un ordre determinat.

        Fila 0: Capçalera
        Fila 1: Canvas de la figura
        Fila 2: Peu de figura

        Parameters
        ----------
        column: int
            Columna on es coloca la classe sobre el requadre de l'aplicació

        """
        self.header.grid(row=0, column=column, pady=5)
        self.header.columnconfigure(0, weight=1)

        self.canvas.get_tk_widget().grid(row=1, column=column, sticky="nsew")

        self.footer.grid(row=2, column=column, pady=5)
        self.footer.columnconfigure(0, weight=1)

    @abstractmethod
    def _connect(self) -> None:
        """Connecta les interaccions corresponents de la figura."""


class MapView(FigureView):
    """Objecte que crea i controla la vista del mapa que mostra les matrius de dades del fitxer."""

    header: HeaderMap
    footer: FooterMap

    image: AxesImage
    cbar: Colorbar
    cbar_lims: dict[InfSup, Text]
    binds: MapInteraction
    scale: mapdraw.Scale
    profiles: ProfileView

    def _create_plot(self) -> None:
        ch = self.channel
        self.figure, self.axis, self.image, self.cbar, self.cbar_lims =\
        mapdraw.create_map(data=ch.data, lims=ch.lims, cmap=ch.color.cmap, units=ch.units,
                           cbar_colors=ch.color.lims, size=self.file.geometry.base_size)

        self.scale = mapdraw.Scale(self.axis)

    def _create_header(self) -> None:
        self.header = HeaderMap(self)

    def _create_footer(self) -> None:
        self.footer = FooterMap(self)

    def _create_objects(self) -> None:
        self.profiles = ProfileView(self.file.objects.profiles, self.axis, self.file.geometry)

    def _connect(self) -> None:
        self.binds = MapInteraction(self)
        self.refresh_geometry()

    def update_channel(self, channel: ChannelData) -> None:
        """Actualitza la capçalera i el mapa quan es canvia de canal.

        Parameters
        ----------
        channel: ChannelData
            Canal triat

        """
        self.header.set_channel(channel)
        self.refresh_map(channel)

    def redraw(self, *, cmap: bool = False, lims: bool = False, scale: bool = False) -> None:
        """Modifica les propietats del mapa seleccionades i canvia els elements de la capçalera modificats.

        Parameters
        ----------
        cmap: bool = False
            Canvi del color del mapa
        lims: bool = False
            Canvi dels límits de la barra de colors
        scale: bool = False
            Canvi del color de l'escala

        """
        ch = self.channel

        if cmap:
            self.image.set_cmap(ch.color.cmap)
            self.cbar_lims["inf"].set_color(ch.color.lim_inf)
            self.cbar_lims["sup"].set_color(ch.color.lim_sup)

        if lims:
            self.image.set_clim(*ch.lims)
            self.cbar_lims["inf"].set_text(f"{ch.lims[0]:g}" + (f" {ch.units}" if ch.units else ""))
            self.cbar_lims["sup"].set_text(f"{ch.lims[1]:g}" + (f" {ch.units}" if ch.units else ""))

        if scale:
            self.scale.color = self.channel.color.scale

        self.canvas.draw_idle()

    def refresh_map(self, ch: ChannelData | None = None) -> None:
        """Actualitza les dades del mapa i les propietats visuals assignades pel canal.

        Parameters
        ----------
        ch: ChannelData | None = None
            Canal triat. Si és None, agafa el canal actual.

        """
        if ch is None:
            ch = self.channel

        mapdraw.update_map(
            image=self.image,
            data=ch.data,
            lims=ch.lims,
            cmap=ch.color.cmap,
            units=ch.units,
            cbar=self.cbar,
            cbar_lims=self.cbar_lims,
            cbar_colors=ch.color.lims,
            size=self.file.geometry.base_size,
            mask=self.file.objects.mask,
        )
        self.scale.color = ch.color.scale
        self.image.set_clim(*ch.lims)

        self.header.widgets["lim_sup"].set(ch.lims[1])
        self.header.widgets["lim_inf"].set(ch.lims[0])
        self.header.widgets["cmap_c"].set(ch.color.cmap_c)

        self.canvas.draw_idle()

    def refresh_geometry(self) -> None:
        """Actualitza la geometria del mapa relacionada amb els límits del requadre i la mida de l'escala."""
        self.axis.set_xlim(self.file.geometry.xlims)
        self.axis.set_ylim(self.file.geometry.ylims)
        self.scale.update(*self.file.geometry.xylims)

        self.canvas.draw_idle()

    def resize(self) -> None:
        """Recalcula les dimensions del requadre del mapa quan es redimensiona la finestra de l'aplicació."""
        dimensions = mapdraw.get_dimensions(self.axis, self.file.geometry.rect)
        mapdraw.set_dimensions(self.canvas, self.scale, self.cbar, self.cbar_lims,
                               self.file.geometry.rect, *dimensions)

    def base_size(self) -> None:
        """Redibuixa el mapa amb la geometria base del fitxer."""
        self.file.geometry.reset_zoom()
        self.refresh_geometry()
        self.resize()


class SpecView(FigureView):
    """Objecte que crea i controla la vista dels espectres associats a la matriu de dades d'un fitxer espectral."""

    header: HeaderSpec
    footer: FooterSpec

    xlabels: dict[SpecUnits, str]
    line: Line2D
    bkg_line: Line2D
    fit_line: Line2D
    fit_peaks: dict[str, PeakView]

    @property
    def spectra(self) -> SpecData:
        """Retorna les dades espectral del canal actual, si existeix."""
        return self.channel.spec

    @property
    def xdata(self) -> NDArray[np.float32]:
        """Retorna el rang de dades de l'espectre seleccionat actualment."""
        return self.spectra.x

    @property
    def bkg(self) -> NDArray[np.float32]:
        """Retorna el fons de les dades o de l'ajust actual."""
        fit_key = self.header.fit_key

        if fit_key != "rawdata":
            fit = self.spectra.fits[fit_key]
            xfit = self.spectra.x[fit.xrange]
            bkg = fit.bkg(self.spectra.coords, len(self.spectra.y))

            for peak in fit.peaks.values():
                if peak.func.is_bkg:
                    params = [param[self.spectra.coords] for param in peak.params.values()]

                    if not any(np.isnan(param) for param in params):
                        bkg[fit.xrange] += peak.ydata(xfit, self.spectra.coords)

        else:
            bkg = self.spectra.bkg.copy()

        return bkg

    def _create_plot(self) -> None:
        self.xlabels = {"nm": "λ (nm)", "eV": "E (eV)", "1/cm": r"Raman Shift (cm⁻¹)"}

        self.figure, self.axis = base_plot(xtitle=self.xlabels[self.channel.spec.units], ytitle="Intensity (a.u.)")
        self.figure.subplots_adjust(left=0.2, right=0.95, bottom=0.2, top=0.8)

    def _create_header(self) -> None:
        self.header = HeaderSpec(self)

    def _create_footer(self) -> None:
        self.footer = FooterSpec(self)

    def _create_objects(self) -> None:
        spec = self.channel.spec

        self.line, = self.axis.plot(spec.x, spec.y, color="b")
        self.bkg_line, = self.axis.plot(spec.x, spec.bkg, color="tab:blue")
        self.bkg_line.set_visible(spec.bkg_active)

        self.fit_line, = self.axis.plot([], [], color="k")
        self.fit_peaks = {}

        self.axis.set_title(f"X={spec.coords[1] + 1} Y={spec.coords[0] + 1}", fontsize=20, pad=10, fontname="Consolas")
        self.axis.set_xlim(*spec.lims)
        self.axis.set_ylim(bottom=0)

        self.header.fit = "rawdata"

    def _connect(self) -> None:
        self.canvas.mpl_connect("key_press_event", lambda e: zoom.copy_figure(self.figure)
                                if e.key == "ctrl+c" else None)

    def plot_pixel(self, px: int, py: int) -> None:
        """Mostra l'espectre del píxel corresponent.

        px: int
            Coordenada x sobre el mapa del píxel.
        py: int
            Coordenada y sobre el mapa del píxel

        """
        self.channel.spec.coords = py, px
        self.axis.set_title(f"X={px + 1} Y={py + 1}", fontsize=16, pad=10)

        self.plot_data()

    def get_label_coords(self, peak: PeakData, xdata: NDArray[np.float32]) -> tuple[float, float]:
        """Calcula les coordenades on es dibuixarà l'etiqueta del pic corresponent.

        Parameters
        ----------
        peak: PeakData
            Dades del pic
        xdata: NDArray[np.float32]
            Rang de dades de l'espectre triat

        Returns
        -------
        x0, y0: tuple[float, float]
            Coordenades del text

        """
        coords = self.spectra.coords
        x0 = peak.params["x0"][coords]
        idx, = find_nearest(xdata, x0)
        y0 = (peak.params["amp"][coords] + self.bkg[idx] if self.spectra.bkg_active else peak.params["amp"][coords])

        return float(x0), float(y0)

    def plot_data(self) -> None:
        """Dibuixa l'espectre i els ajusts existents que conté."""
        spec = self.channel.spec

        if spec.bkg_active:
            ydata = spec.y
        else:
            ydata = spec.y - self.bkg
            ydata[ydata < 0] = 0

        fit_key = self.header.fit_key

        if fit_key != "rawdata":
            fit = spec.fits[fit_key]
            xfit = self.xdata[fit.xrange]
            bkg = self.bkg[fit.xrange]

            yfit: NDArray[np.float32] = np.zeros_like(xfit)

            for peak, peak_plot in zip(fit.peaks.values(), self.fit_peaks.values(), strict=False):
                if not peak.func.is_bkg:
                    ypeak = peak.ydata(xfit, spec.coords)
                    yfit += ypeak

                    peak_plot.update(
                        verts=get_verts(xfit, ypeak, bkg),
                        label_text=peak.name,
                        label_coords=self.get_label_coords(peak, xdata=xfit))

            if spec.bkg_active:
                yfit += bkg

            self.fit_line.set_data(xfit, yfit)

        self.line.set_ydata(ydata)
        self.bkg_line.set_ydata(self.bkg)

        top = int(1.25 * np.nanmax(ydata[spec.xrange]))
        self.axis.set_ylim(top=top)
        self.header.widgets["top"].set(top)

        self.canvas.draw_idle()


class PeakView:
    """Controla la vista d'un pic dibuixat sobre la gràfica d'espectres."""

    def __init__(self, axis: Axes, color: str) -> None:
        """Crea l'àrea del pic i l'etiqueta corresponent.

        Parameters
        ----------
        axis: Axes
            Eix sobre el que es dibuixa el pic
        color: str
            Color del pic

        """
        self.plot: FillBetweenPolyCollection = axis.fill_between([], [], color=color, alpha=0.6)
        self.label: Annotation = axis.annotate("", (0, 0))

    def remove(self) -> None:
        """Elimina els objectes visuals del pic."""
        self.plot.remove()
        self.label.remove()

    def update(self, verts: NDArray[np.float32], label_text: str, label_coords: tuple[float, float]) -> None:
        """Actualitza els objectes visual del pics.

        Parameters
        ----------
        verts: NDArray[np.float32]
            Nous límits del pic
        label_text: str
            Text que indica la posició del pic
        label_coords: tuple[float, float]
            Coordenades del text

        """
        self.plot.set_verts([verts])

        self.update_text(label_text, label_coords[0])
        self.label.xy = label_coords

    def update_text(self, name: str, value: float) -> None:
        """Actualitza el text de l'etiqueta del pic.

        Parameters
        ----------
        name: str
            Nom del pic
        value: float
            Valor del centre del pic

        """
        self.label.set_text(f"{name}\n{value:.2f}")


class ProfileView:
    """Dibuixa les fletxes sobre el mapa i les associa amb els perfils."""

    def __init__(self, profiles: dict[int, ProfileData], axis: Axes, geometry: GeometryData) -> None:
        """Crea i dibuixa les fletxes sobre la figura a partir dels perfils actuals.

        Parameters
        ----------
        profiles: dict[int, ProfileData]
            Perfils del fitxer
        axis: Axes
            Objecte eix de Matplotlib
        geometry: Geometry
            Geometria del fitxer

        """
        self.data = profiles
        self.geometry = geometry

        self.colors: tuple[str, ...] = ("r", "b", "g", "orange", "y", "cyan", "pink", "k")
        self.create_arrows(axis)

    def create_arrows(self, axis: Axes) -> None:
        """Dibuixa totes les fletxes.

        Parameters
        ----------
        axis: Axes
            Objecte eix de Matplotlib

        """
        self.arrow = {num: self._add_arrow(axis, num, prof.lims) for num, prof in self.data.items()}

    def update(self) -> None:
        """Actualitza les fletxes segons els canvis sobre els perfils."""
        for num, prof in self.data.items():
            start, end = pixel_to_coords(prof.lims, self.geometry.dim, self.geometry.base_size)
            self.arrow[num].update(start, end)

    def delete(self) -> None:
        """Elimina les fletxes."""
        for arrow in self.arrow.values():
            arrow.delete()
        self.arrow.clear()

    def plot(self, num: int, axis: Axes, data: NDArray[np.float32])\
             -> tuple[NDArray[np.float32], NDArray[np.float32], Line2D]:
        """Dibuixa un perfil sobre un gràfic d'ordenades.

        Parameters
        ----------
        num: int
            Referència del perfil
        axis: Axes
            Objecte eix de la gràfica
        data: NDArray[np.float32]
            Conjunt de dades sobre les que el perfil actua

        Returns
        -------
        line: NDArray[np.float32]
            Punts del perfil
        dades: NDArray[np.float32]
            Dades d'una matriu en els punts del perfil
        profile: Line2D
            Línia del perfil sobre la gràfica

        """
        prof = self.data[num]

        coords = np.asarray(prof.line)
        x_vals = coords[:, 0]
        y_vals = coords[:, 1]

        dades = data[y_vals, x_vals]
        zmin, zmax = np.nanmin(dades), np.nanmax(dades)
        diff = (zmax - zmin) / 15
        line = np.linspace(0, prof.length, len(dades), dtype=np.float32)

        profile, = axis.plot(line, dades, color=self.colors[num % 8])
        axis.set_xlim(left=0, right=prof.length)
        axis.set_ylim(bottom=float(zmin - diff), top=float(zmax + diff))

        return line, dades, profile

    def _add_arrow(self, axis: Axes, num: int, lims: list[tuple[int, int]]) -> FletxaBase:
        start, end = pixel_to_coords(lims, self.geometry.dim, self.geometry.base_size)
        return FletxaBase(axis, start, end, self.geometry.base_size, str(num + 1), self.colors[num % 8])


def create_tab(notebook: NotebookProtocol, name: str) -> ttk.Frame:
    """Crea una pestanya sobre un full de treball.

    Parameters
    ----------
    notebook: ttk.Notebook
        Full de treball
    name: str
        Nom de la pestanya

    Returns
    -------
    tab: ttk.Frame
        Pestanya creada

    """
    parent = cast("Misc", notebook)
    tab = ttk.Frame(parent)
    notebook.add(tab, text=name)
    return tab
