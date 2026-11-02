"""Rotacions, voltejaments i zoom de l'aplicació."""
from functools import partial
from operator import xor
from tkinter import Menu, messagebox
from typing import TYPE_CHECKING, Literal, TypedDict, cast

from drawing.mapdraw import update_data
from process.images import rotate_coords, transform_matrix
from window.builder import MapWindow
from window.widgets import Widget

from .base import BaseMenu

if TYPE_CHECKING:
    from classes.data import ChannelData, GeometryData, ObjectData, SpecData
    from classes.protocols import GestorProtocol
    from classes.views import FileView


class GestorImages(BaseMenu):
    """Menú que controla les rotacions i el zoom del mapa."""

    def _add_menu(self, menu: Menu) -> None:
        self.add_tab(text="Rotar en sentit horari", func=self.transform, kwargs={"rot": 1}, shortcut="Shift-R")
        self.add_tab(text="Rotar en sentit antihorari", func=self.transform, kwargs={"rot": 3}, shortcut="Shift-L")
        self.add_tab(text="Voltejar imatge", func=self.transform, kwargs={"flip": True}, shortcut="Shift-F")
        self.add_tab(text="Sincronitzar rotació", func=self._sync_rot)
        self.add_tab(text="Zoom manual", func=partial(ZoomManual, self))
        self.add_tab(text="Sincronitzar zoom", func=self._sync_zoom)
        self.add_tab()
        self.add_tab(text="Desfer zoom", func=self._base_zoom)

        menu.add_cascade(label="Operacions bàsiques", menu=self.submenu)

    def transform(self, rot: Literal[0, 1, 2, 3] = 0, *, flip: bool = False,
                          file: FileView | None = None) -> None:
        """Transforma tots els elements del fitxer corresponent sotmés a rotacions i voltejaments.

        Parameters
        ----------
        rot: Literal[0, 1, 2, 3] = 0
            Classe de rotació que es fa
        flip: bool = False
            Indica si la imatge s'ha de voltejar
        file: FileView | None = None
            Fitxer triat. Si és None, es pren el fitxer actual.

        """
        if file is None:
            file = self.current_file

        self.transform_geometry(file.geometry, rot=rot, flip=flip)
        self.transform_channels(file.channel, file.geometry.dim, rot=rot, flip=flip)
        self.transform_objects(file.objects, file.geometry.dim, rot=rot, flip=flip)

        update_data(file.mapview.image, file.current_channel.data, file.objects.mask)
        self.update_images(file)

    @staticmethod
    def transform_geometry(geometry: GeometryData, rot: Literal[0, 1, 2, 3] = 0, *, flip: bool = False) -> None:
        """Transforma la geometria del fitxer.

        Parameters
        ----------
        geometry: GeometryData
            Geometria del fitxer
        rot: Literal[0, 1, 2, 3] = 0
            Classe de rotació que es fa
        flip: bool = False
            Indica si la imatge s'ha de voltejar

        """
        geometry.rotation += rot if not geometry.flip else -rot

        if flip:
            geometry.flip = not geometry.flip

        if rot % 2:
            geometry.base_size = geometry.base_size[::-1]
            geometry.dim = geometry.dim[::-1]

        geometry.rotate_lims(rot, flip=flip)

    def transform_channels(self, channel: dict[str, ChannelData], dim: tuple[int, int],
                          rot: Literal[0, 1, 2, 3] = 0, *, flip: bool = False) -> None:
        """Transforma els canals del fitxer.

        Parameters
        ----------
        channel: dict[str, ChannelData]
            Canals del fitxer
        dim: tuple[int, int]
            Dimensions de la matriu
        rot: Literal[0, 1, 2, 3] = 0
            Classe de rotació que es fa
        flip: bool = False
            Indica si la imatge s'ha de voltejar

        """
        for ch in channel.values():
            ch.data = transform_matrix(ch.data, rot=rot, flip=flip)

            if ch.spectra is not None:
                self.transform_spectra(ch.spectra, dim, rot=rot, flip=flip)

    @staticmethod
    def transform_spectra(spectra: SpecData, dim: tuple[int, int],
                          rot: Literal[0, 1, 2, 3] = 0, *, flip: bool = False) -> None:
        """Transforma les matrius i els objectes espectrals.

        Parameters
        ----------
        spectra: SpecData
            Dades espectrals
        dim: tuple[int, int]
            Dimensions de la matriu
        rot: Literal[0, 1, 2, 3] = 0
            Classe de rotació que es fa
        flip: bool = False
            Indica si la imatge s'ha de voltejar

        """
        spectra.raw_ydata = transform_matrix(spectra.raw_ydata, rot=rot, flip=flip)
        spectra.coords = rotate_coords([spectra.coords], dim, rot=rot, flip=flip)[0]

        if spectra.bkgdata is not None:
            spectra.bkgdata = transform_matrix(spectra.bkgdata, rot=rot, flip=flip)

        for fit in spectra.fits.values():
            for peak in fit.peaks.values():
                for name, par in peak.params.items():
                    peak.params[name] = transform_matrix(par, rot=rot, flip=flip)

            fit.r2 = transform_matrix(fit.r2, rot=rot, flip=flip)

    @staticmethod
    def transform_objects(objects: ObjectData, dim: tuple[int, int],
                          rot: Literal[0, 1, 2, 3] = 0, *, flip: bool = False) -> None:
        """Transforma els objectes del fitxer.

        Parameters
        ----------
        objects: ObjectData
            Objectes del fitxer
        dim: tuple[int, int]
            Dimensions de la matriu
        rot: Literal[0, 1, 2, 3] = 0
            Classe de rotació que es fa
        flip: bool = False
            Indica si la imatge s'ha de voltejar

        """
        objects.mask = transform_matrix(objects.mask, rot=rot, flip=flip)

        for prof in objects.profiles.values():
            prof.line = rotate_coords(prof.line, dim, rot=rot, flip=flip)

    @staticmethod
    def update_images(file: FileView) -> None:
        """Actualitza la rotació sobre els objectes visuals i addicionals.

        Parameters
        ----------
        file: FileView
            Fitxer triat

        """
        file.mapview.refresh_geometry()
        file.mapview.image.set_extent((0, file.geometry.base_size[0], 0, file.geometry.base_size[1]))

        file.mapview.profiles.update()

        if file.geometry.size[0] != file.geometry.size[1]:
            file.mapview.resize()

    def _sync_rot(self) -> None:
        """Sincronitza la rotació del fitxer actual amb la resta de fitxers."""
        file = self.current_file

        for f in self.files.values():
            if f is not file:
                flip = xor(file.geometry.flip, f.geometry.flip)
                rotation = (file.geometry.rotation - f.geometry.rotation) % 4
                rot = cast("Literal[0, 1, 2, 3]", rotation if not f.geometry.flip else -rotation % 4)
                self.transform(rot=rot, flip=flip, file=f)

    def _sync_zoom(self) -> None:
        """Sincronitza els marges del mapa del fitxer actual amb la resta de fitxers."""
        file = self.current_file

        for f in self.files.values():
            if f.geometry.dim != file.geometry.dim and f.geometry.base_size != file.geometry.base_size:
                messagebox.showerror("Error", "Les dimensions dels arxius són diferents")
                return
            if f is not file:
                f.geometry.xylims = file.geometry.xylims
                f.mapview.refresh_geometry()

    def _base_zoom(self) -> None:
        """Recupera la mida base del fitxer."""
        self.current_file.mapview.base_size()


