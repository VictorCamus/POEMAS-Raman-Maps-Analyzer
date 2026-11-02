"""Funcions de creació i actualització dels mapes de dades."""

from typing import TYPE_CHECKING, cast

import numpy as np
from matplotlib.figure import Figure

from process.basics import truncar_significatives

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.colorbar import Colorbar
    from matplotlib.image import AxesImage
    from matplotlib.lines import Line2D
    from matplotlib.text import Text
    from numpy.typing import NDArray

    from classes.protocols import ColorBool, InfSup, TkCanvasProtocol


def create_map(data: NDArray[np.float32], lims: list[float], cmap: str,
               units: str, cbar_colors: tuple[ColorBool, ColorBool],
               size: tuple[float, float], mask: NDArray[np.bool_] | None = None)\
               -> tuple[Figure, Axes, AxesImage, Colorbar, dict[InfSup, Text]]:
    """Creació del mapa de dades.

    Parameters
    ----------
    data: NDArray[np.float32]
        Dades de la matriu
    lims: list[float]
        Límits del mapa
    cmap: str
        Color del mapa
    units: str
        Unitats del mapa
    cbar_colors: tuple[ColorBool, ColorBool]
        Colors del text de cbar_lims
    size: tuple[float, float]
        Mida del mapa
    mask: NDArray[np.bool_] | None = None
        Màscara de les dades

    Returns
    -------
    figure: Figure
        Objecte figura del mapa
    axis: Axes
        Objecte eix del mapa
    image: AxesImage
        Objecte imatge del mapa
    cbar: Colorbar
        Objecte barra de color del mapa
    cbar_lims: dict[InfSup, Text]
        Text dels límits sobre la barra de colors

    """
    figure = Figure()
    figure.patch.set_alpha(0)
    figure.subplots_adjust(left=0.05, right=0.95, bottom=0.1, top=0.9)

    axis = figure.add_subplot(111)
    image = axis.imshow([[0]], origin="lower")

    cbar, cbar_lims = _create_cbar(figure, image)
    update_map(image, data, lims, cmap, units=units, cbar=cbar, cbar_lims=cbar_lims,
               cbar_colors=cbar_colors, size=size, mask=mask)
    _ajust_eixos(axis)

    return figure, axis, image, cbar, cbar_lims


def update_map(image: AxesImage, data: NDArray[np.float32], lims: list[float],
               cmap: str, units: str, cbar: Colorbar, cbar_lims: dict[InfSup, Text],
               cbar_colors: tuple[ColorBool, ColorBool],
               size: tuple[float, float], mask: NDArray[np.bool_] | None = None) -> None:
    """Actualització completa de tots els objectes del mapa.

    Parameters
    ----------
    image: AxesImage
        Objecte imatge del mapa
    data: NDArray[np.float32]
        Dades de la matriu
    lims: list[float]
        Límits del mapa
    cmap: str
        Color del mapa
    units: str
        Unitats del mapa
    cbar: Colorbar
        Objecte barra de color del mapa
    cbar_lims: dict[InfSup, Text]
        Text dels límits sobre la barra de colors
    cbar_colors: tuple[ColorBool, ColorBool] = ("w", "k")
        Colors del text de cbar_lims
    size: tuple[float, float]
        Mida del mapa
    mask: NDArray[np.bool_] | None = None
        Màscara de les dades

    """
    vmin, vmax = lims

    if cmap == "GRAIN":
        data = (data > 0).astype(int)  # Matriu binària: 1 si és un gra, 0 si no

    update_data(image, data, mask)
    image.set_cmap(cmap)
    image.set_clim(vmin, vmax)
    image.set_clim(vmin, vmax)

    image.set_extent((0, size[0], 0, size[1]))

    _update_cbar(cbar, lims, cbar_lims, units=units, cbar_colors=cbar_colors)  # Barra de colors.


def update_data(image: AxesImage, data: NDArray[np.float32],
                mask: NDArray[np.bool_] | None = None) -> None:
    """S'actualitzen les dades de la imatge i s'aplica cap màscara si hi ha.

    Parameters
    ----------
    image: AxesImage
        Objecte imatge del mapa
    data: NDArray[np.float32]
        Dades de la matriu
    mask: NDArray[np.bool_] | None = None
        Màscara de les dades

    """
    data = np.ma.masked_where(~mask, data) if mask is not None else data.copy()
    image.set_data(data)


