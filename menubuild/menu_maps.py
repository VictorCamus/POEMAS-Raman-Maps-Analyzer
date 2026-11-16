"""Operacions, transformacions i creacions de màscares booleanes sobre els fitxers oberts."""
from copy import deepcopy
from functools import partial
from tkinter import messagebox
from typing import TYPE_CHECKING, Literal

import numpy as np
from matplotlib.pyplot import close

from classes.data import ChannelData
from classes.views import create_tab
from process.shiftphase import cross_correlation_shift
from window import ImageWindow, MapWindow
from window.mixin import MapWidgets
from window.widgets import Widget

from .base import BaseMenu

if TYPE_CHECKING:
    from tkinter import Menu

    from numpy.typing import NDArray

    from classes.protocols import GestorProtocol
    from classes.views import FileView


class GestorMaps(BaseMenu):
    """Menú que opera amb entre diferents mapes i aplica transformacions i màscares booleanes."""

    def _add_menu(self, menu: Menu) -> None:
        self.add_tab(text="Sincronitzar límits", func=self.lims_sync)
        self.add_tab(text="Afegir llindar", func=partial(self.open_window, Llindar))
        self.add_tab(text="Operar amb canals", func=partial(self.open_window, OperarMaps))
        self.add_tab(text="Ajustar mapes desplaçats", func=partial(self.open_window, ShiftMaps))
        self.add_tab()
        self.add_tab(text="Tancar canals", func=partial(self.open_window, TancarMaps))

        menu.add_cascade(label="Mapes", menu=self.submenu)

    def lims_sync(self) -> None:
        """Sincronitza els límits del mapes de color d'un fitxer amb la resta de fitxers."""
        file = self.current_file

        for key, channel in file.channel.items():
            for f in self.files.values():
                if f is file:
                    continue
                if key in f.channel:
                    f.channel[key].lims = deepcopy(channel.lims)

        for f in self.files.values():
            f.mapview.refresh_map()


class LlindarWidgets(MapWidgets):
    """Ginys de la classe Llindar."""

    thr_inf: Widget[float]
    thr_sup: Widget[float]
    apply: Widget[str]


class Llindar(ImageWindow):
    """Afig una màscara booleana que amaga els valors fora dels límits establerts."""

    widgets: LlindarWidgets

    def __init__(self, gestor: GestorProtocol) -> None:
        """Crea la finestra amb la imatge del canal corresponent a la dreta.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal

        """
        super().__init__(gestor, "Calcular fons")

        self.z: NDArray[np.float32] = self.channel.data.copy()
        self._mask: NDArray[np.bool_] = np.ones_like(self.z, dtype=np.bool_)

    def _create_widgets(self) -> None:
        files = list(self.files)
        channels = list(self.file.channel)

        self.widgets = {
            "file": Widget(
                key="file",
                var_type=str,
                init=self.file.name,
                text="Arxiu:",
                widget="cb",
                widget_kwargs={"options": files},
                setter=self.file_changed,
            ),
            "channel": Widget(
                key="channel",
                var_type=str,
                init=self.channel.name,
                text="Canal:",
                widget="cb",
                widget_kwargs={"options": channels},
                setter=self.channel_changed,
            ),
            "thr_inf": Widget(
                key="thr_inf",
                var_type=float,
                init=round(float(np.nanmin(self.channel.data)), 3),
                text="Llindar inferior:",
                widget="entry",
                setter=partial(self.threshold, key="thr_inf"),
            ),
            "thr_sup": Widget(
                key="thr_sup",
                var_type=float,
                init=round(float(np.nanmax(self.channel.data)), 3),
                text="Llindar superior:",
                widget="entry",
                setter=partial(self.threshold, key="thr_sup"),
            ),
            "apply": Widget(
                key="apply",
                init="Aplicar",
                widget="button",
                setter=self.apply_threshold,
            ),
        }

    def threshold(self, value: float, key: Literal["thr_inf", "thr_sup"]) -> None:
        """Dona el valor del llindar escollit i crea la màscara boolena.

        Parameters
        ----------
        value: float
            Valor del llindar
        key: Literal["thr_inf", "thr_sup"]
            Llindar escollit

        """
        inf, sup = (value if key == "thr_inf" else self.widgets["thr_inf"].get(),
                                  value if key == "thr_sup" else self.widgets["thr_sup"].get())

        self._mask = (self.z >= inf) & (self.z <= sup)
        self.update_fig(mask=self._mask)

    def apply_threshold(self) -> None:
        """Aplica el llindar sobre el fitxer seleccionat."""
        self.file.objects.mask = self._mask
        self.file.mapview.refresh_map()