class ZoomWidgets(TypedDict):
    """Ginys de la classe ZoomManual."""

    left: Widget[float]
    right: Widget[float]
    bottom: Widget[float]
    top: Widget[float]


class ZoomManual(MapWindow):
    """Canvia el zoom de la imatge manualment."""

    widgets: ZoomWidgets

    def __init__(self, gestor: GestorProtocol) -> None:
        """Obri la finestra amb els ginys dels límits del mapa.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal

        """
        super().__init__(gestor, "Canviar límits")

    def _create_widgets(self) -> None:
        self.widgets = {
            "left": Widget(
                key="left",
                var_type=float,
                init=self.file.geometry.xlims[0],
                text="Left (Eix X):",
                widget="entry",
                setter=partial(self.set_lims, key="left")),
            "right": Widget(
                key="right",
                var_type=float,
                init=self.file.geometry.xlims[1],
                text="Right (Eix X):",
                widget="entry",
                setter=partial(self.set_lims, key="right")),
            "bottom": Widget(
                key="bottom",
                var_type=float,
                init=self.file.geometry.ylims[0],
                text="Bottom (Eix Y):",
                widget="entry",
                setter=partial(self.set_lims, key="bottom")),
            "top": Widget(
                key="top",
                var_type=float,
                init=self.file.geometry.ylims[1],
                text="Top (Eix Y):",
                widget="entry",
                setter=partial(self.set_lims, key="top")),
        }

    def set_lims(self, value: float, key: Literal["left", "right", "bottom", "top"]) -> None:
        """Actualitza un marge del mapa segons el valor triat.

        Parameters
        ----------
        value: float
            Nou valor
        key:  Literal["left", "right", "bottom", "top"]
            Límit escollit.

        """
        left = value if key == "left" else self.file.geometry.xlims[0]
        right = value if key == "right" else self.file.geometry.xlims[1]

        xlims = self._check_limits(left, right, self.file.geometry.base_size[0])
        self.widgets["left"].value.set(xlims[0])
        self.widgets["right"].value.set(xlims[1])

        bottom = value if key == "bottom" else self.file.geometry.ylims[0]
        top = value if key == "top" else self.file.geometry.ylims[1]

        ylims = self._check_limits(bottom, top, self.file.geometry.base_size[1])
        self.widgets["bottom"].value.set(ylims[0])
        self.widgets["top"].value.set(ylims[1])

        self.file.geometry.xylims = xlims, ylims
        self.file.mapview.refresh_geometry()
        self.file.mapview.resize()

    @staticmethod
    def _check_limits(lim_inf: float, lim_sup: float, size: float) -> tuple[float, float]:
        """Comprova que el límit inferior no és major que el superior.

        Parameters
        ----------
        lim_inf: float
            Valor del límit inferior
        lim_sup: float
            Valor del límit superior
        size: float
            Mida de la dimensió corresponent

        Returns
        -------
        lims: tuple[float, float]
            Nous límits

        Raises
        ------
        ValueError
            Si el límit inferior escrit és major que el superior actual

        """
        lim_inf = max(0, lim_inf)
        lim_sup = min(size, lim_sup)

        if lim_inf >= lim_sup:
            msg = "El límit superior ha de ser major que l'inferior."
            messagebox.showerror("Límits del mapa", msg)
            raise ValueError(msg)

        return lim_inf, lim_sup