def get_dimensions(axis: Axes, rect: float) -> tuple[float, float, tuple[float, float, float, float]]:
    """Torna les dimensions del mapa.

    Parameters
    ----------
    axis: Axes
        Objecte eix del mapa
    rect: float
        Factor de correcció associat a la proporció de dimensions del mapa

    Returns
    -------
    width: float
        Nova amplària de la imatge
    height: float
        Nova altura de la imatge
    cax_pos: tuple[float, float, float, float]
        Nova posició de la barra de colors

    """
    fig = cast("Figure", axis.figure)
    canvas = cast("TkCanvasProtocol", fig.canvas)
    canvas.draw()
    renderer = canvas.get_renderer()

    bbox = axis.get_window_extent(renderer=renderer)

    width, height = bbox.width, bbox.height

    fig_w, fig_h = map(float, fig.get_size_inches())
    dpi = fig.dpi
    fig_w *= dpi
    fig_h *= dpi

    cax_pos = ((bbox.x1 + 0.05 * width) / fig_w, bbox.y0 / fig_h,
                               0.12 * width / fig_w * float(np.sqrt(rect)), height / fig_h)

    return width, height, cax_pos


def set_dimensions(canvas: TkCanvasProtocol, scale: Scale,
                   cbar: Colorbar, cbar_lims: dict[InfSup, Text],
                   rect: float, width: float, height: float,
                   cax_pos: tuple[float, float, float, float]) -> None:
    """Estableix les dimensions del mapa.

    Parameters
    ----------
    canvas: FigureCanvasBase
        Objecte canvas associat al mapa
    scale: Escala
        Objecte escala del mapa
    cbar: Colorbar
        Objecte barra de colors del mapa
    cbar_lims: dict[InfSup, Text]
        Text dels límits sobre la barra de colors
    rect: float
        Factor de correcció associat a la proporció de dimensions del mapa
    width: float
        Amplària actual de la imatge
    height: float
        Altura actual de la imatge
    cax_pos: tuple[float, float, float, float]
        Posició actual de la barra de colors

    """
    scale.size(width, height, rect)

    cbar_lims["inf"].set_fontsize(height / 22)
    cbar_lims["sup"].set_fontsize(height / 22)
    cbar.ax.set_position(cax_pos)

    canvas.draw_idle()


def _create_cbar(figure: Figure, image: AxesImage) -> tuple[Colorbar, dict[InfSup, Text]]:

    cax = figure.add_axes((0.9775, 0.11, 0.08266666, 0.77777))
    cbar = figure.colorbar(image, cax=cax, orientation="vertical")
    cbar.set_ticks([])

    cbar_lims: dict[InfSup, Text] = {}
    cbar_lims["inf"] = cbar.ax.text(0.65, 0.02, "", ha="center", va="bottom", fontweight="bold",
                                    fontname="DejaVu Sans", rotation=90, transform=cbar.ax.transAxes)
    cbar_lims["sup"] = cbar.ax.text(0.65, 0.98, "", ha="center", va="top", fontweight="bold",
                                    fontname="DejaVu Sans", rotation=90, transform=cbar.ax.transAxes)

    return cbar, cbar_lims


def _update_cbar(cbar: Colorbar, lims: list[float], cbar_lims: dict[InfSup, Text],
                 units: str = "", cbar_colors: tuple[ColorBool, ColorBool] = ("w", "k"))\
                 -> None:

    vmin, vmax = lims  # Assignació directa
    color_inf, color_sup = cbar_colors
    cbar.ax.set_ylim(vmin, vmax)

    text_inf = f"{vmin:g} {units}" if units else f"{vmin:g}"
    text_sup = f"{vmax:g} {units}" if units else f"{vmax:g}"

    cbar_lims["inf"].set_text(text_inf)
    cbar_lims["sup"].set_text(text_sup)

    cbar_lims["inf"].set_color(color_inf)
    cbar_lims["sup"].set_color(color_sup)


