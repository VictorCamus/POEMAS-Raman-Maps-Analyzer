"""Dibuix, visualització i esborrament dels perfils com a dades i objectes visuals del mapa."""
from functools import partial
from pathlib import Path
from tkinter import Button, Frame, Menu, filedialog, messagebox
from typing import TYPE_CHECKING

import numpy as np

from classes.data import ProfileData
from drawing.arrows import FletxaInteractiva
from drawing.plots import PLOT_COLORS
from process.basics import get_line
from process.converter import coords_to_pixel
from window import FigureWindow
from window.mixin import MapWidgets
from window.widgets import Widget

from .base import BaseMenu

if TYPE_CHECKING:
    from matplotlib.lines import Line2D

    from classes.protocols import GestorProtocol, InfSup


class GestorProfiles(BaseMenu):
    """Menú que gestiona les accions relacionades amb els perfils sobre el mapa."""

    def _add_menu(self, menu: Menu) -> None:
        self.add_tab(text="Afegir perfil", func=self._add_prf, shortcut="Shift-P")
        self.add_tab(text="Sincronitzar perfils", func=self._sync_prf)
        self.add_tab(text="Mostrar perfils", func=self._open_profiles)
        self.add_tab()
        self.add_tab(text="Esborrar", func=self._close_prf, shortcut="Control-Alt-p")

        menu.add_cascade(label="Perfils", menu=self.submenu)

    def _open_profiles(self) -> None:
        """Obri la finestra de perfils si existeixen."""
        if not [key for key, f in self.files.items() if f.objects.profiles]:
            messagebox.showinfo("Informació", "No hi ha cap perfil dibuixat.")
            return

        MostrarPerfils(self)

    def _sync_prf(self) -> None:
        """Sincronitza els perfils del mapa actual amb la resta si les dimensions i la mida base són iguals."""
        file = self.current_file

        if not file.objects.profiles:
            return

        for f in self.files.values():
            if f is file:
                continue

            if f.geometry.dim != file.geometry.dim or f.geometry.base_size != file.geometry.base_size:
                messagebox.showwarning("Atenció",
                               f"El fitxer '{f.name}' té una mida diferent i no es poden propagar els perfils.")
                continue

            for num, prof in file.objects.profiles.items():
                f.objects.profiles[num] = ProfileData(prof.line, prof.length)
            f.mapview.profiles.create_arrows(axis=f.mapview.axis)

    def _add_prf(self) -> None:
        """Afig un nou perfil i dibuixa la fletxa corresponent al visor del mapa interactivament."""
        file = self.current_file

        num = len(file.objects.profiles)

        def save_arrow() -> None:
            """Guarda el perfil una vegada s'ha dibuixat la fletxa."""
            if arrow.start is None or arrow.end is None:
                return

            p1, p2 = coords_to_pixel(([arrow.start, arrow.end]), arrow.dim, arrow.base_size)
            length = float(np.hypot(arrow.end[0] - arrow.start[0], arrow.end[1] - arrow.start[1]))

            profile.line = get_line(p1, p2)
            profile.length = length

            file.objects.profiles[num] = profile
            file.mapview.profiles.arrow[num] = arrow

        profile = ProfileData()
        arrow = FletxaInteractiva(
            file.mapview.axis,
            file.geometry.dim,
            file.geometry.base_size,
            str(num + 1),
            color=PLOT_COLORS[num % 8],
            on_fletxa_finalitzada=save_arrow,
        )

    def _close_prf(self) -> None:
        """Elimina i esborra els perfils i les fletxes del fitxer corresponent."""
        file = self.current_file
        file.objects.profiles.clear()
        file.mapview.profiles.delete()

        file.mapview.canvas.draw_idle()


class PerfilsWidgets(MapWidgets):
    """Ginys de la classe MostrarPerfils."""

    profile: Widget[str]
    inf: Widget[float]
    sup: Widget[float]
    save: Widget[str]


