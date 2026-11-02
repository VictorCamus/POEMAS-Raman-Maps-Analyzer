"""Correccions, nivellaments i reescalaments de les matrius dels mapes."""
from functools import partial
from typing import TYPE_CHECKING, Literal

import numpy as np

from process import flatten as flat
from process.basics import set_lims
from window import ImageWindow
from window.mixin import MapWidgets
from window.widgets import Widget

from .base import BaseMenu

if TYPE_CHECKING:
    from tkinter import Menu

    from numpy.typing import NDArray

    from classes.protocols import GestorProtocol


class GestorCorr(BaseMenu):
    """Menú que gestiona l'aplanament, les correccions i el reescalament dels mapes."""

    def _add_menu(self, menu: Menu) -> None:
        self.add_tab(text="Reescalar", func=partial(RescaleMaps, self))
        self.add_tab(text="Establir la mediana a zero", func=self._remove_median)
        self.add_tab(text="Aplanar mapes", func=partial(LevelMaps, self))
        self.add_tab(text="Corregir enganxons", func=partial(RescaleMaps, self))

        menu.add_cascade(label="Correcció", menu=self.submenu)

    def _remove_median(self) -> None:
        """Reescala la mediana de la matriu a zero."""
        ch = self.current_file.current_channel
        x0, x1, y0, y1 = self.current_file.geometry.limit_pixels()

        ch.data -= np.median(ch.data[y0:y1, x0:x1])
        ch.update_lims()
        self.current_file.mapview.refresh_map(ch)


class RescaleWidgets(MapWidgets):
    """Ginys de la classe RescaleWidgets."""

    opt: Widget[str]
    value: Widget[float]
    apply: Widget[str]


class RescaleMaps(ImageWindow):
    """Reescala els valors de la matriu de dades del mapa."""

    widgets: RescaleWidgets

    def __init__(self, gestor: GestorProtocol) -> None:
        """Crea la finestra de treball amb la imatge provisional del mapa.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal

        """
        self.opt: Literal["sum", "mult", "norm"] = "sum"
        super().__init__(gestor, "Reescalar mapes")

    def _create_widgets(self) -> None:
        files = list(self.files.keys())
        channels = list(self.file.channel.keys())
        opts = {"Sumar": "sum", "Multiplicar": "mult", "Normalitzar": "norm"}

        self.widgets = {
            "file": Widget(
                key="file",
                var_type=str,
                init=self.file.name,
                text="Arxiu:",
                widget="cb",
                widget_kwargs={"options": files},
                setter=self.file_changed),
            "channel": Widget(
                key="channel",
                var_type=str,
                init=self.channel.name,
                text="Canal:",
                widget="cb",
                widget_kwargs={"options": channels},
                setter=self.channel_changed),
            "opt": Widget(
                key="opt",
                var_type=str,
                init=self.opt,
                text="Opcions:",
                widget="radiobutton",
                widget_kwargs={"options": opts},
                setter=self,
                mode="attr"),
            "value": Widget(
                key="value",
                var_type=float,
                init=0,
                text="Valor:",
                widget="entry",
                setter=self.reescale_ops),
            "apply": Widget(
                key="apply",
                init="Aplicar",
                widget="button",
                setter=self.apply),
        }

    def reescale_ops(self, value: float) -> None:
        """Reescala la matriu del canal actual segons el mètode seleccionat.

        Parameters
        ----------
        value: float
            Valor de reparametrització

        """
        opt = self.opt

        self.z = np.copy(self.channel.data)
        match opt:
            case "sum":
                self.z += value
                self.lims = [self.channel.lims[0] + value, self.channel.lims[1] + value]
            case "mult":
                self.z *= value
                self.lims = [self.channel.lims[0] * value, self.channel.lims[1] * value]
            case "norm":
                zmin, zmax = self.z.min(), self.z.max()
                self.z = (self.z - zmin) / (zmax - zmin)
                self.lims = [0, 1]

        self.update_fig()


class LevelWidgets(MapWidgets):
    """Ginys de la classe LevelWidgets."""

    level: Widget[str]
    linematch: Widget[str]
    direction: Widget[bool]
    apply: Widget[str]
    apply_all: Widget[str]


