"""Classes base de les finestres flotants creades."""

from abc import ABC, abstractmethod
from tkinter import Toplevel
from tkinter.ttk import Frame
from typing import TYPE_CHECKING

from drawing import mapdraw
from drawing.plots import base_plot, create_canvas
from process.images import copy_figure
from window.mixin import MapMixin, SpecMixin
from window.widgets import Widget

if TYPE_CHECKING:
    import numpy as np
    from matplotlib.figure import Figure
    from numpy.typing import NDArray

    from classes.protocols import GestorProtocol, TkCanvasProtocol
    from window.widgets import GenericWidgets


def connect_canvas(main_frame: Frame, figure: Figure) -> tuple[Frame, TkCanvasProtocol]:
    """Connecta l'objecte canvas al requadre.

    Parameters
    ----------
    main_frame: Frame
        Requadre principal
    figure: Figure
        Figura que es connecta al requadre

    Returns
    -------
    frame: Frame
        Requadre creat sobre el requadre principal
    canvas: TkCanvasProtocol
        Objecte canvas creat sobre el requadre

    """
    frame = Frame(main_frame)
    frame.pack(side="right", fill="both", expand=True)

    canvas: TkCanvasProtocol = create_canvas(figure, frame=frame)
    canvas.get_tk_widget().pack(fill="both", expand=True)
    canvas.mpl_connect("key_press_event", lambda event: copy_figure(figure) if event.key == "ctrl+c" else None)

    canvas.draw()

    return frame, canvas


class BaseWindow(ABC):
    """Finestra base genèrica."""

    widgets: GenericWidgets

    def __init__(self, gestor: GestorProtocol, title: str) -> None:
        """Crea la finestra amb els ginys corresponents en columna.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal
        title: str
            Títol de la finestra

        Raises
        ------
        TypeError
            Si hi ha cap giny que no és de la classe Widget.

        """
        self.intersect = True
        self.update = True

        self.window = Toplevel(gestor.root)
        self.window.title(title)
        self.window.resizable(width=False, height=False)

        self.window.transient(gestor.root)
        self.window.focus_force()

        self.main_frame = Frame(self.window)
        self.main_frame.pack(padx=10, pady=10)

        self.control_frame = Frame(self.main_frame)
        self.control_frame.pack(side="left", fill="y", expand=True, padx=10, pady=10)

        self._create_widgets()

        for i, widget in enumerate(self.widgets.values()):
            if not isinstance(widget, Widget):
                msg = "La variable donada no és un objecte de tipus Widget."
                raise TypeError(msg)

            widget.add(self.control_frame, row=i, col=0)

    @abstractmethod
    def _create_widgets(self) -> None:
        """."""


class MapWindow(MapMixin, BaseWindow):
    """Finestra base genèrica amb els ginys de mapa estàndards."""

    def __init__(self, gestor: GestorProtocol, title: str) -> None:
        """Crea la finestra base i connecta els ginys de mapa.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal
        title: str
            Títol de la finestra

        """
        MapMixin.__init__(self, gestor)
        BaseWindow.__init__(self, gestor, title)


class SpecWindow(SpecMixin, BaseWindow):
    """Finestra base genèrica amb els ginys d'espectre estàndards."""

    def __init__(self, gestor: GestorProtocol, title: str) -> None:
        """Crea la finestra base i connecta els ginys d'espectre.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal
        title: str
            Títol de la finestra

        """
        SpecMixin.__init__(self, gestor.current_file.current_channel.spec)
        BaseWindow.__init__(self, gestor, title)