class MostrarPerfils(FigureWindow):
    """Finestra que dibuixa els perfils d'un mapa sobre una figura."""

    widgets: PerfilsWidgets

    def __init__(self, gestor: GestorProtocol) -> None:
        """Obri la finestra amb els perfils dibuixats a la dreta.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal

        """
        super().__init__(gestor, "Mostrar perfils", dim=(5, 4))

        self.color = ["r", "b", "g", "orange", "y", "cyan", "pink", "k"]
        self.num = 0
        self.line: dict[int, Line2D] = {}

        self.axis.set_xlabel(r"Length ($\mu$m)")
        self.axis.set_xlim(0, self.profiles[0].length)
        self.axis.set_ylabel(self.channel.ax_title)

        data = self.channel.data
        data[~self.file.objects.mask] = np.nan
        _, _, self.line[0] = self.file.mapview.profiles.plot(0, self.axis, data)

        self.lims: list[float] = list(self.axis.get_ylim())
        self.widgets["inf"].set(round(self.lims[0], 0))
        self.widgets["sup"].set(round(self.lims[1], 0))

        buttons = Frame(self.fig_frame)
        buttons.pack(anchor="center", pady=5)

        btn_prev = Button(buttons, text="◀", command=lambda: self.toggle_plot(k=-1), font=("Arial", 16))
        btn_prev.pack(side="left", padx=2)

        btn_next = Button(buttons, text="▶", command=lambda: self.toggle_plot(k=1), font=("Arial", 16))
        btn_next.pack(side="left", padx=4)

        self.figure.tight_layout()
        self.canvas.draw_idle()

    @property
    def profiles(self) -> dict[int, ProfileData]:
        """Retorna les dades dels perfils del fitxer seleccionat."""
        return self.file.objects.profiles

    @property
    def nprof(self) -> int:
        """Retorna el nombre de perfils actuals."""
        return len(self.profiles)

    @property
    def num(self) -> int:
        """Retorna el número del perfil actual.

        num comença a 0, i num == nprof indica que s'estan mostrant tots els perfils alhora.
        """
        return self._num

    @num.setter
    def num(self, value: int) -> None:
        self._num = value % (self.nprof + 1)

    def _create_widgets(self) -> None:
        files = [key for key in self.files if self.profiles]
        if not self.profiles:
            self.file = files[0]

        channels = list(self.file.channel)

        self.widgets = {
            "file": Widget(
                key="file",
                var_type=str,
                init=self.file.name,
                text="Arxiu:",
                widget="cb",
                widget_kwargs={"options": files},
                setter=self.plot_file),
            "channel": Widget(
                key="channel",
                var_type=str,
                init=self.channel.name,
                text="Canal:",
                widget="cb",
                widget_kwargs={"options": channels},
                setter=self.plot_channel),
            "profile": Widget(
                key="profile",
                var_type=str,
                init="1",
                text="Perfil:",
                widget="entry",
                widget_kwargs={"state": "readonly"},
                setter=self,
                mode="attr"),
            "inf": Widget(
                key="inf",
                var_type=float,
                init=0,
                text="Límit inferior:",
                widget="entry",
                setter=partial(self.plot_lims, key="inf")),
            "sup": Widget(
                key="sup",
                var_type=float,
                init=1,
                text="Límit superior:",
                widget="entry",
                setter=partial(self.plot_lims, key="sup")),
            "save": Widget(
                key="save",
                init="Guardar",
                widget="button",
                setter=self._save_prf,
            ),
        }

    def plot_file(self, file_key: str) -> None:
        """Es dibuixen els perfils del fitxer seleccionat.

        Parameters
        ----------
        file_key: str
            Clau del fitxer

        """
        self.file = file_key
        self.toggle_plot()

    def plot_channel(self, ch_key: str) -> None:
        """Es dibuixen els perfils del canal seleccionat.

        Parameters
        ----------
        ch_key: str
            Clau del fitxer

        """
        self.channel = ch_key
        self.axis.set_ylabel(self.channel.ax_title)
        self.toggle_plot()

    def plot_lims(self, value: float, key: InfSup) -> None:
        """Es dibuixa la figura amb els nous límits de l'eix Y.

        Parameters
        ----------
        value: float
            Valor del límit
        key: InfSup
            Límit seleccionat

        """
        match key:
            case "inf":
                self.lims[0] = value
            case "sup":
                self.lims[1] = value

        self.axis.set_ylim(*self.lims)

        self.figure.tight_layout()
        self.figure.canvas.draw_idle()

    def toggle_plot(self, k: int = 0) -> None:
        """Redibuixa la figura amb els nous perfils triats.

        Parameters
        ----------
        k: int = 0
            Perfil triat. Si k == self.nprof, s'estan mostrant tots els perfils alhora

        """
        if self.num == self.nprof:
            for line in self.line.values():
                line.remove()
        else:
            self.line[self.num].remove()

        self.num += k

        if self.num == self.nprof:
            xmax: float = 0
            ymin: float = np.inf
            ymax: float = -np.inf

            for num in self.profiles:
                data = self.channel.data
                data[~self.file.objects.mask] = np.nan
                x, y, self.line[num] =\
                self.file.mapview.profiles.plot(num, self.axis, data)

                xmax = float(np.nanmax([xmax, x[-1]]))
                ymin = float(np.nanmin([ymin, np.nanmin(y)]))
                ymax = float(np.nanmax([ymax, np.nanmax(y)]))

            diff = (ymax - ymin) / 15 if ymax > ymin else 1

            self.axis.set_xlim(0, xmax)
            self.lims = [ymin - diff, ymax + diff]
            self.axis.set_ylim(*self.lims)

        else:
            _, _, self.line[self.num] = self.file.mapview.profiles.plot(self.num, self.axis, self.channel.data)

        self.figure.tight_layout()
        self.figure.tight_layout()
        self.figure.canvas.draw_idle()
        self._set_widgets()

    def _set_widgets(self) -> None:
        """Canvia el valor dels ginys quan se selecciona un nou perfil."""
        self.lims = list(self.axis.get_ylim())
        self.widgets["inf"].set(round(self.lims[0], 3))
        self.widgets["sup"].set(round(self.lims[1], 3))

        if self.num == self.nprof:
            self.widgets["profile"].set("Tots els perfils")
        else:
            self.widgets["profile"].set(f"{self.num + 1}")

    def _save_prf(self) -> None:
        """Guardar la figura i les dades dels perfils dibuixats amb el nom triat."""
        text = f"{self.file.name} - {self.channel.name} Tots els perfils" if self.num == self.nprof\
                    else f"{self.file.name} - {self.channel.name} Perfil {self.num + 1}"

        ruta = filedialog.asksaveasfilename(
            parent=self.main_frame,
            defaultextension=".png",
            initialfile=f"{text}.png",
            filetypes=[("PNG", "*.png")],
        )

        if not ruta:
            return

        self.figure.savefig(ruta, bbox_inches="tight")
        p = Path(ruta)

        if self.num == self.nprof:
            for i, line in enumerate(self.line.values(), start=1):
                self._save_prf_txt(p, line, i)
        else:
            self._save_prf_txt(p, self.line[self.num], self.num + 1)

        map_route = p.parent / p.stem

        self.file.mapview.figure.savefig(f"{map_route} - MAP.png", bbox_inches="tight")

    def _save_prf_txt(self, path: Path, line: Line2D, i: int) -> None:
        """Guarda les dades del perfil triat.

        Parameters
        ----------
        path: Path
            Camí de la figura guardada
        line: Line2D
            Objecte Line2D de Matplotlib
        i: int
            Perfil indicat

        """
        txt_ruta = path.with_name(f"{self.file.name} - {self.channel.name} Perfil {i}.txt")
        x = line.get_xdata()
        y = line.get_ydata()

        np.savetxt(txt_ruta, np.column_stack((x, y)), fmt="%.3f")
