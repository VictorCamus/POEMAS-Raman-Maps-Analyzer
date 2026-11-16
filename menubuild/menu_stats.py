"""Càlcul d'histogrames, mitjanes direccionals i boxplots."""

from functools import partial
from pathlib import Path
from tkinter import Button, Frame, Menu, filedialog, ttk
from typing import TYPE_CHECKING, Literal

import numpy as np

from process.statistics import boxplot, hist, remove_boxplot
from window import FigureWindow
from window.mixin import MapWidgets
from window.widgets import Widget

from .base import BaseMenu

if TYPE_CHECKING:
    from matplotlib.collections import FillBetweenPolyCollection
    from matplotlib.patches import Patch
    from numpy.typing import NDArray

    from classes.protocols import GestorProtocol, InfSup


class GestorStats(BaseMenu):
    """Menú que controla el càlcul estadístic d'histogrames i mitjanes."""

    def _add_menu(self, menu: Menu) -> None:
        self.add_tab(text="Mostrar histogrames", func=partial(Histogrames, self))
        self.add_tab(text="Mitjana direccional", func=partial(DirectionMean, self))
        self.add_tab(text="Guardar dades crues", func=self.save_rawdata)

        menu.add_cascade(label="Estadística", menu=self.submenu)

    def save_rawdata(self) -> None:
        """Guarda un fitxer d'una columna amb les dades crues del canal corresponent."""
        file = self.current_file
        channel = file.current_channel

        ruta = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=".txt",
            initialfile=f"{file.name} - {channel.name} Data.txt",
            filetypes=[("TXT", "*.txt")],
        )

        if ruta:
            x0, x1, y0, y1 = file.geometry.limit_pixels()
            data = channel.data[y0:y1, x0:x1].ravel()

            np.savetxt(ruta, data, fmt="%.4g")


class HistogramesWidgets(MapWidgets):
    """Ginys de la classe Histogrames."""

    color: Widget[str]
    inf: Widget[float]
    sup: Widget[float]
    nbins: Widget[int]
    mean: Widget[float]
    stderr: Widget[float]
    skewness: Widget[float]
    kurtosis: Widget[float]
    lower: Widget[float]
    q1: Widget[float]
    q2: Widget[float]
    q3: Widget[float]
    upper: Widget[float]
    copy: Widget[str]
    save: Widget[str]