class ImageWindow(MapWindow):
    """Finestra amb un mapa addicional per a fer canvis temporals reversibles."""

    def __init__(self, gestor: GestorProtocol, title: str) -> None:
        """Crea la finestra base amb el mapa al requadre de la dreta.

        Parameters
        ----------
        gestor: GestorProtocol
            Protocol que conté les variables necessàries per a connectar-se amb l'aplicació principal
        title: str
            Títol de la finestra

        """
        super().__init__(gestor, title)

        self.update: bool = False
        ch = self.channel
        self.lims: list[float] = ch.lims
        self.z = ch.data
        self.units = ch.units

        self.figure, self.axis, self.image, self.cbar, self.cbar_lims =\
        mapdraw.create_map(data=self.z[self.region], lims=self.lims, cmap=ch.color.cmap, units=self.units,
                            size=self.file.geometry.size, cbar_colors=ch.color.lims, mask=self.mask[self.region])
        width, height = self.figure.get_size_inches()  # mida actual

        factor = 0.8
        self.figure.set_size_inches(width * factor, height * factor)
        self.scale = mapdraw.Scale(self.axis, color=ch.color.scale)
        self.axis.set_anchor("W")
        self.figure.subplots_adjust(left=0.02, right=0.8, top=1, bottom=0)

        self.image.set_clim(*self.lims)

        self.fig_frame, self.canvas = connect_canvas(self.main_frame, self.figure)
        self.canvas.get_tk_widget().configure({"bg": "#2e2e2e", "highlightthickness": 0, "bd": 0})

        dimensions = mapdraw.get_dimensions(self.axis, self.file.geometry.rect)
        mapdraw.set_dimensions(self.canvas, self.scale, self.cbar,
                               self.cbar_lims, self.file.geometry.rect, *dimensions)

    @property
    def region(self) -> tuple[slice[int, int, None], slice[int, int, None]]:
        """Retorna la regió actual mostrada del mapa seleccionat."""
        return self.file.geometry.region

    @property
    def mask(self) -> NDArray[np.bool_]:
        """Retorna la màscara booleana actual del mapa seleccionat."""
        return self.file.objects.mask

    def file_changed(self, file_key: str) -> None:
        """Actualitza la imatge en canviar de fitxer.

        Parameters
        ----------
        file_key: str
            Clau del fitxer

        """
        self.file = file_key
        self.channel_changed(self.channel_key)

        xsize, ysize = self.file.geometry.size
        self.image.set_extent((0, xsize, 0, ysize))
        self.axis.set_xlim(0, xsize)
        self.axis.set_ylim(0, ysize)
        self.scale.update(*self.file.geometry.xylims)

        dimensions = mapdraw.get_dimensions(self.axis, self.file.geometry.rect)
        mapdraw.set_dimensions(
            self.canvas,
            self.scale,
            self.cbar,
            self.cbar_lims,
            self.file.geometry.rect,
            *dimensions)

        self.canvas.draw_idle()

    def channel_changed(self, ch_key: str) -> None:
        """Actualitza la imatge en canviar de canal.

        Parameters
        ----------
        ch_key: str
            Clau del fitxer

        """
        self.channel = ch_key
        ch = self.channel
        self.z = ch.data
        self.lims = ch.lims
        self.units = ch.units

        self.cbar_lims["inf"].set_color(ch.color.lim_inf)
        self.cbar_lims["sup"].set_color(ch.color.lim_sup)

        mapdraw.update_map(
            self.image,
            self.z[self.region],
            ch.lims,
            ch.color.cmap,
            self.units,
            size=self.file.geometry.size,
            cbar=self.cbar,
            cbar_lims=self.cbar_lims,
            cbar_colors=ch.color.lims,
            mask=self.mask[self.region],
        )

        self.scale.color = ch.color.scale
        self.image.set_clim(*ch.lims)
        self.canvas.draw_idle()

    def update_fig(self, mask: NDArray[np.bool_] | None = None) -> None:
        """Actualitza la imatge de la finestra amb les màscares existents.

        mask: NDArray[np.bool_] | None = None
            Màscara booleana de la finestra

        """
        if mask is None:
            mask = self.mask

        mapdraw.update_data(self.image, self.z[self.region], mask[self.region])
        self.image.set_clim(*self.lims)
        self.image.set_clim(*self.lims)

        self.cbar_lims["inf"].set_text(f"{self.lims[0]} {self.units}")
        self.cbar_lims["sup"].set_text(f"{self.lims[1]} {self.units}")
        self.canvas.draw_idle()

    def apply(self) -> None:
        """Aplica permanentment els canvis realitzats al mapa principal."""
        if self.channel_key not in list(self.file.channel):
            return

        self.channel.data = self.z
        self.channel.lims = self.lims
        current_chframe = self.file.notebook.select()

        if current_chframe == str(self.file.channel_tabs[self.channel.name]):
            self.file.mapview.header.set_channel(self.channel)
            self.file.mapview.refresh_map()


class FigureWindow(MapWindow):
    """Finestra amb una figura addicional que mostra una estadística relacionada amb el mapa."""

    def __init__(self, gestor: GestorProtocol, nom: str, dim: tuple[float, float] = (4, 4)) -> None:
        """Crea la finestra amb la figura a la dreta."""
        super().__init__(gestor, nom)

        self.figure, self.axis = base_plot(dim=dim)
        self.figure.tight_layout()
        self.fig_frame, self.canvas = connect_canvas(self.main_frame, self.figure)

    @property
    def masked_data(self) -> NDArray[np.float32]:
        """Retorna les dades d'un canal filtrades amb la màscara booleana actual."""
        return self.channel.data[self.file.objects.mask]