def _ajust_eixos(ax: Axes) -> None:  # Elimina els eixos del mapa
    ax.set_axis_off()
    ax.set_aspect("equal")  # Quadra l'aspecte de la imatge sense deformar-la.
    ax.set_facecolor("none")  # Lleva el fons.
    ax.set_autoscale_on(False)


# ESCALA: Classe que afegeix l'escala al mapa. Per conveni estarà sempre en micres.
class Scale:
    """Gestiona l'escala gràfica d'un mapa."""

    def __init__(self, axis: Axes, color: ColorBool = "w") -> None:
        """Inicialitza l'escala gràfica.

        Parameters
        ----------
        axis: Axes
            Objecte eix del mapa corresponent.
        color: ColorBool = "w"
            Color de l'escala.

        """
        xdim, ydim, xtext, ytext, num = self._coords(axis.get_xlim(), axis.get_ylim())

        self.line: Line2D = axis.plot(xdim, ydim, color=color)[0]
        self.text: Text = axis.text(x=xtext, y=ytext, s=self._set_text(num), color=color,
                                  ha="center", fontname="Arial", weight="bold")

        self._color: ColorBool = color

    @property
    def color(self) -> ColorBool:
        """Color de l'escala."""
        return self._color

    @color.setter
    def color(self, value: ColorBool) -> None:
        self._color = value
        self.text.set_color(value)
        self.line.set_color(value)

    # Actualitza les coordenades de l'escala en cas de fer zoom o moure la imatge.
    def update(self, xlims: tuple[float, float], ylims: tuple[float, float]) -> None:
        """Actualitza la posició i la mida de l'escala.

        Parameters
        ----------
        xlims: tuple[float, float]
            Límits actuals de l'eix X.
        ylims: tuple[float, float]
            Límits actuals de l'eix Y.

        """
        xlims, ylims, xpos, ypos, num = self._coords(xlims, ylims)

        self.line.set_xdata(xlims)
        self.line.set_ydata(ylims)

        self.text.set_text(self._set_text(num))
        self.text.set_position((xpos, ypos))

    def size(self, width: float, height: float, rect: float) -> None:
        """Actualitza la mida visual de l'escala.

        Parameters
        ----------
        width: float
            Amplària de la línia d'escala.
        height: float
            Alçària de la línia d'escala.
        rect: float
            Factor de correcció associat a la proporció de dimensions del mapa.

        """
        self.text.set_fontsize(width / 20 * np.sqrt(rect))
        self.line.set_linewidth(height / 100 / np.sqrt(rect))

    @staticmethod
    def _set_text(num: float, units: str = r"$\mu$m", nsign: int = 2) -> str:
        """Genera el text que representa la longitud de l'escala.

        Returns
        -------
        text: str
            Text de l'escala

        """
        change_units = 0.5
        change_precision = 0.1

        if num <= change_units:
            units = "nm"
            if num <= change_precision:
                nsign = 1
            num *= 1e3

        final_num = truncar_significatives(num, nsign, cap_a="avall")

        return f"{final_num} {units}"

    # Calcula les coordenades on es posarà l'escala i el text.
    @staticmethod
    def _coords(xlims: tuple[float, float], ylims: tuple[float, float])\
                       -> tuple[tuple[float, float], tuple[float, float], float, float, float]:
        """Calcula les coordenades de l'escala i del seu text.

        Returns
        -------
        new_xlims: tuple[float, float]
            Nous límits X de l'escala
        new_ylims: tuple[float, float]
            Nous límits Y de l'escala
        xpos: float
            Posició X del text
        ypos: float
            Posició Y del text
        num: float
            Número d'escala que mostra el text

        """
        xmin, xmax = xlims
        ymin, ymax = ylims
        xsize = xmax - xmin
        ysize = ymax - ymin
        a = 2 * xsize
        num = a / 10

        # Escriu les coordenades de l'escala.
        x1 = 1 / 10 * xsize + xmin
        x2 = 3 / 10 * xsize + xmin
        y1 = 1 / 10 * ysize + ymin
        new_xlims = x1, x2
        new_ylims = y1, y1

        xpos = (x1 + x2) / 2
        ypos = 1.3 / 10 * ysize + ymin  # Escriu el text de l'escala.

        return new_xlims, new_ylims, xpos, ypos, num