class LevelMaps(ImageWindow):
    """Aplana i corregeix la matriu de dades del mapes."""

    widgets: LevelWidgets

    def __init__(self, gestor: GestorProtocol) -> None:
        """Crea la finestra de treball amb la imatge temporal creada del mapa.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal

        """
        super().__init__(gestor, "Aplanar mapes")

        self._direction: bool = True
        self._level_mode: Literal["Cap", "General", "Cara dominant"] = "Cap"
        self._linematch_mode: Literal["Cap", "median", "median_diff", "modus", "match"] = "Cap"

    def _create_widgets(self) -> None:
        files = list(self.files.keys())
        channels = list(self.file.channel.keys())
        options_level = ["Cap", "General", "Cara dominant"]
        options_linematch = {
            "Cap": "Cap",
            "Mediana": "median",
            "Diferència de medianes": "median_diff",
            "Mòdul": "modus",
            "Comparació": "match",
        }

        self.widgets = {
            "file": Widget(
                key="file",
                var_type=str,
                init=self.file.name,
                text="Arxiu:",
                widget="cb",
                widget_kwargs={"options": files},
                setter=self.on_file_changed,
            ),
            "channel": Widget(
                key="channel",
                var_type=str,
                init=self.channel.name,
                text="Canal:",
                widget="cb",
                widget_kwargs={"options": channels},
                setter=self.on_channel_changed,
            ),
            "level": Widget(
                key="level",
                var_type=str,
                init="Cap",
                text="Aplanament:",
                widget="radiobutton",
                widget_kwargs={"options": options_level},
                setter=self.level,
            ),
            "linematch": Widget(
                key="linematch",
                var_type=str,
                init="Cap",
                text="Corregir línies:",
                widget="radiobutton",
                widget_kwargs={"options": options_linematch},
                setter=self.linematch,
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
            "apply": Widget(
                key="apply",
                init="Aplicar",
                widget="button",
                setter=self.apply,
            ),
            "apply_all": Widget(
                key="apply_all",
                init="Aplicar a tots",
                widget="button",
                widget_kwargs={"width": 12},
                setter=self.apply_all,
            ),
        }

    def on_file_changed(self, file_key: str) -> None:
        """Canvia de fitxer i recalcula com seria la transformació per al nou canal.

        Parameters
        ----------
        file_key: str
            Clau del canal

        """
        self.file_changed(file_key)
        self.update_map_window()

    def on_channel_changed(self, ch_key: str) -> None:
        """Canvia de canal i recalcula com seria la transformació per al nou canal.

        Parameters
        ----------
        ch_key: str
            Clau del canal

        """
        self.channel_changed(ch_key)
        self.update_map_window()

    def level(self, level: Literal["Cap", "General", "Cara dominant"]) -> None:
        """Indica quina classe d'aplanament es vol fer i actualitza el mapa.

        Parameters
        ----------
        level: Literal["Cap", "General", "Cara dominant"]
            Nivellament seleccionat

        """
        self._level_mode = level
        self.update_map_window()

    def linematch(self, linematch: Literal["Cap", "median", "median_diff", "modus", "match"]) -> None:
        """Indica quina classe de correcció de línies es vol fer i actualitza el mapa.

        Parameters
        ----------
        linematch: Literal["Cap", "median", "median_diff", "modus", "match"]
            Correcció seleccionada

        """
        self._linematch_mode = linematch
        self.update_map_window()

    def direction(self, *, direction: bool) -> None:
        """Indica sobre quina direcció es realitza la correcció de línies.

        direction: bool
            True: Horitzonal. False: Vertical

        """
        self._direction = direction
        self.update_map_window()

    def _level_map(self, z: NDArray[np.float32], dim: tuple[int, int]) -> NDArray[np.float32]:
        """Aplica el nivell seleccionat al mapa.

        Parameters
        ----------
        z: NDArray[np.float32]
            Matriu de dades
        dim: tuple[int, int]
            Dimensions de la matriu

        Returns
        -------
        z: NDArray[np.float32]
            Matriu transformada

        """
        match self._level_mode:
            case "General":
                return flat.level_plane(z, dim)
            case "Cara dominant":
                return flat.level_facet(z, dim)
            case "Cap":
                return z

    def _linematch_map(self, z: NDArray[np.float32], dim: tuple[int, int]) -> NDArray[np.float32]:
        """Aplica la correcció de línies seleccionada.

        Parameters
        ----------
        z: NDArray[np.float32]
            Matriu de dades
        dim: tuple[int, int]
            Dimensions de la matriu

        Returns
        -------
        z: NDArray[np.float32]
            Matriu transformada

        """
        if not self._direction:
            z = z.T
            dim = dim[::-1]

        ydim = dim[1]

        match self._linematch_mode:
            case "median":
                z = flat.linematch_median(z, ydim)
            case "median_diff":
                z = flat.linematch_median_diff(z, ydim)
            case "modus":
                z = flat.linematch_modus(z, ydim)
            case "match":
                z = flat.linematch_match(z, dim)

        if not self._direction:
            z = z.T

        return z

    def update_map_window(self, *, update: bool = True) -> None:
        """Actualitza el mapa temporal creat.

        Parameters
        ----------
        update: bool
            True: Actualitza. False: No actualitza

        """
        if self.channel_key not in self.file.channel:
            return

        z = self.channel.data.copy()
        dim = self.file.geometry.dim

        z = self._level_map(z, dim)
        z = self._linematch_map(z, dim)

        self.lims, self.z = set_lims(self.channel.name, z)

        if update:
            self.update_fig()

    def apply_all(self) -> None:
        """Propaga les transformacions a tots els fitxers."""
        curr_file = self.file_key
        for file in self.files.values():
            self.file = file.name
            self.update_map_window(update=False)
            self.apply()

        self.file = curr_file
        self.update_map_window()