class OperarMaps(MapWindow):
    """Opera punt per punt amb les matrius de dades mitjançant les operacions aritmètiques bàsiques."""

    def __init__(self, gestor: GestorProtocol) -> None:
        """Crea la finestra amb els ginys corresponents.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal

        """
        super().__init__(gestor, "Operar amb canals")

        self.opt: Literal["sum", "subs", "mult", "div"] = "subs"
        self.new_chname: str

    def _create_widgets(self) -> None:
        list_files, channels, ch_key = self.compare_files()

        operations = {
            "Suma (F2+F1)": "sum",
            "Resta (F2-F1)": "subs",
            "Multiplicació (F2*F1)": "mult",
            "Divisió (F2/F1)": "div",
        }

        self.widgets = {
            "file_ref": Widget(
                key="file_ref",
                var_type=str,
                init=self.file_ref.name,
                text="Arxiu Referència (F1)",
                widget="cb",
                widget_kwargs={"options": list_files[1:]},
                setter=self,
                mode="attr",
            ),
            "file": Widget(
                key="file",
                var_type=str,
                init=self.file.name,
                text="Arxiu 2 (F2)",
                widget="cb",
                widget_kwargs={"options": list_files},
                setter=self,
                mode="attr",
            ),
            "channel": Widget(
                key="channel",
                var_type=str,
                init=ch_key,
                text="Canal",
                widget="cb",
                widget_kwargs={"options": channels},
                setter=self,
                mode="attr",
            ),
            "opt": Widget(
                key="opt",
                var_type=str,
                init="subs",
                text="Operació",
                widget="radiobutton",
                widget_kwargs={"options": operations},
                setter=self,
                mode="attr",
            ),
            "new_chname": Widget(
                key="new_chname",
                var_type=str,
                init=None,
                text="Nom nou canal",
                widget="entry",
                setter=self,
                mode="attr",
            ),
            "newCh": Widget(
                key="newCh",
                init="Aplicar",
                widget="button",
                setter=self.apply_op),
        }

    def _create_channel(self, files: list[FileView]) -> None:
        """Crea un nou canal a partir de l'operació aritmètica triada amb el fitxer de referència.

        Parameters
        ----------
        files: list[FileView]
            Llista de canals sobre la que s'opera

        Raises
        ------
        ValueError
            Si les dimensions de cap dels mapes són diferents

        """
        file_ref = self.file_ref
        ch_ref = file_ref.channel[self.channel_key]

        for f in files:
            if f is file_ref:
                continue

            if file_ref.geometry.dim != f.geometry.dim or file_ref.geometry.base_size != f.geometry.base_size:
                msg = "Els mapes triats no tenen les mateixes dimensions."
                messagebox.showerror("Operacions amb mapes", msg)
                raise ValueError(msg)

            ch = f.channel[self.channel_key]

            match self.opt:
                case "sum":
                    new_data = ch.data + ch_ref.data
                    units = ch_ref.units
                case "subs":
                    new_data = ch.data - ch_ref.data
                    units = ch_ref.units
                case "mult":
                    new_data = ch.data * ch_ref.data
                    units = f"{ch_ref.units}²"
                case "div":
                    new_data = ch.data / ch_ref.data
                    units = ""

            tab = create_tab(f.notebook, self.new_chname)

            f.channel[self.new_chname] = ChannelData(self.new_chname, new_data, units)
            f.channel_tabs[self.new_chname] = tab

    def apply_op(self) -> None:
        """Calcula el nou canal i el crea sobre cada fitxer elegit."""
        if not self.new_chname:
            messagebox.showerror("Operacions amb mapes", "Cal triar un nom per al nou arxiu")
            return

        files = self.files_list()
        self._create_channel(files)

        if self.file_key != "Tots els fitxers" and self.new_chname in list(self.file.channel):
            self.file.notebook.select(self.file.channel_tabs[self.new_chname])