class Histogrames(FigureWindow):
    """Classe que controla la finestra de dibuix d'histogrames i boxplots."""

    widgets: HistogramesWidgets
    hist_plot: FillBetweenPolyCollection
    box_plot: dict[str, list[Patch]]

    def __init__(self, gestor: GestorProtocol) -> None:
        """Crea la finestra amb la figura de l'histograma del canal actual a la dreta.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal

        """
        self.mode: Literal["Hist", "Box"] = "Hist"
        self.color: str = "blue"
        self.nbins: int = 50
        self.hist_data: tuple[NDArray[np.float32], NDArray[np.float32]] = (np.array([]), np.array([]))

        super().__init__(gestor, "Mostrar histogrames", dim=(5, 4))

        self.update_plot(remove=False)

        buttons = Frame(self.fig_frame)
        buttons.pack(anchor="center", pady=5)

        btn_prev = Button(buttons, text="◀", command=self.toggle_plot, font=("Arial", 16))
        btn_prev.pack(side="left", padx=2)

        btn_next = Button(buttons, text="▶", command=self.toggle_plot, font=("Arial", 16))
        btn_next.pack(side="left", padx=2)

    @property
    def data(self) -> NDArray[np.float32]:
        """Retorna les dades contingudes entre els límits establerts."""
        region = self.file.geometry.region
        mask = self.file.objects.mask[region]
        data = self.channel.data[region][mask].ravel()
        lims_mask = (self.lims[0] < data) & (data < self.lims[1])

        return data[lims_mask]

    def _create_widgets(self) -> None:
        files = list(self.files.keys())
        channels = list(self.file.channel.keys())

        self.lims = self.channel.lims.copy()

        mean, std, skew, kurt, lw, q1, q2, q3, tw = self.compute_stats()

        self.widgets = {
            "file": Widget(
                key="file",
                var_type=str,
                init=self.file.name,
                text="Arxiu:",
                widget="cb",
                widget_kwargs={"options": files},
                setter=self.set_file,
            ),
            "channel": Widget(
                key="channel",
                var_type=str,
                init=self.channel.name,
                text="Canal:",
                widget="cb",
                widget_kwargs={"options": channels},
                setter=self.set_channel,
            ),
            "color": Widget(
                key="color",
                var_type=str,
                init=self.color,
                text="Color de l'histograma:",
                widget="colorcb",
                setter=self.set_color,
            ),
            "inf": Widget(
                key="inf",
                var_type=float,
                init=round(self.lims[0], 3),
                text="Límit inferior:",
                widget="entry",
                setter=partial(self.set_lims, key="inf"),
            ),
            "sup": Widget(
                key="sup",
                var_type=float,
                init=round(self.lims[1], 3),
                text="Límit superior:",
                widget="entry",
                setter=partial(self.set_lims, key="sup"),
            ),
            "nbins": Widget(
                key="nbins",
                var_type=int,
                init=self.nbins,
                text="Nombre de barres:",
                widget="entry",
                setter=self.set_nbins,
            ),
            "mean": Widget(
                key="mean",
                var_type=float,
                init=round(mean, 3),
                text="Mitjana:",
                widget="entry",
                widget_kwargs={"state": "readonly"},
                setter=self,
                mode="attr",
            ),
            "stderr": Widget(
                key="stderr",
                var_type=float,
                init=round(std, 3),
                text="Desviació estàndard RMS:",
                widget="entry",
                widget_kwargs={"state": "readonly"},
                setter=self,
                mode="attr",
            ),
            "skewness": Widget(
                key="skewness",
                var_type=float,
                init=round(skew, 3),
                text="Asimetria:",
                widget="entry",
                widget_kwargs={"state": "readonly"},
                setter=self,
                mode="attr",
            ),
            "kurtosis": Widget(
                key="kurtosis",
                var_type=float,
                init=round(kurt, 3),
                text="Curtosi:",
                widget="entry",
                widget_kwargs={"state": "readonly"},
                setter=self,
                mode="attr",
            ),
            "lower": Widget(
                key="lower",
                var_type=float,
                init=round(lw, 3),
                text="Llindar inferior (5%):",
                widget="entry",
                widget_kwargs={"state": "readonly"},
                setter=self,
                mode="attr",
            ),
            "q1": Widget(
                key="q1",
                var_type=float,
                init=round(q1, 3),
                text="Primer quartil (25%):",
                widget="entry",
                widget_kwargs={"state": "readonly"},
                setter=self,
                mode="attr",
            ),
            "q2": Widget(
                key="q2",
                var_type=float,
                init=round(q2, 3),
                text="Mediana (50%):",
                widget="entry",
                widget_kwargs={"state": "readonly"},
                setter=self,
                mode="attr",
            ),
            "q3": Widget(
                key="q3",
                var_type=float,
                init=round(q3, 3),
                text="Tercer quartil (75%):",
                widget="entry",
                widget_kwargs={"state": "readonly"},
                setter=self,
                mode="attr",
            ),
            "upper": Widget(
                key="upper",
                var_type=float,
                init=round(tw, 3),
                text="Llindar superior (95%):",
                widget="entry",
                widget_kwargs={"state": "readonly"},
                setter=self,
                mode="attr",
            ),
            "copy": Widget(
                key="copy",
                init="Copiar dades",
                widget="button",
                widget_kwargs={"width": 14},
                setter=lambda: self.copy_data(*self.hist_data),
            ),
            "save": Widget(
                key="save",
                init="Guardar",
                widget="button",
                widget_kwargs={"width": 14},
                setter=self.save_hist),
        }

    def set_file(self, file_key: str) -> None:
        """Dibuixa el fitxer donat.

        Parameters
        ----------
        file_key: str
            Clau del fitxer

        """
        self.file = file_key

        self.default_lims()
        self.set_widgets()

    def set_channel(self, ch_key: str) -> None:
        """Dibuixa el canal donat.

        Parameters
        ----------
        ch_key: str
            Clau del fitxer

        """
        self.channel = ch_key

        self.default_lims()
        self.set_widgets()

    def default_lims(self) -> None:
        """Iguala els límits als predeterminats del canal actual."""
        self.lims = self.channel.lims.copy()
        self.widgets["inf"].set(round(self.lims[0], 3))
        self.widgets["sup"].set(round(self.lims[1], 3))

    def set_lims(self, value: float, key: InfSup) -> None:
        """Canvia els límits de l'eix corresponent: eix X ("Hist") o eix Y ("Box").

        Parameters
        ----------
        value: str
            Nou valor del límit
        key: InfSup
            Clau del límit

        """
        match key:
            case "inf":
                self.lims[0] = value
            case "sup":
                self.lims[1] = value

        self.set_widgets()
        self.update_plot()

    def set_color(self, color: str) -> None:
        """Assigna i canvia el color de les dades.

        Parameters
        ----------
        color: str
            Color triat

        """
        self.color = color
        match self.mode:
            case "Hist":
                self.hist_plot.set_color(color)
            case "Box":
                for element in self.box_plot["boxes"]:
                    element.set_facecolor(color)

        self.figure.canvas.draw()

    def set_nbins(self, nbins: int) -> None:
        """Assigna el nombre de caixes de l'histograma.

        Parameters
        ----------
        nbins: int
            Nombre de caixes triades

        """
        self.nbins = nbins
        self.update_plot()

    def plot_remove(self) -> None:
        """Elimina les dades del gràfic actual."""
        match self.mode:
            case "Hist":
                self.hist_plot.remove()
            case "Box":
                remove_boxplot(self.box_plot)

    def set_widgets(self) -> None:
        """Actualitza els ginys relacionats amb l'estadística del gràfic."""
        mean, std, skew, kurt, lw, q1, q2, q3, tw = self.compute_stats()
        self.widgets["mean"].set(round(mean, 3))
        self.widgets["stderr"].set(round(std, 3))
        self.widgets["skewness"].set(round(skew, 3))
        self.widgets["kurtosis"].set(round(kurt, 3))
        self.widgets["q1"].set(round(q1, 3))
        self.widgets["q2"].set(round(q2, 3))
        self.widgets["q3"].set(round(q3, 3))
        self.widgets["lower"].set(round(lw, 3))
        self.widgets["upper"].set(round(tw, 3))

        self.update_plot()

    def compute_stats(self) -> tuple[float, ...]:
        """Calcula les variables estadístiques de les dades corresponents.

        Returns
        -------
        mean: float
            Mitjana de les dades
        std: float
            Desviació estàndard de les dades
        skew: float
            Asimetria de les dades
        kurt: float
            Curtosi de les dades
        lw: float
            Percentil 5%.
        q1: float
            Primer quartil.
        q2: float
            Segon quartil (mediana).
        q3: float
            Tercer quartil.
        tw:
            Percentil 95%.

        """
        data = self.data
        mean = float(np.nanmean(data))
        std = float(np.nanstd(data))

        norm = (data - mean) / std
        skew = float(0) if std == 0 else float(np.nanmean(norm**3))
        kurt = float(0) if std == 0 else float(np.nanmean(norm**4))

        lw, q1, q2, q3, tw = map(float, np.nanpercentile(data, [5, 25, 50, 75, 95]))

        return mean, std, skew, kurt, lw, q1, q2, q3, tw

    def toggle_plot(self) -> None:
        """Canvia d'un gràfic d'histogrames a un de boxplot i a l'inrevés."""
        self.plot_remove()

        match self.mode:
            case "Hist":
                self.mode = "Box"
                self.widgets["nbins"].config(state="disabled")
            case "Box":
                self.mode = "Hist"
                self.widgets["nbins"].config(state="normal")

        self.update_plot(remove=False)

    def update_plot(self, *, remove: bool = True) -> None:
        """Actualitza les dades del gràfic donat."""
        if remove:
            self.plot_remove()

        match self.mode:
            case "Hist":
                self.hist_plot, self.hist_data, _ = hist(
                    self.axis,
                    self.data,
                    self.lims,
                    nbins=self.nbins,
                    xlabel=self.channel.ax_title,
                    color=self.color,
                )
            case "Box":
                self.box_plot = boxplot(
                    self.axis,
                    self.data,
                    self.lims,
                    name=self.channel.name,
                    ylabel=self.channel.ax_title,
                    color=self.color,
                )

        self.figure.tight_layout()
        self.figure.tight_layout()
        self.figure.canvas.draw_idle()

    def save_hist(self) -> None:
        """Guarda el gràfic, les dades i l'estadística derivada.

        Raises
        ------
        TypeError
            Si hi ha cap valor dins de self.widgets que no és un giny.

        """
        ruta = filedialog.asksaveasfilename(
            parent=self.main_frame,
            defaultextension=".png",
            initialfile=f"{self.file.name} - {self.channel.name} {self.mode}.png",
            filetypes=[("PNG", "*.png")],
        )

        if ruta:
            self.figure.savefig(ruta)
            p = Path(ruta)
            txt_ruta = p.with_name(f"{self.file.name} - {self.channel.name} Data.txt")

            with Path(txt_ruta).open("w", encoding="utf-8") as f:
                for widget in self.widgets.values():
                    if not isinstance(widget, Widget):
                        msg = "La variable triada no és un giny"
                        raise TypeError(msg)

                    if (isinstance(widget.widget, ttk.Entry)
                       and widget.widget.cget("state") == "readonly"
                       and widget.label is not None):
                        f.write(f"{widget.label.cget('text'):<30} {widget.get():>10}\n")

                f.write("\n")
                f.write(f"{'Bin':<10}{'Count':<8}\n")

                f.writelines(f"{bin_:<10.2f}{count:<8.5f}\n" for bin_, count in self.hist_data)