class ShiftMaps(MapWindow):
    """Corregeix el desplaçament lineal entre imatges d'una mateixa mostra.

    Esta funció normalment s'aplica sobre la topografia per a recalibrar les imatges que s'han desplaçat
    durant l'escaneig de les mesures experimentals.
    """

    def __init__(self, gestor: GestorProtocol) -> None:
        """Crea la finestra amb els ginys corresponents.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal

        """
        super().__init__(gestor, "Ajustar mapes desplaçats")

    def _create_widgets(self) -> None:
        list_files, channels, ch_key = self.compare_files()

        self.widgets = {
            "file_ref": Widget(
                key="file_ref",
                var_type=str,
                init=self.file_ref.name,
                text="Arxiu Referència (F1)",
                widget="cb",
                widget_kwargs={"options": list_files[1:]},
                setter=self,
                mode="attr",
            ),
            "file": Widget(
                key="file",
                var_type=str,
                init=self.file.name,
                text="Arxiu 2 (F2)",
                widget="cb",
                widget_kwargs={"options": list_files},
                setter=self,
                mode="attr",
            ),
            "channel": Widget(
                key="channel",
                var_type=str,
                init=ch_key,
                text="Canal",
                widget="cb",
                widget_kwargs={"options": channels},
                setter=self,
                mode="attr",
            ),
            "phcorr": Widget(
                key="phcorr",
                init="Aplicar",
                text="Dibuixa la correlació de fase",
                widget="button",
                setter=self.plot_corr_shift,
            ),
            "newCh": Widget(
                key="newCh",
                init="Aplicar",
                text="Obtindre nou canal:",
                widget="button",
                setter=self.apply_op,
            ),
        }

    def plot_corr_shift(self) -> None:
        """Dibuixa la matriu de correlació dels dos mapes, el màxim del qual indicarà el desplaçament en el pla."""
        if self.file_key == "Tots els fitxers":
            messagebox.showerror("Error", "Tria un arxiu específic per a vore la correlació de fase")
            return

        if self.file_ref is self._file:
            messagebox.showerror("Error", "Tria dos arxius diferents")
            return

        cross_correlation_shift(self.file_ref.channel[self.channel_key].data,
                                self.file.channel[self.channel_key].data, plot=True)

    def apply_op(self) -> None:
        """Alinea els fitxers desplaçats seleccionats."""
        files = self.files_list()
        file_ref = self.file_ref

        shifts, roi = self._roi_shifts()

        px_ref = file_ref.geometry.base_size[0] / file_ref.geometry.dim[0]
        py_ref = file_ref.geometry.base_size[1] / file_ref.geometry.dim[1]

        for f in files:
            pixel_size = (px_ref, py_ref) if f is file_ref\
                            else (f.geometry.base_size[0] / f.geometry.xdim, f.geometry.base_size[1] / f.geometry.ydim)

            self._crop_file(f, shifts[f.name], roi, pixel_size)

    def _roi_shifts(self) -> tuple[dict[str, tuple[float, float]], list[float]]:
        """Calcula els desplaçaments de cada imatge i la regió d'interés compartida (ROI) dels fitxers.

        Returns
        -------
        shifts: dict[str, tuple[float, float]]
            Diccionari amb els desplaçaments
        roi: list[float]

        Raises
        ------
        ValueError:
            Si la intersecció dels desplaçaments dona com a resultat una matriu nul·la

        """
        files = self.files_list()
        file_ref = self.file_ref

        xdim_ref, ydim_ref = file_ref.geometry.base_size
        nx_ref, ny_ref = file_ref.geometry.dim
        px_ref, py_ref = xdim_ref / nx_ref, ydim_ref / ny_ref

        shifts: dict[str, tuple[float, float]] = {file_ref.name: (0.0, 0.0)}
        roi: list[float] = [0.0, xdim_ref, 0.0, ydim_ref]

        data_ref = file_ref.channel[self.channel_key].data

        for f in files:
            if f is file_ref:
                continue

            dx, dy = cross_correlation_shift(data_ref, f.channel[self.channel_key].data)
            shifts[f.name] = dx * px_ref, dy * py_ref

            roi[0] = max(roi[0], shifts[f.name][0])
            roi[1] = min(roi[1], shifts[f.name][0] + f.geometry.base_size[0])
            roi[2] = max(roi[2], shifts[f.name][1])
            roi[3] = min(roi[3], shifts[f.name][1] + f.geometry.base_size[1])

            if roi[0] >= roi[1] or roi[2] >= roi[3]:
                msg = "No hi ha solapament global"
                raise ValueError(msg)

        return shifts, roi

    @staticmethod
    def _crop_file(f: FileView, shift: tuple[float, float], roi: list[float], pixel_size: tuple[float, float]) -> None:
        """Propaga la ROI compartida a tots els fitxers i actualitza la geometria i els visors.

        Parameters
        ----------
        f: FileView
            Fitxer actualitzat
        shift: tuple[float, float]
            Desplaçament corresponent
        roi: list[float]
            Regió d'interés sobre la que es retalla
        pixel_size: tuple[float, float]
            Mida de cada píxel

        """
        px, py = pixel_size
        dx, dy = shift
        x0 = round((roi[0] - dx) / px)
        x1 = round((roi[1] - dx) / px)
        y0 = round((roi[2] - dy) / py)
        y1 = round((roi[3] - dy) / py)

        f.geometry.dim = x1 - x0, y1 - y0
        f.geometry.base_size = (round(f.geometry.xdim * px, 5), round(f.geometry.ydim * py, 5))

        for ch in f.channel.values():
            ch.data = ch.data[y0:y1, x0:x1]

        for prof in f.objects.profiles.values():
            prof.line = [(x - x0, y - y0) for x, y in prof.line]

        f.objects.mask = f.objects.mask[y0:y1, x0:x1]
        f.mapview.base_size()


class TancarMaps(MapWindow):
    """Tanca els canals triats."""

    intersect = False

    def __init__(self, gestor: GestorProtocol) -> None:
        """Inicia la finestra base amb els ginys corresponents.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal

        """
        super().__init__(gestor, "Tancar canals")

    def _create_widgets(self) -> None:
        files = ["Tots els fitxers", *self.files]
        channels = list(self.file.channel)

        self.widgets = {
            "file": Widget(
                key="file",
                var_type=str,
                init=self.file.name,
                text="Arxiu:",
                widget="cb",
                widget_kwargs={"options": files},
                setter=self,
                mode="attr",
            ),
            "channel": Widget(
                key="channel",
                var_type=str,
                init=self.channel.name,
                text="Canal:",
                widget="cb",
                widget_kwargs={"options": channels},
                setter=self,
                mode="attr",
            ),
            "close": Widget(
                key="close",
                init="Tancar",
                widget="button",
                setter=self.close_channel,
            ),
        }

    def close_channel(self) -> None:
        """Tanca el canal seleccionat."""
        if not self.files:
            return
        files = self.files_list()

        for f in files:
            if self.channel_key not in f.channel:
                continue

            f.notebook.forget(f.channel_tabs[self.channel_key])
            f.channel.pop(self.channel_key, None)

            if not f.channel:
                self.notebook.forget(str(f.notebook))
                close(self.file.mapview.figure)

                if f is self.file:
                    self.files.pop(f.name, None)

                    if not self.files:
                        self.notebook.lower()
                        return

                    self.file = next(iter(self.files))

                files_keys = ["Tots els fitxers", *self.files]
                self.update_files(files_keys)

        self.update_channels()
        first_channel = next(iter(self.file.channel.keys()))
        self.file.notebook.select(self.file.channel_tabs[first_channel])