class DirectionWidgets(MapWidgets):
    """Ginys de la classe DirectionMean."""

    color: Widget[str]
    inf: Widget[float]
    sup: Widget[float]
    direction: Widget[bool]
    units: Widget[bool]
    freq: Widget[float]
    copy: Widget[str]
    save: Widget[str]


class DirectionMean(FigureWindow):
    """Calcula i dibuixa la mitjana d'un canal en la direcció triada."""

    widgets: DirectionWidgets

    def __init__(self, gestor: GestorProtocol) -> None:
        """Crea la finestra amb la mitjana dibuixada en la figura a la dreta.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal

        """
        self._direction: bool = True
        self._units: bool = True
        self._freq: float = 0.5
        self.xval: NDArray[np.float32] = np.array([])
        self.mean: NDArray[np.float32] = np.array([])

        super().__init__(gestor, "Mostrar mitjana direccional", dim=(6, 4))

        self.plot, = self.axis.plot([], [], color="blue")
        self.axis.set_xlabel(r"Length ($\mu$m)")
        self.axis.set_ylabel(self.channel.ax_title)
        self.set_widgets()

    def _create_widgets(self) -> None:
        files = ["Tots els fitxers", *list(self.files)]
        channels = list(self.file.channel)

        optxunits = {"Longitud (μm)": True, "Temps (min)": False}

        self.widgets = {
            "file": Widget(
                key="file",
                var_type=str,
                init=self.file.name,
                text="Arxiu:",
                widget="cb",
                widget_kwargs={"options": files},
                setter=self.plot_file,
            ),
            "channel": Widget(
                key="channel",
                var_type=str,
                init=self.channel.name,
                text="Canal:",
                widget="cb",
                widget_kwargs={"options": channels},
                setter=self.plot_channel,
            ),
            "color": Widget(
                key="color",
                var_type=str,
                init="blue",
                text="Color de l'histograma:",
                widget="colorcb",
                setter=self.plot_color,
            ),
            "inf": Widget(
                key="inf",
                var_type=float,
                init=0,
                text="Límit inferior:",
                widget="entry",
                setter=partial(self.plot_lims, key="inf"),
            ),
            "sup": Widget(
                key="sup",
                var_type=float,
                init=1,
                text="Límit superior:",
                widget="entry",
                setter=partial(self.plot_lims, key="sup"),
            ),
            "direction": Widget(
                key="direction",
                var_type=bool,
                init=True,
                text="Direcció:",
                widget="radiobutton",
                widget_kwargs={"options": {"H": True, "V": False}, "direction": "h"},
                setter=lambda value: self.direction(direction=value),
            ),
            "units": Widget(
                key="units",
                var_type=bool,
                init=True,
                text="Unitats:",
                widget="radiobutton",
                widget_kwargs={"options": optxunits},
                setter=lambda value: self.units(units=value),
            ),
            "freq": Widget(
                key="freq",
                var_type=float,
                init=0.5,
                text="Freqüència (Hz):",
                widget="entry",
                widget_kwargs={"state": "readonly"},
                setter=self.freq,
            ),
            "copy": Widget(
                key="copy",
                init="Copiar dades",
                widget="button",
                widget_kwargs={"width": 14},
                setter=lambda: self.copy_data(self.xval, self.mean),
            ),
            "save": Widget(
                key="save",
                init="Guardar",
                widget="button",
                widget_kwargs={"width": 14},
                setter=self.save_mean,
            ),
        }

    def plot_file(self, file_key: str) -> None:
        """Dibuixa el fitxer donat.

        Parameters
        ----------
        file_key: str
            Clau del fitxer

        """
        self.file = file_key
        self.set_widgets()

    def plot_channel(self, ch_key: str) -> None:
        """Dibuixa el canal donat.

        Parameters
        ----------
        ch_key: str
            Clau del canal

        """
        self.channel = ch_key
        self.axis.set_ylabel(self.channel.ax_title)
        self.set_widgets()

    def plot_color(self, color: str) -> None:
        """Indica el color de línia de dades.

        Parameters
        ----------
        color: str
            Color triat

        """
        self.plot.set_color(color)
        self.figure.canvas.draw()

    def plot_lims(self, value: float, key: InfSup) -> None:
        """Canvia els límits de l'eix Y de la figura.

        Parameters
        ----------
        value: float
            Nou valor del límit
        key: InfSup
            Clau del límit

        """
        match key:
            case "inf":
                self.lims[0] = value
                self.axis.set_ylim(bottom=value)
            case "sup":
                self.lims[1] = value
                self.axis.set_ylim(top=value)

        self.figure.tight_layout()
        self.figure.canvas.draw_idle()

    def direction(self, *, direction: bool) -> None:
        """Indica la nova direcció de la mitjana.

        Parameters
        ----------
        direction: bool
            True: Horitzontal, "H".
            False: Vertical, "V".

        """
        self._direction = direction
        self.set_widgets()

    def units(self, *, units: bool) -> None:
        """Indica les unitats de l'eix X de la mitjana.

        Parameters
        ----------
        units: bool
            True: Longitud (μm)
            False: Temps (min). Seguint la direcció de l'escaneig, principalment útil per a mapes one-line.

        """
        self._units = units

        if units:
            self.axis.set_xlabel("Length (μm)")
            self.widgets["freq"].config(state="readonly")
        else:
            self.axis.set_xlabel("Time (min)")
            self.widgets["freq"].config(state="normal")

        self.set_widgets()

    def freq(self, freq: float) -> None:
        """Indica la freqüència d'escaneig. Només activat si les unitats són temporals.

        Parameters
        ----------
        freq: float
            Freqüència donada, en Hz.

        """
        self._freq = freq
        self.set_widgets()

    def save_mean(self) -> None:
        """Guarda les dades de la mitjana i la imatge amb el nom escollit."""
        ruta = filedialog.asksaveasfilename(
            parent=self.main_frame,
            defaultextension=".png",
            initialfile=f"{self.file_key} - {self.channel_key} Mitjana.png",
            filetypes=[("PNG", "*.png")],
        )

        if ruta:
            self.figure.savefig(ruta)
            p = Path(ruta)
            np.savetxt(f"{p.parent}/{p.stem}.txt", np.column_stack((self.xval, self.mean)), fmt="%.4f")

    def set_widgets(self) -> None:
        """Actualitza els ginys i la figura en fer-se cap canvi."""
        self.compute_values()
        self.widgets["inf"].set(round(self.lims[0], 3))
        self.widgets["sup"].set(round(self.lims[1], 3))
        self.update_plot()

    def compute_values(self) -> None:
        """Calcula la mitjana del canal segons els paràmetres escollits."""
        self.mean = np.array([], dtype=np.float32)
        self.xval = np.array([], dtype=np.float32)

        files = list(self.files.values()) if self.file_key == "Tots els fitxers" else [self.file]

        for file in files:
            x0, x1, y0, y1 = file.geometry.limit_pixels()
            region = file.geometry.region
            mask = file.objects.mask[region]
            z = file.channel[self.channel_key].data[region].copy()
            z[~mask] = np.nan
            nx, ny = x1 - x0, y1 - y0

            if self._direction:
                pixels = nx
                xlength = file.geometry.base_size[0]
                for a in range(pixels):
                    self.mean = np.append(self.mean, np.nanmean(z[0:, a]))

            else:
                pixels = ny
                xlength = file.geometry.base_size[1]
                for a in range(pixels):
                    self.mean = np.append(self.mean, np.nanmean(z[a, 0:]))

            interval = xlength / pixels if self._units else 1 / (self._freq * 60)

            start = 0.0 if self.xval.size == 0 else self.xval[-1] + interval
            x = start + np.arange(pixels) * interval
            self.xval = np.append(self.xval, x)

        self.lims = [float(np.nanmin(self.mean)), float(np.nanmax(self.mean))]

    def update_plot(self) -> None:
        """Actualitza la figura amb la nova mitjana."""
        self.axis.set_xlim(float(self.xval.min()), float(self.xval.max()))
        self.axis.set_ylim(*self.lims)

        self.plot.set_data(self.xval, self.mean)

        self.figure.tight_layout()
        self.figure.tight_layout()
        self.figure.canvas.draw_idle()
